from __future__ import annotations

from typing import Any, Dict, List, Optional

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .config import EnsembleConfig, FeatureSpec, ModelFlags
from .mixins.api import PublicApiMixin
from .mixins.features import FeatureEngineeringMixin
from .mixins.metrics import MetricsMixin
from .mixins.models import ModelingMixin
from .mixins.optuna import OptunaMixin
from .mixins.splitting import SplittingMixin


class FlexibleRegressorEnsemble(
    PublicApiMixin,
    FeatureEngineeringMixin,
    SplittingMixin,
    MetricsMixin,
    ModelingMixin,
    OptunaMixin,
):
    """
    Гибкий ансамбль с registry-моделей.

    Рефакторинг выполнен без изменения внешнего поведения: публичный API
    класса сохранён, а код разделён на тематические mixin-модули.
    """
    def __init__(
            self,
            feature_spec: FeatureSpec,
            model_flags: ModelFlags,
            config: EnsembleConfig,
        ) -> None:
            self.feature_spec = feature_spec
            self.model_flags = model_flags
            self.config = config

            self.enabled_models_: List[str] = []
            self.embedding_dims_: Dict[str, int] = {}
            self.expanded_embedding_columns_: List[str] = []
            self.base_feature_columns_: List[str] = []
            self.numeric_like_columns_: List[str] = []
            self.catboost_native_embedding_columns_: List[str] = []

            self.best_params_: Dict[str, Dict[str, Any]] = {}
            self.cv_scores_: Dict[str, float] = {}
            self.cv_scores_per_fold_: Dict[str, List[float]] = {}
            self.oof_predictions_: Dict[str, np.ndarray] = {}
            self.oof_fold_predictions_: Dict[str, List[np.ndarray]] = {}
            self.model_weights_: Dict[str, float] = {}
            self.full_models_: Dict[str, Any] = {}
            self.fold_models_: Dict[str, List[Any]] = {}

            self.is_fitted_: bool = False

            self.cv_global_metrics_per_fold_: Dict[str, List[Dict[str, float]]] = {}
            self.cv_bin_reports_per_fold_: Dict[str, List[pd.DataFrame]] = {}

            self.oof_global_metrics_: Dict[str, Dict[str, float]] = {}
            self.oof_bin_reports_: Dict[str, pd.DataFrame] = {}

            self.ensemble_oof_global_metrics_: Dict[str, float] = {}
            self.ensemble_oof_bin_report_: pd.DataFrame = pd.DataFrame()

            self.split_strat_labels_: Optional[np.ndarray] = None
            self.optuna_strat_labels_: Optional[np.ndarray] = None

            self.fold_assignments_: Optional[pd.DataFrame] = None
            self.last_oof_df_: Optional[pd.DataFrame] = None
            self.optuna_trials_metrics_: Dict[str, pd.DataFrame] = {}
            self.optuna_best_trials_summary_: Dict[str, Dict[str, Any]] = {}

            self.gnn_store_ = None
            self.gnn_reserved_part_key_col_: str = "__gnn_part_key__"
            self.gnn_predict_prefer_inference_: bool = False

            self.fit_input_df_index_: Optional[pd.Index] = None
            self.fit_filtered_df_index_: Optional[pd.Index] = None
            self.excluded_training_rows_: pd.DataFrame = pd.DataFrame()
            self.exclusion_log_: List[Dict[str, Any]] = []

    def _transform_target_for_fit(self, y: np.ndarray) -> np.ndarray:
            y = np.asarray(y, dtype=float)
            mode = self.config.target_transform

            if mode == "none":
                return y
            if mode == "log":
                if np.any(y <= 0):
                    raise ValueError("target_transform='log' требует строго положительный target")
                return np.log(y)
            if mode == "log1p":
                if np.any(y < -1.0):
                    raise ValueError("target_transform='log1p' требует y >= -1")
                return np.log1p(y)

            raise ValueError(f"Неизвестный target_transform: {mode}")

    def _inverse_target_after_predict(self, pred: np.ndarray) -> np.ndarray:
            pred = np.asarray(pred, dtype=float)
            mode = self.config.target_transform

            if mode == "none":
                return pred
            if mode == "log":
                return np.exp(pred)
            if mode == "log1p":
                return np.expm1(pred)

            raise ValueError(f"Неизвестный target_transform: {mode}")

    def _validate_target_transform_train(self, y: np.ndarray) -> None:
            _ = self._transform_target_for_fit(y)

    def _validate_final_fit_mode(self) -> None:
            mode = self.config.final_fit_mode
            if mode not in {"full_refit", "fold_ensemble", "hybrid"}:
                raise ValueError(f"Неизвестный final_fit_mode: {mode}")
            if not (0.0 <= float(self.config.hybrid_full_weight) <= 1.0):
                raise ValueError("hybrid_full_weight должен быть в диапазоне [0, 1]")

    def _predict_base_model_final(
            self,
            model_name: str,
            X: pd.DataFrame,
        ) -> np.ndarray:
            mode = self.config.final_fit_mode

            if mode == "full_refit":
                model = self.full_models_.get(model_name)
                if model is None:
                    raise ValueError(f"Не найдена full_model для {model_name}")
                return self._predict_one_model(model_name, model, X)

            fold_models = self.fold_models_.get(model_name, [])
            if not fold_models:
                model = self.full_models_.get(model_name)
                if model is None:
                    raise ValueError(f"Не найдена ни full_model, ни fold_models для {model_name}")
                return self._predict_one_model(model_name, model, X)

            fold_preds = np.column_stack([
                self._predict_one_model(model_name, m, X) for m in fold_models
            ])
            fold_mean = np.mean(fold_preds, axis=1)

            if mode == "fold_ensemble":
                return fold_mean

            if mode == "hybrid":
                full_model = self.full_models_.get(model_name)
                if full_model is None:
                    return fold_mean
                full_pred = self._predict_one_model(model_name, full_model, X)
                w = float(self.config.hybrid_full_weight)
                return w * full_pred + (1.0 - w) * fold_mean

            raise ValueError(f"Неизвестный final_fit_mode: {mode}")

    def _check_is_fitted(self) -> None:
            if not self.is_fitted_:
                raise RuntimeError("Сначала вызовите fit().")

    def get_inference_schema(self) -> Dict[str, Any]:
            self._check_is_fitted()
            required_columns = (
                list(self.feature_spec.numeric_features)
                + list(self.feature_spec.categorical_features)
                + list(self.feature_spec.embedding_features)
            )
            if self._gnn_enabled():
                required_columns.append(self._get_gnn_part_key_col())

            return {
                "required_input_columns": list(dict.fromkeys(required_columns)),
                "numeric_features": list(self.feature_spec.numeric_features),
                "categorical_features": list(self.feature_spec.categorical_features),
                "embedding_features": list(self.feature_spec.embedding_features),
                "catboost_embedding_features": list(self.feature_spec.catboost_embedding_features),
                "enabled_models": list(self.enabled_models_),
                "base_feature_columns": list(self.base_feature_columns_),
                "expanded_embedding_columns": list(self.expanded_embedding_columns_),
                "numeric_like_columns": list(self.numeric_like_columns_),
                "catboost_native_embedding_columns": list(self.catboost_native_embedding_columns_),
                "embedding_dims": dict(self.embedding_dims_),
                "model_weights": dict(self.model_weights_),
                "target_col": str(self.config.target_col),
                "target_transform": str(self.config.target_transform),
                "final_fit_mode": str(self.config.final_fit_mode),
                "hybrid_full_weight": float(self.config.hybrid_full_weight),
            }

    @staticmethod
    def _resolve_bundle_paths(path: str | Path) -> tuple[Path, Path]:
            raw_path = Path(path)
            if raw_path.suffix.lower() in {".joblib", ".pkl"}:
                bundle_path = raw_path
                manifest_path = raw_path.with_suffix(raw_path.suffix + ".manifest.json")
                bundle_path.parent.mkdir(parents=True, exist_ok=True)
                return bundle_path, manifest_path

            raw_path.mkdir(parents=True, exist_ok=True)
            return raw_path / "bundle.joblib", raw_path / "manifest.json"

    @staticmethod
    def _ensure_legacy_pickle_import_aliases() -> None:
            """Register old import names used inside previously saved joblib bundles.

            Some bundles were saved when ``flexible_ensemble`` was a top-level
            package.  In this backend it lives under ``ml_models``.  Pickle/joblib
            imports classes by their original module path, so loading such bundles
            requires the legacy module names to be importable.
            """
            import sys
            import importlib

            ml_models_dir = Path(__file__).resolve().parents[1]
            ml_models_dir_str = str(ml_models_dir)
            if ml_models_dir_str not in sys.path:
                sys.path.insert(0, ml_models_dir_str)

            aliases = {
                "flexible_ensemble": "ml_models.flexible_ensemble",
                "flexible_ensemble.config": "ml_models.flexible_ensemble.config",
                "flexible_ensemble.trainer": "ml_models.flexible_ensemble.trainer",
            }
            for legacy_name, current_name in aliases.items():
                if legacy_name not in sys.modules:
                    sys.modules[legacy_name] = importlib.import_module(current_name)

    @classmethod
    def load_bundle(cls, path: str | Path) -> Dict[str, Any]:
            raw_path = Path(path)
            bundle_path = raw_path if raw_path.is_file() else raw_path / "bundle.joblib"
            cls._ensure_legacy_pickle_import_aliases()
            payload = joblib.load(bundle_path)
            if isinstance(payload, cls):
                trainer = payload
                return {
                    "trainer": trainer,
                    "extra_artifacts": {},
                    "manifest": trainer.get_inference_schema() if trainer.is_fitted_ else {},
                    "bundle_path": bundle_path,
                }
            if not isinstance(payload, dict) or "trainer" not in payload:
                raise ValueError("Некорректный формат bundle: ожидался dict с ключом 'trainer'")
            payload = dict(payload)
            payload["bundle_path"] = bundle_path
            return payload

    def save_bundle(
            self,
            path: str | Path,
            extra_artifacts: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Path]:
            self._check_is_fitted()
            bundle_path, manifest_path = self._resolve_bundle_paths(path)
            manifest = {
                "bundle_format": "flexible_ensemble_bundle_v1",
                "schema": self.get_inference_schema(),
            }
            payload = {
                "trainer": self,
                "extra_artifacts": dict(extra_artifacts or {}),
                "manifest": manifest,
            }
            joblib.dump(payload, bundle_path)
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            return {"bundle_path": bundle_path, "manifest_path": manifest_path}

