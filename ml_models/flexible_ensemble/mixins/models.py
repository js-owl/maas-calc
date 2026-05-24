from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR

from ml_models.flexible_ensemble.gnn_backend import (
    GraphStore,
    attach_targets_to_graphs,
    fit_gnn_full_model,
    train_gnn_model,
    predict_graphs,
)


class ModelingMixin:
    def _get_model_registry(self) -> Dict[str, str]:
            return {
                "mlp": "pipeline_scaled",
                "ridge": "pipeline_scaled",
                "lasso": "pipeline_scaled",
                "elasticnet": "pipeline_scaled",
                "svr": "pipeline_scaled",
                "rf": "pipeline_unscaled",
                "xgb": "pipeline_unscaled",
                "lgbm": "lgbm_native",
                "catboost": "catboost_native",
                "gnn": "gnn_native",
            }

    def _validate_model_names(self, model_names: List[str]) -> List[str]:
            registry = self._get_model_registry()
            unknown = [m for m in model_names if m not in registry]
            if unknown:
                raise ValueError(
                    f"Неизвестные модели: {unknown}. Поддерживаются: {sorted(registry)}"
                )
            return list(dict.fromkeys(model_names))

    def _get_enabled_models(self) -> List[str]:
            if self.model_flags.models_override is not None and len(self.model_flags.models_override) > 0:
                return self._validate_model_names(self.model_flags.models_override)

            models = []
            if self.model_flags.use_mlp:
                models.append("mlp")
            if self.model_flags.use_lgbm:
                models.append("lgbm")
            if self.model_flags.use_catboost:
                models.append("catboost")
            if self.model_flags.use_xgb:
                models.append("xgb")
            if self.model_flags.use_rf:
                models.append("rf")
            if self.model_flags.use_gnn:
                models.append("gnn")

            models.extend(self.model_flags.extra_models)
            return self._validate_model_names(models)

    def _make_sklearn_preprocessor(
            self,
            scale_numeric: bool,
            sparse_ohe: bool = False,
        ) -> ColumnTransformer:
            transformers = []

            if self.numeric_like_columns_:
                num_steps = [("imputer", SimpleImputer(strategy="median"))]
                if scale_numeric:
                    num_steps.append(("scaler", StandardScaler()))
                num_pipe = Pipeline(num_steps)
                transformers.append(("num", num_pipe, self.numeric_like_columns_))

            if self.feature_spec.categorical_features:
                cat_pipe = Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=sparse_ohe)),
                    ]
                )
                transformers.append(("cat", cat_pipe, self.feature_spec.categorical_features))

            return ColumnTransformer(
                transformers=transformers,
                remainder="drop",
                verbose_feature_names_out=False,
                sparse_threshold=1.0 if sparse_ohe else 0.0,
            )

    def _build_pipeline_estimator(self, model_name: str, params: Dict[str, Any]) -> Any:
            if model_name == "mlp":
                return MLPRegressor(**params)
            if model_name == "ridge":
                return Ridge(**params)
            if model_name == "lasso":
                return Lasso(**params)
            if model_name == "elasticnet":
                return ElasticNet(**params)
            if model_name == "svr":
                return SVR(**params)
            if model_name == "rf":
                return RandomForestRegressor(**params)

            if model_name == "xgb":
                try:
                    from xgboost import XGBRegressor
                except ImportError as e:
                    raise ImportError("xgboost не установлен, а use_xgb=True") from e
                return XGBRegressor(**params)

            raise ValueError(f"Неизвестная pipeline-модель: {model_name}")

    def _initialize_gnn_store(self) -> None:
            if self.gnn_store_ is not None:
                return
            cfg = self.config.gnn_config
            if not cfg.enabled:
                raise ValueError("GNN store requested but config.gnn_config.enabled=False")
            if not cfg.dataset_dir:
                raise ValueError("Для GNN нужно задать config.gnn_config.dataset_dir")
            if not cfg.part_key_col:
                raise ValueError("Для GNN нужно задать config.gnn_config.part_key_col")
            self.gnn_store_ = GraphStore(
                train_dataset_dir=str(cfg.dataset_dir),
                inference_dataset_dir=str(cfg.inference_dataset_dir) if cfg.inference_dataset_dir else None,
            )

    def _get_gnn_model_params(self, tuned_params: Dict[str, Any]) -> Dict[str, Any]:
            cfg = self.config.gnn_config
            defaults = {
                "hidden_dim": int(cfg.hidden_dim),
                "num_layers": int(cfg.num_layers),
                "dropout": float(cfg.dropout),
                "train_eps": bool(cfg.train_eps),
                "epochs": int(cfg.epochs),
                "batch_size": int(cfg.batch_size),
                "eval_batch_size": int(cfg.eval_batch_size),
                "lr": float(cfg.lr),
                "weight_decay": float(cfg.weight_decay),
                "loss": str(cfg.loss),
                "monitor_metric": str(cfg.monitor_metric),
                "lr_factor": float(cfg.lr_factor),
                "lr_patience": int(cfg.lr_patience),
                "early_stopping_patience": int(cfg.early_stopping_patience),
                "min_delta": float(cfg.min_delta),
                "device": cfg.device,
                "prediction_cap_multiplier": float(cfg.prediction_cap_multiplier),
                "grad_clip_norm": float(cfg.grad_clip_norm),
                "weighted_loss_enabled": bool(cfg.weighted_loss_enabled),
                "weighted_loss_bins": int(cfg.weighted_loss_bins),
                "weighted_loss_power": float(cfg.weighted_loss_power),
                "weighted_loss_max_weight": float(cfg.weighted_loss_max_weight),
                "weighted_sampler_enabled": bool(cfg.weighted_sampler_enabled),
                "weighted_sampler_power": float(cfg.weighted_sampler_power),
                "weighted_sampler_max_weight": float(cfg.weighted_sampler_max_weight),
            }
            custom = self.config.custom_params.get("gnn", {})
            return {**defaults, **dict(tuned_params or {}), **custom}

    def _extract_gnn_part_keys(self, X: pd.DataFrame) -> List[str]:
            col = self.gnn_reserved_part_key_col_
            if col not in X.columns:
                raise ValueError(f"В feature frame отсутствует колонка part_key для GNN: {col}")
            return X[col].astype(str).tolist()

    def _get_gnn_graphs_from_X(
            self,
            X: pd.DataFrame,
            y: Optional[np.ndarray] = None,
            prefer_inference: Optional[bool] = None,
        ) -> List[Any]:
            self._initialize_gnn_store()
            prefer = self.gnn_predict_prefer_inference_ if prefer_inference is None else bool(prefer_inference)
            part_keys = self._extract_gnn_part_keys(X)
            graphs = self.gnn_store_.get_graphs_for_part_keys(part_keys, prefer_inference=prefer)
            if y is not None:
                graphs = attach_targets_to_graphs(graphs, y)
            return graphs

    def _build_model(self, model_name: str, tuned_params: Dict[str, Any]) -> Any:
            registry = self._get_model_registry()
            if model_name not in registry:
                raise ValueError(f"Неизвестная модель: {model_name}")

            if model_name == "gnn":
                self._initialize_gnn_store()
                return self._get_gnn_model_params(tuned_params)

            defaults = self._default_params(model_name)
            custom = self.config.custom_params.get(model_name, {})
            params = {**defaults, **tuned_params, **custom}
            family = registry[model_name]

            if family == "pipeline_scaled":
                pre = self._make_sklearn_preprocessor(scale_numeric=True)
                model = self._build_pipeline_estimator(model_name, params)
                return Pipeline([("preprocessor", pre), ("model", model)])

            if family == "pipeline_unscaled":
                sparse_ohe = model_name == "xgb"
                pre = self._make_sklearn_preprocessor(scale_numeric=False, sparse_ohe=sparse_ohe)
                model = self._build_pipeline_estimator(model_name, params)
                return Pipeline([("preprocessor", pre), ("model", model)])

            if family == "lgbm_native":
                try:
                    from lightgbm import LGBMRegressor
                except ImportError as e:
                    raise ImportError("lightgbm не установлен, а use_lgbm=True") from e
                return LGBMRegressor(**params)

            if family == "catboost_native":
                try:
                    from catboost import CatBoostRegressor
                except ImportError as e:
                    raise ImportError("catboost не установлен, а use_catboost=True") from e
                return CatBoostRegressor(**params)

            raise ValueError(f"Неизвестное семейство модели для {model_name}: {family}")

    def _default_params(self, model_name: str) -> Dict[str, Any]:
            rs = self.config.random_state
            defaults = {
                "mlp": {
                    "hidden_layer_sizes": (256, 128),
                    "activation": "relu",
                    "solver": "adam",
                    "alpha": 1e-4,
                    "learning_rate_init": 1e-3,
                    "max_iter": 400,
                    "early_stopping": True,
                    "validation_fraction": 0.1,
                    "n_iter_no_change": 20,
                    "random_state": rs,
                },
                "ridge": {"alpha": 1.0},
                "lasso": {
                    "alpha": 1e-3,
                    "max_iter": 5000,
                    "random_state": rs,
                },
                "elasticnet": {
                    "alpha": 1e-3,
                    "l1_ratio": 0.5,
                    "max_iter": 5000,
                    "random_state": rs,
                },
                "svr": {
                    "C": 1.0,
                    "epsilon": 0.1,
                    "kernel": "rbf",
                    "gamma": "scale",
                },
                "lgbm": {
                    "n_estimators": 600,
                    "learning_rate": 0.03,
                    "num_leaves": 31,
                    "max_depth": -1,
                    "min_child_samples": 20,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "random_state": rs,
                    "n_jobs": -1,
                    "verbosity": -1,
                },
                "catboost": {
                    "iterations": 700,
                    "learning_rate": 0.03,
                    "depth": 6,
                    "loss_function": "RMSE",
                    "eval_metric": "RMSE",
                    "random_seed": rs,
                    "verbose": False,
                },
                "xgb": {
                    "n_estimators": 700,
                    "learning_rate": 0.03,
                    "max_depth": 6,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "objective": "reg:squarederror",
                    "tree_method": "hist",
                    "random_state": rs,
                    "n_jobs": -1,
                },
                "rf": {
                    "n_estimators": 500,
                    "max_depth": None,
                    "min_samples_split": 2,
                    "min_samples_leaf": 1,
                    "max_features": "sqrt",
                    "n_jobs": -1,
                    "random_state": rs,
                },
            }
            return defaults[model_name]

    def _prepare_tree_input(
            self,
            X: pd.DataFrame,
            categorical_as_category: bool,
        ) -> pd.DataFrame:
            out = X[self.base_feature_columns_].copy()
            for col in self.numeric_like_columns_:
                out[col] = pd.to_numeric(out[col], errors="coerce")
            for col in self.feature_spec.categorical_features:
                s = out[col].astype("string").fillna("__MISSING__")
                out[col] = s.astype("category") if categorical_as_category else s
            return out

    def _prepare_catboost_input(self, X: pd.DataFrame) -> pd.DataFrame:
            cols = list(self.base_feature_columns_)
            for col in self.catboost_native_embedding_columns_:
                if col in X.columns and col not in cols:
                    cols.append(col)

            out = X[cols].copy()

            for col in self.numeric_like_columns_:
                if col in out.columns:
                    out[col] = pd.to_numeric(out[col], errors="coerce")

            for col in self.feature_spec.categorical_features:
                if col in out.columns:
                    out[col] = out[col].astype("string").fillna("__MISSING__")

            for col in self.catboost_native_embedding_columns_:
                if col in out.columns:
                    out[col] = [self._to_1d_float_array(v).astype(float).tolist() for v in out[col].values]

            return out
    
    def _make_safe_unique_feature_names(self, columns: List[Any]) -> List[str]:
            safe_names: List[str] = []
            used: Dict[str, int] = {}
            for col in columns:
                name = str(col)
                for bad in ['"', "'", "\\", "\n", "\r", "\t", "{", "}", "[", "]", ":", ","]:
                    name = name.replace(bad, "_")
                name = name.strip() or "feature"
                if name in used:
                    used[name] += 1
                    name = f"{name}__dup{used[name]}"
                else:
                    used[name] = 0
                safe_names.append(name)
            return safe_names

    def _prepare_lgbm_input(self, X: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
            out = self._prepare_tree_input(X, categorical_as_category=True)
            original_cols = list(out.columns)
            safe_cols = self._make_safe_unique_feature_names(original_cols)
            out.columns = safe_cols
            col_map = dict(zip(original_cols, safe_cols))
            cat_features = [col_map[c] for c in self.feature_spec.categorical_features if c in col_map]
            if out.shape[1] != len(out.columns):
                raise ValueError(f"LGBM input shape mismatch: {out.shape[1]} cols vs {len(out.columns)} names")
            if not pd.Index(out.columns).is_unique:
                dupes = pd.Index(out.columns)[pd.Index(out.columns).duplicated()].tolist()
                raise ValueError(f"LGBM columns are not unique after normalization: {dupes}")
            return out, cat_features

    def _fit_one_model(
            self,
            model_name: str,
            model: Any,
            X: pd.DataFrame,
            y: np.ndarray,
        ) -> Any:
            family = self._get_model_registry()[model_name]
            y_fit = self._transform_target_for_fit(y)

            if family in {"pipeline_scaled", "pipeline_unscaled"}:
                model.fit(X[self.base_feature_columns_], y_fit)
                return model

            if model_name == "lgbm":
                X_fit, cat_features = self._prepare_lgbm_input(X)
                fit_kwargs = {"X": X_fit, "y": y_fit, "feature_name": list(X_fit.columns)}
                if cat_features:
                    fit_kwargs["categorical_feature"] = cat_features
                model.fit(**fit_kwargs)
                return model

            if model_name == "catboost":
                X_fit = self._prepare_catboost_input(X)
                fit_kwargs = {"X": X_fit, "y": y_fit, "verbose": False}
                if self.feature_spec.categorical_features:
                    fit_kwargs["cat_features"] = self.feature_spec.categorical_features
                if self.catboost_native_embedding_columns_:
                    fit_kwargs["embedding_features"] = self.catboost_native_embedding_columns_
                model.fit(**fit_kwargs)
                return model

            if model_name == "gnn":
                train_graphs = self._get_gnn_graphs_from_X(X, y=y, prefer_inference=False)
                bundle = fit_gnn_full_model(
                    train_graphs_raw=train_graphs,
                    node_onehot_dim=self.gnn_store_.node_onehot_dim,
                    edge_onehot_dim=self.gnn_store_.edge_onehot_dim,
                    params=model,
                    target_transform=self.config.target_transform,
                    seed=int(self.config.random_state),
                )
                return bundle

            raise ValueError(f"Неизвестная модель: {model_name}")

    def _fit_one_model_with_valid(
            self,
            model_name: str,
            model: Any,
            X_tr: pd.DataFrame,
            y_tr: np.ndarray,
            X_va: pd.DataFrame,
            y_va: np.ndarray,
            fold_id: int,
        ) -> Any:
            if model_name != "gnn":
                return self._fit_one_model(model_name, model, X_tr, y_tr)
            train_graphs = self._get_gnn_graphs_from_X(X_tr, y=y_tr, prefer_inference=False)
            valid_graphs = self._get_gnn_graphs_from_X(X_va, y=y_va, prefer_inference=False)
            return train_gnn_model(
                train_graphs_raw=train_graphs,
                valid_graphs_raw=valid_graphs,
                node_onehot_dim=self.gnn_store_.node_onehot_dim,
                edge_onehot_dim=self.gnn_store_.edge_onehot_dim,
                params=model,
                target_transform=self.config.target_transform,
                seed=int(self.config.random_state + fold_id),
            )

    def _predict_one_model(
            self,
            model_name: str,
            model: Any,
            X: pd.DataFrame,
        ) -> np.ndarray:
            family = self._get_model_registry()[model_name]

            if family in {"pipeline_scaled", "pipeline_unscaled"}:
                raw_pred = np.asarray(model.predict(X[self.base_feature_columns_]), dtype=float)
                return self._inverse_target_after_predict(raw_pred)

            if model_name == "lgbm":
                X_pred, _ = self._prepare_lgbm_input(X)
                raw_pred = np.asarray(model.predict(X_pred), dtype=float)
                return self._inverse_target_after_predict(raw_pred)

            if model_name == "catboost":
                X_pred = self._prepare_catboost_input(X)
                raw_pred = np.asarray(model.predict(X_pred), dtype=float)
                return self._inverse_target_after_predict(raw_pred)

            if model_name == "gnn":
                graphs = self._get_gnn_graphs_from_X(X, y=None, prefer_inference=None)
                return np.asarray(
                    predict_graphs(
                        model=model.model,
                        graphs_raw=graphs,
                        norm_stats=model.norm_stats,
                        device=model.device,
                        target_transform=self.config.target_transform,
                        batch_size=int(getattr(self.config.gnn_config, "eval_batch_size", 64)),
                        return_targets=False,
                        final_prediction_upper=getattr(model, "final_prediction_upper", None),
                    ),
                    dtype=float,
                )

            raise ValueError(f"Неизвестная модель: {model_name}")
