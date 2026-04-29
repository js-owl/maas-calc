from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PublicApiMixin:
    def _record_exclusion_event(
            self,
            stage: str,
            reason: str,
            rows_df: pd.DataFrame,
        ) -> None:
            rows_df = rows_df.copy()
            event = {
                "stage": str(stage),
                "reason": str(reason),
                "n_rows": int(len(rows_df)),
                "index": rows_df.index.tolist(),
            }
            self.exclusion_log_.append(event)
            self.excluded_training_rows_ = pd.concat(
                [self.excluded_training_rows_, rows_df],
                axis=0,
            ) if not self.excluded_training_rows_.empty else rows_df

    def _drop_rows_without_gnn_graphs(
            self,
            df: pd.DataFrame,
            stage: str,
        ) -> pd.DataFrame:
            if "gnn" not in self.enabled_models_:
                return df

            self._initialize_gnn_store()
            part_key_col = self.config.gnn_config.part_key_col
            if not part_key_col:
                raise ValueError("Для GNN нужно задать config.gnn_config.part_key_col")

            normalized_keys = df[part_key_col].map(self._normalize_gnn_part_key)
            missing_keys = set(self.gnn_store_.get_missing_part_keys(normalized_keys.tolist(), prefer_inference=False))
            if not missing_keys:
                return df

            missing_mask = normalized_keys.isin(missing_keys)
            dropped = df.loc[missing_mask].copy()
            dropped["__normalized_gnn_part_key__"] = normalized_keys.loc[missing_mask].values
            dropped["__exclusion_reason__"] = "missing_gnn_graph"
            dropped["__exclusion_stage__"] = str(stage)

            message = (
                f"Исключено {int(missing_mask.sum())} строк без графов GNN на этапе '{stage}'. "
                f"Примеры ключей: {sorted(list(missing_keys))[:10]}"
            )
            logger.warning(message)
            print(message)
            self._record_exclusion_event(stage=stage, reason="missing_gnn_graph", rows_df=dropped)

            filtered = df.loc[~missing_mask].copy()
            if filtered.empty:
                raise ValueError("После исключения строк без графов GNN обучающая выборка пуста")
            return filtered

    def _prepare_fit_dataframe(
            self,
            df: pd.DataFrame,
        ) -> pd.DataFrame:
            self.fit_input_df_index_ = df.index.copy()
            self.fit_filtered_df_index_ = None
            self.excluded_training_rows_ = pd.DataFrame()
            self.exclusion_log_ = []

            prepared = df.copy()
            prepared = self._drop_rows_without_gnn_graphs(prepared, stage="fit_train")
            self.fit_filtered_df_index_ = prepared.index.copy()
            return prepared

    def fit(
            self,
            df: pd.DataFrame,
            optuna_test_df: Optional[pd.DataFrame] = None,
            optuna_test_target_col: Optional[str] = None,
        ) -> "FlexibleRegressorEnsemble":
            self._validate_columns(df)
            self.enabled_models_ = self._get_enabled_models()
            if not self.enabled_models_:
                raise ValueError("Не включена ни одна модель.")
            if "gnn" in self.enabled_models_:
                self._initialize_gnn_store()

            df = self._prepare_fit_dataframe(df)

            y = df[self.config.target_col].astype(float).to_numpy()
            self._validate_target_transform_train(y)
            self._validate_final_fit_mode()
            groups = (
                df[self.config.group_col].to_numpy()
                if self.config.group_col is not None
                else None
            )

            X = self._build_feature_frame(df, fit_mode=True)
            self.split_strat_labels_ = self._build_split_strat_labels(
                df=df,
                y=y,
                n_splits=self.config.n_splits,
            )
            self.optuna_strat_labels_ = self._build_split_strat_labels(
                df=df,
                y=y,
                n_splits=self.config.optuna_n_splits,
            )

            optuna_test_target = None
            if self.config.optuna_test_score_weight > 0.0:
                if optuna_test_df is None:
                    raise ValueError("optuna_test_score_weight > 0, но optuna_test_df не передан")
                if not optuna_test_target_col:
                    raise ValueError("optuna_test_score_weight > 0, но optuna_test_target_col не задан")
                if optuna_test_target_col not in optuna_test_df.columns:
                    raise ValueError(f"Колонка таргета test-набора не найдена: {optuna_test_target_col}")
                self._validate_columns_for_inference(optuna_test_df, require_target=False)
                optuna_test_target = optuna_test_df[optuna_test_target_col].astype(float).to_numpy()

            # Optuna
            if self.config.use_optuna:
                for model_name in self.enabled_models_:
                    self.best_params_[model_name] = self._run_optuna(
                        model_name=model_name,
                        X=X,
                        y=y,
                        groups=groups,
                        strat_labels=self.optuna_strat_labels_,
                        optuna_test_df=optuna_test_df,
                        optuna_test_target=optuna_test_target,
                    )
            else:
                self.best_params_ = {m: {} for m in self.enabled_models_}

            # OOF + full fit
            n = len(df)

            # Сохраняем разбиение на фолды для последующего анализа
            fold_id_arr = np.full(len(df), -1, dtype=int)
            for fold_id, (_, va_idx) in enumerate(
                self._iter_splits(
                    X=X,
                    y=y,
                    groups=groups,
                    n_splits=self.config.n_splits,
                    strat_labels=self.split_strat_labels_,
                )
            ):
                fold_id_arr[va_idx] = fold_id

            fold_assignments = pd.DataFrame(index=df.index)
            fold_assignments["fold_id"] = fold_id_arr
            fold_assignments[self.config.target_col] = df[self.config.target_col].values

            if self.config.group_col is not None:
                fold_assignments[self.config.group_col] = df[self.config.group_col].values

            for col in self.config.balance_columns:
                fold_assignments[col] = df[col].values

            if self.split_strat_labels_ is not None:
                fold_assignments["split_stratum"] = self.split_strat_labels_

            self.fold_assignments_ = fold_assignments

            for model_name in self.enabled_models_:
                oof = np.zeros(n, dtype=float)
                fold_scores: List[float] = []

                fold_global_metrics: List[Dict[str, float]] = []
                fold_bin_reports: List[pd.DataFrame] = []
                stored_fold_models: List[Any] = []
                stored_fold_oof_predictions: List[np.ndarray] = []

                for fold_id, (tr_idx, va_idx) in enumerate(
                    self._iter_splits(
                        X=X,
                        y=y,
                        groups=groups,
                        n_splits=self.config.n_splits,
                        strat_labels=self.split_strat_labels_,
                    )
                ):
                    X_tr = X.iloc[tr_idx].copy()
                    X_va = X.iloc[va_idx].copy()
                    y_tr = y[tr_idx]
                    y_va = y[va_idx]

                    model = self._build_model(model_name, self.best_params_[model_name])
                    model = self._fit_one_model_with_valid(model_name, model, X_tr, y_tr, X_va, y_va, fold_id=fold_id)

                    pred = self._predict_one_model(model_name, model, X_va)
                    oof[va_idx] = pred

                    fold_oof = np.full(n, np.nan, dtype=float)
                    fold_oof[va_idx] = pred
                    stored_fold_oof_predictions.append(fold_oof)
                    
                    fold_global = self._build_global_metrics(y_va, pred)
                    fold_bin = self._build_bin_report(
                        y_true=y_va,
                        y_pred=pred,
                        y_reference_for_edges=y_tr,  # ВАЖНО: без утечки
                    )

                    fold_global_metrics.append(fold_global)
                    fold_bin_reports.append(fold_bin)

                    if self.config.cv_score_mode == "composite_optuna":
                        fold_score = self._optuna_score_from_reports(fold_global, fold_bin)
                    else:
                        fold_score = self._score(y_va, pred)

                    fold_scores.append(float(fold_score))

                    if self.config.final_fit_mode in {"fold_ensemble", "hybrid"}:
                        stored_fold_models.append(model)

                self.oof_predictions_[model_name] = oof
                self.oof_fold_predictions_[model_name] = stored_fold_oof_predictions
                self.cv_scores_per_fold_[model_name] = fold_scores
                self.cv_scores_[model_name] = float(np.mean(fold_scores))

                self.cv_global_metrics_per_fold_[model_name] = fold_global_metrics
                self.cv_bin_reports_per_fold_[model_name] = fold_bin_reports
                self.fold_models_[model_name] = stored_fold_models

                full_model = self._build_model(model_name, self.best_params_[model_name])
                full_model = self._fit_one_model(model_name, full_model, X, y)
                self.full_models_[model_name] = full_model

            self.model_weights_ = self._build_ensemble_weights()

            # OOF-метрики по отдельным моделям
            for model_name, oof_pred in self.oof_predictions_.items():
                self.oof_global_metrics_[model_name] = self._build_global_metrics(y, oof_pred)
                self.oof_bin_reports_[model_name] = self._build_bin_report(
                    y_true=y,
                    y_pred=oof_pred,
                    y_reference_for_edges=y,  # это уже post-hoc analysis, не влияет на fit
                )

            # OOF-метрики ансамбля
            oof_pred_df = pd.DataFrame(
                {name: pred for name, pred in self.oof_predictions_.items()},
                index=df.index,
            )
            ensemble_oof_pred = self._ensemble_predict_from_pred_df(oof_pred_df)

            self.ensemble_oof_global_metrics_ = self._build_global_metrics(y, ensemble_oof_pred)
            self.ensemble_oof_bin_report_ = self._build_bin_report(
                y_true=y,
                y_pred=ensemble_oof_pred,
                y_reference_for_edges=y,
            )

            self.is_fitted_ = True
            return self

    def _append_oof_detail_columns(self, oof_df: pd.DataFrame) -> pd.DataFrame:
            if self.fold_assignments_ is not None and "fold_id" in self.fold_assignments_.columns:
                oof_df["oof_fold_id"] = self.fold_assignments_["fold_id"].values

            for model_name, fold_preds in self.oof_fold_predictions_.items():
                for fold_id, fold_oof in enumerate(fold_preds):
                    oof_df[f"{model_name}__fold_{fold_id}_oof"] = fold_oof

            return oof_df

    def _build_prediction_detail_df(
            self,
            X: pd.DataFrame,
            index: pd.Index,
        ) -> pd.DataFrame:
            data: Dict[str, np.ndarray] = {}
            mode = self.config.final_fit_mode

            for model_name in self.enabled_models_:
                fold_models = self.fold_models_.get(model_name, [])
                if fold_models and mode in {"fold_ensemble", "hybrid"}:
                    fold_stack = []
                    for fold_id, model in enumerate(fold_models):
                        pred = self._predict_one_model(model_name, model, X)
                        data[f"{model_name}__fold_{fold_id}"] = pred
                        fold_stack.append(pred)
                    data[f"{model_name}__fold_mean"] = np.mean(np.column_stack(fold_stack), axis=1)

                full_model = self.full_models_.get(model_name)
                if full_model is not None and mode in {"full_refit", "hybrid"}:
                    data[f"{model_name}__full_refit"] = self._predict_one_model(model_name, full_model, X)

            if not data:
                return pd.DataFrame(index=index)

            return pd.DataFrame(data, index=index)
    
    def predict(
            self,
            df: pd.DataFrame,
            include_detail_columns: bool = False,
        ) -> pd.DataFrame:
            self._check_is_fitted()
            X = self._build_feature_frame(df, fit_mode=False)

            preds: Dict[str, np.ndarray] = {}
            prev_prefer = self.gnn_predict_prefer_inference_
            self.gnn_predict_prefer_inference_ = True
            try:
                for model_name in self.enabled_models_:
                    preds[model_name] = self._predict_base_model_final(model_name, X)
            finally:
                self.gnn_predict_prefer_inference_ = prev_prefer

            pred_df = pd.DataFrame(preds, index=df.index)

            if include_detail_columns:
                prev_prefer = self.gnn_predict_prefer_inference_
                self.gnn_predict_prefer_inference_ = True
                try:
                    detail_df = self._build_prediction_detail_df(X=X, index=df.index)
                finally:
                    self.gnn_predict_prefer_inference_ = prev_prefer
                if not detail_df.empty:
                    pred_df = pd.concat([pred_df, detail_df], axis=1)

            pred_df["ensemble"] = self._ensemble_predict_from_pred_df(pred_df)
            return pred_df

    def fit_predict_oof(
            self,
            df: pd.DataFrame,
            optuna_test_df: Optional[pd.DataFrame] = None,
            optuna_test_target_col: Optional[str] = None,
            include_fold_columns: bool = False,
        ) -> pd.DataFrame:
            self.fit(
                df,
                optuna_test_df=optuna_test_df,
                optuna_test_target_col=optuna_test_target_col,
            )

            df_used = df.loc[self.fit_filtered_df_index_].copy() if self.fit_filtered_df_index_ is not None else df.copy()

            oof_df = pd.DataFrame(
                {name: pred for name, pred in self.oof_predictions_.items()},
                index=df_used.index,
            )

            if include_fold_columns:
                oof_df = self._append_oof_detail_columns(oof_df)

            oof_df["ensemble"] = self._ensemble_predict_from_pred_df(oof_df)

            if "filename" in df_used.columns:
                 oof_df["filename"] = df_used["filename"].values

            oof_df[self.config.target_col] = df_used[self.config.target_col].values

            y_true = oof_df[self.config.target_col].to_numpy(dtype=float)
            y_pred = oof_df["ensemble"].to_numpy(dtype=float)

            abs_error = self._safe_abs_error(y_true, y_pred)
            pct_error_to_true = self._safe_pct_error_to_true(y_true, y_pred)
            pct_error_to_pred = self._safe_pct_error_to_pred(y_true, y_pred)
            business_penalty = self._sample_business_rule_penalty(y_true, y_pred)

            cfg = self.config.business_loss_config
            small_mask = y_true < cfg.small_target_threshold
            large_mask = ~small_mask

            small_rule_violation = small_mask & (abs_error > cfg.small_abs_error_limit)
            large_rule_violation_true = (
                large_mask & (pct_error_to_true > cfg.large_pct_error_to_true_limit)
            )
            large_rule_violation_pred = (
                large_mask & (pct_error_to_pred > cfg.large_pct_error_to_pred_limit)
            )

            oof_df["abs_error"] = abs_error
            oof_df["pct_error_to_true"] = pct_error_to_true
            oof_df["pct_error_to_pred"] = pct_error_to_pred

            oof_df["small_case_flag"] = small_mask.astype(int)
            oof_df["large_case_flag"] = large_mask.astype(int)

            oof_df["small_rule_violation"] = small_rule_violation.astype(int)
            oof_df["large_rule_violation_true"] = large_rule_violation_true.astype(int)
            oof_df["large_rule_violation_pred"] = large_rule_violation_pred.astype(int)

            oof_df["business_rule_violation"] = (
                small_rule_violation | large_rule_violation_true | large_rule_violation_pred
            ).astype(int)

            oof_df["business_rule_penalty"] = business_penalty
            oof_df["negative_pred_flag"] = (y_pred < 0.0).astype(int)

            self.last_oof_df_ = oof_df.copy()

            return oof_df

    def get_summary(self) -> Dict[str, Any]:
            self._check_is_fitted()
            return {
                "enabled_models": self.enabled_models_,
                "best_params": self.best_params_,
                "cv_scores": self.cv_scores_,
                "cv_scores_per_fold": self.cv_scores_per_fold_,
                "model_weights": self.model_weights_,
                "base_feature_columns": self.base_feature_columns_,
                "expanded_embedding_columns": self.expanded_embedding_columns_,
                "numeric_like_columns": self.numeric_like_columns_,
                "oof_global_metrics": self.oof_global_metrics_,
                "ensemble_oof_global_metrics": self.ensemble_oof_global_metrics_,
                "balance_columns": self.config.balance_columns,
                "cv_score_mode": self.config.cv_score_mode,
                "optuna_objective_mode": self.config.optuna_objective_mode,
                "optuna_test_score_weight": self.config.optuna_test_score_weight,
                "target_transform": self.config.target_transform,
                "final_fit_mode": self.config.final_fit_mode,
                "hybrid_full_weight": self.config.hybrid_full_weight,
                "stored_fold_models_per_model": {k: len(v) for k, v in self.fold_models_.items()},
                "optuna_models_with_trials": list(self.optuna_trials_metrics_.keys()),
                "split_strat_nunique": int(pd.Series(self.split_strat_labels_).nunique()) if self.split_strat_labels_ is not None else 0,
                "excluded_training_rows_count": int(len(self.excluded_training_rows_)),
                "exclusion_log": list(self.exclusion_log_),
            }

    def get_oof_metrics_table(self) -> pd.DataFrame:
            self._check_is_fitted()

            rows = []
            for model_name, metrics in self.oof_global_metrics_.items():
                row = {"model": model_name, **metrics}
                rows.append(row)

            if self.ensemble_oof_global_metrics_:
                rows.append({"model": "ensemble", **self.ensemble_oof_global_metrics_})

            return pd.DataFrame(rows)

    def get_bin_report(self, model_name: str = "ensemble") -> pd.DataFrame:
            self._check_is_fitted()

            if model_name == "ensemble":
                return self.ensemble_oof_bin_report_.copy()

            if model_name not in self.oof_bin_reports_:
                raise ValueError(f"Неизвестная модель для bin report: {model_name}")

            return self.oof_bin_reports_[model_name].copy()

    def get_optuna_trials_metrics_table(self) -> pd.DataFrame:
            self._check_is_fitted()
            if not self.optuna_trials_metrics_:
                return pd.DataFrame()
            tables = []
            for model_name, df_trials in self.optuna_trials_metrics_.items():
                if df_trials is None or df_trials.empty:
                    continue
                tables.append(df_trials.copy())
            if not tables:
                return pd.DataFrame()
            return pd.concat(tables, axis=0, ignore_index=True)

    def _build_segment_metrics_table(
            self,
            df_with_pred: pd.DataFrame,
            segment_col: str,
            pred_col: str = "ensemble",
            min_size: int = 5,
        ) -> pd.DataFrame:
            if segment_col not in df_with_pred.columns:
                raise ValueError(f"Колонка не найдена: {segment_col}")

            target_col = self.config.target_col
            rows: List[Dict[str, Any]] = []

            for seg_value, chunk in df_with_pred.groupby(segment_col, dropna=False):
                if len(chunk) < min_size:
                    continue

                y_true = chunk[target_col].to_numpy(dtype=float)
                y_pred = chunk[pred_col].to_numpy(dtype=float)

                metrics = self._build_global_metrics(y_true, y_pred)

                row = {
                    "segment_col": segment_col,
                    "segment_value": str(seg_value),
                    "n": int(len(chunk)),
                    "share": float(len(chunk) / max(len(df_with_pred), 1)),
                    "target_mean": float(np.mean(y_true)),
                    "target_median": float(np.median(y_true)),
                    "pred_mean": float(np.mean(y_pred)),
                    "pred_median": float(np.median(y_pred)),
                }
                row.update(metrics)
                rows.append(row)

            out = pd.DataFrame(rows)
            if not out.empty:
                out = out.sort_values(["rmsle", "wape", "n"], ascending=[False, False, False]).reset_index(drop=True)
            return out

    def get_fold_distribution_table(self) -> pd.DataFrame:
            self._check_is_fitted()

            if self.fold_assignments_ is None or self.fold_assignments_.empty:
                return pd.DataFrame()

            df = self.fold_assignments_.copy()

            # target bins для анализа разбиения
            edges = self._resolve_analysis_bin_edges(df[self.config.target_col].to_numpy(dtype=float))
            df["analysis_bin_id"] = self._assign_analysis_bin_ids(
                df[self.config.target_col].to_numpy(dtype=float),
                edges,
            )

            group_cols = ["fold_id", "analysis_bin_id"]
            for col in self.config.balance_columns:
                if col in df.columns:
                    group_cols.append(col)

            out = (
                df.groupby(group_cols, dropna=False)
                .size()
                .reset_index(name="n")
            )

            totals = df.groupby("fold_id").size().rename("fold_total").reset_index()
            out = out.merge(totals, on="fold_id", how="left")
            out["share_in_fold"] = out["n"] / out["fold_total"]

            return out.sort_values(group_cols).reset_index(drop=True)

    def get_segment_metrics_table(
            self,
            df_source: pd.DataFrame,
            segment_columns: Optional[List[str]] = None,
            pred_col: str = "ensemble",
            min_size: int = 5,
        ) -> pd.DataFrame:
            self._check_is_fitted()

            if self.last_oof_df_ is None or self.last_oof_df_.empty:
                raise RuntimeError("Сначала вызовите fit_predict_oof(df), чтобы получить OOF-таблицу.")

            if segment_columns is None:
                segment_columns = []
                if self.config.group_col:
                    segment_columns.append(self.config.group_col)
                segment_columns.extend(self.config.balance_columns)

            segment_columns = list(dict.fromkeys(segment_columns))
            if not segment_columns:
                return pd.DataFrame()

            oof_df = self.last_oof_df_.copy()

            for col in segment_columns:
                if col not in oof_df.columns:
                    if col not in df_source.columns:
                        raise ValueError(f"Колонка {col} отсутствует и в oof_df, и в исходном df")
                    source_aligned = df_source.loc[oof_df.index]
                    oof_df[col] = source_aligned[col].values

            tables = []
            for col in segment_columns:
                seg_table = self._build_segment_metrics_table(
                    df_with_pred=oof_df,
                    segment_col=col,
                    pred_col=pred_col,
                    min_size=min_size,
                )
                if not seg_table.empty:
                    tables.append(seg_table)

            if not tables:
                return pd.DataFrame()

            return pd.concat(tables, axis=0, ignore_index=True)

    def get_worst_cases_summary(
            self,
            top_n: int = 50,
            sort_by: str = "business_rule_penalty",
        ) -> pd.DataFrame:
            self._check_is_fitted()

            if self.last_oof_df_ is None or self.last_oof_df_.empty:
                raise RuntimeError("Сначала вызовите fit_predict_oof(df), чтобы получить OOF-таблицу.")

            if sort_by not in self.last_oof_df_.columns:
                raise ValueError(f"Колонка для сортировки не найдена: {sort_by}")

            df = self.last_oof_df_.copy()
            worst = df.sort_values(sort_by, ascending=False).head(top_n).copy()

            rows = []

            def _safe_rate(col: str) -> float:
                if col not in worst.columns:
                    return 0.0
                return float(worst[col].mean())

            rows.append({
                "slice_name": f"top_{top_n}_by_{sort_by}",
                "n": int(len(worst)),
                "target_mean": float(worst[self.config.target_col].mean()),
                "target_median": float(worst[self.config.target_col].median()),
                "pred_mean": float(worst["ensemble"].mean()),
                "pred_median": float(worst["ensemble"].median()),
                "abs_error_mean": float(worst["abs_error"].mean()) if "abs_error" in worst.columns else np.nan,
                "pct_error_to_true_mean": float(worst["pct_error_to_true"].mean()) if "pct_error_to_true" in worst.columns else np.nan,
                "pct_error_to_pred_mean": float(worst["pct_error_to_pred"].mean()) if "pct_error_to_pred" in worst.columns else np.nan,
                "business_rule_penalty_mean": float(worst["business_rule_penalty"].mean()) if "business_rule_penalty" in worst.columns else np.nan,
                "business_rule_violation_rate": _safe_rate("business_rule_violation"),
                "small_rule_violation_rate": _safe_rate("small_rule_violation"),
                "large_rule_violation_true_rate": _safe_rate("large_rule_violation_true"),
                "large_rule_violation_pred_rate": _safe_rate("large_rule_violation_pred"),
                "negative_pred_rate": _safe_rate("negative_pred_flag"),
                "rmsle": self._rmsle(
                    worst[self.config.target_col].to_numpy(dtype=float),
                    worst["ensemble"].to_numpy(dtype=float),
                ),
                "wape": self._wape(
                    worst[self.config.target_col].to_numpy(dtype=float),
                    worst["ensemble"].to_numpy(dtype=float),
                ),
            })

            return pd.DataFrame(rows)

    def get_balance_columns_bin_report(
            self,
            df_source: pd.DataFrame,
            balance_columns: Optional[List[str]] = None,
            pred_col: str = "ensemble",
            min_segment_size: int = 5,
            min_bin_size: Optional[int] = None,
        ) -> pd.DataFrame:
            self._check_is_fitted()

            if self.last_oof_df_ is None or self.last_oof_df_.empty:
                raise RuntimeError("Сначала вызовите fit_predict_oof(df), чтобы получить OOF-таблицу.")

            if pred_col not in self.last_oof_df_.columns:
                raise ValueError(f"Колонка предсказаний не найдена: {pred_col}")

            if balance_columns is None:
                balance_columns = list(self.config.balance_columns or [])
            balance_columns = list(dict.fromkeys(balance_columns))
            if not balance_columns:
                return pd.DataFrame()

            oof_df = self.last_oof_df_.copy()
            for col in balance_columns:
                if col not in oof_df.columns:
                    if col not in df_source.columns:
                        raise ValueError(f"Колонка {col} отсутствует и в oof_df, и в исходном df")
                    source_aligned = df_source.loc[oof_df.index]
                    oof_df[col] = source_aligned[col].values

            rows = []
            original_min_bin_size = self.config.bin_metric_config.min_bin_size
            effective_min_bin_size = original_min_bin_size if min_bin_size is None else int(min_bin_size)

            try:
                self.config.bin_metric_config.min_bin_size = effective_min_bin_size

                for segment_col in balance_columns:
                    for segment_value, chunk in oof_df.groupby(segment_col, dropna=False):
                        if len(chunk) < min_segment_size:
                            continue

                        y_true = chunk[self.config.target_col].to_numpy(dtype=float)
                        y_pred = chunk[pred_col].to_numpy(dtype=float)

                        segment_report = self._build_bin_report(
                            y_true=y_true,
                            y_pred=y_pred,
                            y_reference_for_edges=oof_df[self.config.target_col].to_numpy(dtype=float),
                        )

                        if segment_report.empty:
                            continue

                        segment_report.insert(0, "segment_value", str(segment_value))
                        segment_report.insert(0, "segment_col", segment_col)
                        segment_report.insert(2, "segment_n", int(len(chunk)))
                        segment_report.insert(3, "segment_share", float(len(chunk) / max(len(oof_df), 1)))
                        rows.append(segment_report)
            finally:
                self.config.bin_metric_config.min_bin_size = original_min_bin_size

            if not rows:
                return pd.DataFrame()

            out = pd.concat(rows, axis=0, ignore_index=True)
            return out.sort_values(["segment_col", "segment_value", "bin_id"]).reset_index(drop=True)


    def get_excluded_training_rows(self) -> pd.DataFrame:
            if self.excluded_training_rows_ is None or self.excluded_training_rows_.empty:
                return pd.DataFrame()
            return self.excluded_training_rows_.copy()
