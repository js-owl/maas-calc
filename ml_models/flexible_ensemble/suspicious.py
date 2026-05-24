from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from .config import EnsembleConfig, FeatureSpec, ModelFlags
from .trainer import FlexibleRegressorEnsemble


DEFAULT_REPEATED_OOF_MODEL_GROUPS: Dict[str, List[str]] = {
    "linear": ["ridge", "elasticnet"],
    "kernel": ["svr"],
    "bagging": ["rf"],
    "boosting": ["lgbm", "xgb", "catboost"],
}


def _iqr(values: pd.Series | np.ndarray) -> float:
    arr = pd.Series(values).dropna().to_numpy(dtype=float)
    if arr.size == 0:
        return np.nan
    return float(np.quantile(arr, 0.75) - np.quantile(arr, 0.25))


def parse_model_groups_json(value: Optional[str]) -> Dict[str, List[str]]:
    if value is None or not str(value).strip():
        return deepcopy(DEFAULT_REPEATED_OOF_MODEL_GROUPS)

    raw = json.loads(value)
    if not isinstance(raw, dict):
        raise ValueError("--suspicious-model-groups-json должен быть JSON-объектом")

    out: Dict[str, List[str]] = {}
    for group_name, models in raw.items():
        if isinstance(models, str):
            model_list = [x.strip() for x in models.split(",") if x.strip()]
        elif isinstance(models, list):
            model_list = [str(x).strip() for x in models if str(x).strip()]
        else:
            raise ValueError(f"Группа {group_name} должна содержать список моделей или CSV-строку")

        if not model_list:
            continue
        out[str(group_name)] = model_list

    if not out:
        raise ValueError("После парсинга --suspicious-model-groups-json не осталось ни одной группы")
    return out


def build_repeated_oof_seeds(
    base_random_state: int,
    explicit_seeds: Optional[List[int]] = None,
    n_seeds: int = 5,
    step: int = 101,
) -> List[int]:
    if explicit_seeds:
        return list(dict.fromkeys(int(x) for x in explicit_seeds))
    return [int(base_random_state + i * step) for i in range(n_seeds)]


def _make_group_model_flags(models: List[str]) -> ModelFlags:
    return ModelFlags(
        use_mlp=False,
        use_lgbm=False,
        use_catboost=False,
        use_xgb=False,
        use_rf=False,
        extra_models=[],
        models_override=list(dict.fromkeys(models)),
    )


