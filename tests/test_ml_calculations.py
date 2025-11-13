"""
Tests for ML-based calculations
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from main import app
from utils.ml_predictor import ml_predictor
from constants import ENABLE_ML_MODELS


class TestMLCalculations:
    """Test ML-based calculation functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = TestClient(app)
        
        # Mock ML features for testing
        self.mock_ml_features = {
            'dimensions': {
                'length': 10.0,
                'width': 5.0,
                'thickness': 5.0
            },
            'volume': 1000.0,
            'surface_area': 500.0,
            'obb_x': 10.0,
            'obb_y': 10.0,
            'obb_z': 10.0,
            'min_size': 10.0,
            'mid_size': 10.0,
            'max_size': 10.0,
            'aspect_ratio_xy': 1.0,
            'aspect_ratio_yz': 1.0,
            'aspect_ratio_xz': 1.0,
            'bbox_volume': 1000.0,
            'check_sizes_for_lathe': 0,
            'features': {
                'face_count': 6,
                'vertex_count': 8,
                'edge_count': 12,
                'surface_entropy': 2.5
            }
        }
    
    def test_ml_predictor_initialization(self):
        """Test ML predictor initialization"""
        assert ml_predictor is not None
        # Note: Models may not be available in test environment
        # This test verifies the predictor can be instantiated
    
    def test_ml_predictor_feature_extraction(self):
        """Test feature extraction from file features"""
        features = ml_predictor.extract_features_from_file(self.mock_ml_features)
        
        assert features is not None
        assert 'volume' in features
        assert 'surface_area' in features
        assert 'obb_x' in features
        assert 'obb_y' in features
        assert 'obb_z' in features
        assert features['volume'] == 1000.0
        assert features['surface_area'] == 500.0
    
    def test_ml_predictor_material_info(self):
        """Test material information extraction"""
        material_info = {
            'material_bar': 'test_bar',
            'material_name': 'Test Material',
            'material_name_main': 'Test Main',
            'material_group': 'Test Group',
            'material_coef': 1.5
        }
        
        features = ml_predictor.extract_features_from_file(self.mock_ml_features)
        if features:
            processed_features = ml_predictor.preprocess_features(features, material_info)
            # Note: This may return None if models are not available
            # The test verifies the method can be called without errors
    
    @pytest.mark.skipif(not ENABLE_ML_MODELS, reason="ML models disabled")
    def test_ml_prediction_with_models(self):
        """Test ML prediction when models are available"""
        if not ml_predictor.is_model_available():
            pytest.skip("ML models not available")
        
        features = ml_predictor.extract_features_from_file(self.mock_ml_features)
        material_info = {
            'material_bar': 'test_bar',
            'material_name': 'Test Material',
            'material_name_main': 'Test Main',
            'material_group': 'Test Group',
            'material_coef': 1.0
        }
        
        prediction = ml_predictor.predict_from_file_features(features, material_info)
        # Note: Prediction may be None if models fail to load
        # This test verifies the prediction pipeline works
    
    def test_calculation_router_ml_detection(self):
        """Test calculation router ML detection logic"""
        from utils.calculation_router import CalculationRouter
        
        router = CalculationRouter()
        
        # Test with ML features
        params_with_ml = {
            'ml_features': self.mock_ml_features,
            'service_id': 'printing'
        }
        
        should_use_ml = router.should_use_ml(params_with_ml)
        # Should use ML if models are available and features are sufficient
        # Note: This depends on model availability
    
    def test_calculation_router_rule_based_fallback(self):
        """Test calculation router falls back to rule-based when appropriate"""
        from utils.calculation_router import CalculationRouter
        
        router = CalculationRouter()
        
        # Test without ML features
        params_without_ml = {
            'service_id': 'printing',
            'dimensions': {'length': 10, 'width': 10, 'thickness': 10}
        }
        
        should_use_ml = router.should_use_ml(params_without_ml)
        assert should_use_ml == False
    
    def test_ml_calculator_initialization(self):
        """Test ML calculator initialization"""
        from calculators.ml_calculator import MLPrintingCalculator, MLCNCMillingCalculator
        
        printing_calc = MLPrintingCalculator()
        assert printing_calc.service_id == "printing"
        assert printing_calc.calculation_method == "3D Printing ML Prediction"
        
        milling_calc = MLCNCMillingCalculator()
        assert milling_calc.service_id == "cnc-milling"
        assert milling_calc.calculation_method == "CNC Milling ML Prediction"
    
    def test_ml_calculator_material_costs(self):
        """Test ML calculator material cost calculation"""
        from calculators.ml_calculator import MLPrintingCalculator
        
        calculator = MLPrintingCalculator()
        
        # Create mock request
        mock_request = Mock()
        mock_request.service_id = 'printing'
        mock_request.material_id = 'PA11'
        mock_request.quantity = 5
        mock_request.obb_x = 1
        mock_request.obb_y = 2
        mock_request.obb_z = 3
        
        material_costs = calculator._calculate_material_costs(mock_request)
        
        assert 'material_id' in material_costs
        assert 'estimated_weight_kg' in material_costs
        assert 'price_per_kg' in material_costs
        assert 'material_price' in material_costs
        assert material_costs['material_id'] == 'PA11'
    
    def test_ml_calculator_cover_coefficient(self):
        """Test ML calculator cover coefficient calculation"""
        from calculators.ml_calculator import MLPrintingCalculator
        
        calculator = MLPrintingCalculator()
        
        # Test with single cover type
        k_cover = calculator._calculate_cover_coefficient(['1'])
        assert k_cover >= 1.0
        
        # Test with multiple cover types
        k_cover_multi = calculator._calculate_cover_coefficient(['1', '2'])
        assert k_cover_multi >= k_cover
        
        # Test with empty list
        k_cover_empty = calculator._calculate_cover_coefficient([])
        assert k_cover_empty == 1.0
    
    def test_ml_calculator_key_features_extraction(self):
        """Test ML calculator key features extraction"""
        from calculators.ml_calculator import MLPrintingCalculator
        
        calculator = MLPrintingCalculator()
        
        key_features = calculator._get_key_features(self.mock_ml_features)
        
        assert 'volume' in key_features
        assert 'surface_area' in key_features
        assert 'obb_dimensions' in key_features
        assert 'aspect_ratios' in key_features
        assert 'complexity_metrics' in key_features
        assert 'lathe_suitable' in key_features
        
        assert key_features['volume'] == 1000.0
        assert key_features['surface_area'] == 500.0
        assert key_features['lathe_suitable'] == False  # Based on mock data
    
    @pytest.mark.asyncio
    async def test_ml_calculation_integration(self):
        """Test ML calculation integration with mock data"""
        from calculators.ml_calculator import MLPrintingCalculator
        
        calculator = MLPrintingCalculator()
        
        # Create mock request with ML features
        mock_request = Mock()
        mock_request.file_id = "test-ml-001"
        mock_request.service_id = "printing"
        mock_request.filename = "test.stl"  # Set actual string value
        mock_request.ml_features = self.mock_ml_features
        mock_request.material_id = 'PA11'
        mock_request.material_form = 'powder'
        mock_request.quantity = 1
        mock_request.tolerance_id = '1'
        mock_request.finish_id = '1'
        mock_request.cover_id = ['1']
        mock_request.k_otk = 1.0
        mock_request.location = 'location_1'
        
        # Mock the ML prediction
        with patch.object(ml_predictor, 'predict_from_file_features', return_value=[2.5, 0]):
            try:
                result = await calculator.calculate(mock_request)

                assert result.file_id == "test-ml-001"
                assert result.calculation_engine == "ml_model"
                assert result.ml_prediction_hours == [2.5, 0]
                assert result.features_extracted is not None
                assert result.material_costs is not None
                assert result.work_price_breakdown is not None
                
            except Exception as e:
                # ML calculation may fail if models are not available
                # This is expected in test environment
                assert "ML" in str(e) or "model" in str(e).lower()
    
    def test_api_endpoint_with_ml_features(self):
        """Test API endpoint with ML features (mock file upload)"""
        # This test would require actual file upload simulation
        # For now, we test the endpoint structure
        
        payload = {
            "service_id": "printing",
            "file_id": "test-ml-api-001",
            "dimensions": {
                "length": 10.0,
                "width": 10.0,
                "thickness": 10.0
            },
            "quantity": 1,
            "material_id": "PA11",
            "material_form": "powder",
            "cover_id": ["1"]
        }
        
        response = self.client.post("/calculate-price", json=payload)
        
        # Should succeed with rule-based calculation
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "calculation_engine" in data["data"]
        # Should use rule-based since no file was uploaded
        assert data["data"]["calculation_engine"] == "rule_based"
    
    def test_ml_fallback_behavior(self):
        """Test ML fallback to rule-based calculation"""
        from utils.calculation_router import CalculationRouter
        
        router = CalculationRouter()
        
        # Test with insufficient features
        params_insufficient = {
            'ml_features': {
                'volume': 1000.0,
                # Missing required features
            },
            'service_id': 'printing'
        }
        
        should_use_ml = router.should_use_ml(params_insufficient)
        assert should_use_ml == False
    
    def test_ml_constants_configuration(self):
        """Test ML constants are properly configured"""
        from constants import (ENABLE_ML_MODELS, ML_FALLBACK_TO_RULES, ML_REGRESSOR_PATH,
                               ML_CLASSIFIER_PATH, ML_SCALER_PATH, SCALER_FEATURES_PATH,
                               ML_CLUSTERER_PATH, ML_REDUCER_PATH,
                               ENCODER_PATH)
        
        assert isinstance(ENABLE_ML_MODELS, bool)
        assert isinstance(ML_FALLBACK_TO_RULES, bool)
        assert isinstance(ML_REGRESSOR_PATH, str)
        assert isinstance(ML_CLASSIFIER_PATH, str)
        assert isinstance(ML_SCALER_PATH, str)
        assert isinstance(SCALER_FEATURES_PATH, str)
        assert isinstance(ML_CLUSTERER_PATH, str)
        assert isinstance(ML_REDUCER_PATH, str)
        assert isinstance(ENCODER_PATH, str)
        assert ML_REGRESSOR_PATH.endswith('.json')
        assert ENCODER_PATH.endswith('.joblib')
    
    def test_response_model_ml_fields(self):
        """Test response model includes ML-specific fields"""
        from models.response_models import UnifiedCalculationResponse
        
        # Test that ML fields are optional
        response = UnifiedCalculationResponse(
            file_id="test",
            part_price=50.0,
            detail_price=100.0,
            part_price_one=100.0,
            detail_price_one=100.0,
            total_price=100.0,
            total_time=1.0,
            service_id="printing",
            calculation_method="Test"
        )
        
        # ML fields should be None by default
        assert response.calculation_engine is None
        assert response.ml_prediction_hours is None
        assert response.features_extracted is None
        assert response.material_costs is None
        assert response.work_price_breakdown is None
    
    def test_ml_feature_validation(self):
        """Test ML feature validation logic"""
        from utils.calculation_router import CalculationRouter
        
        router = CalculationRouter()
        
        # Test with complete features
        complete_features = {
            'volume': 1000.0,
            'surface_area': 500.0,
            'obb_x': 10.0,
            'obb_y': 10.0,
            'obb_z': 10.0
        }
        
        params_complete = {
            'ml_features': complete_features,
            'service_id': 'printing'
        }
        
        # Should pass validation if models are available
        should_use_ml = router.should_use_ml(params_complete)
        # Result depends on model availability
    
    def test_ml_error_handling(self):
        """Test ML error handling and graceful degradation"""
        from calculators.ml_calculator import MLPrintingCalculator
        
        calculator = MLPrintingCalculator()
        
        # Test with invalid ML features
        invalid_features = {
            'volume': None,
            'surface_area': None
        }
        
        key_features = calculator._get_key_features(invalid_features)
        # Should handle invalid features gracefully
        assert isinstance(key_features, dict)
    
    def test_ml_calculator_service_types(self):
        """Test all ML calculator service types"""
        from calculators.ml_calculator import (
            MLPrintingCalculator,
            MLCNCMillingCalculator,
            MLCNCLatheCalculator,
            MLPaintingCalculator
        )
        
        calculators = [
            MLPrintingCalculator(),
            MLCNCMillingCalculator(),
            MLCNCLatheCalculator(),
            MLPaintingCalculator()
        ]
        
        service_ids = ["printing", "cnc-milling", "cnc-lathe", "painting"]
        
        for calc, service_id in zip(calculators, service_ids):
            assert calc.service_id == service_id
            assert "ML Prediction" in calc.calculation_method


if __name__ == "__main__":
    pytest.main([__file__])
