"""Direct in-process composite predictor based on flexible_ensemble bundle."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from constants import COMPOSITE_BUNDLE_PATH, ENABLE_COMPOSITE_MODEL

logger = logging.getLogger(__name__)


class CompositeMLPredictor:
    """Direct inference wrapper for the composite labor-intensity ensemble."""

    def __init__(self) -> None:
        self.bundle_path = Path(os.getenv("COMPOSITE_BUNDLE_PATH", COMPOSITE_BUNDLE_PATH))
        self._resolved_bundle_path: Optional[Path] = None
        self._trainer = None
        self._schema: Optional[Dict[str, Any]] = None

    def _resolve_bundle_path(self) -> Optional[Path]:
        if self._resolved_bundle_path is not None:
            return self._resolved_bundle_path

        candidates: list[Path] = []
        if self.bundle_path.exists():
            candidates.append(self.bundle_path)

        ml_models_dir = self.bundle_path.parent if self.bundle_path.parent.exists() else Path("ml_models")
        if ml_models_dir.exists():
            patterns = [
                "*composite*.pkl",
                "*composite*.joblib",
                "*metalcomposite*.pkl",
                "*metalcomposite*.joblib",
                "*.pkl",
                "*.joblib",
            ]
            for pattern in patterns:
                for candidate in sorted(ml_models_dir.glob(pattern)):
                    manifest = candidate.with_suffix(candidate.suffix + ".manifest.json")
                    if manifest.exists() or "composite" in candidate.name.lower() or "metalcomposite" in candidate.name.lower():
                        candidates.append(candidate)

        seen: set[str] = set()
        deduped: list[Path] = []
        for candidate in candidates:
            key = str(candidate.resolve()) if candidate.exists() else str(candidate)
            if key not in seen:
                seen.add(key)
                deduped.append(candidate)

        self._resolved_bundle_path = deduped[0] if deduped else None
        if self._resolved_bundle_path is not None:
            logger.info("Using composite bundle: %s", self._resolved_bundle_path)
        return self._resolved_bundle_path

    def _ensure_loaded(self) -> bool:
        if self._trainer is not None and self._schema is not None:
            return True

        bundle_path = self._resolve_bundle_path()
        if bundle_path is None or not bundle_path.exists():
            logger.warning("Composite bundle not found. Requested path: %s", self.bundle_path)
            return False

        try:
            from ml_models.flexible_ensemble.trainer import FlexibleRegressorEnsemble

            payload = FlexibleRegressorEnsemble.load_bundle(bundle_path)
            trainer = payload.get("trainer")
            if trainer is None:
                raise ValueError("Bundle does not contain trainer")
            self._trainer = trainer
            manifest = payload.get("manifest") if isinstance(payload, dict) else None
            if isinstance(manifest, dict) and isinstance(manifest.get("schema"), dict):
                self._schema = dict(manifest["schema"])
            else:
                self._schema = trainer.get_inference_schema()
            return True
        except Exception as e:
            logger.error("Failed to load composite flexible_ensemble bundle: %s", e)
            self._trainer = None
            self._schema = None
            return False

    def is_model_available(self) -> bool:
        if not ENABLE_COMPOSITE_MODEL:
            logger.info("Composite model disabled by configuration")
            return False
        return self._ensure_loaded()

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _build_feature_row(self, file_features: Dict[str, Any], material_info: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(file_features or {})
        file_info = row.get("file_info") or {}

        for bad_key in ["features", "file_info", "dimensions"]:
            if bad_key in row and isinstance(row[bad_key], dict):
                row.pop(bad_key, None)

        surface_area = self._safe_float(row.get("surface_area"), 0.0)
        surface_area_obb = self._safe_float(row.get("surface_area_obb"), 0.0)
        obb_x = self._safe_float(row.get("obb_x"), 0.0)
        obb_y = self._safe_float(row.get("obb_y"), 0.0)
        obb_z = self._safe_float(row.get("obb_z"), 0.0)

        if "bbox_volume" not in row or row.get("bbox_volume") in (None, ""):
            row["bbox_volume"] = obb_x * obb_y * obb_z
        if "surface_area_detail_obb_ratio" not in row or row.get("surface_area_detail_obb_ratio") in (None, ""):
            row["surface_area_detail_obb_ratio"] = (
                surface_area / surface_area_obb if surface_area_obb > 1e-12 else 0.0
            )
        if "diff_obb_detail_area" not in row or row.get("diff_obb_detail_area") in (None, ""):
            row["diff_obb_detail_area"] = surface_area - surface_area_obb
        if "is_metal" not in row or row.get("is_metal") in (None, ""):
            material_group = str(material_info.get("material_group", "")).lower()
            family = str(material_info.get("family", "")).lower()
            row["is_metal"] = int(material_group not in {"composite", "plastic", "other"} and family not in {"glass", "pre-preg", "other", "plastic"})

        row.update({
            "filename": file_info.get("filename", row.get("filename", "unknown")),
            "material_bar": material_info.get("material_bar", "unknown"),
            "material_name": material_info.get("material_name", "unknown"),
            "material_name_main": material_info.get("material_name_main", "unknown"),
        })
        return row

    def _validate_input_columns(self, df: pd.DataFrame) -> None:
        schema = self._schema or {}
        required = [str(col) for col in schema.get("required_input_columns", []) if col]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(
                "Во входном наборе отсутствуют обязательные колонки для composite inference: "
                f"{missing}"
            )

    def _extract_prediction(self, pred_df: pd.DataFrame) -> Optional[float]:
        preferred_cols = ["ensemble", "prediction", "pred", "y_pred", "target_pred"]
        for col in preferred_cols:
            if col in pred_df.columns:
                return float(pred_df.iloc[0][col])
        numeric_cols = [c for c in pred_df.columns if pd.api.types.is_numeric_dtype(pred_df[c])]
        if len(numeric_cols) == 1:
            return float(pred_df.iloc[0][numeric_cols[0]])
        if "pred__ensemble" in pred_df.columns:
            return float(pred_df.iloc[0]["pred__ensemble"])
        raise ValueError(f"Could not determine prediction column from composite inference output: {list(pred_df.columns)}")

    def predict_from_file_features(self, file_features: Dict[str, Any], material_info: Dict[str, Any]) -> Optional[float]:
        try:
            if not self.is_model_available():
                return None
            row = self._build_feature_row(file_features, material_info)
            df = pd.DataFrame([row])
            df["material_bar"] = df["material_bar"].map(
                {"sheet": "Лист", "rod": "Пруток", "hexagon": "Шестигранник", "textile": "Ткань"}
            )
            self._validate_input_columns(df)

            required_cols = [str(col) for col in (self._schema or {}).get("required_input_columns", []) if col]
            debug_input_df = df.loc[:, required_cols].copy()
            
            # logger.info("Composite model input columns: %s", required_cols)
            # logger.info("Composite model input values: %s", debug_input_df.to_string(index=False))

            pred_df = self._trainer.predict(df, include_detail_columns=False)
            prediction = self._extract_prediction(pred_df)
            logger.info("Composite labor prediction: %.4f hours", prediction)
            return prediction
        except Exception as e:
            logger.error("Error in direct composite prediction pipeline: %s", e)
            return None


composite_ml_predictor = CompositeMLPredictor()
