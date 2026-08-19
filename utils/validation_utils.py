"""
Standardized validation utilities
"""

from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from constants import (
    ERROR_MESSAGES, ERROR_CODES, TOLERANCE, FINISH, COVER,
    AUTO_SERVICES, NON_AUTO_SERVICES, OTHER_SERVICES
)
# from MATERIALS_gen import MATERIALS
from utils.logging_utils import get_logger
from utils.response_utils import ResponseWrapper
from calculations.core import resolve_priced_material_form, lookup_material
from utils.electroplating_config import (
    ELECTROPLATING_SERVICE_ID,
    get_electroplating_process,
    get_electroplating_material_family,
    get_material_families,
    infer_material_family,
    is_material_family_allowed_for_electroplating_process,
    normalize_material_family_id,
    NOT_APPLICABLE_ELECTROPLATING_FAMILY,
)

logger = get_logger(__name__)

VALID_SERVICES_LIST = []
AUTO_SERVICES_LIST = [v["service"] for v in AUTO_SERVICES.values()]
VALID_SERVICES_LIST.extend(AUTO_SERVICES_LIST)
VALID_SERVICES_LIST.extend([v["service"] for v in OTHER_SERVICES.values()])
VALID_SERVICES_LIST.extend([v["service"] for v in NON_AUTO_SERVICES.values()])

class ValidationError(Exception):
    """Custom validation error with standardized message"""
    
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")


class Validator:
    """Centralized validation utilities"""
    
    @staticmethod
    def validate_service_id(service_id: str) -> None:
        """Validate service ID"""
        valid_services = VALID_SERVICES_LIST
        if service_id not in valid_services:
            raise ValidationError(
                field="service_id",
                message=ERROR_MESSAGES["invalid_parameter_value"],
                value=service_id
            )
    
    @staticmethod
    def validate_material_id(material_id: str, service_id: str, material_info: Dict[str, Any]) -> None:
        """Validate material ID and its applicability to service."""
 
        applicable_processes = material_info.get("applicable_processes", [])

        if service_id == ELECTROPLATING_SERVICE_ID:
            try:
                material_family = infer_material_family(material_id, material_info)
            except ValueError as exc:
                raise ValidationError(
                    field="material_id",
                    message=str(exc),
                    value=material_id,
                )

            family_info = get_material_families().get(material_family)
            if material_family == NOT_APPLICABLE_ELECTROPLATING_FAMILY or not family_info or not family_info.get("allowed_processes"):
                raise ValidationError(
                    field="material_id",
                    message=f"Material {material_id} is not applicable for service {service_id}",
                    value=material_id,
                )
            return

        if service_id in AUTO_SERVICES_LIST and service_id not in applicable_processes:
            raise ValidationError(
                field="material_id",
                message=f"Material {material_id} is not applicable for service {service_id}",
                value=material_id
            )

    @staticmethod
    def validate_material_form(material_id: str, material_form: str, service_id: str, material_info: Dict[str, Any]) -> None:
        """Validate material form for the selected material and service."""
        forms = material_info.get("forms", {})

        if material_form not in forms:
            fallback_form = resolve_priced_material_form(material_id, material_form, service_id)
            if service_id == "cnc-milling" and fallback_form:
                logger.warning(
                    "material_form=%s is unavailable for material_id=%s; cnc-milling will use fallback form=%s",
                    material_form,
                    material_id,
                    fallback_form,
                )
                return
            available_forms = list(forms.keys())
            raise ValidationError(
                field="material_form",
                message=f"Invalid material form. Available forms for {material_id}: {available_forms}",
                value=material_form
            )

        # For electroplating the material form is kept only for compatibility with
        # the common request schema; galvanic applicability is defined by
        # electroplating_family, not by form-level applicable_processes.
        if service_id == ELECTROPLATING_SERVICE_ID:
            return

        form_processes = forms.get(material_form, {}).get("applicable_processes", [])
        if service_id and service_id in AUTO_SERVICES_LIST and service_id not in form_processes:
            fallback_form = resolve_priced_material_form(material_id, material_form, service_id)
            if service_id == "cnc-milling" and fallback_form:
                logger.warning(
                    "material_form=%s is not applicable for service=%s; cnc-milling will use fallback form=%s",
                    material_form,
                    service_id,
                    fallback_form,
                )
                return
            raise ValidationError(
                field="material_form",
                message=f"Material form {material_form} is not applicable for service {service_id}",
                value=material_form,
            )
    
    @staticmethod
    def validate_dimensions(dimensions: Dict[str, float]) -> None:
        """Validate dimensions"""
        required_fields = ["length", "width", "height"]
        
        for field in required_fields:
            if field not in dimensions:
                raise ValidationError(
                    field=field,
                    message=ERROR_MESSAGES["missing_required_field"],
                    value=None
                )
            
            if not isinstance(dimensions[field], (int, float)) or dimensions[field] <= -0.1:
                raise ValidationError(
                    field=field,
                    message=ERROR_MESSAGES["invalid_dimensions"],
                    value=dimensions[field]
                )
    
    @staticmethod
    def validate_quantity(quantity: int) -> None:
        """Validate quantity"""
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError(
                field="quantity",
                message=ERROR_MESSAGES["invalid_quantity"],
                value=quantity
            )
    
    @staticmethod
    def validate_tolerance_id(tolerance_id: str) -> None:
        """Validate tolerance ID"""
        if tolerance_id not in TOLERANCE:
            available_tolerances = list(TOLERANCE.keys())
            raise ValidationError(
                field="tolerance_id",
                message=f"Invalid tolerance ID. Available: {available_tolerances}",
                value=tolerance_id
            )
    
    @staticmethod
    def validate_finish_id(finish_id: str) -> None:
        """Validate finish ID"""
        if finish_id not in FINISH:
            available_finishes = list(FINISH.keys())
            raise ValidationError(
                field="finish_id",
                message=f"Invalid finish ID. Available: {available_finishes}",
                value=finish_id
            )
    
    @staticmethod
    def validate_cover_ids(cover_ids: List[str]) -> None:
        """Validate cover processing IDs"""
        if not isinstance(cover_ids, list):
            raise ValidationError(
                field="cover_id",
                message="Cover processing IDs must be a list",
                value=cover_ids
            )
        
        for cover_id in cover_ids:
            if cover_id not in COVER:
                available_covers = list(COVER.keys())
                raise ValidationError(
                    field="cover_id",
                    message=f"Invalid cover ID: {cover_id}. Available: {available_covers}",
                    value=cover_id
                )
    
    @staticmethod
    def validate_file_data(file_data: str, file_name: str, file_type: str) -> None:
        """Validate file upload data"""
        if not file_data:
            raise ValidationError(
                field="file_data",
                message="File data is required",
                value=None
            )
        
        if not file_name:
            raise ValidationError(
                field="file_name",
                message="File name is required",
                value=None
            )
        
        if not file_type:
            raise ValidationError(
                field="file_type",
                message="File type is required",
                value=None
            )
        
        valid_types = ["stl", "stp", "step"]
        if file_type.lower() not in valid_types:
            raise ValidationError(
                field="file_type",
                message=ERROR_MESSAGES["unsupported_file_type"],
                value=file_type
            )
    
    @staticmethod
    def validate_file_type(file_type: str, service_id: str) -> None:
        """Validate file type and service conformity"""
        if file_type == "stl" and service_id in ("cnc-milling", "composite", ELECTROPLATING_SERVICE_ID):
            raise ValidationError(
                field="file_type",
                message=ERROR_MESSAGES["unsupported_file_type"],
                value=file_type
            )

    @staticmethod
    def validate_electroplating_family(family_id: str) -> None:
        """Validate electroplating material family ID."""
        normalized = normalize_material_family_id(family_id)
        family = get_electroplating_material_family(normalized)
        if family is None:
            raise ValidationError(
                field="electroplating_family",
                message=f"Invalid electroplating family ID: {family_id}",
                value=family_id,
            )

    @staticmethod
    def validate_electroplating_process(process_id: str) -> None:
        """Validate electroplating process ID."""
        if process_id and get_electroplating_process(process_id) is None:
            raise ValidationError(
                field="electroplating_process_id",
                message=f"Invalid electroplating process ID: {process_id}",
                value=process_id
            )

