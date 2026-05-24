from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class FeatureEngineeringMixin:


    def _gnn_enabled(self) -> bool:
            return bool(getattr(self.model_flags, "gnn_requested", lambda: False)())

    def _get_gnn_part_key_col(self) -> str:
            col = getattr(self.config.gnn_config, "part_key_col", None)
            if not col:
                raise ValueError("Для GNN нужно задать config.gnn_config.part_key_col")
            return str(col)
    def _map_transformed_feature_to_base(self, feature_name: str) -> str:
            # 1) точное совпадение с numeric
            if feature_name in self.feature_spec.numeric_features:
                return feature_name

            # 2) embedding expansion: emb_col__0 -> emb_col
            for emb_col in self.feature_spec.embedding_features:
                prefix = f"{emb_col}__"
                if feature_name.startswith(prefix):
                    return emb_col

            # 3) raw categorical feature (для catboost/lgbm без OHE)
            if feature_name in self.feature_spec.categorical_features:
                return feature_name

            # 4) one-hot encoded categorical: material_steel -> material
            for cat_col in self.feature_spec.categorical_features:
                prefix = f"{cat_col}_"
                if feature_name.startswith(prefix):
                    return cat_col

            return feature_name

    def _aggregate_importance_series(self, s: pd.Series) -> pd.Series:
            if s.empty:
                return s

            mapped_index = [self._map_transformed_feature_to_base(str(idx)) for idx in s.index]
            out = pd.DataFrame({"feature": mapped_index, "importance": s.values})
            out = out.groupby("feature", as_index=True)["importance"].sum()
            out = out.sort_values(ascending=False)
            return out

    def _extract_model_feature_importance_series(
            self,
            model_name: str,
            aggregate: bool = True,
            normalize: bool = True,
        ) -> pd.Series:
            self._check_is_fitted()

            if model_name not in self.full_models_:
                raise ValueError(f"Модель не найдена: {model_name}")

            if model_name == "mlp":
                raise ValueError(
                    "MLPRegressor не имеет надёжных нативных feature_importances_. "
                    "Для него лучше использовать permutation importance отдельной функцией."
                )

            model = self.full_models_[model_name]

            # -------------------------
            # sklearn pipeline models
            # -------------------------
            if model_name in {"rf", "xgb"}:
                preprocessor = model.named_steps["preprocessor"]
                estimator = model.named_steps["model"]

                feature_names = preprocessor.get_feature_names_out()
                if not hasattr(estimator, "feature_importances_"):
                    raise ValueError(f"У модели {model_name} нет feature_importances_")

                importances = np.asarray(estimator.feature_importances_, dtype=float)
                s = pd.Series(importances, index=feature_names, name="importance")

            # -------------------------
            # lightgbm
            # -------------------------
            elif model_name == "lgbm":
                if not hasattr(model, "feature_importances_"):
                    raise ValueError("У LGBMRegressor нет feature_importances_")

                if hasattr(model, "feature_name_") and model.feature_name_ is not None:
                    feature_names = list(model.feature_name_)
                else:
                    feature_names = list(self.base_feature_columns_)

                importances = np.asarray(model.feature_importances_, dtype=float)
                s = pd.Series(importances, index=feature_names, name="importance")

            # -------------------------
            # catboost
            # -------------------------
            elif model_name == "catboost":
                try:
                    importances = np.asarray(model.get_feature_importance(), dtype=float)
                except Exception as e:
                    raise ValueError(f"Не удалось получить feature importances у CatBoost: {e}") from e

                if hasattr(model, "feature_names_") and model.feature_names_:
                    feature_names = list(model.feature_names_)
                else:
                    feature_names = list(self.base_feature_columns_)

                s = pd.Series(importances, index=feature_names, name="importance")

            else:
                raise ValueError(f"Feature importances для модели {model_name} не поддерживаются")

            s = s.fillna(0.0)

            if aggregate:
                s = self._aggregate_importance_series(s)

            if normalize:
                total = float(s.sum())
                if total > 0:
                    s = s / total

            s = s.sort_values(ascending=False)
            return s

    def get_feature_importances(
            self,
            model_name: str = "ensemble",
            top_n: Optional[int] = None,
            aggregate: bool = True,
            normalize: bool = True,
        ) -> pd.DataFrame:
            """
            model_name:
                - "lgbm"
                - "catboost"
                - "xgb"
                - "rf"
                - "ensemble"

            aggregate=True:
                - material_steel/material_titanium -> material
                - emb_1__0/emb_1__1/... -> emb_1

            normalize=True:
                importances приводятся к сумме 1.0
            """
            self._check_is_fitted()

            if model_name == "ensemble":
                parts = []

                for base_model_name in self.enabled_models_:
                    if base_model_name == "mlp":
                        continue
                    if base_model_name not in self.full_models_:
                        continue

                    try:
                        s = self._extract_model_feature_importance_series(
                            model_name=base_model_name,
                            aggregate=aggregate,
                            normalize=True,   # для ансамбля обязательно нормализуем по моделям
                        )
                    except Exception:
                        continue

                    weight = float(self.model_weights_.get(base_model_name, 0.0))
                    if weight <= 0:
                        continue

                    parts.append(s * weight)

                if not parts:
                    raise ValueError("Не удалось собрать feature importances для ансамбля")

                s = pd.concat(parts, axis=1).fillna(0.0).sum(axis=1)
                s = s.sort_values(ascending=False)

                if normalize:
                    total = float(s.sum())
                    if total > 0:
                        s = s / total

            else:
                s = self._extract_model_feature_importance_series(
                    model_name=model_name,
                    aggregate=aggregate,
                    normalize=normalize,
                )

            if top_n is not None:
                s = s.head(top_n)

            return pd.DataFrame(
                {
                    "feature": s.index.astype(str),
                    "importance": s.values.astype(float),
                }
            )

    def _validate_columns(self, df: pd.DataFrame) -> None:
            required = (
                [self.config.target_col]
                + self.feature_spec.numeric_features
                + self.feature_spec.categorical_features
                + self.feature_spec.embedding_features
                + list(self.config.balance_columns or [])
            )
            if self.config.group_col is not None:
                required.append(self.config.group_col)
            if self._gnn_enabled():
                required.append(self._get_gnn_part_key_col())

            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"В df отсутствуют колонки: {missing}")

    def _validate_columns_for_inference(self, df: pd.DataFrame, require_target: bool = False) -> None:
            required = (
                ([] if not require_target else [self.config.target_col])
                + self.feature_spec.numeric_features
                + self.feature_spec.categorical_features
                + self.feature_spec.embedding_features
            )
            if self._gnn_enabled():
                required = list(required) + [self._get_gnn_part_key_col()]
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"В inference/eval df отсутствуют колонки: {missing}")

    def _build_feature_frame(self, df: pd.DataFrame, fit_mode: bool) -> pd.DataFrame:
            """
            embedding_features ожидаются как колонки, где каждая ячейка содержит
            list/tuple/np.ndarray фиксированной или плавающей длины.
            Они разворачиваются в emb_col__0, emb_col__1, ...
            """
            base = pd.DataFrame(index=df.index)

            # numeric
            for col in self.feature_spec.numeric_features:
                base[col] = pd.to_numeric(df[col], errors="coerce")

            # categorical
            for col in self.feature_spec.categorical_features:
                base[col] = df[col]

            # embeddings -> numeric expansion
            expanded_emb_cols: List[str] = []
            for emb_col in self.feature_spec.embedding_features:
                if not base.columns.is_unique:
                    dupes = base.columns[base.columns.duplicated()].tolist()
                    raise ValueError(f"После сборки feature frame получены дублирующиеся колонки: {dupes}")
                if fit_mode:
                    dim = int(df[emb_col].map(self._embedding_len).max())
                    self.embedding_dims_[emb_col] = dim
                else:
                    if emb_col not in self.embedding_dims_:
                        raise ValueError(f"Неизвестна размерность embedding-колонки {emb_col}")
                    dim = self.embedding_dims_[emb_col]

                mat = np.full((len(df), dim), np.nan, dtype=float)
                for i, val in enumerate(df[emb_col].values):
                    vec = self._to_1d_float_array(val)
                    if vec.size > 0:
                        use_dim = min(dim, vec.size)
                        mat[i, :use_dim] = vec[:use_dim]

                emb_names = [f"{emb_col}__{j}" for j in range(dim)]
                emb_df = pd.DataFrame(mat, index=df.index, columns=emb_names)
                base = pd.concat([base, emb_df], axis=1)
                expanded_emb_cols.extend(emb_names)

            feature_only_columns = base.columns.tolist()

            catboost_native_embedding_cols: List[str] = []
            for emb_col in self.feature_spec.catboost_embedding_features:
                if emb_col not in self.feature_spec.embedding_features:
                    raise ValueError(
                        f"catboost_embedding_features содержит колонку '{emb_col}', "
                        f"которая отсутствует в embedding_features"
                    )
                base[emb_col] = [self._to_1d_float_array(v).astype(float).tolist() for v in df[emb_col].values]
                catboost_native_embedding_cols.append(emb_col)
                
            if self._gnn_enabled():
                part_key_col = self._get_gnn_part_key_col()
                base[self.gnn_reserved_part_key_col_] = df[part_key_col].map(self._normalize_gnn_part_key)

            if fit_mode:
                self.expanded_embedding_columns_ = expanded_emb_cols
                self.base_feature_columns_ = feature_only_columns
                self.numeric_like_columns_ = (
                    list(self.feature_spec.numeric_features) + list(expanded_emb_cols)
                )
                self.catboost_native_embedding_columns_ = list(catboost_native_embedding_cols)

            return base

    @staticmethod
    def _normalize_gnn_part_key(x: Any) -> str:
            from ml_models.flexible_ensemble.gnn_backend import normalize_part_key
            return normalize_part_key(x)

    @staticmethod
    def _embedding_len(x: Any) -> int:
            return len(FeatureEngineeringMixin._to_1d_float_array(x))

    @staticmethod
    def _to_1d_float_array(x: Any) -> np.ndarray:
            if x is None:
                return np.array([], dtype=float)
            if isinstance(x, np.ndarray):
                return x.astype(float).ravel()
            if isinstance(x, (list, tuple)):
                return np.asarray(x, dtype=float).ravel()
            if isinstance(x, str):
                s = x.strip()
                if not s:
                    return np.array([], dtype=float)
                if s.startswith("[") and s.endswith("]"):
                    try:
                        import json
                        parsed = json.loads(s)
                        return np.asarray(parsed, dtype=float).ravel()
                    except Exception:
                        inner = s[1:-1].strip()
                        if not inner:
                            return np.array([], dtype=float)
                        parts = [p.strip() for p in inner.replace(";", ",").split(",") if p.strip()]
                        return np.asarray(parts, dtype=float).ravel()
            if pd.isna(x):
                return np.array([], dtype=float)
            return np.asarray([x], dtype=float)

