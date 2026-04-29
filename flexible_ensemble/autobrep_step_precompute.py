from __future__ import annotations

import argparse
import math
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .autobrep_fsq import (
    AutoBrepKeyMode,
    _bbox_from_world_points,
    _edge_face_incidence_to_face_edge_adj,
    _normalize_key,
    _prepare_edge_ncs,
    _prepare_face_ncs,
    build_autobrep_fsq_feature_table,
    select_autobrep_feature_columns,
)
from .utils import _load_dataframe


class AutoBrepStepPrecomputeError(RuntimeError):
    pass


@dataclass
class StepToNPZConfig:
    output_npz_dir: str
    face_grid_size: int = 32
    edge_grid_size: int = 32
    key_mode: AutoBrepKeyMode = "stem"
    heal_shape: bool = True
    skip_existing: bool = True
    strict: bool = False


@dataclass
class StepJob:
    source_value: Any
    merge_value: Any
    merge_key: str
    step_path: str


class _OccBackend(SimpleNamespace):
    pass


def _load_occ_backend() -> _OccBackend:
    """
    Lazy OCC backend import.

    Supports either OCP (cadquery/new OCC bindings) or pythonocc-core.
    The module is imported only when STEP preprocessing is actually used, so the
    main training pipeline keeps working without OCC installed.
    """

    # OCP first
    try:
        from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.STEPControl import STEPControl_Reader
        from OCP.ShapeFix import ShapeFix_Shape
        from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopoDS import TopoDS

        def cast_face(shape: Any) -> Any:
            for name in ("Face_s", "Face", "topods_Face"):
                fn = getattr(TopoDS, name, None)
                if fn is not None:
                    return fn(shape)
            return shape

        def cast_edge(shape: Any) -> Any:
            for name in ("Edge_s", "Edge", "topods_Edge"):
                fn = getattr(TopoDS, name, None)
                if fn is not None:
                    return fn(shape)
            return shape

        return _OccBackend(
            flavor="OCP",
            STEPControl_Reader=STEPControl_Reader,
            IFSelect_RetDone=IFSelect_RetDone,
            ShapeFix_Shape=ShapeFix_Shape,
            TopExp_Explorer=TopExp_Explorer,
            TopAbs_FACE=TopAbs_FACE,
            TopAbs_EDGE=TopAbs_EDGE,
            BRepAdaptor_Surface=BRepAdaptor_Surface,
            BRepAdaptor_Curve=BRepAdaptor_Curve,
            cast_face=cast_face,
            cast_edge=cast_edge,
        )
    except Exception:
        pass

    # pythonocc-core fallback
    try:
        from OCC.Core.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.ShapeFix import ShapeFix_Shape
        from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopoDS import topods_Edge, topods_Face

        return _OccBackend(
            flavor="pythonocc",
            STEPControl_Reader=STEPControl_Reader,
            IFSelect_RetDone=IFSelect_RetDone,
            ShapeFix_Shape=ShapeFix_Shape,
            TopExp_Explorer=TopExp_Explorer,
            TopAbs_FACE=TopAbs_FACE,
            TopAbs_EDGE=TopAbs_EDGE,
            BRepAdaptor_Surface=BRepAdaptor_Surface,
            BRepAdaptor_Curve=BRepAdaptor_Curve,
            cast_face=topods_Face,
            cast_edge=topods_Edge,
        )
    except Exception as e:
        raise AutoBrepStepPrecomputeError(
            "Для STEP→AutoBrep preprocessing нужен OCC backend: cadquery/OCP или pythonocc-core."
        ) from e


def _shape_hash(shape: Any, upper: int = 2_147_483_647) -> int:
    for name in ("HashCode", "hashCode"):
        fn = getattr(shape, name, None)
        if callable(fn):
            try:
                return int(fn(int(upper)))
            except TypeError:
                continue
    return int(hash(shape))


def _shapes_same(a: Any, b: Any) -> bool:
    for name in ("IsSame", "isSame"):
        fn = getattr(a, name, None)
        if callable(fn):
            try:
                return bool(fn(b))
            except Exception:
                break
    return _shape_hash(a) == _shape_hash(b)


