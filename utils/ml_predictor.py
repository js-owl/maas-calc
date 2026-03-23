"""
ML Model Predictor for Manufacturing Calculations

This module handles ML model loading, feature extraction, and time prediction
for manufacturing cost calculations using XGBoost models.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import pandas as pd
import numpy as np
from joblib import load
from xgboost import XGBRegressor, XGBClassifier
from catboost import CatBoostRegressor, Pool

from constants import (
    ML_REGRESSOR_PATH, ML_CLASSIFIER_PATH, ML_SCALER_PATH, 
    CLASSIFIER_SCALER_FEATURES_PATH,
    ML_CLUSTERER_PATH, ML_REDUCER_PATH, ENCODER_PATH, 
    ENABLE_ML_MODELS, NUM_CORE_CLASSIFIER_FEATURES, CLASSIFIER_CATEGORICAL_FEATURES,
    REGRESSOR_FEATURES_PATH, REGRESSOR_CATEGORICAL_FEATURES
)

logger = logging.getLogger(__name__)


class MLPredictor:
    """ML Model Predictor for manufacturing time estimation"""
    
    def __init__(self):
        self.regressor = None
        self.classifier = None
        self.scaler = None
        self.clusterer = None
        self.reducer = None
        self.encoder = None
        self.scaler_features = None
        self.regressor_features = None
        self.models_loaded = False
        self._load_models()
    
    def _load_models(self) -> None:
        """Load XGBoost model and encoder if available"""
        if not ENABLE_ML_MODELS:
            logger.info("ML models disabled by configuration")
            return
            
        try:
            # Check if model files exist
            regressor_path = Path(ML_REGRESSOR_PATH)
            classifier_path = Path(ML_CLASSIFIER_PATH)
            scaler_path = Path(ML_SCALER_PATH)
            scaler_features_path = Path(CLASSIFIER_SCALER_FEATURES_PATH)
            regressor_features_path = Path(REGRESSOR_FEATURES_PATH)
            clusterer_path = Path(ML_CLUSTERER_PATH)
            reducer_path = Path(ML_REDUCER_PATH)
            encoder_path = Path(ENCODER_PATH)
            
            if not regressor_path.exists():
                logger.warning(f"ML model file not found: {ML_REGRESSOR_PATH}")
                return
            
            if not classifier_path.exists():
                logger.warning(f"ML model file not found: {ML_CLASSIFIER_PATH}")
                return
            
            if not scaler_path.exists():
                logger.warning(f"ML model file not found: {ML_SCALER_PATH}")
                return

            if not scaler_features_path.exists():
                logger.warning(f"Features not found: {CLASSIFIER_SCALER_FEATURES_PATH}")
                return
            
            if not regressor_features_path.exists():
                logger.warning(f"Features not found: {REGRESSOR_FEATURES_PATH}")
                return
            
            if not clusterer_path.exists():
                logger.warning(f"ML model file not found: {ML_CLUSTERER_PATH}")
                return
            
            if not reducer_path.exists():
                logger.warning(f"ML model file not found: {ML_REDUCER_PATH}")
                return
            
            if not encoder_path.exists():
                logger.warning(f"Encoder file not found: {ENCODER_PATH}")
                return
            
            # Load ML models
            self.regressor = CatBoostRegressor()
            self.regressor.load_model(str(regressor_path))
            logger.info(f"Regressor model loaded from {ML_REGRESSOR_PATH}")

            self.classifier = XGBClassifier()
            self.classifier.load_model(str(classifier_path))
            logger.info(f"XGBoost classifier model loaded from {ML_CLASSIFIER_PATH}")
            
            # Load encoders
            self.scaler = load(str(scaler_path))
            logger.info(f"Encoder loaded from {ML_SCALER_PATH}")

            self.scaler_features = load(str(scaler_features_path))
            logger.info(f"Encoder loaded from {CLASSIFIER_SCALER_FEATURES_PATH}")

            self.regressor_features = load(str(regressor_features_path))
            logger.info(f"Encoder loaded from {REGRESSOR_FEATURES_PATH}")

            self.clusterer = load(str(clusterer_path))
            logger.info(f"Encoder loaded from {ML_CLUSTERER_PATH}")
            
            self.reducer = load(str(reducer_path))
            logger.info(f"Encoder loaded from {ML_REDUCER_PATH}")

            self.encoder = load(str(encoder_path))
            logger.info(f"Encoder loaded from {ENCODER_PATH}")
            
            self.models_loaded = True
            logger.info("ML models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading ML models: {e}")
            self.models_loaded = False
    
    def is_model_available(self) -> bool:
        """Check if ML models are available and loaded"""
        return self.models_loaded and \
            self.classifier is not None and self.scaler is not None and \
            self.scaler_features is not None and self.clusterer is not None and \
            self.reducer is not None and self.encoder is not None and \
            self.regressor is not None and self.regressor_features is not None
    
    def extract_classifier_features_from_file(self, file_features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract and preprocess features from file analysis results
        
        Args:
            file_features: Features extracted from STP/STL file analysis
            
        Returns:
            Processed features dict or None if extraction fails
        """
        try:
            if not file_features:
                return None
            # Extract basic geometric features
            features = {}
            
            features_names = self.scaler_features[:NUM_CORE_CLASSIFIER_FEATURES]
            for feature_name in features_names:
                features[feature_name] = file_features.get(feature_name, 0.0)
            
            # add for success tests
            features['obb_x'] = file_features.get('obb_x', 0.0)
            features['obb_y'] = file_features.get('obb_y', 0.0)
            features['obb_z'] = file_features.get('obb_z', 0.0)

            # Material properties (will be filled by caller)
            features['material_bar'] = 'unknown'
            features['material_name'] = 'unknown'
            features['material_name_main'] = 'unknown'
            features['material_group'] = 'unknown'
            features['material_coef'] = 0.0
            features['hardness'] = 0.0
            features['strenghtness'] = 0.0
            features['thermal_conductivity'] = 0.0
            features['relative_coef'] = 0.0
            features['filename'] = file_features.get('file_info', {}).get('filename', 'unknown')
            
            logger.info(f"Extracted {len(features)} classifier features from file analysis")
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features from file: {e}")
            return None
    
    def extract_regressor_features_from_file(self, file_features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract and preprocess features for regressor model from file analysis results
        
        Args:
            file_features: Features extracted from STP/STL file analysis
            
        Returns:
            Processed features dict or None if extraction fails
        """
        try:
            if not file_features:
                return None
            # Extract basic geometric features
            features = {}
            
            features_names = self.regressor_features
            for feature_name in features_names:
                features[feature_name] = file_features.get(feature_name, 0.0)

            # Material properties (will be filled by caller)
            features['material_bar'] = 'unknown'
            features['material_name_main'] = 'unknown'
            features['filename'] = file_features.get('file_info', {}).get('filename', 'unknown')
            
            logger.info(f"Extracted {len(features)} regressor features from file analysis")
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features from file: {e}")
            return None

    def preprocess_features(
            self, 
            features: Dict[str, Any], 
            material_info: Dict[str, Any],
            predictor_type: str,
        ) -> Optional[pd.DataFrame]:
        """
        Preprocess features for ML model prediction
        
        Args:
            features: Raw features from file analysis
            material_info: Material properties and metadata
            
        Returns:
            Preprocessed DataFrame ready for ML prediction or None if fails
        """
        try:
            if not self.is_model_available():
                logger.warning("ML models not available for preprocessing")
                return None
            
            # Update material information
            features.update({
                'material_bar': material_info.get('material_bar', 'unknown'),
                'material_name': material_info.get('material_name', 'unknown'),
                'material_name_main': material_info.get('material_name_main', 'unknown'),
                'material_group': material_info.get('material_group', 'unknown'),
                'material_name_group': material_info.get('material_name_group', 'unknown'),
                'density_approximately': material_info.get('density', 0.0),
                'hardness': material_info.get('hardness', 0.0),
                'strenghtness': material_info.get('strenghtness', 0.0),
                'thermal_conductivity': material_info.get('thermal_conductivity', 0.0),
                'relative_coef': material_info.get('relative_coef', 0.0),
            })

            # Create DataFrame
            features_df = pd.DataFrame([features])
            # Mapping bars because it was senn during fit in russian
            features_df['material_bar'] = features_df['material_bar'].map(
                {'sheet': 'Лист', 'rod': 'Пруток', 'hexagon': 'Шестигранник'}
            )

            # Update materials features in df
            features_df['density_approximately'] = features_df['density_approximately'] * 1e-9
            features_df['weight_approximately'] = features_df['density_approximately'] * features_df['volume']

            if predictor_type=='classifier':
                # Apply one-hot encoding to categorical features
                categoricals = CLASSIFIER_CATEGORICAL_FEATURES
                
                # Apply OHE transformation
                features_ohe = self.encoder.transform(features_df[categoricals])
                features_ohe_df = pd.DataFrame(
                    features_ohe,
                    columns=self.encoder.get_feature_names_out(),
                    index=features_df.index
                )
                
                # Combine features
                features_combined = pd.concat(
                    [features_df.drop(categoricals, axis=1), features_ohe_df],
                    axis=1
                )
                
                # add clusters, pca
                scaler_features = self.scaler_features
                normalized = self.scaler.transform(features_combined[scaler_features].astype('float'))
                features_combined['kmeans_cluster'] = self.clusterer.predict(normalized)
                pca_projected = self.reducer.transform(normalized)
                features_combined['pca_projected_0'] = pca_projected[:, 0]
                features_combined['pca_projected_1'] = pca_projected[:, 1]

                # Reindex to match model's expected features
                features_final = features_combined.reindex(
                    columns=self.classifier.feature_names_in_,
                    fill_value=0
                )
                # features_final.to_excel(r'C:\Users\serma10\Documents\maas-backend-stl\tests\TEST_DETAIL.xlsx', index=False) # for debug
            elif predictor_type=='regressor':
                features_final = features_df[self.regressor_features].copy()

            logger.info(f"Preprocessed features: {features_final.shape}")
            return features_final
            
        except Exception as e:
            logger.error(f"Error preprocessing features: {e}")
            return None
    
    def cat_cols_to_indices(self, feature_cols: List[str], cat_cols: List[str]) -> List[int]:
        """Translate categorical features to indices"""
        cat_set = set(cat_cols)
        missing = [c for c in cat_cols if c not in feature_cols]
        if missing:
            logger.error(f"categoricals not found in regressor_features: {missing}")
        
        return [i for i, c in enumerate(feature_cols) if c in cat_set]
    
    def predict_work_time(self, features_df: pd.DataFrame) -> Optional[float]:
        """
        Predict work time using ML model
        
        Args:
            features_df: Preprocessed features DataFrame
            
        Returns:
            Predicted work time in hours or None if prediction fails
        """
        try:
            if not self.is_model_available():
                logger.warning("ML models not available for prediction")
                return None
            
            if features_df is None or features_df.empty:
                logger.warning("No features provided for prediction")
                return None
            
            # compute categorical indices
            categoricals = REGRESSOR_CATEGORICAL_FEATURES
            cat_idx = self.cat_cols_to_indices(self.regressor_features, categoricals)
            features_df[categoricals] = features_df[categoricals].astype('category')
            
            # make pool object
            pool = Pool(features_df, None, cat_features=cat_idx)

            # Make prediction
            log_prediction = self.regressor.predict(pool) # predict log_labor_intensity
            prediction = np.expm1(log_prediction) # transform to labor_intensity
            work_time_hours = float(prediction[0])
            
            logger.info(f"ML prediction: {work_time_hours:.2f} hours")
            return work_time_hours
            
        except Exception as e:
            logger.error(f"Error making ML prediction: {e}")
            return None
    
    def predict_is_need_special_equipment(self, features_df: pd.DataFrame) -> Optional[float]:
        """
        Predict is need special_equipment using ML model
        
        Args:
            features_df: Preprocessed features DataFrame
            
        Returns:
            Predicted bool param
        """
        try:
            if not self.is_model_available():
                logger.warning("ML models not available for prediction")
                return None
            
            if features_df is None or features_df.empty:
                logger.warning("No features provided for prediction")
                return None
            
            # Make prediction
            is_need_special_equipment = self.classifier.predict(features_df)[0] # predict bool feature for use special equipment

            logger.info(f"ML bool prediction: {is_need_special_equipment}")
            return is_need_special_equipment
            
        except Exception as e:
            logger.error(f"Error making ML bool prediction: {e}")
            return None

    def predict_from_file_features(
        self, 
        file_features: Dict[str, Any], 
        material_info: Dict[str, Any]
    ) -> Optional[float]:
        """
        Complete ML prediction pipeline from file features
        
        Args:
            file_features: Features extracted from file analysis
            material_info: Material properties and metadata
            
        Returns:
            Predicted work time in hours or None if prediction fails
        """
        try:
            # Extract features
            features = self.extract_classifier_features_from_file(file_features)
            if not features:
                logger.warning("Failed to extract classifier features from file")
                return None
            
            regressor_features = self.extract_regressor_features_from_file(file_features)
            if not regressor_features:
                logger.warning("Failed to extract regressor features from file")
                return None
            
            # Preprocess features
            features_df = self.preprocess_features(features, material_info, 'classifier')
            if features_df is None:
                logger.warning("Failed to preprocess classifier features")
                return None
            
            regressor_features_df = self.preprocess_features(regressor_features, material_info, 'regressor')
            if regressor_features_df is None:
                logger.warning("Failed to preprocess regressor features")
                return None
            
            # Make prediction
            prediction_work_time = self.predict_work_time(regressor_features_df)
            prediction_is_need_special_equipment = self.predict_is_need_special_equipment(features_df)
            
            return prediction_work_time, prediction_is_need_special_equipment
            
        except Exception as e:
            logger.error(f"Error in ML prediction pipeline: {e}")
            return None


# Global ML predictor instance
ml_predictor = MLPredictor()

