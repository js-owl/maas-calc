from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class MetricsMixin:
    def _safe_abs_error(self, y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            return np.abs(y_true - y_pred)

    def _safe_pct_error_to_true(self, y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
            cfg = self.config.business_loss_config
            abs_err = self._safe_abs_error(y_true, y_pred)
            denom = np.maximum(np.abs(np.asarray(y_true, dtype=float)), cfg.denom_eps)
            return abs_err / denom

    def _safe_pct_error_to_pred(self, y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
            cfg = self.config.business_loss_config
            abs_err = self._safe_abs_error(y_true, y_pred)
            denom = np.maximum(np.abs(np.asarray(y_pred, dtype=float)), cfg.denom_eps)
            return abs_err / denom

    @staticmethod
    def _mean_or_zero(x: np.ndarray) -> float:
            x = np.asarray(x, dtype=float)
            if x.size == 0:
                return 0.0
            return float(np.mean(x))

    @staticmethod
    def _quantile_or_zero(x: np.ndarray, q: float) -> float:
            x = np.asarray(x, dtype=float)
            if x.size == 0:
                return 0.0
            q = float(np.clip(q, 0.0, 1.0))
            return float(np.quantile(x, q))

    @staticmethod
    def _weighted_mean_or_zero(x: np.ndarray, weights: Optional[np.ndarray] = None) -> float:
            x = np.asarray(x, dtype=float)
            if x.size == 0:
                return 0.0
            if weights is None:
                return float(np.mean(x))
            weights = np.asarray(weights, dtype=float)
            if weights.size == 0 or np.sum(weights) <= 0:
                return float(np.mean(x))
            return float(np.average(x, weights=weights))
    
    def _sample_business_rule_penalty(
            self,
            y_true: np.ndarray,
            y_pred: np.ndarray,
        ) -> np.ndarray:
            cfg = self.config.business_loss_config

            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)

            abs_err = self._safe_abs_error(y_true, y_pred)
            pct_true = self._safe_pct_error_to_true(y_true, y_pred)
            pct_pred = self._safe_pct_error_to_pred(y_true, y_pred)

            small_mask = y_true < cfg.small_target_threshold
            large_mask = ~small_mask

            small_excess = np.maximum(abs_err - cfg.small_abs_error_limit, 0.0)
            small_excess = small_excess / max(cfg.small_abs_error_limit, cfg.denom_eps)

            large_true_excess = np.maximum(
                pct_true - cfg.large_pct_error_to_true_limit,
                0.0,
            )
            large_pred_excess = np.maximum(
                pct_pred - cfg.large_pct_error_to_pred_limit,
                0.0,
            )

            if cfg.excess_power != 1.0:
                small_excess = small_excess ** cfg.excess_power
                large_true_excess = large_true_excess ** cfg.excess_power
                large_pred_excess = large_pred_excess ** cfg.excess_power

            penalty = np.zeros_like(abs_err, dtype=float)
            penalty[small_mask] = small_excess[small_mask]
            penalty[large_mask] = (
                large_true_excess[large_mask] + large_pred_excess[large_mask]
            )

            return penalty

    def _build_business_rule_metrics(
            self,
            y_true: np.ndarray,
            y_pred: np.ndarray,
        ) -> Dict[str, float]:
            cfg = self.config.business_loss_config

            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)

            abs_err = self._safe_abs_error(y_true, y_pred)
            pct_true = self._safe_pct_error_to_true(y_true, y_pred)
            pct_pred = self._safe_pct_error_to_pred(y_true, y_pred)

            small_mask = y_true < cfg.small_target_threshold
            large_mask = ~small_mask

            small_violation = abs_err > cfg.small_abs_error_limit
            large_true_violation = pct_true > cfg.large_pct_error_to_true_limit
            large_pred_violation = pct_pred > cfg.large_pct_error_to_pred_limit

            overall_rule_violation = (
                (small_mask & small_violation)
                | (large_mask & (large_true_violation | large_pred_violation))
            )

            sample_penalty = self._sample_business_rule_penalty(y_true, y_pred)

            return {
                "small_share": float(np.mean(small_mask)) if len(y_true) else 0.0,
                "large_share": float(np.mean(large_mask)) if len(y_true) else 0.0,

                "small_violation_rate": self._mean_or_zero(small_violation[small_mask]),
                "small_excess_mean": self._mean_or_zero(sample_penalty[small_mask]),

                "large_true_violation_rate": self._mean_or_zero(
                    large_true_violation[large_mask]
                ),
                "large_true_excess_mean": self._mean_or_zero(
                    np.maximum(
                        pct_true[large_mask] - cfg.large_pct_error_to_true_limit,
                        0.0,
                    ) ** cfg.excess_power
                    if cfg.excess_power != 1.0
                    else np.maximum(
                        pct_true[large_mask] - cfg.large_pct_error_to_true_limit,
                        0.0,
                    )
                ),

                "large_pred_violation_rate": self._mean_or_zero(
                    large_pred_violation[large_mask]
                ),
                "large_pred_excess_mean": self._mean_or_zero(
                    np.maximum(
                        pct_pred[large_mask] - cfg.large_pct_error_to_pred_limit,
                        0.0,
                    ) ** cfg.excess_power
                    if cfg.excess_power != 1.0
                    else np.maximum(
                        pct_pred[large_mask] - cfg.large_pct_error_to_pred_limit,
                        0.0,
                    )
                ),

                "business_rule_violation_rate": float(np.mean(overall_rule_violation))
                if len(y_true)
                else 0.0,

                "business_rule_penalty_mean": self._mean_or_zero(sample_penalty),

                "negative_pred_rate": float(np.mean(y_pred < 0.0)) if len(y_true) else 0.0,
            }

    def _business_rule_score_from_global_metrics(
            self,
            global_metrics: Dict[str, float],
        ) -> float:
            cfg = self.config.business_loss_config

            return float(
                cfg.w_small_violation_rate * global_metrics["small_violation_rate"]
                + cfg.w_small_excess_mean * global_metrics["small_excess_mean"]
                + cfg.w_large_true_violation_rate * global_metrics["large_true_violation_rate"]
                + cfg.w_large_true_excess_mean * global_metrics["large_true_excess_mean"]
                + cfg.w_large_pred_violation_rate * global_metrics["large_pred_violation_rate"]
                + cfg.w_large_pred_excess_mean * global_metrics["large_pred_excess_mean"]
            )

    def _rmse(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    def _mae(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            return float(np.mean(np.abs(y_true - y_pred)))

    def _rmsle(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
            y_true = np.clip(np.asarray(y_true, dtype=float), 0.0, None)
            y_pred = np.clip(np.asarray(y_pred, dtype=float), 0.0, None)
            return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))

    def _wape(self, y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-12) -> float:
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            denom = max(np.sum(np.abs(y_true)), eps)
            return float(np.sum(np.abs(y_pred - y_true)) / denom)
    
    def _mape_smooth(
            self,
            y_true: np.ndarray,
            y_pred: np.ndarray,
            alpha: Optional[float] = None,
            eps: float = 1e-12,
        ) -> float:
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            alpha = self.config.mape_smooth_alpha if alpha is None else float(alpha)
            denom = np.maximum(y_true + alpha, eps)
            return float(np.mean(np.abs(y_pred - y_true) / denom))

    def _smape_smooth(
            self,
            y_true: np.ndarray,
            y_pred: np.ndarray,
            alpha: Optional[float] = None,
            eps: float = 1e-12,
        ) -> float:
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            alpha = self.config.mape_smooth_alpha if alpha is None else float(alpha)
            denom = np.maximum(np.abs(y_true) + np.abs(y_pred) + alpha, eps)
            return float(np.mean(2.0 * np.abs(y_pred - y_true) / denom))
    
    def _clipped_ape_mean(
            self,
            y_true: np.ndarray,
            y_pred: np.ndarray,
            floor: Optional[float] = None,
        ) -> float:
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            floor = self.config.bin_metric_config.ape_floor if floor is None else floor
            denom = np.maximum(np.abs(y_true), floor)
            return float(np.mean(np.abs(y_pred - y_true) / denom))

    def _bias_pct(self, y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-12) -> float:
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            denom = max(np.sum(np.abs(y_true)), eps)
            return float(np.sum(y_pred - y_true) / denom)

    def _overprediction_rate(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            return float(np.mean(y_pred > y_true))

    def _build_pct_error_metrics(
            self,
            y_true: np.ndarray,
            y_pred: np.ndarray,
        ) -> Dict[str, float]:
            pct_true = self._safe_pct_error_to_true(y_true, y_pred)
            pct_pred = self._safe_pct_error_to_pred(y_true, y_pred)
            pct_sum = pct_true + pct_pred

            tail_q = self._quantile_or_zero(
                pct_sum,
                self.config.pct_error_sum_tail_quantile,
            )
            tail_score = self._mean_or_zero(pct_sum) + self.config.pct_error_sum_tail_weight * tail_q

            return {
                "pct_error_to_true_mean": self._mean_or_zero(pct_true),
                "pct_error_to_pred_mean": self._mean_or_zero(pct_pred),
                "pct_error_sum_mean": self._mean_or_zero(pct_sum),
                "pct_error_sum_tail_q": tail_q,
                "pct_error_sum_tail_score": float(tail_score),
            }

    def _build_global_metrics(
            self,
            y_true: np.ndarray,
            y_pred: np.ndarray,
        ) -> Dict[str, float]:
            metrics = {
                "rmse": self._rmse(y_true, y_pred),
                "mae": self._mae(y_true, y_pred),
                "rmsle": self._rmsle(y_true, y_pred),
                "wape": self._wape(y_true, y_pred),
                "mape_smooth": self._mape_smooth(y_true, y_pred),
                "smape_smooth": self._smape_smooth(y_true, y_pred),
                "clipped_ape_mean": self._clipped_ape_mean(y_true, y_pred),
                "bias_pct": self._bias_pct(y_true, y_pred),
                "overprediction_rate": self._overprediction_rate(y_true, y_pred),
            }

            metrics.update(self._build_pct_error_metrics(y_true, y_pred))

            if self.config.business_loss_config.enabled:
                metrics.update(self._build_business_rule_metrics(y_true, y_pred))

            return metrics

    def _resolve_analysis_bin_edges(
            self,
            y_reference: np.ndarray,
        ) -> np.ndarray:
            cfg = self.config.bin_metric_config

            if not cfg.enabled:
                return np.array([-np.inf, np.inf], dtype=float)

            if cfg.strategy == "fixed":
                if not cfg.fixed_edges:
                    return np.array([-np.inf, np.inf], dtype=float)

                edges = np.asarray(cfg.fixed_edges, dtype=float)
                edges = edges[np.isfinite(edges)]
                edges = np.unique(edges)
                edges.sort()
                return np.concatenate(([-np.inf], edges, [np.inf]))

            # quantile strategy
            y_reference = np.asarray(y_reference, dtype=float)
            y_reference = y_reference[np.isfinite(y_reference)]

            if y_reference.size == 0:
                return np.array([-np.inf, np.inf], dtype=float)

            n_unique = len(np.unique(y_reference))
            n_bins = max(2, min(cfg.n_bins, n_unique))
            q = np.linspace(0.0, 1.0, n_bins + 1)
            edges = np.quantile(y_reference, q)
            edges[0] = -np.inf
            edges[-1] = np.inf
            edges = np.unique(edges)

            if len(edges) < 3:
                return np.array([-np.inf, np.inf], dtype=float)

            return edges

    def _assign_analysis_bin_ids(
            self,
            y: np.ndarray,
            edges: np.ndarray,
        ) -> np.ndarray:
            y = np.asarray(y, dtype=float)
            return np.digitize(y, edges[1:-1], right=False)

    def _build_bin_report(
            self,
            y_true: np.ndarray,
            y_pred: np.ndarray,
            y_reference_for_edges: Optional[np.ndarray] = None,
        ) -> pd.DataFrame:
            cfg = self.config.bin_metric_config

            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)

            if y_reference_for_edges is None:
                y_reference_for_edges = y_true

            edges = self._resolve_analysis_bin_edges(y_reference_for_edges)
            bin_ids = self._assign_analysis_bin_ids(y_true, edges)

            rows: List[Dict[str, Any]] = []
            total_n = len(y_true)

            for b in sorted(np.unique(bin_ids)):
                mask = bin_ids == b
                n = int(mask.sum())
                if n < cfg.min_bin_size:
                    continue

                yt = y_true[mask]
                yp = y_pred[mask]

                row = {
                    "bin_id": int(b),
                    "bin_left": float(edges[b]),
                    "bin_right": float(edges[b + 1]),
                    "n": n,
                    "share": float(n / max(total_n, 1)),
                    "target_mean": float(np.mean(yt)),
                    "target_median": float(np.median(yt)),
                    "pred_mean": float(np.mean(yp)),
                    "pred_median": float(np.median(yp)),
                    "rmse": self._rmse(yt, yp),
                    "mae": self._mae(yt, yp),
                    "rmsle": self._rmsle(yt, yp),
                    "wape": self._wape(yt, yp),
                    "clipped_ape_mean": self._clipped_ape_mean(yt, yp),
                    "pct_error_to_true_mean": self._mean_or_zero(self._safe_pct_error_to_true(yt, yp)),
                    "pct_error_to_pred_mean": self._mean_or_zero(self._safe_pct_error_to_pred(yt, yp)),
                    "pct_error_sum_mean": self._mean_or_zero(
                        self._safe_pct_error_to_true(yt, yp) + self._safe_pct_error_to_pred(yt, yp)
                    ),
                    "pct_error_sum_tail_q": self._quantile_or_zero(
                        self._safe_pct_error_to_true(yt, yp) + self._safe_pct_error_to_pred(yt, yp),
                        self.config.pct_error_sum_tail_quantile,
                    ),
                    "bias_pct": self._bias_pct(yt, yp),
                    "overprediction_rate": self._overprediction_rate(yt, yp),
                }

                if self.config.business_loss_config.enabled:
                    row.update(self._build_business_rule_metrics(yt, yp))

                rows.append(row)

            return pd.DataFrame(rows)

    def _optuna_score_from_reports(
            self,
            global_metrics: Dict[str, float],
            bin_report: pd.DataFrame,
        ) -> float:
            cfg = self.config.bin_metric_config

            if (not cfg.enabled) or bin_report.empty:
                base_score = float(
                    global_metrics["rmsle"]
                    + 0.25 * global_metrics["wape"]
                    + 0.10 * abs(global_metrics["bias_pct"])
                )
            else:
                if cfg.bin_weights:
                    weights = (
                        bin_report["bin_id"]
                        .map(cfg.bin_weights)
                        .fillna(1.0)
                        .to_numpy(dtype=float)
                    )
                else:
                    weights = np.ones(len(bin_report), dtype=float)

                mean_bin_rmsle = float(np.average(bin_report["rmsle"], weights=weights))
                std_bin_rmsle = float(bin_report["rmsle"].std(ddof=0))
                mean_bin_wape = float(np.average(bin_report["wape"], weights=weights))
                global_bias_abs = float(abs(global_metrics["bias_pct"]))

                base_score = float(
                    cfg.optuna_w_mean_bin_rmsle * mean_bin_rmsle
                    + cfg.optuna_w_std_bin_rmsle * std_bin_rmsle
                    + cfg.optuna_w_mean_bin_wape * mean_bin_wape
                    + cfg.optuna_w_global_bias * global_bias_abs
                )

            business_cfg = self.config.business_loss_config
            if not business_cfg.enabled:
                return base_score

            business_score = self._business_rule_score_from_global_metrics(global_metrics)

            final_score = (
                business_cfg.optuna_existing_score_weight * base_score
                + business_cfg.optuna_business_score_weight * business_score
            )
            return float(final_score)

    def _get_optuna_objective_value(
            self,
            global_metrics: Dict[str, float],
            bin_report: pd.DataFrame,
        ) -> float:
            mode = self.config.optuna_objective_mode

            if mode == "pct_error_sum":
                return float(global_metrics["pct_error_sum_mean"])

            if mode == "pct_error_sum_tail":
                return float(global_metrics["pct_error_sum_tail_score"])

            if mode == "pct_error_sum_bin_balanced":
                if bin_report.empty or "pct_error_sum_mean" not in bin_report.columns:
                    return float(global_metrics["pct_error_sum_mean"])

                cfg = self.config.bin_metric_config
                if cfg.bin_weights:
                    weights = (
                        bin_report["bin_id"]
                        .map(cfg.bin_weights)
                        .fillna(1.0)
                        .to_numpy(dtype=float)
                    )
                else:
                    weights = None

                return self._weighted_mean_or_zero(
                    bin_report["pct_error_sum_mean"].to_numpy(dtype=float),
                    weights=weights,
                )
            
            if mode == "metric_name":
                metric = self.config.metric_name.lower()
                if metric not in global_metrics:
                    raise ValueError(f"Metric '{metric}' is not available in global_metrics")
                return float(global_metrics[metric])

            return self._optuna_score_from_reports(global_metrics, bin_report)
    
    def _score(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
            # Legacy single-metric scorer. Main CV / ensemble weighting can be switched
            # to composite Optuna-aligned scoring via config.cv_score_mode.
            metric = self.config.metric_name.lower()

            if metric == "mae":
                return self._mae(y_true, y_pred)
            if metric == "rmsle":
                return self._rmsle(y_true, y_pred)
            if metric == "wape":
                return self._wape(y_true, y_pred)
            if metric == "mape_smooth":
                return self._mape_smooth(y_true, y_pred)
            if metric == "smape_smooth":
                return self._smape_smooth(y_true, y_pred)

            return self._rmse(y_true, y_pred)

    def _build_ensemble_weights(self) -> Dict[str, float]:
            if self.config.ensemble_mode == "mean":
                w = 1.0 / len(self.cv_scores_)
                return {m: w for m in self.cv_scores_}

            # weighted: inverse metric
            eps = 1e-12
            inv = {m: 1.0 / (score + eps) for m, score in self.cv_scores_.items()}
            s = sum(inv.values())
            return {m: v / s for m, v in inv.items()}

    def _ensemble_predict_from_pred_df(self, pred_df: pd.DataFrame) -> np.ndarray:
            cols = [m for m in self.enabled_models_ if m in pred_df.columns]
            if not cols:
                raise ValueError("В pred_df нет ни одной включенной модели.")

            out = np.zeros(len(pred_df), dtype=float)
            for m in cols:
                out += self.model_weights_[m] * pred_df[m].to_numpy()
            return out