def _pnt_xyz(pnt: Any) -> Tuple[float, float, float]:
    return float(pnt.X()), float(pnt.Y()), float(pnt.Z())


def _safe_param(v: Any, fallback: float) -> float:
    try:
        out = float(v)
    except Exception:
        return float(fallback)
    if not math.isfinite(out):
        return float(fallback)
    return out


def _sanitize_bounds(lo: float, hi: float, eps: float = 1e-6) -> Tuple[float, float]:
    lo = float(lo)
    hi = float(hi)
    if not math.isfinite(lo) or not math.isfinite(hi):
        raise ValueError(f"Non-finite parameter bounds: lo={lo}, hi={hi}")
    if hi < lo:
        lo, hi = hi, lo
    if abs(hi - lo) < eps:
        mid = (lo + hi) / 2.0
        lo = mid - eps
        hi = mid + eps
    return lo, hi


def _sample_face_points(face: Any, backend: _OccBackend, grid_size: int) -> np.ndarray:
    surf = backend.BRepAdaptor_Surface(face, True)
    umin = _safe_param(surf.FirstUParameter(), 0.0)
    umax = _safe_param(surf.LastUParameter(), 1.0)
    vmin = _safe_param(surf.FirstVParameter(), 0.0)
    vmax = _safe_param(surf.LastVParameter(), 1.0)
    umin, umax = _sanitize_bounds(umin, umax)
    vmin, vmax = _sanitize_bounds(vmin, vmax)

    u_grid = np.linspace(umin, umax, int(grid_size), dtype=np.float64)
    v_grid = np.linspace(vmin, vmax, int(grid_size), dtype=np.float64)
    out = np.empty((int(grid_size), int(grid_size), 3), dtype=np.float32)
    for iu, u in enumerate(u_grid):
        for iv, v in enumerate(v_grid):
            p = surf.Value(float(u), float(v))
            out[iu, iv, :] = _pnt_xyz(p)
    return out


def _sample_edge_points(edge: Any, backend: _OccBackend, grid_size: int) -> np.ndarray:
    curve = backend.BRepAdaptor_Curve(edge)
    umin = _safe_param(curve.FirstParameter(), 0.0)
    umax = _safe_param(curve.LastParameter(), 1.0)
    umin, umax = _sanitize_bounds(umin, umax)
    u_grid = np.linspace(umin, umax, int(grid_size), dtype=np.float64)
    out = np.empty((int(grid_size), 3), dtype=np.float32)
    for iu, u in enumerate(u_grid):
        p = curve.Value(float(u))
        out[iu, :] = _pnt_xyz(p)
    return out


def _read_step_shape(step_path: str, backend: _OccBackend, heal_shape: bool = True) -> Any:
    reader = backend.STEPControl_Reader()
    status = reader.ReadFile(str(step_path))
    if int(status) != int(backend.IFSelect_RetDone):
        raise AutoBrepStepPrecomputeError(f"STEP reader returned status={status} for file {step_path}")
    transferred = reader.TransferRoots()
    if int(transferred) <= 0:
        raise AutoBrepStepPrecomputeError(f"STEP reader did not transfer any roots for file {step_path}")
    shape = reader.OneShape()

    if heal_shape and getattr(backend, "ShapeFix_Shape", None) is not None:
        try:
            fixer = backend.ShapeFix_Shape(shape)
            fixer.Perform()
            shape = fixer.Shape()
        except Exception:
            # Healing is useful, but not mandatory.
            pass

    return shape


