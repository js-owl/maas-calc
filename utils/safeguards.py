"""
Parameter safeguard system.

Only two non-price-critical compatibility defaults are applied here:
- material_form: when material_id is present but material_form is absent;
- location: when location is absent.

All other price-critical parameters must be provided by the request or extracted
from the file. This avoids silent price changes caused by hidden defaults.
"""

import logging
from typing import Dict, Any, Optional

from constants import DEFAULTS, PRINTING_LOCATION
# from MATERIALS_gen import MATERIALS
from models.base_models import Dimensions
from utils.electroplating_config import ELECTROPLATING_SERVICE_ID
from calculations.core import resolve_priced_material_form, lookup_material

logger = logging.getLogger(__name__)


class SafeguardManager:
    """Applies narrow compatibility safeguards for request parameters."""

    def __init__(self):
        self.location_default = DEFAULTS["location"]

    def apply_safeguards(self, service_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply only material_form and location safeguards."""
        logger.info("Applying parameter safeguards for service: %s", service_id)
        safeguarded = parameters.copy()

        if safeguarded.get("location") is None:
            location_default = PRINTING_LOCATION if service_id == "printing" else self.location_default
            safeguarded["location"] = location_default
            logger.warning("Using default location: %s", location_default)

        if safeguarded.get("material_form") is None and safeguarded.get("material_id"):
            default_form = self._default_material_form(
                safeguarded["material_id"],
                service_id=service_id,
            )
            if default_form is not None:
                safeguarded["material_form"] = default_form
                logger.warning(
                    "Using default material_form for %s: %s",
                    safeguarded["material_id"],
                    default_form,
                )

        if safeguarded.get("material_id") and safeguarded.get("material_form"):
            safeguard_form = self._validate_material_form(
                safeguarded["material_id"],
                safeguarded["material_form"],
                service_id=service_id,
            )
            if safeguard_form:
                safeguarded["material_form"] = safeguard_form

        logger.info("Safeguarded material form: %s", safeguarded.get("material_form"))
        return safeguarded

    def _default_material_form(self, material_id: str, service_id: str = "") -> Optional[str]:
        """Return the first material form applicable to the service, if any."""
        # material = MATERIALS.get(material_id) or {}
        material = lookup_material(material_id)
        forms = material.get("forms") or {}
        if not forms:
            return None

        if service_id == ELECTROPLATING_SERVICE_ID:
            return next(iter(forms.keys()), None)

        resolved_form = resolve_priced_material_form(material_id, None, service_id)
        if resolved_form is not None:
            return resolved_form
        return next(iter(forms.keys()), None)

    def _validate_material_form(
        self,
        material_id: str,
        material_form: str,
        service_id: str = "",
    ) -> Optional[str]:
        """Replace an invalid material form with the first valid form for this material."""
        try:
            # material = MATERIALS.get(material_id) or {}
            material = lookup_material(material_id)
            forms = material.get("forms") or {}
            allowed_forms = list(forms.keys())
            resolved_form = resolve_priced_material_form(material_id, material_form, service_id)
            if resolved_form and resolved_form != material_form:
                logger.warning(
                    "Form %r is not priced/allowed for %s and service %s. Using %r.",
                    material_form,
                    material_id,
                    service_id,
                    resolved_form,
                )
                return resolved_form
            if allowed_forms and material_form not in allowed_forms:
                logger.warning(
                    "Form %r is not allowed for %s. Using first allowed form.",
                    material_form,
                    material_id,
                )
                return self._default_material_form(material_id, service_id) or allowed_forms[0]
        except Exception as e:
            logger.warning("Error validating material form: %s", e)
        return None

    def get_default_dimensions(self, service_id: str) -> Dimensions:
        """Legacy helper kept for compatibility; dimensions are no longer auto-filled."""
        raise ValueError(
            f"Default dimensions are not available for service_id={service_id!r}. "
            "Pass dimensions explicitly or provide file_data for extraction."
        )
