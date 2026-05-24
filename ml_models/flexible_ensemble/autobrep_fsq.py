from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .utils import _load_dataframe

AutoBrepKeyMode = Literal[
    "exact",
    "basename",
    "stem",
    "lower",
    "lower_basename",
    "lower_stem",
]


@dataclass
class AutoBrepFSQRuntimeConfig:
    merge_col: str
    npz_dir: Optional[str] = None
    features_path: Optional[str] = None
    cache_path: Optional[str] = None
    surf_ckpt: Optional[str] = None
    edge_ckpt: Optional[str] = None
    ar_ckpt: Optional[str] = None
    device: Optional[str] = None
    batch_size: int = 128
    key_mode: AutoBrepKeyMode = "stem"
    strict: bool = True
    add_surface_embedding: bool = True
    add_edge_embedding: bool = True
    add_combined_embedding: bool = True
    add_cad_embedding: bool = False
    add_numeric_meta: bool = True
    sequence_window_stride: Optional[int] = None

    def enabled(self) -> bool:
        return bool(self.features_path or self.npz_dir)


class AutoBrepFSQError(RuntimeError):
    pass


def _normalize_key(value: Any, mode: AutoBrepKeyMode) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    p = Path(s)

    if mode == "exact":
        return s
    if mode == "basename":
        return p.name
    if mode == "stem":
        return p.stem
    if mode == "lower":
        return s.lower()
    if mode == "lower_basename":
        return p.name.lower()
    if mode == "lower_stem":
        return p.stem.lower()
    raise ValueError(f"Неизвестный key_mode: {mode}")


def _load_autobrep_utils():
    try:
        from autobrep import utils as autobrep_utils
        from autobrep.data.abc_data import ARDataModule
    except Exception as e:  # pragma: no cover - optional runtime dependency
        raise AutoBrepFSQError(
            "Для точного AutoBrep preprocessing нужен локальный пакет autobrep из core/src/autobrep."
        ) from e
    return autobrep_utils, ARDataModule


def _bbox_from_world_points(points_world: np.ndarray) -> np.ndarray:
    pts = np.asarray(points_world, dtype=np.float32).reshape(-1, 3)
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    return np.concatenate([mins, maxs], axis=0).astype(np.float32)