def _extract_faces_and_edges(shape: Any, backend: _OccBackend) -> Tuple[List[Any], List[Any], np.ndarray, int]:
    faces: List[Any] = []
    explorer = backend.TopExp_Explorer(shape, backend.TopAbs_FACE)
    while explorer.More():
        faces.append(backend.cast_face(explorer.Current()))
        explorer.Next()

    if not faces:
        raise AutoBrepStepPrecomputeError("В STEP не найдено ни одной грани")

    edges: List[Any] = []
    edge_faces: List[List[int]] = []
    hash_to_edge_indices: Dict[int, List[int]] = {}
    non_manifold_edges = 0

    for face_idx, face in enumerate(faces):
        edge_explorer = backend.TopExp_Explorer(face, backend.TopAbs_EDGE)
        local_seen: List[int] = []
        while edge_explorer.More():
            edge = backend.cast_edge(edge_explorer.Current())
            raw_hash = _shape_hash(edge)

            # Avoid counting the same edge twice on the same face.
            duplicate_on_face = False
            for prev_idx in local_seen:
                if _shapes_same(edge, edges[prev_idx]):
                    duplicate_on_face = True
                    break
            if duplicate_on_face:
                edge_explorer.Next()
                continue

            existing_idx: Optional[int] = None
            for idx in hash_to_edge_indices.get(raw_hash, []):
                if _shapes_same(edge, edges[idx]):
                    existing_idx = idx
                    break

            if existing_idx is None:
                existing_idx = len(edges)
                edges.append(edge)
                edge_faces.append([face_idx])
                hash_to_edge_indices.setdefault(raw_hash, []).append(existing_idx)
            else:
                if face_idx not in edge_faces[existing_idx]:
                    edge_faces[existing_idx].append(face_idx)
                    if len(edge_faces[existing_idx]) > 2:
                        non_manifold_edges += 1

            local_seen.append(existing_idx)
            edge_explorer.Next()

    incidence = np.full((len(edges), 2), fill_value=-1, dtype=np.int64)
    for edge_idx, incident_faces in enumerate(edge_faces):
        if not incident_faces:
            continue
        uniq = list(dict.fromkeys(int(v) for v in incident_faces))
        if len(uniq) > 2:
            uniq = uniq[:2]
        incidence[edge_idx, 0] = int(uniq[0])
        if len(uniq) >= 2:
            incidence[edge_idx, 1] = int(uniq[1])

    return faces, edges, incidence, int(non_manifold_edges)


def extract_step_to_autobrep_npz(
    step_path: str,
    output_npz_path: str,
    *,
    face_grid_size: int = 32,
    edge_grid_size: int = 32,
    heal_shape: bool = True,
) -> Dict[str, Any]:
    backend = _load_occ_backend()
    shape = _read_step_shape(step_path=step_path, backend=backend, heal_shape=heal_shape)
    faces, edges, edge_face_incidence, non_manifold_edges = _extract_faces_and_edges(shape=shape, backend=backend)

    face_points_world = np.stack(
        [_sample_face_points(face, backend=backend, grid_size=face_grid_size) for face in faces],
        axis=0,
    ).astype(np.float32)

    if edges:
        edge_points_world = np.stack(
            [_sample_edge_points(edge, backend=backend, grid_size=edge_grid_size) for edge in edges],
            axis=0,
        ).astype(np.float32)
    else:
        edge_points_world = np.zeros((0, int(edge_grid_size), 3), dtype=np.float32)

    face_bbox_world = (
        np.stack([_bbox_from_world_points(x) for x in face_points_world], axis=0).astype(np.float32)
        if len(face_points_world)
        else np.zeros((0, 6), dtype=np.float32)
    )
    edge_bbox_world = (
        np.stack([_bbox_from_world_points(x) for x in edge_points_world], axis=0).astype(np.float32)
        if len(edge_points_world)
        else np.zeros((0, 6), dtype=np.float32)
    )
    face_points_normalized = (
        np.stack([_prepare_face_ncs(x) for x in face_points_world], axis=0).astype(np.float32)
        if len(face_points_world)
        else np.zeros((0, int(face_grid_size), int(face_grid_size), 3), dtype=np.float32)
    )
    edge_points_normalized = (
        np.stack([_prepare_edge_ncs(x) for x in edge_points_world], axis=0).astype(np.float32)
        if len(edge_points_world)
        else np.zeros((0, int(edge_grid_size), 3), dtype=np.float32)
    )
    face_edge_incidence = _edge_face_incidence_to_face_edge_adj(
        edge_face_incidence=edge_face_incidence,
        num_faces=len(face_points_world),
    )

    out_path = Path(output_npz_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        str(out_path),
        face_points_world=face_points_world,
        edge_points_world=edge_points_world,
        edge_face_incidence=edge_face_incidence.astype(np.int64),
        face_bbox_world=face_bbox_world,
        edge_bbox_world=edge_bbox_world,
        face_points_normalized=face_points_normalized,
        edge_points_normalized=edge_points_normalized,
        face_edge_incidence=face_edge_incidence.astype(bool),
    )

    return {
        "npz_path": str(out_path),
        "face_count": int(len(faces)),
        "edge_count": int(len(edges)),
        "open_edge_fraction": float(np.mean(edge_face_incidence[:, 1] < 0)) if len(edge_face_incidence) else 0.0,
        "non_manifold_edge_count": int(non_manifold_edges),
        "occ_backend": str(backend.flavor),
    }


