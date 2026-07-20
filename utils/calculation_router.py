"""
Calculation routing utility.

Active production routes:
- printing: rule-based calculation;
- electroplating_auto: rule-based galvanic coating calculation;
- cnc-milling: ML-only calculation;
- composite: ML calculation.

Unsupported routes are rejected explicitly instead of using non-active calculation logic.
"""

import logging
from typing import Any, Dict

from calculators import ElectroplatingAutoCalculator, PrintingCalculator
from calculators.ml_calculator import MLCNCMillingCalculator, MLCompositeCalculator
from constants import ENABLE_ML_MODELS, DEFAULTS, PRINTING_LOCATION
from models.calculation_models import ElectroplatingCalculationRequest, PrintingCalculationRequest
from models.response_models import UnifiedCalculationResponse
from utils.composite_ml_predictor import composite_ml_predictor
from utils.electroplating_config import ELECTROPLATING_SERVICE_ID
from utils.ml_predictor import ml_predictor

logger = logging.getLogger(__name__)

ML_ONLY_SERVICES = {"cnc-milling", "composite"}


class CalculationRouter:
    """Routes calculations to the active calculator for a service."""

    def __init__(self):
        self.calculators = {}

    def _get_calculator(self, service_id: str, use_ml: bool = False):
        """Get calculator lazily to avoid circular imports."""
        if service_id in ML_ONLY_SERVICES and not use_ml:
            raise ValueError(f"ML calculator is required for service_id={service_id}.")

        calculator_key = f"{service_id}_{'ml' if use_ml else 'rule'}"
        if calculator_key in self.calculators:
            return self.calculators[calculator_key]

        use_ml_calculator = use_ml and (
            (service_id == "composite" and composite_ml_predictor.is_model_available())
            or (
                # CNC milling uses the flexible_ensemble bundle for labor regression
                # and the existing XGBoost classifier for special tooling.
                service_id == "cnc-milling"
                and ENABLE_ML_MODELS
                and composite_ml_predictor.is_model_available()
                and ml_predictor.is_classifier_available()
            )
        )

        if use_ml_calculator:
            if service_id == "cnc-milling":
                self.calculators[calculator_key] = MLCNCMillingCalculator()
            elif service_id == "composite":
                self.calculators[calculator_key] = MLCompositeCalculator()
        else:
            # Rule-based calculators are intentionally limited to active non-CNC services.
            if service_id == "printing":
                self.calculators[calculator_key] = PrintingCalculator()
            elif service_id == ELECTROPLATING_SERVICE_ID:
                self.calculators[calculator_key] = ElectroplatingAutoCalculator()

        return self.calculators.get(calculator_key)

    async def route_calculation(
        self,
        service_id: str,
        parameters: Dict[str, Any],
        use_ml: bool = False,
    ) -> UnifiedCalculationResponse:
        """Route calculation to the active calculator."""
        logger.info("Routing calculation to service: %s (ML: %s)", service_id, use_ml)

        calculator = self._get_calculator(service_id, use_ml)
        if not calculator:
            raise ValueError(f"Unknown or unsupported service ID: {service_id}")

        request = self._create_request(service_id, parameters, use_ml)
        return await calculator.calculate(request)

    def should_use_ml(self, parameters: Dict[str, Any]) -> bool:
        """
        Determine if ML calculation should be used.

        CNC milling is ML-only. Missing model assets or extracted features are a
        hard calculation error, not a reason to switch calculation strategy.
        """
        service_id = parameters.get("service_id", None)

        if service_id == "printing":
            return False

        if service_id == ELECTROPLATING_SERVICE_ID:
            return False

        if service_id == "composite":
            if not composite_ml_predictor.is_model_available():
                logger.warning("Composite ML model is not available")
                return False
            return self._has_required_ml_features(parameters)

        if service_id == "cnc-milling":
            missing_reasons = []
            if not ENABLE_ML_MODELS:
                missing_reasons.append("ML models are disabled")
            if not composite_ml_predictor.is_model_available():
                missing_reasons.append("flexible_ensemble labor model is not available")
            if not ml_predictor.is_classifier_available():
                missing_reasons.append("XGBoost special-equipment classifier is not available")
            missing_features = self._missing_required_ml_features(parameters)
            if missing_features:
                missing_reasons.append("insufficient ML features: " + ", ".join(missing_features))

            if missing_reasons:
                raise ValueError(
                    "Cannot calculate service_id='cnc-milling': "
                    + "; ".join(missing_reasons)
                    + ". CNC milling is ML-only in the current runtime."
                )
            return True

        logger.warning("ML calculation is not configured for service id: %s", service_id)
        return False

    def _has_required_ml_features(self, parameters: Dict[str, Any]) -> bool:
        missing = self._missing_required_ml_features(parameters)
        if missing:
            logger.warning("Insufficient ML features: %s", ", ".join(missing))
            return False
        return True

    def _missing_required_ml_features(self, parameters: Dict[str, Any]) -> list[str]:
        ml_features = parameters.get("ml_features")
        if not ml_features:
            return ["volume", "surface_area"]
        required_features = ["volume", "surface_area"]
        return [
            feature
            for feature in required_features
            if feature not in ml_features or ml_features[feature] is None
        ]

    def _create_request(self, service_id: str, parameters: Dict[str, Any], use_ml: bool = False):
        """Create an internal request object for the selected service."""
        file_id = parameters.get("file_id", "unknown")

        if service_id == "cnc-milling" and not use_ml:
            raise ValueError(
                "ML request is required for service_id='cnc-milling'. "
                "Rule-based CNC milling request path was removed."
            )

        if use_ml:
            ml_features = parameters.get("ml_features", {})
            base_params = {
                "file_id": file_id,
                "ml_features": ml_features,
                "filename": parameters.get("filename"),
                "location": parameters.get("location", "location_1"),
                "material_id": parameters.get("material_id"),
                "material_form": parameters.get("material_form"),
                "tolerance_id": parameters.get("tolerance_id", "4"),
                "finish_id": parameters.get("finish_id", "3"),
                "quantity": parameters.get("quantity", 1),
                "cover_id": parameters.get("cover_id", ["1"]),
                "k_otk": parameters.get("k_otk", 1.0),
                "service_id": service_id,
                "obb_x": parameters.get("obb_x"),
                "obb_y": parameters.get("obb_y"),
                "obb_z": parameters.get("obb_z"),
            }
            if service_id == "cnc-milling":
                return type("MLCNCMillingRequest", (), base_params)()
            if service_id == "composite":
                base_params["is_need_special_equipment"] = parameters.get("is_need_special_equipment", 0)
                return type("MLCompositeRequest", (), base_params)()

        if service_id == ELECTROPLATING_SERVICE_ID:
            return ElectroplatingCalculationRequest(
                file_id=file_id,
                ml_features=parameters.get("ml_features") or parameters.get("features_dict") or {},
                filename=parameters.get("filename") or parameters.get("file_name"),
                material_id=parameters.get("material_id"),
                material_form=parameters.get("material_form"),
                electroplating_family=parameters.get("electroplating_family"),
                quantity=parameters.get("quantity", 1),
                cover_id=parameters.get("cover_id"),
                location=parameters.get("location", "location_1"),
                k_otk=parameters.get("k_otk", 1.0),
                electroplating_process_id=parameters.get("electroplating_process_id"),
                coating_thickness_microns=parameters.get("coating_thickness_microns"),
                processing_depth_microns=parameters.get("processing_depth_microns"),
                service_id=service_id,
            )

        if service_id == "printing":
            try:
                dimensions = parameters.get("ml_features", {}).get("dimensions")
                if dimensions is None:
                    dimensions = parameters.get("dimensions")
            except Exception:
                dimensions = parameters.get("dimensions")
            return PrintingCalculationRequest(
                file_id=file_id,
                dimensions=dimensions,
                material_id=parameters["material_id"],
                material_form=parameters["material_form"],
                quantity=parameters.get("quantity", 1),
                cover_id=parameters.get("cover_id", DEFAULTS["cover_id_list"]),
                location=PRINTING_LOCATION,
                k_otk=parameters.get("k_otk", DEFAULTS["k_otk"]),
                k_cert=parameters.get("k_cert", DEFAULTS["k_cert_printing"]),
                service_id=service_id,
            )

        raise ValueError(f"Unknown or unsupported service ID: {service_id}")


# Global router instance
calculation_router = CalculationRouter()
