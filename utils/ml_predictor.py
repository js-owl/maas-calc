"""
XGBoost special-equipment classifier for CNC milling.

Labor intensity for `service_id="cnc-milling"` and `service_id="composite"`
is predicted by the `ml_models.flexible_ensemble` bundle via
`utils.composite_ml_predictor`. This module contains the classifier branch
that predicts `is_need_special_equipment` for CNC milling.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

import pandas as pd
from joblib import load
from xgboost import XGBClassifier

from constants import (
    ML_CLASSIFIER_PATH,
    ML_SCALER_PATH,
    CLASSIFIER_SCALER_FEATURES_PATH,
    ML_CLUSTERER_PATH,
    ML_REDUCER_PATH,
    ENCODER_PATH,
    ENABLE_ML_MODELS,
    NUM_CORE_CLASSIFIER_FEATURES,
    CLASSIFIER_CATEGORICAL_FEATURES,
)

logger = logging.getLogger(__name__)


class MLPredictor:
    """Classifier-only ML helper for the CNC special-equipment flag."""

    def __init__(self):
        self.classifier = None
        self.scaler = None
        self.clusterer = None
        self.reducer = None
        self.encoder = None
        self.scaler_features = None
        self.classifier_loaded = False
        self._load_models()

    def _load_models(self) -> None:
        """Load the XGBoost classifier and its preprocessing assets."""
        if not ENABLE_ML_MODELS:
            logger.info("ML models disabled by configuration")
            return

        classifier_path = Path(ML_CLASSIFIER_PATH)
        scaler_path = Path(ML_SCALER_PATH)
        scaler_features_path = Path(CLASSIFIER_SCALER_FEATURES_PATH)
        clusterer_path = Path(ML_CLUSTERER_PATH)
        reducer_path = Path(ML_REDUCER_PATH)
        encoder_path = Path(ENCODER_PATH)

        classifier_assets = {
            "classifier": classifier_path,
            "scaler": scaler_path,
            "classifier scaler features": scaler_features_path,
            "clusterer": clusterer_path,
            "reducer": reducer_path,
            "encoder": encoder_path,
        }
        missing_classifier_assets = [
            f"{name}: {path}" for name, path in classifier_assets.items()
            if not path.exists()
        ]

        if missing_classifier_assets:
            logger.warning(
                "XGBoost special-equipment classifier assets are incomplete: %s",
                missing_classifier_assets,
            )
            return

        try:
            self.classifier = XGBClassifier()
            self.classifier.load_model(str(classifier_path))
            logger.info("XGBoost classifier model loaded from %s", ML_CLASSIFIER_PATH)

            self.scaler = load(str(scaler_path))
            logger.info("Scaler loaded from %s", ML_SCALER_PATH)

            self.scaler_features = load(str(scaler_features_path))
            logger.info("Classifier scaler features loaded from %s", CLASSIFIER_SCALER_FEATURES_PATH)

            self.clusterer = load(str(clusterer_path))
            logger.info("Clusterer loaded from %s", ML_CLUSTERER_PATH)

            self.reducer = load(str(reducer_path))
            logger.info("Reducer loaded from %s", ML_REDUCER_PATH)

            self.encoder = load(str(encoder_path))
            logger.info("Encoder loaded from %s", ENCODER_PATH)

            self.classifier_loaded = True
        except Exception as e:
            logger.error("Error loading XGBoost special-equipment classifier assets: %s", e)
            self.classifier_loaded = False

    def is_classifier_available(self) -> bool:
        """Check if the XGBoost special-equipment classifier is available."""
        return (
            self.classifier_loaded
            and self.classifier is not None
            and self.scaler is not None
            and self.scaler_features is not None
            and self.clusterer is not None
            and self.reducer is not None
            and self.encoder is not None
        )

    def is_model_available(self) -> bool:
        """Backward-compatible alias for classifier availability."""
        return self.is_classifier_available()

    def extract_classifier_features_from_file(self, file_features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract classifier features from file-analysis results.

        Material fields are initialized as placeholders and then overwritten in
        `preprocess_classifier_features` from the selected material reference data.
        """
        try:
            if not file_features:
                return None
            # Extract basic geometric features
            features = {}
            feature_names = self.scaler_features[:NUM_CORE_CLASSIFIER_FEATURES]
            for feature_name in feature_names:
                features[feature_name] = file_features.get(feature_name, 0.0)

            # Extra geometry fields used by tests/debug output and tolerated by preprocessing.
            features["obb_x"] = file_features.get("obb_x", 0.0)
            features["obb_y"] = file_features.get("obb_y", 0.0)
            features["obb_z"] = file_features.get("obb_z", 0.0)

            # Material properties (will be filled by caller)
            features.update({
                "material_bar": "unknown",
                "material_name": "unknown",
                "material_name_main": "unknown",
                "material_group": "unknown",
                "material_coef": 0.0,
                "hardness": 0.0,
                "strenghtness": 0.0,
                "thermal_conductivity": 0.0,
                "relative_coef": 0.0,
                "filename": file_features.get("file_info", {}).get("filename", "unknown"),
            })

            logger.info("Extracted %s classifier features from file analysis", len(features))
            return features
        except Exception as e:
            logger.error("Error extracting classifier features from file: %s", e)
            return None

    def preprocess_classifier_features(
        self,
        features: Dict[str, Any],
        material_info: Dict[str, Any],
    ) -> Optional[pd.DataFrame]:
        """Preprocess features for the XGBoost special-equipment classifier."""
        try:
            if not self.is_classifier_available():
                logger.warning("XGBoost special-equipment classifier is not available for preprocessing")
                return None

            features.update({
                "material_bar": material_info.get("material_bar", "unknown"),
                "material_name": material_info.get("material_name", "unknown"),
                "material_name_main": material_info.get("material_name_main", "unknown"),
                "material_group": material_info.get("material_group", "unknown"),
                "material_name_group": material_info.get("material_name_group", "unknown"),
                "density_approximately": material_info.get("density", 0.0),
                "hardness": material_info.get("hardness", 0.0),
                "strenghtness": material_info.get("strenghtness", 0.0),
                "thermal_conductivity": material_info.get("thermal_conductivity", 0.0),
                "relative_coef": material_info.get("relative_coef", 0.0),
            })

            # Add new features: is_metal and is_metal_sheet
            features['is_metal'] = 1
            features['is_metal_sheet'] = 0

            # Create DataFrame
            features_df = pd.DataFrame([features])

            # Models were fitted on Russian material-form labels. Keep unknown values
            # unchanged instead of mapping them to NaN.
            material_bar_mapping = {
                "sheet": "Лист",
                "plate": "Плита",
                "rod": "Пруток",
                "bar": "Пруток",
                "hexagon": "Шестигранник",
                "textile": "Ткань",
            }
            mapped_material_bar = features_df["material_bar"].map(material_bar_mapping)
            features_df["material_bar"] = mapped_material_bar.fillna(features_df["material_bar"])

            # Update materials features in df
            features_df["density_approximately"] = features_df["density_approximately"] * 1e-9
            features_df["weight_approximately"] = (
                features_df["density_approximately"] * features_df["volume"]
            )

            categoricals = CLASSIFIER_CATEGORICAL_FEATURES
            # Apply OHE transformation
            features_ohe = self.encoder.transform(features_df[categoricals])
            features_ohe_df = pd.DataFrame(
                features_ohe,
                columns=self.encoder.get_feature_names_out(),
                index=features_df.index,
            )

            # Combine features
            features_combined = pd.concat(
                [features_df.drop(categoricals, axis=1), features_ohe_df],
                axis=1,
            )

            normalized = self.scaler.transform(features_combined[self.scaler_features].astype("float"))
            features_combined["kmeans_cluster"] = self.clusterer.predict(normalized)
            pca_projected = self.reducer.transform(normalized)
            features_combined["pca_projected_0"] = pca_projected[:, 0]
            features_combined["pca_projected_1"] = pca_projected[:, 1]

            # Reindex to match model's expected features
            features_final = features_combined.reindex(
                columns=self.classifier.feature_names_in_,
                fill_value=0,
            )

            logger.info("Preprocessed classifier features: %s", features_final.shape)
            return features_final
        except Exception as e:
            logger.error("Error preprocessing classifier features: %s", e)
            return None

    def predict_is_need_special_equipment(self, features_df: pd.DataFrame) -> Optional[int]:
        """Predict whether special equipment is needed for CNC milling."""
        try:
            if not self.is_classifier_available():
                logger.warning("XGBoost special-equipment classifier is not available for prediction")
                return None

            if features_df is None or features_df.empty:
                logger.warning("No features provided for special-equipment prediction")
                return None

            is_need_special_equipment = int(self.classifier.predict(features_df)[0])
            logger.info("Special-equipment classifier prediction: %s", is_need_special_equipment)
            return is_need_special_equipment
        except Exception as e:
            logger.error("Error making special-equipment classifier prediction: %s", e)
            return None

    def predict_special_equipment_from_file_features(
        self,
        file_features: Dict[str, Any],
        material_info: Dict[str, Any],
    ) -> Optional[int]:
        """
        Run the complete classifier-only pipeline from extracted file features.
        """
        try:
            features = self.extract_classifier_features_from_file(file_features)
            if not features:
                logger.warning("Failed to extract classifier features from file")
                return None

            features_df = self.preprocess_classifier_features(features, material_info)
            if features_df is None:
                logger.warning("Failed to preprocess classifier features")
                return None

            return self.predict_is_need_special_equipment(features_df)
        except Exception as e:
            logger.error("Error in special-equipment classifier pipeline: %s", e)
            return None


# Global ML predictor instance
ml_predictor = MLPredictor()