def _resolve_step_path(value: Any, step_root: Optional[str]) -> Path:
    raw = str(value).strip()
    if not raw:
        raise FileNotFoundError("Пустой путь к STEP")

    raw_path = Path(raw)

    candidate_names = [raw]
    if raw_path.suffix == "":
        candidate_names.extend([
            f"{raw}.stp",
            f"{raw}.step",
            f"{raw}.STP",
            f"{raw}.STEP",
        ])

    candidates: List[Path] = []

    for name in candidate_names:
        p = Path(name)
        if p.is_absolute():
            candidates.append(p)
        else:
            candidates.append(Path.cwd() / p)
            if step_root:
                candidates.append(Path(step_root) / p)

    for cand in candidates:
        if cand.exists():
            return cand.resolve()

    if step_root:
        root = Path(step_root)
        matches: List[Path] = []
        for name in candidate_names:
            matches.extend(root.rglob(Path(name).name))

        uniq = []
        seen = set()
        for m in matches:
            rp = str(m.resolve())
            if rp not in seen:
                seen.add(rp)
                uniq.append(m.resolve())

        if len(uniq) == 1:
            return uniq[0]
        if len(uniq) > 1:
            raise FileNotFoundError(
                f"Найдено несколько STEP-файлов для '{raw}': {[str(x) for x in uniq[:10]]}"
            )

    raise FileNotFoundError(f"Не найден STEP файл: {raw}")


def _unwrap_cell_value(value: Any, col_name: str) -> Any:
    if isinstance(value, pd.Series):
        vals = []
        for v in value.tolist():
            if pd.isna(v):
                continue
            s = str(v).strip()
            if s:
                vals.append(v)

        if not vals:
            return ""

        uniq = []
        seen = set()
        for v in vals:
            key = str(v)
            if key not in seen:
                seen.add(key)
                uniq.append(v)

        if len(uniq) > 1:
            raise ValueError(
                f"Для колонки '{col_name}' найдено несколько разных значений в одной строке: "
                f"{[str(x) for x in uniq]}"
            )

        return uniq[0]

    return value


def _collect_jobs_from_dataframe(
    df: pd.DataFrame,
    *,
    step_col: str,
    merge_col: str,
    step_root: Optional[str],
    key_mode: AutoBrepKeyMode,
) -> List[StepJob]:
    if step_col not in df.columns:
        raise ValueError(f"В таблице нет step_col='{step_col}'")
    if merge_col not in df.columns:
        raise ValueError(f"В таблице нет merge_col='{merge_col}'")

    dup_cols = df.columns[df.columns.duplicated()].tolist()
    if dup_cols:
        raise ValueError(
            f"В таблице есть дублирующиеся имена колонок: {dup_cols}"
        )

    cols = [step_col] if step_col == merge_col else [step_col, merge_col]

    jobs: List[StepJob] = []
    seen: Dict[str, str] = {}

    for _, row in df.loc[:, cols].drop_duplicates().iterrows():
        step_value = _unwrap_cell_value(row[step_col], step_col)
        merge_value = (
            _unwrap_cell_value(row[merge_col], merge_col)
            if merge_col in row.index
            else step_value
        )

        merge_key = _normalize_key(merge_value, key_mode)
        if not merge_key:
            continue

        step_path = str(_resolve_step_path(step_value, step_root=step_root))

        prev = seen.get(merge_key)
        if prev is not None and prev != step_path:
            raise ValueError(
                f"Для merge key '{merge_key}' найдены разные STEP-файлы: '{prev}' и '{step_path}'"
            )

        seen[merge_key] = step_path
        jobs.append(
            StepJob(
                source_value=step_value,
                merge_value=merge_value,
                merge_key=merge_key,
                step_path=step_path,
            )
        )

    return jobs


