from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import json
import numpy as np
import pandas as pd


class OptunaMixin:
    def _mean_metrics_dicts(self, metrics_list: List[Dict[str, float]]) -> Dict[str, float]:
            if not metrics_list:
                return {}
            keys = sorted({k for d in metrics_list for k in d.keys()})
            out: Dict[str, float] = {}
            for key in keys:
                vals = [float(d[key]) for d in metrics_list if key in d and pd.notna(d[key])]
                out[key] = float(np.mean(vals)) if vals else np.nan
            return out

    def _flatten_metrics(self, metrics: Dict[str, float], prefix: str) -> Dict[str, float]:
            return {f"{prefix}{k}": float(v) if pd.notna(v) else np.nan for k, v in metrics.items()}

    def _get_gnn_optuna_config(self):
            return getattr(self.config, "gnn_optuna_config", None)

    def _get_gnn_reject_score(self) -> float:
            cfg = self._get_gnn_optuna_config()
            if cfg is None:
                return 1e9
            return float(getattr(cfg, "reject_score_value", 1e9))

    def _check_gnn_trial_instability(
            self,
            y_train: np.ndarray,
            train_pred: np.ndarray,
            cv_score: float,
            train_score: float,
        ) -> Optional[str]:
            cfg = self._get_gnn_optuna_config()
            if cfg is None:
                return None
            if bool(getattr(cfg, "reject_on_nonfinite", True)):
                if not np.all(np.isfinite(train_pred)):
                    return "nonfinite_train_pred"
                if not np.isfinite(float(cv_score)):
                    return "nonfinite_cv_score"
                if not np.isfinite(float(train_score)):
                    return "nonfinite_train_score"
            y_arr = np.asarray(y_train, dtype=float)
            pred_arr = np.asarray(train_pred, dtype=float)
            if y_arr.size and pred_arr.size:
                y_max = float(np.nanmax(y_arr))
                pred_max = float(np.nanmax(pred_arr))
                max_mult = float(getattr(cfg, "reject_pred_above_train_multiplier", 3.0))
                if np.isfinite(y_max) and np.isfinite(pred_max) and y_max > 0 and pred_max > y_max * max_mult:
                    return f"pred_max_above_train_max:{pred_max:.6g}>{y_max:.6g}*{max_mult:.3g}"
            ratio_limit = float(getattr(cfg, "reject_train_cv_ratio", 20.0))
            if ratio_limit > 0 and np.isfinite(float(cv_score)) and np.isfinite(float(train_score)):
                denom = max(abs(float(cv_score)), 1e-12)
                ratio = float(train_score) / denom
                if ratio > ratio_limit:
                    return f"train_cv_ratio:{ratio:.6g}>{ratio_limit:.6g}"
            return None

    def _prepare_optuna_trial_params(self, model_name: str, suggested_params: Dict[str, Any]) -> Dict[str, Any]:
            effective_params = dict(suggested_params or {})
            if model_name != "gnn":
                return effective_params
            cfg = self._get_gnn_optuna_config()
            if cfg is None or not bool(getattr(cfg, "enabled", True)):
                return effective_params
            if cfg.epochs_override is not None:
                effective_params["epochs"] = int(cfg.epochs_override)
            if cfg.early_stopping_patience_override is not None:
                effective_params["early_stopping_patience"] = int(cfg.early_stopping_patience_override)
            if cfg.eval_batch_size_override is not None:
                effective_params["eval_batch_size"] = int(cfg.eval_batch_size_override)
            if cfg.min_delta_override is not None:
                effective_params["min_delta"] = float(cfg.min_delta_override)
            return effective_params

    def _run_optuna(
            self,
            model_name: str,
            X: pd.DataFrame,
            y: np.ndarray,
            groups: Optional[np.ndarray],
            strat_labels: Optional[np.ndarray],
            optuna_test_df: Optional[pd.DataFrame],
            optuna_test_target: Optional[np.ndarray],
        ) -> Dict[str, Any]:
            try:
                import ml_models.flexible_ensemble.mixins.optuna as optuna
            except ImportError as e:
                raise ImportError("optuna не установлен, а use_optuna=True") from e

            trial_rows: List[Dict[str, Any]] = []

            def objective(trial) -> float:
                suggested_params = self._suggest_params(model_name, trial)
                params = self._prepare_optuna_trial_params(model_name, suggested_params)
                reject_reason: Optional[str] = None
                reject_score = self._get_gnn_reject_score() if model_name == "gnn" else 1e9
                scores: List[float] = []
                fold_global_metrics: List[Dict[str, float]] = []
                fold_bin_reports: List[List[Dict[str, Any]]] = []

                for fold_id, (tr_idx, va_idx) in enumerate(self._iter_splits(
                    X=X,
                    y=y,
                    groups=groups,
                    n_splits=self.config.optuna_n_splits,
                    strat_labels=strat_labels,
                )):
                    X_tr = X.iloc[tr_idx].copy()
                    X_va = X.iloc[va_idx].copy()
                    y_tr = y[tr_idx]
                    y_va = y[va_idx]

                    model = self._build_model(model_name, params)
                    model = self._fit_one_model_with_valid(model_name, model, X_tr, y_tr, X_va, y_va, fold_id=int(trial.number) * 100 + int(fold_id))
                    pred = self._predict_one_model(model_name, model, X_va)
                    if model_name == "gnn" and not np.all(np.isfinite(pred)):
                        reject_reason = f"nonfinite_valid_pred_fold_{fold_id}"
                        break

                    global_metrics = self._build_global_metrics(y_va, pred)
                    bin_report = self._build_bin_report(
                        y_true=y_va,
                        y_pred=pred,
                        y_reference_for_edges=y_tr,
                    )

                    fold_score = self._get_optuna_objective_value(global_metrics, bin_report)

                    scores.append(float(fold_score))
                    fold_global_metrics.append(global_metrics)
                    fold_bin_reports.append(bin_report.to_dict(orient="records"))

                cv_score = float(np.mean(scores)) if scores else float(reject_score)
                cv_mean_metrics = self._mean_metrics_dicts(fold_global_metrics)
                train_global_metrics: Dict[str, float] = {}
                train_bin_report = pd.DataFrame()
                train_score = float(reject_score)
                final_score = float(reject_score) if reject_reason is not None else float(cv_score)
                test_score = np.nan
                test_global_metrics: Dict[str, float] = {}
                test_bin_report = pd.DataFrame()

                if reject_reason is None:
                    full_model = self._build_model(model_name, params)
                    full_model = self._fit_one_model(model_name, full_model, X, y)
                    train_pred = self._predict_one_model(model_name, full_model, X)
                    train_global_metrics = self._build_global_metrics(y, train_pred)
                    train_bin_report = self._build_bin_report(
                        y_true=y,
                        y_pred=train_pred,
                        y_reference_for_edges=y,
                    )
                    train_score = self._get_optuna_objective_value(train_global_metrics, train_bin_report)
                    if model_name == "gnn":
                        reject_reason = self._check_gnn_trial_instability(y_train=y, train_pred=train_pred, cv_score=cv_score, train_score=train_score)
                        if reject_reason is not None:
                            final_score = float(reject_score)

                if reject_reason is None and self.config.optuna_test_score_weight > 0.0 and optuna_test_df is not None and optuna_test_target is not None:
                    X_test = self._build_feature_frame(optuna_test_df, fit_mode=False)
                    prev_prefer = self.gnn_predict_prefer_inference_
                    self.gnn_predict_prefer_inference_ = True
                    try:
                        test_pred = self._predict_one_model(model_name, full_model, X_test)
                    finally:
                        self.gnn_predict_prefer_inference_ = prev_prefer
                    if model_name == "gnn" and not np.all(np.isfinite(test_pred)):
                        reject_reason = "nonfinite_test_pred"
                        final_score = float(reject_score)
                    else:
                        test_global_metrics = self._build_global_metrics(optuna_test_target, test_pred)
                        test_bin_report = self._build_bin_report(
                            y_true=optuna_test_target,
                            y_pred=test_pred,
                            y_reference_for_edges=y,
                        )
                        test_score = self._get_optuna_objective_value(test_global_metrics, test_bin_report)
                        w = float(np.clip(self.config.optuna_test_score_weight, 0.0, 1.0))
                        final_score = float((1.0 - w) * cv_score + w * test_score)
                        trial.set_user_attr("test_score", test_score)
                        trial.set_user_attr("test_global_metrics", test_global_metrics)
                        trial.set_user_attr("test_bin_reports", test_bin_report.to_dict(orient="records"))

                if reject_reason is None and not np.isfinite(float(final_score)):
                    reject_reason = "nonfinite_final_score"
                    final_score = float(reject_score)

                trial.set_user_attr("fold_scores", scores)
                trial.set_user_attr("cv_score", cv_score)
                trial.set_user_attr("train_score", train_score)
                trial.set_user_attr("final_score", final_score)
                trial.set_user_attr("fold_global_metrics", fold_global_metrics)
                trial.set_user_attr("fold_bin_reports", fold_bin_reports)
                trial.set_user_attr("train_global_metrics", train_global_metrics)
                trial.set_user_attr("train_bin_reports", train_bin_report.to_dict(orient="records"))
                if reject_reason is not None:
                    trial.set_user_attr("reject_reason", reject_reason)

                row: Dict[str, Any] = {
                    "model": model_name,
                    "trial_number": int(trial.number),
                    "cv_score": float(cv_score),
                    "train_score": float(train_score),
                    "test_score": float(test_score) if pd.notna(test_score) else np.nan,
                    "final_score": float(final_score),
                    "reject_reason": reject_reason,
                    "params_json": json.dumps(suggested_params, ensure_ascii=False, default=str),
                    "effective_params_json": json.dumps(params, ensure_ascii=False, default=str),
                }
                row.update(self._flatten_metrics(cv_mean_metrics, "cv_"))
                if train_global_metrics:
                    row.update(self._flatten_metrics(train_global_metrics, "train_"))
                if test_global_metrics:
                    row.update(self._flatten_metrics(test_global_metrics, "test_"))
                trial_rows.append(row)

                return final_score

            if model_name == "gnn":
                gnn_optuna_cfg = self._get_gnn_optuna_config()
                if gnn_optuna_cfg is not None and not bool(getattr(gnn_optuna_cfg, "enabled", True)):
                    self.optuna_trials_metrics_[model_name] = pd.DataFrame()
                    self.optuna_best_trials_summary_[model_name] = {"skipped": True, "reason": "gnn_optuna_disabled"}
                    return {}

            sampler = optuna.samplers.TPESampler(seed=int(self.config.random_state))
            study = optuna.create_study(direction="minimize", sampler=sampler)
            study.optimize(
                objective,
                n_trials=self.config.optuna_trials,
                timeout=self.config.optuna_timeout,
                show_progress_bar=False,
            )

            trials_df = pd.DataFrame(trial_rows)
            if not trials_df.empty:
                trials_df = trials_df.sort_values(["model", "final_score", "trial_number"], ascending=[True, True, True]).reset_index(drop=True)
            self.optuna_trials_metrics_[model_name] = trials_df

            best_trial = study.best_trial
            self.optuna_best_trials_summary_[model_name] = {
                "trial_number": int(best_trial.number),
                "value": float(best_trial.value),
                "params": dict(best_trial.params),
                "cv_score": best_trial.user_attrs.get("cv_score"),
                "train_score": best_trial.user_attrs.get("train_score"),
                "test_score": best_trial.user_attrs.get("test_score"),
                "final_score": best_trial.user_attrs.get("final_score"),
                "train_global_metrics": best_trial.user_attrs.get("train_global_metrics"),
                "test_global_metrics": best_trial.user_attrs.get("test_global_metrics"),
            }
            return dict(best_trial.params)

    def _suggest_params(self, model_name: str, trial) -> Dict[str, Any]:
            if model_name == "mlp":
                return {
                    "hidden_layer_sizes": trial.suggest_categorical(
                        "hidden_layer_sizes",
                        [(128,), (256,), (256, 128), (512, 256)],
                    ),
                    "alpha": trial.suggest_float("alpha", 1e-6, 1e-2, log=True),
                    "learning_rate_init": trial.suggest_float(
                        "learning_rate_init", 1e-4, 5e-3, log=True
                    ),
                    "max_iter": trial.suggest_int("max_iter", 250, 500),
                }

            if model_name == "ridge":
                return {
                    "alpha": trial.suggest_float("alpha", 1e-4, 100.0, log=True),
                }

            if model_name == "lasso":
                return {
                    "alpha": trial.suggest_float("alpha", 1e-5, 1.0, log=True),
                    "max_iter": trial.suggest_int("max_iter", 3000, 8000),
                }

            if model_name == "elasticnet":
                return {
                    "alpha": trial.suggest_float("alpha", 1e-5, 1.0, log=True),
                    "l1_ratio": trial.suggest_float("l1_ratio", 0.05, 0.95),
                    "max_iter": trial.suggest_int("max_iter", 3000, 8000),
                }

            if model_name == "svr":
                kernel = trial.suggest_categorical("kernel", ["rbf", "linear"])
                params = {
                    "C": trial.suggest_float("C", 1e-2, 100.0, log=True),
                    "epsilon": trial.suggest_float("epsilon", 1e-3, 1.0, log=True),
                    "kernel": kernel,
                }
                if kernel == "rbf":
                    params["gamma"] = trial.suggest_float("gamma", 1e-4, 10.0, log=True)
                return params

            if model_name == "gnn":
                cfg = self._get_gnn_optuna_config()
                hidden_dim_choices = list(getattr(cfg, "hidden_dim_choices", [64, 96, 128, 160]) or [64, 96, 128, 160])
                num_layers_choices = list(getattr(cfg, "num_layers_choices", [3, 4, 5, 6]) or [3, 4, 5, 6])
                batch_size_choices = list(getattr(cfg, "batch_size_choices", [16, 24, 32, 48]) or [16, 24, 32, 48])
                loss_choices = list(getattr(cfg, "loss_choices", ["huber", "mse", "l1"]) or ["huber", "mse", "l1"])
                train_eps_choices = list(getattr(cfg, "train_eps_choices", [False, True]) or [False, True])
                dropout_min, dropout_max = tuple(getattr(cfg, "dropout_range", (0.05, 0.35)))
                lr_min, lr_max = tuple(getattr(cfg, "lr_range", (3e-4, 3e-3)))
                weight_decay_min, weight_decay_max = tuple(getattr(cfg, "weight_decay_range", (1e-6, 3e-3)))
                return {
                    "hidden_dim": trial.suggest_categorical("hidden_dim", [int(v) for v in hidden_dim_choices]),
                    "num_layers": trial.suggest_categorical("num_layers", [int(v) for v in num_layers_choices]),
                    "dropout": trial.suggest_float("dropout", float(dropout_min), float(dropout_max)),
                    "lr": trial.suggest_float("lr", float(lr_min), float(lr_max), log=True),
                    "weight_decay": trial.suggest_float("weight_decay", float(weight_decay_min), float(weight_decay_max), log=True),
                    "batch_size": trial.suggest_categorical("batch_size", [int(v) for v in batch_size_choices]),
                    "loss": trial.suggest_categorical("loss", [str(v) for v in loss_choices]),
                    "train_eps": trial.suggest_categorical("train_eps", [bool(v) for v in train_eps_choices]),
                }

            if model_name == "lgbm":
                return {
                    "n_estimators": trial.suggest_int("n_estimators", 300, 1200),
                    "learning_rate": trial.suggest_float(
                        "learning_rate", 0.01, 0.15, log=True
                    ),
                    "num_leaves": trial.suggest_int("num_leaves", 8, 256),
                    "max_depth": trial.suggest_int("max_depth", 3, 8),
                    "min_child_samples": trial.suggest_int("min_child_samples", 5, 80),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                    "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 5.0),
                    "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 5.0),
                }

            if model_name == "catboost":
                return {
                    "iterations": trial.suggest_int("iterations", 300, 1200),
                    "learning_rate": trial.suggest_float(
                        "learning_rate", 0.01, 0.15, log=True
                    ),
                    "depth": trial.suggest_int("depth", 4, 8),
                    "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 15.0),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                }

            if model_name == "xgb":
                return {
                    "n_estimators": trial.suggest_int("n_estimators", 300, 1200),
                    "learning_rate": trial.suggest_float(
                        "learning_rate", 0.01, 0.15, log=True
                    ),
                    "max_depth": trial.suggest_int("max_depth", 3, 8),
                    "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 12.0),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                    "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 5.0),
                    "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 5.0),
                }

            if model_name == "rf":
                return {
                    "n_estimators": trial.suggest_int("n_estimators", 200, 1200),
                    "max_depth": trial.suggest_categorical(
                        "max_depth", [None, 4, 6, 8]
                    ),
                    "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                    "min_samples_leaf": trial.suggest_int("min_samples_leaf", 2, 10),
                    "max_features": trial.suggest_categorical(
                        "max_features", ["sqrt", "log2", 0.5, 0.8, 1.0]
                    ),
                }

            raise ValueError(f"Неизвестная модель для Optuna: {model_name}")