def _prepare_face_ncs(face_points_world: np.ndarray) -> np.ndarray:
    autobrep_utils, _ = _load_autobrep_utils()
    ncs = autobrep_utils.normalize_pc(np.asarray(face_points_world, dtype=np.float32))
    ncs = np.nan_to_num(np.asarray(ncs, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    ncs = autobrep_utils.sort_uv_grid(np.asarray(ncs, dtype=np.float32))
    return np.ascontiguousarray(ncs, dtype=np.float32)


def _prepare_edge_ncs(edge_points_world: np.ndarray) -> np.ndarray:
    autobrep_utils, _ = _load_autobrep_utils()
    ncs = autobrep_utils.normalize_pc(np.asarray(edge_points_world, dtype=np.float32)[np.newaxis, :, :])[0]
    ncs = np.nan_to_num(np.asarray(ncs, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    ncs = autobrep_utils.sort_u_grid(np.asarray(ncs, dtype=np.float32))
    return np.ascontiguousarray(ncs, dtype=np.float32)


def _prepare_face_tensor(face_points_world: np.ndarray) -> np.ndarray:
    ncs = _prepare_face_ncs(face_points_world)
    return np.transpose(ncs, (2, 0, 1)).astype(np.float32)


def _prepare_edge_tensor(edge_points_world: np.ndarray) -> np.ndarray:
    ncs = _prepare_edge_ncs(edge_points_world)
    return np.transpose(ncs, (1, 0)).astype(np.float32)


def _edge_face_incidence_to_face_edge_adj(edge_face_incidence: np.ndarray, num_faces: int) -> np.ndarray:
    incidence = np.asarray(edge_face_incidence, dtype=np.int64)
    adj = np.zeros((int(num_faces), int(len(incidence))), dtype=bool)
    for edge_idx, pair in enumerate(incidence):
        for face_idx in np.asarray(pair, dtype=np.int64).tolist():
            if int(face_idx) >= 0:
                adj[int(face_idx), edge_idx] = True
    return adj


def _prepare_npz_arrays(npz: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    face_points_world = np.asarray(npz["face_points_world"], dtype=np.float32)
    edge_points_world = np.asarray(npz["edge_points_world"], dtype=np.float32)
    edge_face_incidence = np.asarray(npz["edge_face_incidence"], dtype=np.int64)

    face_bbox_world = np.asarray(npz["face_bbox_world"], dtype=np.float32) if "face_bbox_world" in npz else (
        np.stack([_bbox_from_world_points(x) for x in face_points_world], axis=0).astype(np.float32)
        if len(face_points_world)
        else np.zeros((0, 6), dtype=np.float32)
    )
    edge_bbox_world = np.asarray(npz["edge_bbox_world"], dtype=np.float32) if "edge_bbox_world" in npz else (
        np.stack([_bbox_from_world_points(x) for x in edge_points_world], axis=0).astype(np.float32)
        if len(edge_points_world)
        else np.zeros((0, 6), dtype=np.float32)
    )
    face_points_normalized = np.asarray(npz["face_points_normalized"], dtype=np.float32) if "face_points_normalized" in npz else (
        np.stack([_prepare_face_ncs(x) for x in face_points_world], axis=0).astype(np.float32)
        if len(face_points_world)
        else np.zeros((0, 32, 32, 3), dtype=np.float32)
    )
    edge_points_normalized = np.asarray(npz["edge_points_normalized"], dtype=np.float32) if "edge_points_normalized" in npz else (
        np.stack([_prepare_edge_ncs(x) for x in edge_points_world], axis=0).astype(np.float32)
        if len(edge_points_world)
        else np.zeros((0, 32, 3), dtype=np.float32)
    )
    face_edge_adj = np.asarray(npz["face_edge_incidence"], dtype=bool) if "face_edge_incidence" in npz else _edge_face_incidence_to_face_edge_adj(
        edge_face_incidence=edge_face_incidence,
        num_faces=len(face_points_world),
    )
    return {
        "face_points_world": face_points_world,
        "edge_points_world": edge_points_world,
        "edge_face_incidence": edge_face_incidence,
        "face_bbox_world": face_bbox_world,
        "edge_bbox_world": edge_bbox_world,
        "face_points_normalized": face_points_normalized,
        "edge_points_normalized": edge_points_normalized,
        "face_edge_incidence": face_edge_adj,
    }

def _safe_entropy_from_ids(token_ids: np.ndarray, codebook_size: int) -> float:
    ids = np.asarray(token_ids).reshape(-1)
    if ids.size == 0:
        return 0.0
    ids = ids[(ids >= 0) & np.isfinite(ids)]
    if ids.size == 0:
        return 0.0
    values, counts = np.unique(ids.astype(np.int64), return_counts=True)
    probs = counts.astype(np.float64) / max(counts.sum(), 1)
    entropy = float(-(probs * np.log(probs + 1e-12)).sum())
    max_entropy = math.log(max(int(codebook_size), 2))
    if max_entropy <= 0:
        return 0.0
    return float(entropy / max_entropy)


def _safe_unique_ratio_from_ids(token_ids: np.ndarray, codebook_size: int) -> float:
    ids = np.asarray(token_ids).reshape(-1)
    if ids.size == 0:
        return 0.0
    ids = ids[(ids >= 0) & np.isfinite(ids)]
    if ids.size == 0:
        return 0.0
    nunique = int(np.unique(ids.astype(np.int64)).size)
    return float(nunique / max(int(codebook_size), 1))


def _build_position_hist_embedding(token_ids: np.ndarray, codebook_size: int) -> Tuple[List[float], Dict[str, float]]:
    ids = np.asarray(token_ids, dtype=np.int64)
    if ids.size == 0:
        return [0.0] * int(codebook_size), {
            "token_entropy_norm": 0.0,
            "token_unique_ratio": 0.0,
            "token_count": 0.0,
            "token_slot_count": 1.0,
        }

    if ids.ndim == 0:
        ids = ids.reshape(1, 1)
    elif ids.ndim == 1:
        ids = ids.reshape(-1, 1)
    else:
        ids = ids.reshape(ids.shape[0], -1)

    slot_hists: List[np.ndarray] = []
    for slot_idx in range(ids.shape[1]):
        slot_ids = ids[:, slot_idx]
        valid = slot_ids[(slot_ids >= 0) & (slot_ids < int(codebook_size))]
        hist = np.zeros(int(codebook_size), dtype=np.float32)
        if valid.size:
            binc = np.bincount(valid.astype(np.int64), minlength=int(codebook_size)).astype(np.float32)
            hist[: len(binc)] = binc[: int(codebook_size)]
            hist /= max(float(valid.size), 1.0)
        slot_hists.append(hist)

    emb = np.concatenate(slot_hists, axis=0).astype(np.float32)
    meta = {
        "token_entropy_norm": _safe_entropy_from_ids(ids, codebook_size=codebook_size),
        "token_unique_ratio": _safe_unique_ratio_from_ids(ids, codebook_size=codebook_size),
        "token_count": float(ids.size),
        "token_slot_count": float(ids.shape[1]),
    }
    return emb.astype(float).tolist(), meta


class _LazyAutoBrepFSQEncoder:
    def __init__(
        self,
        surf_ckpt: str,
        edge_ckpt: str,
        device: Optional[str] = None,
        ar_ckpt: Optional[str] = None,
        sequence_window_stride: Optional[int] = None,
    ) -> None:
        try:
            import torch
            from autobrep.models.autoregressive import AutoBrepModel
            from autobrep.models.vaes import EdgeFSQVAE, SurfaceFSQVAE
        except Exception as e:  # pragma: no cover - depends on optional environment
            raise AutoBrepFSQError(
                "Для извлечения AutoBrep-признаков нужно установить AutoBrep и его зависимости. "
                "Минимум: torch, pytorch-lightning, diffusers, x-transformers и локальный пакет autobrep."
            ) from e

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.surf_model = SurfaceFSQVAE.load_from_checkpoint(surf_ckpt, map_location=self.device).drop_decoder().eval().to(self.device)
        self.edge_model = EdgeFSQVAE.load_from_checkpoint(edge_ckpt, map_location=self.device).drop_decoder().eval().to(self.device)
        self.surf_codebook_size = int(getattr(self.surf_model, "codebook_size", 1000))
        self.edge_codebook_size = int(getattr(self.edge_model, "codebook_size", 1000))
        self.sequence_window_stride = sequence_window_stride
        self.ar_model = None
        self.ar_tokenizer = None

        if ar_ckpt:
            self.ar_model = AutoBrepModel.load_from_checkpoint(
                ar_ckpt,
                inference_mode=True,
                strict=False,
                map_location=self.device,
            ).eval().to(self.device)
            _, ARDataModule = _load_autobrep_utils()
            self.ar_tokenizer = ARDataModule(
                data_root=".",
                max_seq=1,
                bit=int(self.ar_model.hparams.bit),
                load_geom=False,
                load_meta=False,
                uv_invariant=True,
                surf_codebook_size=int(self.surf_codebook_size),
                edge_codebook_size=int(self.edge_codebook_size),
                max_face=int(self.ar_model.hparams.max_face),
                max_edge=1,
                batch_size=1,
                limit_train=1,
                limit_val=1,
                materialize=False,
                aug=False,
            )

    def encode_surfaces(self, face_world_list: Sequence[np.ndarray], batch_size: int) -> Tuple[np.ndarray, np.ndarray]:
        if len(face_world_list) == 0:
            return np.zeros((0, 4, 2, 2), dtype=np.float32), np.zeros((0, 2, 2), dtype=np.int64)

        tensors = np.stack([_prepare_face_tensor(x) for x in face_world_list], axis=0)
        all_q: List[np.ndarray] = []
        all_ids: List[np.ndarray] = []
        with self.torch.no_grad():
            for start in range(0, len(tensors), batch_size):
                batch = self.torch.from_numpy(tensors[start:start + batch_size]).to(self.device)
                q, ids = self.surf_model.encode(batch)
                all_q.append(q.detach().float().cpu().numpy())
                all_ids.append(ids.detach().cpu().numpy())
        return np.concatenate(all_q, axis=0), np.concatenate(all_ids, axis=0)

    def encode_edges(self, edge_world_list: Sequence[np.ndarray], batch_size: int) -> Tuple[np.ndarray, np.ndarray]:
        if len(edge_world_list) == 0:
            return np.zeros((0, 4, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.int64)

        tensors = np.stack([_prepare_edge_tensor(x) for x in edge_world_list], axis=0)
        all_q: List[np.ndarray] = []
        all_ids: List[np.ndarray] = []
        with self.torch.no_grad():
            for start in range(0, len(tensors), batch_size):
                batch = self.torch.from_numpy(tensors[start:start + batch_size]).to(self.device)
                q, ids = self.edge_model.encode(batch)
                all_q.append(q.detach().float().cpu().numpy())
                all_ids.append(ids.detach().cpu().numpy())
        return np.concatenate(all_q, axis=0), np.concatenate(all_ids, axis=0)


    def _build_full_cad_sequence(self, arrays: Dict[str, np.ndarray]) -> np.ndarray:
        if self.ar_model is None or self.ar_tokenizer is None:
            raise AutoBrepFSQError("Для AutoBrep CAD embedding нужно задать ar_ckpt")

        import networkx as nx
        from autobrep.data.token_mapping import MMTokenIndex

        face_ncs = np.asarray(arrays["face_points_normalized"], dtype=np.float32)
        edge_ncs = np.asarray(arrays["edge_points_normalized"], dtype=np.float32)
        face_pos = np.asarray(arrays["face_bbox_world"], dtype=np.float32)
        edge_pos = np.asarray(arrays["edge_bbox_world"], dtype=np.float32)
        face_edge_adj = np.asarray(arrays["face_edge_incidence"], dtype=bool)

        if len(face_ncs) > int(self.ar_model.hparams.max_face):
            raise AutoBrepFSQError(
                f"num_faces={len(face_ncs)} превышает max_face={int(self.ar_model.hparams.max_face)} из AR checkpoint"
            )

        face_graph = nx.Graph()
        face_graph.add_nodes_from(np.arange(len(face_ncs)))
        for col in face_edge_adj.T:
            attached = np.where(col)[0]
            if len(attached) == 2:
                face_graph.add_edge(int(attached[0]), int(attached[1]))

        cad_tokens, cad_face_indices = self.ar_tokenizer.cad_tokenization(
            face_pos,
            edge_pos,
            face_edge_adj,
            face_graph,
            [],
        )

        full_seq = np.array([MMTokenIndex.BOS.value] + cad_tokens + [MMTokenIndex.EOS.value], dtype=np.int64)
        remap = {
            x + self.ar_tokenizer.FLAG_PAD: y + self.ar_tokenizer.FLAG_PAD
            for x, y in zip(cad_face_indices, np.arange(len(cad_face_indices)))
        }
        if remap:
            full_seq = np.array([remap.get(int(x), int(x)) for x in full_seq], dtype=np.int64)

        level_idx = np.where(full_seq == MMTokenIndex.BOL.value)[0]
        level_tokens = np.split(full_seq, level_idx)
        updated_tokens: List[int] = []
        for i, (pre_level, cur_level) in enumerate(zip(level_tokens[:-1], level_tokens[1:])):
            cur_face_ids = cur_level[(cur_level >= self.ar_tokenizer.FLAG_PAD) & (cur_level < self.ar_tokenizer.FLAG_PAD + self.ar_tokenizer.ID_PAD)]
            prev_face_ids = pre_level[(pre_level >= self.ar_tokenizer.FLAG_PAD) & (pre_level < self.ar_tokenizer.FLAG_PAD + self.ar_tokenizer.ID_PAD)]
            if i >= 1:
                ppre_level = level_tokens[i - 1]
                pprev_face_ids = ppre_level[(ppre_level >= self.ar_tokenizer.FLAG_PAD) & (ppre_level < self.ar_tokenizer.FLAG_PAD + self.ar_tokenizer.ID_PAD)]
                prev_face_ids = np.array([x for x in prev_face_ids if x not in pprev_face_ids], dtype=np.int64)
            level_faces = np.sort(np.unique(np.concatenate((prev_face_ids, cur_face_ids)))) if (len(prev_face_ids) or len(cur_face_ids)) else np.array([], dtype=np.int64)
            remap_level = {x: y + self.ar_tokenizer.FLAG_PAD for x, y in zip(level_faces, np.arange(len(level_faces)))}
            cur_level = np.array([remap_level.get(int(x), int(x)) for x in cur_level], dtype=np.int64)
            bof_positions = np.where(cur_level == MMTokenIndex.BOF.value)[0] + 1
            bof_positions = bof_positions[bof_positions < len(cur_level)]
            cur_level[bof_positions] = -1
            updated_tokens += list(cur_level[cur_level > 0])

        return np.asarray(list(level_tokens[0]) + updated_tokens, dtype=np.int64)

    def _inject_fsq_codes_into_sequence(self, token_seq: np.ndarray, face_ncs: np.ndarray, edge_ncs: np.ndarray) -> np.ndarray:
        if self.ar_model is None:
            raise AutoBrepFSQError("Для AutoBrep CAD embedding нужно задать ar_ckpt")
        with self.torch.no_grad():
            face_tensor = self.torch.from_numpy(np.asarray(face_ncs, dtype=np.float32)).to(self.device)
            edge_tensor = self.torch.from_numpy(np.asarray(edge_ncs, dtype=np.float32)).to(self.device)
            if face_tensor.numel() == 0:
                surf_id = self.torch.zeros((0, 4), dtype=self.torch.long, device=self.device)
            else:
                _, surf_id = self.surf_model.encode(face_tensor.permute(0, 3, 1, 2))
                surf_id = surf_id.flatten(-2, -1).long()
            if edge_tensor.numel() == 0:
                edge_id = self.torch.zeros((0, 2), dtype=self.torch.long, device=self.device)
            else:
                _, edge_id = self.edge_model.encode(edge_tensor.permute(0, 2, 1))
                edge_id = edge_id.long()

            token = self.torch.as_tensor(np.asarray(token_seq, dtype=np.int64), dtype=self.torch.long, device=self.device)
            batch_data = -self.torch.ones((len(token), 4), dtype=self.torch.long, device=self.device)
            batch_data[:, 0] = token

            face_z_indices = (token >= self.ar_model.face_z_pad) & (token < self.ar_model.edge_z_pad)
            if bool(face_z_indices.any()):
                batch_data[face_z_indices] = (
                    surf_id[token[face_z_indices] - self.ar_model.face_z_pad] + self.ar_model.face_z_pad
                )

            edge_z_indices = token >= self.ar_model.edge_z_pad
            if bool(edge_z_indices.any()):
                batch_data[edge_z_indices, :2] = edge_id[
                    token[edge_z_indices] - self.ar_model.edge_z_pad
                ] + (self.ar_model.face_z_pad + self.ar_model.hparams.surf_codebook_size)

            batch_data = batch_data.flatten()
            batch_data = batch_data[batch_data >= 0]
            return batch_data.detach().cpu().numpy().astype(np.int64)

    def encode_cad_embedding(self, arrays: Dict[str, np.ndarray]) -> Tuple[List[float], Dict[str, float]]:
        if self.ar_model is None:
            raise AutoBrepFSQError("Для AutoBrep CAD embedding нужно задать ar_ckpt")

        token_seq = self._build_full_cad_sequence(arrays)
        token_seq = self._inject_fsq_codes_into_sequence(
            token_seq,
            face_ncs=np.asarray(arrays["face_points_normalized"], dtype=np.float32),
            edge_ncs=np.asarray(arrays["edge_points_normalized"], dtype=np.float32),
        )

        max_seq = int(getattr(self.ar_model.hparams, "max_seq", len(token_seq)))
        stride = int(self.sequence_window_stride or max_seq)
        stride = max(stride, 1)
        pooled_chunks: List[Any] = []
        chunk_sizes: List[int] = []
        with self.torch.no_grad():
            for start in range(0, len(token_seq), stride):
                window = token_seq[start:start + max_seq]
                if len(window) == 0:
                    continue
                batch = self.torch.from_numpy(window.astype(np.int64))[None].to(self.device)
                chunk_emb = self.ar_model.cad_gpt.ar_decoder.net(batch, return_embeddings=True)
                if isinstance(chunk_emb, tuple):
                    chunk_emb = chunk_emb[0]
                chunk_emb = chunk_emb.float()
                last_token_emb = chunk_emb[:, int(len(window)) - 1, :]
                pooled_chunks.append(last_token_emb.squeeze(0).detach().cpu())
                chunk_sizes.append(int(len(window)))
        if not pooled_chunks:
            return [], {"token_count": 0.0, "window_count": 0.0}

        pooled = self.torch.stack(pooled_chunks, dim=0)
        weights = self.torch.tensor(chunk_sizes, dtype=pooled.dtype).unsqueeze(1)
        pooled = (pooled * weights).sum(dim=0) / weights.sum()
        meta = {"token_count": float(len(token_seq)), "window_count": float(len(pooled_chunks))}
        return pooled.numpy().astype(float).tolist(), meta


def _extract_single_npz_features(npz_path: Path, encoder: _LazyAutoBrepFSQEncoder, batch_size: int) -> Dict[str, Any]:
    with np.load(npz_path, allow_pickle=False) as npz:
        arrays = _prepare_npz_arrays(npz)

    face_points_world = arrays["face_points_world"]
    edge_points_world = arrays["edge_points_world"]
    edge_face_incidence = arrays["edge_face_incidence"]

    surf_quant, surf_ids = encoder.encode_surfaces(list(face_points_world), batch_size=batch_size)
    edge_quant, edge_ids = encoder.encode_edges(list(edge_points_world), batch_size=batch_size)

    surf_emb, surf_meta = _build_position_hist_embedding(surf_ids, encoder.surf_codebook_size)
    edge_emb, edge_meta = _build_position_hist_embedding(edge_ids, encoder.edge_codebook_size)

    combined_emb = np.concatenate([
        np.asarray(surf_emb, dtype=np.float32),
        np.asarray(edge_emb, dtype=np.float32),
    ]).astype(float).tolist()

    cad_emb: List[float] = []
    cad_meta: Dict[str, float] = {"token_count": 0.0}
    cad_ok = 1.0

    if encoder.ar_model is not None:
        try:
            cad_emb, cad_meta = encoder.encode_cad_embedding(arrays)
        except AutoBrepFSQError:
            cad_ok = 0.0
            cad_dim = int(getattr(encoder.ar_model.hparams, "dim", 768))
            cad_emb = [0.0] * cad_dim
            cad_meta = {"token_count": 0.0}

    bbox_face_sizes = np.asarray(arrays["face_bbox_world"], dtype=np.float32)
    bbox_face_sizes = bbox_face_sizes[:, 3:] - bbox_face_sizes[:, :3] if len(bbox_face_sizes) else np.zeros((0, 3), dtype=np.float32)
    bbox_edge_sizes = np.asarray(arrays["edge_bbox_world"], dtype=np.float32)
    bbox_edge_sizes = bbox_edge_sizes[:, 3:] - bbox_edge_sizes[:, :3] if len(bbox_edge_sizes) else np.zeros((0, 3), dtype=np.float32)
 
    out: Dict[str, Any] = {
        "autobrep_cad_ok": float(cad_ok),
        "autobrep_surf_fsq_emb": surf_emb,
        "autobrep_edge_fsq_emb": edge_emb,
        "autobrep_fsq_emb": combined_emb,
        "autobrep_cad_emb": cad_emb,
        "autobrep_face_count": int(len(face_points_world)),
        "autobrep_edge_count": int(len(edge_points_world)),
        "autobrep_open_edge_fraction": float(np.mean(edge_face_incidence[:, 1] < 0)) if len(edge_face_incidence) else 0.0,
        "autobrep_surf_token_entropy": float(surf_meta["token_entropy_norm"]),
        "autobrep_edge_token_entropy": float(edge_meta["token_entropy_norm"]),
        "autobrep_surf_token_unique_ratio": float(surf_meta["token_unique_ratio"]),
        "autobrep_edge_token_unique_ratio": float(edge_meta["token_unique_ratio"]),
        "autobrep_cad_token_count": float(cad_meta.get("token_count", 0.0)),
        "autobrep_cad_window_count": float(cad_meta.get("window_count", 0.0)),
        "autobrep_face_bbox_mean_x": float(bbox_face_sizes[:, 0].mean()) if len(bbox_face_sizes) else 0.0,
        "autobrep_face_bbox_mean_y": float(bbox_face_sizes[:, 1].mean()) if len(bbox_face_sizes) else 0.0,
        "autobrep_face_bbox_mean_z": float(bbox_face_sizes[:, 2].mean()) if len(bbox_face_sizes) else 0.0,
        "autobrep_edge_bbox_mean_x": float(bbox_edge_sizes[:, 0].mean()) if len(bbox_edge_sizes) else 0.0,
        "autobrep_edge_bbox_mean_y": float(bbox_edge_sizes[:, 1].mean()) if len(bbox_edge_sizes) else 0.0,
        "autobrep_edge_bbox_mean_z": float(bbox_edge_sizes[:, 2].mean()) if len(bbox_edge_sizes) else 0.0,
    }
    return out


AUTOBREP_EMBEDDING_COLUMNS: List[str] = [
    "autobrep_surf_fsq_emb",
    "autobrep_edge_fsq_emb",
    "autobrep_fsq_emb",
    "autobrep_cad_emb",
]

AUTOBREP_NUMERIC_COLUMNS: List[str] = [
    "autobrep_cad_ok",
    "autobrep_face_count",
    "autobrep_edge_count",
    "autobrep_open_edge_fraction",
    "autobrep_surf_token_entropy",
    "autobrep_edge_token_entropy",
    "autobrep_surf_token_unique_ratio",
    "autobrep_edge_token_unique_ratio",
    "autobrep_cad_token_count",
    "autobrep_cad_window_count",
    "autobrep_face_bbox_mean_x",
    "autobrep_face_bbox_mean_y",
    "autobrep_face_bbox_mean_z",
    "autobrep_edge_bbox_mean_x",
    "autobrep_edge_bbox_mean_y",
    "autobrep_edge_bbox_mean_z",
]


def _save_feature_table(df: pd.DataFrame, path_str: str) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df.to_parquet(path, index=False)
        return
    if suffix in {".xlsx", ".xls"}:
        df.to_excel(path, index=False)
        return
    if suffix == ".csv":
        df.to_csv(path, index=False)
        return
    raise ValueError(f"Неподдерживаемый формат файла AutoBrep features: {suffix}")


def _build_npz_index(npz_dir: str, key_mode: AutoBrepKeyMode) -> Dict[str, Path]:
    root = Path(npz_dir)
    if not root.exists():
        raise FileNotFoundError(f"Не найдена папка с AutoBrep NPZ: {root}")
    paths = sorted(root.rglob("*.npz"))
    if not paths:
        raise FileNotFoundError(f"В папке {root} не найдено ни одного .npz")

    index: Dict[str, Path] = {}
    for path in paths:
        key = _normalize_key(path.name, mode=key_mode)
        if key in index:
            raise ValueError(f"Дублирующийся AutoBrep key={key} в папке {root}")
        index[key] = path
    return index


def build_autobrep_fsq_feature_table(
    part_keys: Sequence[Any],
    npz_dir: str,
    surf_ckpt: str,
    edge_ckpt: str,
    *,
    ar_ckpt: Optional[str] = None,
    device: Optional[str] = None,
    batch_size: int = 128,
    key_mode: AutoBrepKeyMode = "stem",
    strict: bool = True,
    sequence_window_stride: Optional[int] = None,
) -> pd.DataFrame:
    encoder = _LazyAutoBrepFSQEncoder(
        surf_ckpt=surf_ckpt,
        edge_ckpt=edge_ckpt,
        ar_ckpt=ar_ckpt,
        device=device,
        sequence_window_stride=sequence_window_stride,
    )    
    npz_index = _build_npz_index(npz_dir=npz_dir, key_mode=key_mode)

    rows: List[Dict[str, Any]] = []
    missing: List[str] = []
    seen: set[str] = set()
    for raw_key in part_keys:
        norm_key = _normalize_key(raw_key, mode=key_mode)
        if not norm_key or norm_key in seen:
            continue
        seen.add(norm_key)
        npz_path = npz_index.get(norm_key)
        if npz_path is None:
            missing.append(str(raw_key))
            continue
        row = {"__autobrep_merge_key__": norm_key}
        row.update(_extract_single_npz_features(npz_path=npz_path, encoder=encoder, batch_size=batch_size))
        rows.append(row)

    if missing and strict:
        preview = missing[:10]
        raise AutoBrepFSQError(
            f"Не найдены AutoBrep NPZ для {len(missing)} деталей. Примеры: {preview}"
        )

    return pd.DataFrame(rows)


def load_or_build_autobrep_fsq_features(
    part_keys: Sequence[Any],
    cfg: AutoBrepFSQRuntimeConfig,
) -> pd.DataFrame:
    if cfg.features_path:
        df = _load_dataframe(cfg.features_path)
        if "__autobrep_merge_key__" not in df.columns:
            if cfg.merge_col in df.columns:
                df = df.copy()
                df["__autobrep_merge_key__"] = df[cfg.merge_col].map(lambda x: _normalize_key(x, cfg.key_mode))
            else:
                raise ValueError(
                    "В AutoBrep features-файле должна быть колонка __autobrep_merge_key__ "
                    f"или колонка merge key '{cfg.merge_col}'."
                )
        return df

    if cfg.cache_path and os.path.exists(cfg.cache_path):
        df = _load_dataframe(cfg.cache_path)
        if "__autobrep_merge_key__" not in df.columns:
            raise ValueError("В закэшированном AutoBrep features-файле отсутствует __autobrep_merge_key__")
        return df

    if not cfg.npz_dir:
        raise ValueError("Для AutoBrep FSQ extraction нужно задать npz_dir или features_path")
    if not cfg.surf_ckpt or not cfg.edge_ckpt:
        raise ValueError("Для AutoBrep extraction нужно задать оба checkpoint: surf_ckpt и edge_ckpt")
    if cfg.add_cad_embedding and not cfg.ar_ckpt:
        raise ValueError("Для AutoBrep CAD embedding нужно задать ar_ckpt")

    df = build_autobrep_fsq_feature_table(
        part_keys=part_keys,
        npz_dir=cfg.npz_dir,
        surf_ckpt=cfg.surf_ckpt,
        edge_ckpt=cfg.edge_ckpt,
        ar_ckpt=cfg.ar_ckpt,
        device=cfg.device,
        batch_size=cfg.batch_size,
        key_mode=cfg.key_mode,
        strict=cfg.strict,
        sequence_window_stride=cfg.sequence_window_stride,
    )
    if cfg.cache_path:
        _save_feature_table(df, cfg.cache_path)
    return df


def select_autobrep_feature_columns(
    features_df: pd.DataFrame,
    *,
    add_surface_embedding: bool = True,
    add_edge_embedding: bool = True,
    add_combined_embedding: bool = True,
    add_cad_embedding: bool = False,
    add_numeric_meta: bool = True,
) -> pd.DataFrame:
    if features_df.empty:
        raise AutoBrepFSQError("AutoBrep features dataframe пуст")

    features_df = features_df.copy()
    features_df["__autobrep_merge_key__"] = features_df["__autobrep_merge_key__"].astype(str)

    keep_cols: List[str] = ["__autobrep_merge_key__"]
    if add_cad_embedding and "autobrep_cad_emb" in features_df.columns:
        keep_cols.append("autobrep_cad_emb")

    if add_combined_embedding and "autobrep_fsq_emb" in features_df.columns:
        keep_cols.append("autobrep_fsq_emb")
    else:
        if add_surface_embedding and "autobrep_surf_fsq_emb" in features_df.columns:
            keep_cols.append("autobrep_surf_fsq_emb")
        if add_edge_embedding and "autobrep_edge_fsq_emb" in features_df.columns:
            keep_cols.append("autobrep_edge_fsq_emb")

    if add_numeric_meta:
        keep_cols.extend(
            [
                c
                for c in AUTOBREP_NUMERIC_COLUMNS
                if c in features_df.columns and c not in keep_cols and c != "autobrep_cad_emb"
            ]
        )

    return features_df[keep_cols].drop_duplicates(subset=["__autobrep_merge_key__"], keep="first")


def _sanitize_features_df(features_df: pd.DataFrame) -> pd.DataFrame:
    return select_autobrep_feature_columns(
        features_df,
        add_surface_embedding=True,
        add_edge_embedding=True,
        add_combined_embedding=True,
        add_cad_embedding=True,
        add_numeric_meta=True,
    )



def _presence_column(df: pd.DataFrame) -> Optional[str]:
    for col in AUTOBREP_EMBEDDING_COLUMNS + AUTOBREP_NUMERIC_COLUMNS:
        if col in df.columns:
            return col
    return None



def _merge_single_frame_with_features(
    df: pd.DataFrame,
    *,
    split_name: str,
    features_df: pd.DataFrame,
    cfg: AutoBrepFSQRuntimeConfig,
) -> pd.DataFrame:
    if cfg.merge_col not in df.columns:
        raise ValueError(f"В {split_name}_df отсутствует merge column для AutoBrep: {cfg.merge_col}")

    tmp = df.copy()
    tmp["__autobrep_merge_key__"] = tmp[cfg.merge_col].map(lambda x: _normalize_key(x, cfg.key_mode))
    out = tmp.merge(features_df, on="__autobrep_merge_key__", how="left", validate="many_to_one")

    presence_col = _presence_column(features_df)
    if presence_col is not None and cfg.strict:
        missing_mask = out[presence_col].isna()
        if bool(missing_mask.any()):
            preview = out.loc[missing_mask, cfg.merge_col].astype(str).head(10).tolist()
            raise AutoBrepFSQError(
                f"После merge отсутствуют AutoBrep-признаки для {int(missing_mask.sum())} {split_name}-строк. Примеры: {preview}"
            )

    return out.drop(columns=["__autobrep_merge_key__"])



def _same_feature_source(cfg_a: AutoBrepFSQRuntimeConfig, cfg_b: AutoBrepFSQRuntimeConfig) -> bool:
    return (
        cfg_a.merge_col == cfg_b.merge_col
        and cfg_a.npz_dir == cfg_b.npz_dir
        and cfg_a.features_path == cfg_b.features_path
        and cfg_a.cache_path == cfg_b.cache_path
        and cfg_a.surf_ckpt == cfg_b.surf_ckpt
        and cfg_a.edge_ckpt == cfg_b.edge_ckpt
        and cfg_a.ar_ckpt == cfg_b.ar_ckpt
        and cfg_a.device == cfg_b.device
        and cfg_a.batch_size == cfg_b.batch_size
        and cfg_a.key_mode == cfg_b.key_mode
        and cfg_a.strict == cfg_b.strict
        and cfg_a.sequence_window_stride == cfg_b.sequence_window_stride
        and cfg_a.add_cad_embedding == cfg_b.add_cad_embedding
    )



def merge_autobrep_fsq_features_into_frames(
    train_df: pd.DataFrame,
    test_df: Optional[pd.DataFrame],
    cfg: AutoBrepFSQRuntimeConfig,
    test_cfg: Optional[AutoBrepFSQRuntimeConfig] = None,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], List[str], List[str], pd.DataFrame]:
    if not cfg.enabled():
        return train_df, test_df, [], [], pd.DataFrame()
    if cfg.merge_col not in train_df.columns:
        raise ValueError(f"В train_df отсутствует merge column для AutoBrep: {cfg.merge_col}")

    test_cfg = test_cfg if test_cfg is not None else cfg
    train_keys = train_df[cfg.merge_col].map(lambda x: _normalize_key(x, cfg.key_mode)).tolist()
    train_features_df = _sanitize_features_df(load_or_build_autobrep_fsq_features(part_keys=train_keys, cfg=cfg))
    train_out = _merge_single_frame_with_features(train_df, split_name="train", features_df=train_features_df, cfg=cfg)

    if test_df is not None:
        if test_cfg.merge_col not in test_df.columns:
            raise ValueError(f"В test_df отсутствует merge column для AutoBrep: {test_cfg.merge_col}")
        if _same_feature_source(cfg, test_cfg):
            test_features_df = train_features_df
        else:
            test_keys = test_df[test_cfg.merge_col].map(lambda x: _normalize_key(x, test_cfg.key_mode)).tolist()
            test_features_df = _sanitize_features_df(load_or_build_autobrep_fsq_features(part_keys=test_keys, cfg=test_cfg))
        test_out = _merge_single_frame_with_features(test_df, split_name="test", features_df=test_features_df, cfg=test_cfg)
        if train_features_df is test_features_df:
            features_df = train_features_df
        else:
            features_df = pd.concat([train_features_df, test_features_df], axis=0, ignore_index=True)
            features_df = features_df.drop_duplicates(subset=["__autobrep_merge_key__"], keep="first")
    else:
        test_out = None
        features_df = train_features_df

    embedding_cols: List[str] = []
    if cfg.add_cad_embedding and "autobrep_cad_emb" in train_out.columns:
        embedding_cols.append("autobrep_cad_emb")

    # Исключаем дублирование: combined имеет приоритет над separate.
    if cfg.add_combined_embedding and "autobrep_fsq_emb" in train_out.columns:
        embedding_cols.append("autobrep_fsq_emb")
    else:
        if cfg.add_surface_embedding and "autobrep_surf_fsq_emb" in train_out.columns:
            embedding_cols.append("autobrep_surf_fsq_emb")
        if cfg.add_edge_embedding and "autobrep_edge_fsq_emb" in train_out.columns:
            embedding_cols.append("autobrep_edge_fsq_emb")

    numeric_cols: List[str] = []
    if cfg.add_numeric_meta:
        numeric_cols = [c for c in AUTOBREP_NUMERIC_COLUMNS if c in train_out.columns]

    return train_out, test_out, embedding_cols, numeric_cols, features_df