def _collect_jobs_from_directory(
    step_dir: str,
    *,
    key_mode: AutoBrepKeyMode,
    recursive: bool = True,
) -> List[StepJob]:
    root = Path(step_dir)
    if not root.exists():
        raise FileNotFoundError(f"Не найдена папка со STEP: {root}")

    exts = {".stp", ".step", ".STEP", ".STP"}
    iterator = root.rglob("*") if recursive else root.glob("*")
    paths = sorted(p for p in iterator if p.is_file() and p.suffix in exts)
    if not paths:
        raise FileNotFoundError(f"В папке {root} не найдено STEP-файлов")

    jobs: List[StepJob] = []
    seen: Dict[str, str] = {}
    for path in paths:
        merge_value = str(path)
        merge_key = _normalize_key(path.name, key_mode)
        prev = seen.get(merge_key)
        if prev is not None and prev != str(path):
            raise ValueError(
                f"Для merge key '{merge_key}' найдены разные STEP-файлы: '{prev}' и '{path}'"
            )
        seen[merge_key] = str(path)
        jobs.append(
            StepJob(
                source_value=str(path),
                merge_value=merge_value,
                merge_key=merge_key,
                step_path=str(path.resolve()),
            )
        )
    return jobs


def precompute_autobrep_npz_manifest(
    jobs: Sequence[StepJob],
    cfg: StepToNPZConfig,
) -> pd.DataFrame:
    output_root = Path(cfg.output_npz_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    errors: List[str] = []
    for job in jobs:
        out_path = output_root / f"{job.merge_key}.npz"
        row: Dict[str, Any] = {
            "source_value": job.source_value,
            "merge_value": job.merge_value,
            "__autobrep_merge_key__": job.merge_key,
            "step_path": job.step_path,
            "npz_path": str(out_path),
            "status": "ok",
            "error": None,
        }
        try:
            if out_path.exists() and cfg.skip_existing:
                row["status"] = "cached"
                with np.load(out_path, allow_pickle=False) as npz:
                    face_points_world = np.asarray(npz["face_points_world"])
                    edge_points_world = np.asarray(npz["edge_points_world"])
                    edge_face_incidence = np.asarray(npz["edge_face_incidence"])
                row.update(
                    {
                        "face_count": int(len(face_points_world)),
                        "edge_count": int(len(edge_points_world)),
                        "open_edge_fraction": float(np.mean(edge_face_incidence[:, 1] < 0)) if len(edge_face_incidence) else 0.0,
                        "non_manifold_edge_count": 0,
                        "occ_backend": None,
                    }
                )
            else:
                meta = extract_step_to_autobrep_npz(
                    step_path=job.step_path,
                    output_npz_path=str(out_path),
                    face_grid_size=cfg.face_grid_size,
                    edge_grid_size=cfg.edge_grid_size,
                    heal_shape=cfg.heal_shape,
                )
                row.update(meta)
        except Exception as e:
            row["status"] = "error"
            row["error"] = f"{type(e).__name__}: {e}"
            row["traceback_tail"] = "\n".join(traceback.format_exc().splitlines()[-8:])
            errors.append(job.merge_key)
            if cfg.strict:
                raise
        rows.append(row)

    manifest = pd.DataFrame(rows)
    if errors and cfg.strict:
        preview = errors[:10]
        raise AutoBrepStepPrecomputeError(
            f"STEP→NPZ preprocessing завершился с ошибками для {len(errors)} деталей. Примеры: {preview}"
        )
    return manifest


def _save_table(df: pd.DataFrame, path_str: str) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df.to_parquet(path, index=False)
        return
    if suffix == ".csv":
        df.to_csv(path, index=False)
        return
    if suffix in {".xlsx", ".xls"}:
        df.to_excel(path, index=False)
        return
    raise ValueError(f"Неподдерживаемый формат вывода: {suffix}")


def build_ready_autobrep_feature_table_from_manifest(
    manifest_df: pd.DataFrame,
    *,
    merge_col_name: str,
    npz_dir: str,
    surf_ckpt: str,
    edge_ckpt: str,
    ar_ckpt: Optional[str] = None,
    device: Optional[str] = None,
    batch_size: int = 128,
    key_mode: AutoBrepKeyMode = "stem",
    strict: bool = True,
    sequence_window_stride: Optional[int] = None,
    add_surface_embedding: bool = False,
    add_edge_embedding: bool = False,
    add_combined_embedding: bool = True,
    add_cad_embedding: bool = False,
    add_numeric_meta: bool = True,
) -> pd.DataFrame:
    ok_df = manifest_df.loc[manifest_df["status"].isin(["ok", "cached"])].copy()
    if ok_df.empty:
        raise AutoBrepStepPrecomputeError("В manifest нет успешных STEP→NPZ преобразований")

    part_keys = ok_df["__autobrep_merge_key__"].astype(str).tolist()
    if add_cad_embedding and not ar_ckpt:
        raise AutoBrepStepPrecomputeError("Для add_cad_embedding=True нужно задать ar_ckpt")

    features_df = build_autobrep_fsq_feature_table(
        part_keys=part_keys,
        npz_dir=npz_dir,
        surf_ckpt=surf_ckpt,
        edge_ckpt=edge_ckpt,
        ar_ckpt=ar_ckpt,
        device=device,
        batch_size=batch_size,
        key_mode=key_mode,
        strict=strict,
        sequence_window_stride=sequence_window_stride,
    )
    features_df = select_autobrep_feature_columns(
        features_df,
        add_surface_embedding=add_surface_embedding,
        add_edge_embedding=add_edge_embedding,
        add_combined_embedding=add_combined_embedding,
        add_cad_embedding=add_cad_embedding,
        add_numeric_meta=add_numeric_meta,
    )
    merge_map = ok_df[["__autobrep_merge_key__", "merge_value"]].drop_duplicates()
    ready = merge_map.merge(features_df, on="__autobrep_merge_key__", how="left", validate="one_to_one")
    ready = ready.rename(columns={"merge_value": merge_col_name})
    cols = [merge_col_name] + [c for c in ready.columns if c != merge_col_name]
    return ready[cols].copy()


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Precompute STEP -> AutoBrep NPZ and optional FSQ features")

    p.add_argument("--input-path", default=None, help="Таблица train/test с колонкой STEP")
    p.add_argument("--step-col", default="filename", help="Колонка с путями или именами STEP в input-path")
    p.add_argument("--merge-col", default=None, help="Колонка для будущего merge в train CLI; по умолчанию step-col")
    p.add_argument("--step-root", default=None, help="Корневая папка для относительных STEP-путей из таблицы")

    p.add_argument("--step-dir", default=None, help="Альтернатива input-path: просканировать папку со STEP")
    p.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)

    p.add_argument("--output-npz-dir", required=True)
    p.add_argument("--manifest-path", default=None, help="Куда сохранить manifest parquet/csv/xlsx")
    p.add_argument("--features-path", default=None, help="Опционально: сразу собрать готовую таблицу AutoBrep FSQ-признаков")

    p.add_argument("--surf-ckpt", default=None)
    p.add_argument("--edge-ckpt", default=None)
    p.add_argument("--ar-ckpt", default=None, help="Опциональный autoregressive checkpoint для pooled CAD embedding всей детали")
    p.add_argument("--device", default=None)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--sequence-window-stride", type=int, default=None, help="Stride окон при длинной CAD-последовательности; по умолчанию stride=max_seq")
    p.add_argument("--key-mode", choices=["exact", "basename", "stem", "lower", "lower_basename", "lower_stem"], default="stem")
    p.add_argument("--add-surface-emb", action=argparse.BooleanOptionalAction, default=False, help="Экспортировать отдельный autobrep_surf_fsq_emb")
    p.add_argument("--add-edge-emb", action=argparse.BooleanOptionalAction, default=False, help="Экспортировать отдельный autobrep_edge_fsq_emb")
    p.add_argument("--add-combined-emb", action=argparse.BooleanOptionalAction, default=True, help="Экспортировать объединённый autobrep_fsq_emb")
    p.add_argument("--add-cad-emb", action=argparse.BooleanOptionalAction, default=False, help="Экспортировать pooled embedding полной CAD-последовательности через AR")
    p.add_argument("--add-numeric-meta", action=argparse.BooleanOptionalAction, default=True, help="Экспортировать числовые AutoBrep мета-признаки")

    p.add_argument("--face-grid-size", type=int, default=32)
    p.add_argument("--edge-grid-size", type=int, default=32)
    p.add_argument("--heal-shape", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--skip-existing", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--strict", action=argparse.BooleanOptionalAction, default=False)
    return p


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_arg_parser().parse_args(argv)

    merge_col = args.merge_col or args.step_col
    if bool(args.input_path) == bool(args.step_dir):
        raise ValueError("Нужно задать ровно один источник: либо --input-path, либо --step-dir")

    if args.input_path:
        df = _load_dataframe(args.input_path)
        jobs = _collect_jobs_from_dataframe(
            df,
            step_col=args.step_col,
            merge_col=merge_col,
            step_root=args.step_root,
            key_mode=args.key_mode,
        )
    else:
        jobs = _collect_jobs_from_directory(
            args.step_dir,
            key_mode=args.key_mode,
            recursive=bool(args.recursive),
        )

    cfg = StepToNPZConfig(
        output_npz_dir=args.output_npz_dir,
        face_grid_size=args.face_grid_size,
        edge_grid_size=args.edge_grid_size,
        key_mode=args.key_mode,
        heal_shape=bool(args.heal_shape),
        skip_existing=bool(args.skip_existing),
        strict=bool(args.strict),
    )
    manifest = precompute_autobrep_npz_manifest(jobs=jobs, cfg=cfg)

    if args.manifest_path:
        _save_table(manifest, args.manifest_path)

    if args.features_path:
        if not args.surf_ckpt or not args.edge_ckpt:
            raise ValueError("Для --features-path нужно задать оба checkpoint: --surf-ckpt и --edge-ckpt")
        if bool(args.add_cad_emb) and not args.ar_ckpt:
            raise ValueError("Для --add-cad-emb нужно задать --ar-ckpt")
        features_df = build_ready_autobrep_feature_table_from_manifest(
            manifest_df=manifest,
            merge_col_name=merge_col,
            npz_dir=args.output_npz_dir,
            surf_ckpt=args.surf_ckpt,
            edge_ckpt=args.edge_ckpt,
            ar_ckpt=args.ar_ckpt,
            device=args.device,
            batch_size=args.batch_size,
            key_mode=args.key_mode,
            strict=bool(args.strict),
            sequence_window_stride=args.sequence_window_stride,
            add_surface_embedding=bool(args.add_surface_emb),
            add_edge_embedding=bool(args.add_edge_emb),
            add_combined_embedding=bool(args.add_combined_emb),
            add_cad_embedding=bool(args.add_cad_emb),
            add_numeric_meta=bool(args.add_numeric_meta),
        )
        _save_table(features_df, args.features_path)


if __name__ == "__main__":  # pragma: no cover
    main()