def validate_calculation_request(request_data: Dict[str, Any]) -> List[ValidationError]:
    """Validate complete calculation request"""
    errors = []
    
    try:
        # Validate service ID
        Validator.validate_service_id(request_data.get("service_id", ""))
    except ValidationError as e:
        errors.append(e)

    material_id = request_data.get("material_id", "")
    material_info = lookup_material(material_id)

    # Validate material if provided
    if "material_id" in request_data:
        try:
            # Validator.validate_material_id(request_data)
            Validator.validate_material_id(
                request_data["material_id"], 
                request_data.get("service_id", ""),
                request_data.get("material_snapshot", material_info),
            )
        except ValidationError as e:
            errors.append(e)

    # Validate material form if provided
    if "material_id" in request_data and "material_form" in request_data:
        try:
            Validator.validate_material_form(
                request_data["material_id"],
                request_data["material_form"],
                request_data.get("service_id", ""),
                request_data.get("material_snapshot", material_info),
            )
        except ValidationError as e:
            errors.append(e)

    # Validate quantity if provided
    if "quantity" in request_data:
        try:
            Validator.validate_quantity(request_data["quantity"])
        except ValidationError as e:
            errors.append(e)
    
    # Validate tolerance if provided
    if "tolerance_id" in request_data:
        try:
            Validator.validate_tolerance_id(request_data["tolerance_id"])
        except ValidationError as e:
            errors.append(e)
    
    # Validate finish if provided
    if "finish_id" in request_data:
        try:
            Validator.validate_finish_id(request_data["finish_id"])
        except ValidationError as e:
            errors.append(e)
    
    # Validate cover processing if provided. For electroplating_auto cover_id can
    # carry the galvanic process id when electroplating_process_id is absent.
    if "cover_id" in request_data:
        try:
            if request_data.get("service_id") == ELECTROPLATING_SERVICE_ID:
                cover_values = request_data.get("cover_id") or []
                if cover_values:
                    Validator.validate_electroplating_process(cover_values[0])
            else:
                Validator.validate_cover_ids(request_data["cover_id"])
        except ValidationError as e:
            errors.append(e)

    if request_data.get("service_id") == ELECTROPLATING_SERVICE_ID:
        process_id = request_data.get("electroplating_process_id")
        process_id = process_id or ((request_data.get("cover_id") or [None])[0])
        process = None
        if process_id:
            try:
                Validator.validate_electroplating_process(process_id)
                process = get_electroplating_process(process_id)
            except ValidationError as e:
                errors.append(e)

        requested_family = request_data.get("electroplating_family")
        resolved_family = None

        if requested_family:
            try:
                Validator.validate_electroplating_family(requested_family)
                resolved_family = normalize_material_family_id(requested_family)
            except ValidationError as e:
                errors.append(e)

        # if material_id in MATERIALS:
        if material_info:
            try:
                material_family_from_material = infer_material_family(material_id, material_info)
                if resolved_family and material_family_from_material != resolved_family:
                    raise ValidationError(
                        field="electroplating_family",
                        message=(
                            f"electroplating_family={resolved_family} does not match "
                            f"for material_id {material_id!r} material_info['electroplating_family']={material_family_from_material}"
                        ),
                        value=requested_family,
                    )
                resolved_family = resolved_family or material_family_from_material
            except ValueError as exc:
                errors.append(ValidationError(
                    field="material_id",
                    message=str(exc),
                    value=material_id,
                ))
            except ValidationError as e:
                errors.append(e)

        if not resolved_family:
            errors.append(ValidationError(
                field="electroplating_family",
                message=(
                    "electroplating_family is required for service_id='electroplating_auto'. "
                    "material_id is accepted only for deriving the same family."
                ),
                value=requested_family,
            ))

        if process and resolved_family:
            allowed_families = set(process.get("material_families") or [])
            if not is_material_family_allowed_for_electroplating_process(resolved_family, process_id):
                # New frontend flow sends electroplating_family explicitly, so a
                # family/process mismatch is best reported on electroplating_family.
                # Requests may still send only material_id; in that case the invalid
                # user choice is the selected electroplating_process_id for the
                # material-derived family. Keep the field-level contract so clients
                # can highlight the process selector.
                mismatch_field = "electroplating_family" if requested_family else "electroplating_process_id"
                mismatch_value = resolved_family if requested_family else process_id
                errors.append(ValidationError(
                    field=mismatch_field,
                    message=(
                        f"Process {process.get('id')} is not applicable for electroplating_family "
                        f"{resolved_family}. Allowed families: {sorted(allowed_families)}"
                    ),
                    value=mismatch_value,
                ))

        thickness = request_data.get("coating_thickness_microns")
        if thickness is not None:
            try:
                if float(thickness) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(ValidationError(
                    field="coating_thickness_microns",
                    message="Coating/layer thickness must be a non-negative number",
                    value=thickness,
                ))

        processing_depth = request_data.get("processing_depth_microns")
        if processing_depth is not None:
            try:
                if float(processing_depth) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(ValidationError(
                    field="processing_depth_microns",
                    message="Processing/removal depth must be a non-negative number",
                    value=processing_depth,
                ))
    
    # Validate file data if provided
    if all(key in request_data for key in ["file_data", "file_name", "file_type"]):
        try:
            Validator.validate_file_data(
                request_data["file_data"],
                request_data["file_name"],
                request_data["file_type"]
            )
        except ValidationError as e:
            errors.append(e)
    
    # Validate file type and service confirmity
    if all(key in request_data for key in ["file_type", "service_id"]):
        try:
            Validator.validate_file_type(
                request_data["file_type"],
                request_data["service_id"]
            )
        except ValidationError as e:
            errors.append(e)

    return errors


def create_validation_error_response(errors: List[ValidationError], request_id: Optional[str] = None) -> Dict[str, Any]:
    """Create standardized validation error response"""
    from models.error_models import ErrorDetail
    
    error_details = [
        ErrorDetail(
            field=error.field,
            message=error.message,
            value=error.value
        )
        for error in errors
    ]
    
    return ResponseWrapper.error_response(
        error_type="validation",
        error_message=ERROR_MESSAGES["validation_error"],
        error_code=ERROR_CODES["VALIDATION_ERROR"],
        details=error_details,
        request_id=request_id
    )
