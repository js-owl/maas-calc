"""
Parameter safeguard system
"""

import logging
from typing import Dict, Any, Optional
from models.base_models import Dimensions, MaterialForm
from constants import DEFAULTS

logger = logging.getLogger(__name__)


class SafeguardManager:
    """Manages parameter safeguards and default values"""
    
    def __init__(self):
        self.defaults = {
            "printing": {
                "dimensions": Dimensions(length=100.0, width=50.0, thickness=10.0),
                "quantity": 1,
                "material_id": "PA11",
                "material_form": MaterialForm.POWDER,
                "cover_id": DEFAULTS["cover_id_list"],
                "location": DEFAULTS["location"],
                "n_dimensions": DEFAULTS["n_dimensions"],
                "k_type": DEFAULTS["k_type"],
                "k_process": DEFAULTS["k_process"],
                "k_otk": DEFAULTS["k_otk"],
                "k_cert": []
            },
            "cnc-milling": {
                "dimensions": Dimensions(length=100.0, width=50.0, thickness=10.0),
                "quantity": 1,
                "material_id": "alum_D16",
                "material_form": MaterialForm.SHEET,
                "cover_id": DEFAULTS["cover_id_list"],
                "tolerance_id": DEFAULTS["tolerance_id"],
                "finish_id": DEFAULTS["finish_id"],
                "location": DEFAULTS["location"],
                "k_otk": DEFAULTS["k_otk"],
                "cnc_complexity": DEFAULTS["cnc_complexity"],
                "cnc_setup_time": DEFAULTS["cnc_setup_time"]
            },
            "cnc-lathe": {
                "dimensions": Dimensions(length=100.0, width=50.0, thickness=10.0),
                "quantity": 1,
                "material_id": "alum_D16",
                "material_form": MaterialForm.ROD,
                "cover_id": DEFAULTS["cover_id_list"],
                "tolerance_id": DEFAULTS["tolerance_id"],
                "finish_id": DEFAULTS["finish_id"],
                "location": DEFAULTS["location"],
                "k_otk": DEFAULTS["k_otk"],
                "cnc_complexity": DEFAULTS["cnc_complexity"],
                "cnc_setup_time": DEFAULTS["cnc_setup_time"]
            },
            "painting": {
                "dimensions": Dimensions(length=100.0, width=50.0, thickness=10.0),
                "quantity": 1,
                "material_id": "alum_D16",
                "material_form": MaterialForm.SHEET,
                "cover_id": DEFAULTS["cover_id_list"],
                "tolerance_id": DEFAULTS["tolerance_id"],
                "finish_id": DEFAULTS["finish_id"],
                "location": DEFAULTS["location"],
                "k_otk": DEFAULTS["k_otk"]
            }
        }
    
    def apply_safeguards(self, service_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply safeguards to parameters for the given service
        
        Args:
            service_id: Manufacturing service ID
            parameters: Current parameters
            
        Returns:
            Parameters with safeguards applied
        """
        logger.info(f"Applying parameter safeguards for service: {service_id}")
        
        # Get defaults for this service
        defaults = self.defaults.get(service_id, {})
        if not defaults:
            logger.warning(f"No defaults found for service: {service_id}")
            return parameters
        
        # Apply safeguards
        safeguarded = parameters.copy()
        warnings = []
        
        for key, default_value in defaults.items():
            if key not in safeguarded or safeguarded[key] is None:
                safeguarded[key] = default_value
                warnings.append(f"Using default {key}: {default_value}")
                logger.warning(f"Using default {key}: {default_value}")
        
        # Special handling for dimensions
        if "dimensions" not in safeguarded or safeguarded["dimensions"] is None:
            safeguarded["dimensions"] = defaults["dimensions"]
            logger.warning(f"Using default dimensions: {defaults['dimensions']}")
        
        # Special handling for material_form validation
        if "material_id" in safeguarded and "material_form" in safeguarded:
            safeguard_form = self._validate_material_form(safeguarded["material_id"], safeguarded["material_form"])
            if safeguard_form:
                safeguarded["material_form"] = safeguard_form
        logger.info(f"Safeguarded material form: {safeguarded['material_form']}")

        return safeguarded
    
    def _validate_material_form(self, material_id: str, material_form: MaterialForm) -> None:
        """Validate material form against material ID"""
        try:
            from constants import MATERIALS
            if material_id in MATERIALS:
                allowed_forms = list(MATERIALS[material_id].get("forms", []).keys())
                if material_form not in allowed_forms:
                    logger.warning(f"Form '{material_form}' not allowed for {material_id}. Using first allowed form.")
                    # Use first allowed form as fallback
                    if allowed_forms:
                        safeguard_form = allowed_forms[0]
                        return safeguard_form
        except Exception as e:
            logger.warning(f"Error validating material form: {e}")
    
    def get_default_dimensions(self, service_id: str) -> Dimensions:
        """Get default dimensions for service"""
        defaults = self.defaults.get(service_id, {})
        return defaults.get("dimensions", Dimensions(length=100.0, width=50.0, thickness=10.0))
