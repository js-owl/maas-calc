from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ml_models.flexible_ensemble.trainer import FlexibleRegressorEnsemble

def _parse_csv_list(value: Optional[str]) -> List[str]:
    if value is None:
        return []
    value = str(value).strip()
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]

def _parse_float_list(value: Optional[str]) -> List[float]:
    if value is None:
        return []
    value = str(value).strip()
    if not value:
        return []
    out: List[float] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if item.lower() in {"inf", "+inf"}:
            out.append(float("inf"))
        elif item.lower() == "-inf":
            out.append(float("-inf"))
        else:
            out.append(float(item))
    return out

def _parse_json_dict(value: Optional[str]) -> Dict[str, Any]:
    if value is None:
        return {}
    value = str(value).strip()
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Ожидался JSON-объект")
    return parsed

def _parse_int_float_dict(value: Optional[str]) -> Dict[int, float]:
    raw = _parse_json_dict(value)
    return {int(k): float(v) for k, v in raw.items()}

def _load_dataframe(path_str: str) -> pd.DataFrame:
    path = Path(path_str)
    suffix = path.suffix.lower()

    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)

    raise ValueError(f"Неподдерживаемый формат файла: {suffix}")

def _infer_numeric_features(
    df: pd.DataFrame,
    target_col: str,
    categorical_features: List[str],
    embedding_features: List[str],
    excluded_extra: Optional[List[str]] = None,
) -> List[str]:
    excluded = {
        target_col,
        *(categorical_features or []),
        *(embedding_features or []),
        *((excluded_extra or [])),
    }
    return [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]

def _json_dumps_safe(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)

def _summary_to_df(summary: Dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "key": k,
                "value": _json_dumps_safe(v) if isinstance(v, (dict, list, tuple, np.ndarray)) else v,
            }
            for k, v in summary.items()
        ]
    )

def _resolve_eval_target_col(df: pd.DataFrame, explicit_target_col: Optional[str], fallback_target_col: str) -> Optional[str]:
    if explicit_target_col:
        return explicit_target_col if explicit_target_col in df.columns else None
    return fallback_target_col if fallback_target_col in df.columns else None

def _enrich_prediction_df(
    trainer: FlexibleRegressorEnsemble,
    pred_df: pd.DataFrame,
    y_true: np.ndarray,
    target_col_name: str,
) -> pd.DataFrame:
    out = pred_df.copy()
    out[target_col_name] = y_true

    y_pred = out["ensemble"].to_numpy(dtype=float)

    abs_error = trainer._safe_abs_error(y_true, y_pred)
    pct_error_to_true = trainer._safe_pct_error_to_true(y_true, y_pred)
    pct_error_to_pred = trainer._safe_pct_error_to_pred(y_true, y_pred)
    business_penalty = trainer._sample_business_rule_penalty(y_true, y_pred)

    cfg = trainer.config.business_loss_config
    small_mask = y_true < cfg.small_target_threshold
    large_mask = ~small_mask

    small_rule_violation = small_mask & (abs_error > cfg.small_abs_error_limit)
    large_rule_violation_true = (
        large_mask & (pct_error_to_true > cfg.large_pct_error_to_true_limit)
    )
    large_rule_violation_pred = (
        large_mask & (pct_error_to_pred > cfg.large_pct_error_to_pred_limit)
    )

    out["abs_error"] = abs_error
    out["pct_error_to_true"] = pct_error_to_true
    out["pct_error_to_pred"] = pct_error_to_pred
    out["small_case_flag"] = small_mask.astype(int)
    out["large_case_flag"] = large_mask.astype(int)
    out["small_rule_violation"] = small_rule_violation.astype(int)
    out["large_rule_violation_true"] = large_rule_violation_true.astype(int)
    out["large_rule_violation_pred"] = large_rule_violation_pred.astype(int)
    out["business_rule_violation"] = (
        small_rule_violation | large_rule_violation_true | large_rule_violation_pred
    ).astype(int)
    out["business_rule_penalty"] = business_penalty
    out["negative_pred_flag"] = (y_pred < 0.0).astype(int)
    return out

def _evaluate_predictions(
    trainer: FlexibleRegressorEnsemble,
    pred_df: pd.DataFrame,
    y_true: np.ndarray,
    target_col_name: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    enriched = _enrich_prediction_df(trainer, pred_df, y_true=y_true, target_col_name=target_col_name)
    metrics_df = pd.DataFrame([trainer._build_global_metrics(y_true, enriched["ensemble"].to_numpy(dtype=float))])
    bin_report_df = trainer._build_bin_report(
        y_true=y_true,
        y_pred=enriched["ensemble"].to_numpy(dtype=float),
        y_reference_for_edges=y_true,
    )
    return enriched, metrics_df, bin_report_df

def _build_segment_metrics_from_pred_df(
    trainer: FlexibleRegressorEnsemble,
    pred_df: pd.DataFrame,
    segment_columns: List[str],
    pred_col: str = "ensemble",
    min_size: int = 5,
) -> pd.DataFrame:
    tables: List[pd.DataFrame] = []
    for col in list(dict.fromkeys(segment_columns)):
        if col not in pred_df.columns:
            continue
        seg = trainer._build_segment_metrics_table(
            df_with_pred=pred_df,
            segment_col=col,
            pred_col=pred_col,
            min_size=min_size,
        )
        if not seg.empty:
            tables.append(seg)
    if not tables:
        return pd.DataFrame()
    return pd.concat(tables, axis=0, ignore_index=True)

def _collect_feature_importances(
    trainer: FlexibleRegressorEnsemble,
    model_names: List[str],
    top_n: int,
    aggregate: bool = True,
    normalize: bool = True,
) -> pd.DataFrame:
    tables: List[pd.DataFrame] = []
    for model_name in model_names:
        try:
            fi = trainer.get_feature_importances(
                model_name=model_name,
                top_n=top_n,
                aggregate=aggregate,
                normalize=normalize,
            ).copy()
        except Exception:
            continue
        fi.insert(0, "model", model_name)
        tables.append(fi)
    if not tables:
        return pd.DataFrame()
    return pd.concat(tables, axis=0, ignore_index=True)

def _collect_optuna_trials_metrics(trainer: FlexibleRegressorEnsemble) -> pd.DataFrame:
    if not trainer.optuna_trials_metrics_:
        return pd.DataFrame()
    return trainer.get_optuna_trials_metrics_table()

def _safe_sheet_name(name: str) -> str:
    bad = ['\\', '/', '*', '?', ':', '[', ']']
    for ch in bad:
        name = name.replace(ch, '_')
    return name[:31] if len(name) > 31 else name

def _write_results_workbook(path: Path, sheets: Dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df_sheet in sheets.items():
            if df_sheet is None or (isinstance(df_sheet, pd.DataFrame) and df_sheet.empty):
                continue
            df_sheet.to_excel(writer, sheet_name=_safe_sheet_name(sheet_name), index=False)
