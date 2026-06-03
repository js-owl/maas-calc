"""
Standardized validation utilities
"""

from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from constants import (
    ERROR_MESSAGES, ERROR_CODES, MATERIALS, TOLERANCE, FINISH, COVER,
    AUTO_SERVICES, NON_AUTO_SERVICES, OTHER_SERVICES
)
from utils.logging_utils import get_logger
from utils.response_utils import ResponseWrapper
from utils.electroplating_config import (
    ELECTROPLATING_SERVICE_ID,
    get_electroplating_process,
    get_material_families,
    infer_material_family,
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
    def validate_material_id(material_id: str, service_id: str) -> None:
        """Validate material ID and its applicability to service."""
        if material_id not in MATERIALS:
            raise ValidationError(
                field="material_id",
                message=ERROR_MESSAGES["invalid_material"],
                value=material_id
            )

        material_info = MATERIALS[material_id]
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
    def validate_material_form(material_id: str, material_form: str, service_id: str = "") -> None:
        """Validate material form for the selected material and service."""
        if material_id not in MATERIALS:
            return  # Will be caught by material_id validation

        material_info = MATERIALS[material_id]
        forms = material_info.get("forms", {})

        if material_form not in forms:
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
    
    # Validate material if provided
    if "material_id" in request_data:
        try:
            Validator.validate_material_id(
                request_data["material_id"], 
                request_data.get("service_id", "")
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
    # carry the galvanic process id for backward compatibility with the existing
    # frontend request shape.
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

        material_id = request_data.get("material_id")
        if process and material_id in MATERIALS:
            try:
                material_family = infer_material_family(material_id, MATERIALS[material_id])
                allowed_families = set(process.get("material_families") or [])
                if allowed_families and material_family not in allowed_families:
                    raise ValidationError(
                        field="electroplating_process_id",
                        message=(
                            f"Process {process.get('id')} is not applicable for material family "
                            f"{material_family}. Allowed families: {sorted(allowed_families)}"
                        ),
                        value=process_id,
                    )
            except ValueError as exc:
                errors.append(ValidationError(
                    field="material_id",
                    message=str(exc),
                    value=material_id,
                ))
            except ValidationError as e:
                errors.append(e)

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