def _merge_custom_and_best_params(
    base_custom_params: Dict[str, Dict[str, Any]],
    best_params: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = deepcopy(base_custom_params or {})
    for model_name, params in (best_params or {}).items():
        existing = dict(out.get(model_name, {}))
        # best params -> база, пользовательские custom_params -> приоритетнее
        out[model_name] = {**dict(params or {}), **existing}
    return out


def _fit_group_anchor(
    df: pd.DataFrame,
    feature_spec: FeatureSpec,
    base_config: EnsembleConfig,
    group_name: str,
    models: List[str],
    optuna_test_df: Optional[pd.DataFrame],
    optuna_test_target_col: Optional[str],
) -> Tuple[Optional[Dict[str, Dict[str, Any]]], Dict[str, Any]]:
    group_flags = _make_group_model_flags(models)
    trainer = FlexibleRegressorEnsemble(
        feature_spec=feature_spec,
        model_flags=group_flags,
        config=base_config,
    )

    try:
        trainer.fit(
            df,
            optuna_test_df=optuna_test_df if base_config.optuna_test_score_weight > 0.0 else None,
            optuna_test_target_col=optuna_test_target_col,
        )
        return trainer.best_params_, {
            "group_name": group_name,
            "stage": "anchor_tune",
            "status": "ok",
            "n_models": len(models),
            "models": ",".join(models),
            "random_state": base_config.random_state,
            "cv_rmsle": float(trainer.ensemble_oof_global_metrics_.get("rmsle", np.nan)),
            "cv_wape": float(trainer.ensemble_oof_global_metrics_.get("wape", np.nan)),
            "error": "",
        }
    except Exception as exc:
        return None, {
            "group_name": group_name,
            "stage": "anchor_tune",
            "status": "failed",
            "n_models": len(models),
            "models": ",".join(models),
            "random_state": base_config.random_state,
            "cv_rmsle": np.nan,
            "cv_wape": np.nan,
            "error": str(exc),
        }


def _run_group_seed_oof(
    df: pd.DataFrame,
    feature_spec: FeatureSpec,
    config: EnsembleConfig,
    group_name: str,
    models: List[str],
    seed: int,
    id_col: Optional[str],
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    trainer = FlexibleRegressorEnsemble(
        feature_spec=feature_spec,
        model_flags=_make_group_model_flags(models),
        config=config,
    )

    try:
        oof_df = trainer.fit_predict_oof(df, include_fold_columns=False)
        detail = pd.DataFrame(index=df.index)
        detail["row_id"] = np.arange(len(df), dtype=int)
        detail["group_name"] = group_name
        detail["seed"] = int(seed)
        detail["target"] = df[config.target_col].astype(float).values
        detail["prediction"] = oof_df["ensemble"].astype(float).values
        detail["pct_error_to_true"] = oof_df["pct_error_to_true"].astype(float).values
        detail["pct_error_to_pred"] = oof_df["pct_error_to_pred"].astype(float).values
        detail["pct_error_sum"] = detail["pct_error_to_true"] + detail["pct_error_to_pred"]
        detail["business_rule_violation"] = oof_df["business_rule_violation"].astype(int).values
        detail["business_rule_penalty"] = oof_df["business_rule_penalty"].astype(float).values
        detail["abs_error"] = oof_df["abs_error"].astype(float).values
        detail["negative_pred_flag"] = oof_df["negative_pred_flag"].astype(int).values
        if id_col and id_col in df.columns:
            detail[id_col] = df[id_col].values

        metrics = trainer.ensemble_oof_global_metrics_.copy()
        summary_row = {
            "group_name": group_name,
            "stage": "seed_oof",
            "status": "ok",
            "n_models": len(models),
            "models": ",".join(models),
            "random_state": int(seed),
            **metrics,
            "error": "",
        }
        return detail, summary_row
    except Exception as exc:
        return None, {
            "group_name": group_name,
            "stage": "seed_oof",
            "status": "failed",
            "n_models": len(models),
            "models": ",".join(models),
            "random_state": int(seed),
            "error": str(exc),
        }


def _compute_prediction_stability_tables(raw_runs_df: pd.DataFrame) -> pd.DataFrame:
    if raw_runs_df.empty:
        return pd.DataFrame(columns=["row_id"])

    by_row = raw_runs_df.groupby("row_id", as_index=False)
    out = by_row.agg(
        repeated_runs_n=("prediction", "size"),
        pred_mean_all=("prediction", "mean"),
        pred_median_all=("prediction", "median"),
        pred_std_all=("prediction", lambda s: float(np.std(s.to_numpy(dtype=float), ddof=0))),
        pct_error_sum_mean=("pct_error_sum", "mean"),
        pct_error_sum_median=("pct_error_sum", "median"),
        pct_error_sum_q80=("pct_error_sum", lambda s: float(pd.Series(s).quantile(0.80))),
        pct_error_sum_q90=("pct_error_sum", lambda s: float(pd.Series(s).quantile(0.90))),
        business_rule_violation_share=("business_rule_violation", "mean"),
        business_rule_penalty_mean=("business_rule_penalty", "mean"),
        business_rule_penalty_q90=("business_rule_penalty", lambda s: float(pd.Series(s).quantile(0.90))),
        abs_error_mean=("abs_error", "mean"),
        abs_error_q90=("abs_error", lambda s: float(pd.Series(s).quantile(0.90))),
        negative_pred_share=("negative_pred_flag", "mean"),
    )
    pred_iqr_all = by_row["prediction"].agg(pred_iqr_all=_iqr).reset_index()
    out = out.merge(pred_iqr_all, on="row_id", how="left")

    # variability across seeds: сначала усредняем prediction по model families внутри seed
    seed_level = (
        raw_runs_df.groupby(["row_id", "seed"], as_index=False)["prediction"]
        .mean()
    )
    seed_agg = seed_level.groupby("row_id")["prediction"].agg(
        pred_std_across_runs=lambda s: float(np.std(s.to_numpy(dtype=float), ddof=0)),
        pred_iqr_across_runs=_iqr,
    ).reset_index()
    out = out.merge(seed_agg, on="row_id", how="left")

    # variability across model families: сначала усредняем prediction по seeds внутри family
    family_level = (
        raw_runs_df.groupby(["row_id", "group_name"], as_index=False)["prediction"]
        .mean()
    )
    family_agg = family_level.groupby("row_id")["prediction"].agg(
        pred_std_across_models=lambda s: float(np.std(s.to_numpy(dtype=float), ddof=0)),
        pred_iqr_across_models=_iqr,
    ).reset_index()
    out = out.merge(family_agg, on="row_id", how="left")

    return out


def compute_neighbor_consistency(
    df: pd.DataFrame,
    feature_spec: FeatureSpec,
    base_config: EnsembleConfig,
    material_col: str,
    neighbors_k: int,
    id_col: Optional[str] = None,
) -> pd.DataFrame:
    if material_col not in df.columns:
        return pd.DataFrame(columns=["row_id"])

    helper = FlexibleRegressorEnsemble(
        feature_spec=feature_spec,
        model_flags=_make_group_model_flags(["ridge"]),
        config=base_config,
    )
    helper._validate_columns(df)
    X = helper._build_feature_frame(df, fit_mode=True)
    pre = helper._make_sklearn_preprocessor(scale_numeric=True, sparse_ohe=False)
    X_trans = pre.fit_transform(X)
    if hasattr(X_trans, "toarray"):
        X_trans = X_trans.toarray()
    X_trans = np.asarray(X_trans, dtype=float)

    y = df[base_config.target_col].to_numpy(dtype=float)
    alpha = max(float(base_config.mape_smooth_alpha), 1e-6)

    rows: List[Dict[str, Any]] = []
    material_values = df[material_col].astype("string").fillna("__MISSING__").astype(str)

    for material_value, material_idx in material_values.groupby(material_values).groups.items():
        idx = np.asarray(list(material_idx), dtype=int)
        if idx.size == 0:
            continue

        k_eff = min(int(neighbors_k), max(int(idx.size) - 1, 0))
        if k_eff <= 0:
            for local_row_id in idx:
                rows.append({
                    "row_id": int(local_row_id),
                    "neighbor_material": material_value,
                    "neighbor_k_effective": 0,
                    "neighbor_distance_mean": np.nan,
                    "neighbor_distance_median": np.nan,
                    "neighbor_target_mean": np.nan,
                    "neighbor_target_median": np.nan,
                    "neighbor_target_iqr": np.nan,
                    "neighbor_target_abs_gap": np.nan,
                    "neighbor_target_pct_gap_smooth": np.nan,
                    "neighbor_target_robust_gap": np.nan,
                    "neighbor_target_direction": np.nan,
                })
            continue

        sub_x = X_trans[idx]
        nn = NearestNeighbors(n_neighbors=k_eff + 1, metric="euclidean")
        nn.fit(sub_x)
        distances, neigh_local = nn.kneighbors(sub_x)

        distances = distances[:, 1:]
        neigh_local = neigh_local[:, 1:]
        neigh_global = idx[neigh_local]

        for row_pos, global_row_id in enumerate(idx):
            neigh_ids = neigh_global[row_pos]
            neigh_targets = y[neigh_ids]
            neigh_dist = distances[row_pos]

            neigh_mean = float(np.mean(neigh_targets)) if neigh_targets.size else np.nan
            neigh_median = float(np.median(neigh_targets)) if neigh_targets.size else np.nan
            neigh_iqr = _iqr(neigh_targets)
            abs_gap = float(abs(y[global_row_id] - neigh_median)) if pd.notna(neigh_median) else np.nan
            pct_gap_smooth = (
                abs_gap / (abs(neigh_median) + alpha)
                if pd.notna(abs_gap) and pd.notna(neigh_median)
                else np.nan
            )
            robust_gap = (
                abs_gap / max(float(neigh_iqr), alpha)
                if pd.notna(abs_gap) and pd.notna(neigh_iqr)
                else np.nan
            )
            direction = (
                float(np.sign(y[global_row_id] - neigh_median))
                if pd.notna(neigh_median)
                else np.nan
            )

            rows.append({
                "row_id": int(global_row_id),
                "neighbor_material": material_value,
                "neighbor_k_effective": int(k_eff),
                "neighbor_distance_mean": float(np.mean(neigh_dist)) if neigh_dist.size else np.nan,
                "neighbor_distance_median": float(np.median(neigh_dist)) if neigh_dist.size else np.nan,
                "neighbor_target_mean": neigh_mean,
                "neighbor_target_median": neigh_median,
                "neighbor_target_iqr": float(neigh_iqr) if pd.notna(neigh_iqr) else np.nan,
                "neighbor_target_abs_gap": abs_gap,
                "neighbor_target_pct_gap_smooth": float(pct_gap_smooth) if pd.notna(pct_gap_smooth) else np.nan,
                "neighbor_target_robust_gap": float(robust_gap) if pd.notna(robust_gap) else np.nan,
                "neighbor_target_direction": direction,
            })

    out = pd.DataFrame(rows)
    if id_col and id_col in df.columns and not out.empty:
        out[id_col] = df.iloc[out["row_id"].to_numpy(dtype=int)][id_col].values
    return out.sort_values("row_id").reset_index(drop=True)


def _add_suspicious_score(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    severity_cols = [
        "pct_error_sum_median",
        "pct_error_sum_q80",
        "pct_error_sum_q90",
        "business_rule_violation_share",
        "pred_std_across_runs",
        "pred_iqr_across_runs",
        "pred_std_across_models",
        "pred_iqr_across_models",
        "neighbor_target_pct_gap_smooth",
        "neighbor_target_robust_gap",
    ]
    present = [c for c in severity_cols if c in out.columns]
    if not present:
        out["suspicious_score"] = np.nan
        out["suspicious_vote_top10pct"] = 0
        return out

    rank_cols = []
    vote_cols = []
    for col in present:
        s = out[col].astype(float)
        rank_col = f"__rank__{col}"
        vote_col = f"__vote__{col}"
        out[rank_col] = s.rank(pct=True, method="average")
        q90 = float(s.quantile(0.90)) if s.notna().any() else np.nan
        out[vote_col] = ((s >= q90) & s.notna()).astype(int) if pd.notna(q90) else 0
        rank_cols.append(rank_col)
        vote_cols.append(vote_col)

    out["suspicious_score"] = out[rank_cols].mean(axis=1, skipna=True)
    out["suspicious_vote_top10pct"] = out[vote_cols].sum(axis=1)
    out = out.drop(columns=rank_cols + vote_cols)
    return out


def run_repeated_oof_suspicious_analysis(
    df: pd.DataFrame,
    feature_spec: FeatureSpec,
    base_config: EnsembleConfig,
    seeds: List[int],
    model_groups: Dict[str, List[str]],
    material_col: str,
    neighbors_k: int,
    id_col: Optional[str] = None,
    optuna_test_df: Optional[pd.DataFrame] = None,
    optuna_test_target_col: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    work_df = df.copy().reset_index(drop=True)
    work_df["row_id"] = np.arange(len(work_df), dtype=int)

    id_col_resolved = id_col if id_col and id_col in work_df.columns else None

    run_rows: List[pd.DataFrame] = []
    status_rows: List[Dict[str, Any]] = []

    for group_name, models in model_groups.items():
        group_models = list(dict.fromkeys(models))
        if not group_models:
            continue

        anchor_best_params, anchor_status = _fit_group_anchor(
            df=work_df,
            feature_spec=feature_spec,
            base_config=base_config,
            group_name=group_name,
            models=group_models,
            optuna_test_df=optuna_test_df,
            optuna_test_target_col=optuna_test_target_col,
        )
        status_rows.append(anchor_status)
        if anchor_best_params is None:
            continue

        merged_custom_params = _merge_custom_and_best_params(
            base_custom_params=base_config.custom_params,
            best_params=anchor_best_params,
        )

        for seed in seeds:
            run_config = replace(
                base_config,
                random_state=int(seed),
                use_optuna=False,
                custom_params=deepcopy(merged_custom_params),
            )
            run_df, run_status = _run_group_seed_oof(
                df=work_df,
                feature_spec=feature_spec,
                config=run_config,
                group_name=group_name,
                models=group_models,
                seed=int(seed),
                id_col=id_col_resolved,
            )
            status_rows.append(run_status)
            if run_df is not None and not run_df.empty:
                run_rows.append(run_df)

    raw_runs_df = pd.concat(run_rows, axis=0, ignore_index=True) if run_rows else pd.DataFrame()
    status_df = pd.DataFrame(status_rows)

    if raw_runs_df.empty:
        return {
            "suspicious_run_status": status_df,
            "suspicious_raw_runs": pd.DataFrame(),
            "suspicious_cases": pd.DataFrame(),
            "neighbor_consistency": pd.DataFrame(),
        }

    stability_df = _compute_prediction_stability_tables(raw_runs_df)
    neighbor_df = compute_neighbor_consistency(
        df=work_df,
        feature_spec=feature_spec,
        base_config=replace(base_config, custom_params=deepcopy(base_config.custom_params)),
        material_col=material_col,
        neighbors_k=neighbors_k,
        id_col=id_col_resolved,
    )

    base_cols = ["row_id", base_config.target_col]
    if id_col_resolved:
        base_cols.append(id_col_resolved)
    if material_col in work_df.columns and material_col not in base_cols:
        base_cols.append(material_col)

    suspicious_cases = work_df[base_cols].copy()
    suspicious_cases = suspicious_cases.merge(stability_df, on="row_id", how="left")
    suspicious_cases = suspicious_cases.merge(
        neighbor_df.drop(columns=[id_col_resolved], errors="ignore") if not neighbor_df.empty else neighbor_df,
        on="row_id",
        how="left",
    )
    suspicious_cases = _add_suspicious_score(suspicious_cases)
    suspicious_cases = suspicious_cases.sort_values(
        ["suspicious_score", "pct_error_sum_q90", "business_rule_violation_share"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    raw_runs_df = raw_runs_df.sort_values(["group_name", "seed", "row_id"]).reset_index(drop=True)
    status_df = status_df.sort_values(["stage", "group_name", "random_state"]).reset_index(drop=True)

    return {
        "suspicious_run_status": status_df,
        "suspicious_raw_runs": raw_runs_df,
        "suspicious_cases": suspicious_cases,
        "neighbor_consistency": neighbor_df,
    }
