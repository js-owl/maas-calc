"""
Manufacturing Calculation API v3.0.0
Modular architecture with unified API
"""

import logging
import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from starlette.concurrency import run_in_threadpool

# Import our modular components
from models import UnifiedCalculationRequest, UnifiedCalculationResponse
from utils import ParameterExtractor, SafeguardManager, CalculationRouter
from utils.generate_previews import (
    b64, generate_preview_images_sync, png_placeholder,
    PREVIEW_SUPPORTED_EXT
)
from utils.response_utils import ResponseWrapper, add_response_metadata
from utils.logging_utils import get_logger, set_request_id
from utils.middleware import RequestTrackingMiddleware
from utils.versioning import VersioningMiddleware, get_version_info
from utils.validation_utils import validate_calculation_request, create_validation_error_response
from constants import (
    MATERIALS, LOCATIONS, COVER, TOLERANCE, 
    FINISH, CONTROL_TYPES, CERT_COSTS, AUTO_SERVICES, NON_AUTO_SERVICES,
    OTHER_SERVICES, APP_VERSION
)
from utils.electroplating_config import (
    ELECTROPLATING_SERVICE_ID,
    NON_AUTO_ELECTROPLATING_SERVICE,
    get_baths,
    get_material_families,
    get_process_params,
    infer_material_family,
    is_material_allowed_for_electroplating,
    is_material_allowed_for_electroplating_process,
    get_allowed_material_forms,
    get_electroplating_process,
)

# Configure rendering
os.environ["PYOPENGL_PLATFORM"] = "osmesa"

# Configure logging
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=f"Manufacturing Calculation API v{APP_VERSION}",
    description="Unified API for manufacturing cost calculations with file upload support",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request tracking middleware
app.add_middleware(RequestTrackingMiddleware)

# Add versioning middleware
app.add_middleware(VersioningMiddleware)

# Initialize modular components
parameter_extractor = ParameterExtractor()
safeguard_manager = SafeguardManager()
calculation_router = CalculationRouter()


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    data = {
        "message": f"Manufacturing Calculation API v{APP_VERSION}",
        "version": APP_VERSION,
        "docs": "/docs",
        "unified_endpoint": "/calculate-price"
    }
    return ResponseWrapper.success_response(data, "API information retrieved successfully")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    data = {"status": "healthy"}
    return ResponseWrapper.success_response(data, "Health check completed")


@app.get("/version", tags=["System"])
async def get_version():
    """Get API version information"""
    data = get_version_info()
    return ResponseWrapper.success_response(data, "Version information retrieved successfully")


@app.post("/calculate-price", tags=["Manufacturing Calculations"])
async def calculate_price(request: UnifiedCalculationRequest):
    """
    Unified endpoint for manufacturing price calculations
    
    This endpoint handles all manufacturing calculations including:
    - 3D Printing (printing)
    - CNC Milling (cnc-milling, ML-only)
    - Composite labor forecast (composite)
    - Electroplating automatic pricing (electroplating_auto)
    
    Supports file upload via base64 encoding and automatic parameter extraction.
    """
    from utils.logging_utils import log_calculation_start, log_calculation_complete, log_error
    import time
    
    start_time = time.time()
    log_calculation_start(
        logger=logger,
        service_type=request.service_id,
        file_id=request.file_id or "unknown",
        request_id=getattr(request, 'request_id', None)
    )

    AUTO_SERVICES_LIST = [v["service"] for v in AUTO_SERVICES.values()]
    
    if request.service_id == "cnc-milling" and request.file_data is None:
        return ResponseWrapper.calculation_error(
            message=(
                "file_data is required for ML-based service_id='cnc-milling'. "
                "Rule-based CNC milling fallback was removed."
            ),
            request_id=getattr(request, 'request_id', None)
        )

    if request.service_id == ELECTROPLATING_SERVICE_ID and request.file_data is None and not request.features_dict:
        return ResponseWrapper.calculation_error(
            message=(
                "file_data is required for service_id='electroplating_auto' because "
                "the calculation uses STP/STEP surface_area, volume and OBB dimensions."
            ),
            request_id=getattr(request, 'request_id', None)
        )

    if request.service_id not in AUTO_SERVICES_LIST:
        logger.info("Default request!")
        result = UnifiedCalculationResponse(
            service_id=request.service_id,
            part_price=0,
            detail_price=0,
            part_price_one=0,
            detail_price_one=0,
            total_price=0,
            total_time=0,
            calculation_method="rule_based"
        )
        return ResponseWrapper.success_response(
            data=result.model_dump(),
            message=f"Calculation completed successfully for {request.service_id}",
            request_id=getattr(request, 'request_id', None)
        )

    # Validate request before processing
    request_data = request.model_dump(exclude_unset=True, exclude_none=True)
    validation_errors = validate_calculation_request(request_data)
    
    if validation_errors:
        return create_validation_error_response(
            validation_errors,
            request_id=getattr(request, 'request_id', None)
        )

    # logging request to dev
    # filtered_request = {k: v for k, v in request_data.items() if k != "file_data"}
    # logger.info(f"============================= Request: поля: {list(request_data.keys())}, Request data without file_data {filtered_request}")
    try:
        # Step 1: Extract parameters from file if provided
        extracted_params = {}
        ml_features = None
        if request.file_data and request.file_name and request.file_type:
            logger.info(f"Analyzing file: {request.file_name} (file_id: {request.file_id})")
            extracted_params = await parameter_extractor.extract_parameters_from_file(
                request.file_data, request.file_name, request.file_type
            )
            logger.info(f"File analysis completed for file_id: {request.file_id}")
            
            # Extract ML features if available
            if extracted_params.get('volume') and extracted_params.get('surface_area'):
                ml_features = extracted_params
                logger.info(f"ML features extracted")
        
        # Step 2: Merge extracted parameters with request parameters
        request_params = request.model_dump(exclude_unset=True, exclude_none=True)
        merged_params = parameter_extractor.merge_parameters(extracted_params, request_params)
        
        # Add extracted geometry features to merged parameters. The key is named
        # ml_features for historical compatibility with CNC/composite code, but
        # electroplating_auto uses the same STP geometry in a rule-based formula.
        if ml_features:
            merged_params['ml_features'] = ml_features
        elif request.service_id == ELECTROPLATING_SERVICE_ID and request.features_dict:
            merged_params['ml_features'] = request.features_dict
            
        # Step 3: Apply safeguards for missing parameters
        safeguarded_params = safeguard_manager.apply_safeguards(request.service_id, merged_params)
        
        # Step 4: Determine calculation method and route
        use_ml = calculation_router.should_use_ml(safeguarded_params)
        if use_ml:
            logger.info(f"Using ML-based calculation for file_id: {request.file_id}")
        else:
            logger.info(f"Using rule-based calculation for file_id: {request.file_id}")
        
        result = await calculation_router.route_calculation(
            request.service_id, 
            safeguarded_params, 
            use_ml=use_ml
        )
        # logger.info('======================================= main.py calculate_price() result:', result.model_dump())
        
        # Step 5: Add file information and calculation engine info
        if request.file_name:
            result.filename = request.file_name
        # if extracted_params.get('extracted_dimensions'):
        #     result.extracted_dimensions = extracted_params['extracted_dimensions']
        
        # Set calculation engine
        result.calculation_engine = "ml_model" if use_ml else "rule_based"
        
        # Log completion
        duration_ms = (time.time() - start_time) * 1000
        log_calculation_complete(
            logger=logger,
            service_type=request.service_id,
            file_id=request.file_id or "unknown",
            request_id=getattr(request, 'request_id', None),
            duration_ms=duration_ms
        )
        
        # Wrap result in standardized response
        return ResponseWrapper.success_response(
            data=result.model_dump(),
            message=f"Calculation completed successfully for {request.service_id}",
            request_id=getattr(request, 'request_id', None)
        )
        
    except HTTPException as e:
        log_error(
            logger=logger,
            error_type="calculation_error",
            message=f"HTTP error in calculation: {str(e)}",
            file_id=request.file_id,
            request_id=getattr(request, 'request_id', None),
            exception=e
        )
        # Return standardized error response instead of raising
        return ResponseWrapper.calculation_error(
            message=str(e.detail) if hasattr(e, 'detail') else str(e),
            request_id=getattr(request, 'request_id', None)
        )
    except Exception as e:
        log_error(
            logger=logger,
            error_type="calculation_error", 
            message=f"Unexpected error in calculation: {str(e)}",
            file_id=request.file_id,
            request_id=getattr(request, 'request_id', None),
            exception=e
        )
        # Return standardized error response instead of raising
        return ResponseWrapper.calculation_error(
            message=str(e),
            request_id=getattr(request, 'request_id', None)
        )


@app.post("/generate-previews", tags=["Files"])
async def generate_previews(
    file: UploadFile = File(...),
    size: int = Query(512, ge=64, le=2048, description="PNG square size"),
    views: int = Query(1, ge=1, le=4, description="Number of rendered views (1..4)")
):
    """Generate PNG preview images for a 3D model (.stl, .stp, .step).

    Important: this endpoint ONLY generates images and returns them (base64).
    Persisting the final previews should be done by the caller service.
    """
    filename = file.filename or "model"
    ext = Path(filename).suffix.lower()

    if ext not in PREVIEW_SUPPORTED_EXT:
        return ResponseWrapper.calculation_error(
            message=f"Unsupported file type for preview: {ext}. \
                Supported: {sorted(PREVIEW_SUPPORTED_EXT)}"
        )

    try:
        file_bytes = await file.read()
        if not file_bytes:
            return ResponseWrapper.calculation_error(
                message="Empty uploaded file"
            )
        import asyncio
        try:
            images = await run_in_threadpool(
                generate_preview_images_sync, file_bytes, ext, size, views, # timeout=10
                )
        except asyncio.TimeoutError:
            images = [png_placeholder(size)]

        data = {
            "filename": filename,
            "ext": ext,
            "size": size,
            "views": views,
            "images_png_base64": [b64(img) for img in images],
        }
        return ResponseWrapper.success_response(
            data, "Preview images generated successfully"
        )

    except Exception as e:
        logger.exception("Preview generation failed")
        return ResponseWrapper.calculation_error(
            message=f"Preview generation failed: {e}"
        )

def _material_response_item(material_id: str, material_info: Dict[str, Any]) -> Dict[str, Any]:
    """Build a stable material option payload for UI selectors."""
    forms = get_allowed_material_forms(material_info)
    return {
        "id": material_id,
        "label": material_info.get("label", ""),
        "family": material_info.get("family", ""),
        "density": material_info.get("density", 0.0),
        "forms": forms,
        "available_forms": list(forms.keys()),
        "applicable_processes": material_info.get("applicable_processes", []),
        "electroplating_family": material_info.get("electroplating_family"),
    }


def _material_form_response_items(
    material_info: Dict[str, Any],
    service_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build material_form options from constants.MATERIALS only."""
    forms = get_allowed_material_forms(material_info)
    result: List[Dict[str, Any]] = []
    for form_id, form_info in sorted(forms.items(), key=lambda item: item[0]):
        form_processes = form_info.get("applicable_processes", [])
        if (
            service_id
            and service_id != ELECTROPLATING_SERVICE_ID
            and form_processes
            and service_id not in form_processes
        ):
            continue
        result.append({
            "id": form_id,
            "label": form_info.get("label") or form_id,
            "price": form_info.get("price"),
            "applicable_processes": form_processes,
            "one_layer_thickness": form_info.get("one_layer_thickness"),
        })
    return result


@app.get("/materials", tags=["Configuration"])
async def list_materials(
    process: Optional[str] = None,
    electroplating_process_id: Optional[str] = None,
):
    """List available materials, optionally filtered by service/process.

    For electroplating_auto the optional electroplating_process_id narrows the
    result to materials whose explicit electroplating_family is allowed for the
    selected galvanic operation.
    """
    if process == ELECTROPLATING_SERVICE_ID and electroplating_process_id:
        if get_electroplating_process(electroplating_process_id) is None:
            return ResponseWrapper.validation_error(
                field="electroplating_process_id",
                message=f"Invalid electroplating process ID: {electroplating_process_id}",
                value=electroplating_process_id,
            )

    materials_list = []

    for material_id, material_info in MATERIALS.items():
        if process == ELECTROPLATING_SERVICE_ID:
            try:
                if electroplating_process_id:
                    if not is_material_allowed_for_electroplating_process(
                        material_id, material_info, electroplating_process_id
                    ):
                        continue
                elif not is_material_allowed_for_electroplating(material_id, material_info):
                    continue
            except ValueError:
                continue
        elif process and process not in material_info.get("applicable_processes", []):
            continue

        materials_list.append(_material_response_item(material_id, material_info))

    materials_list = sorted(materials_list, key=lambda x: x["label"])

    data = {
        "materials": materials_list,
        "process": process,
        "electroplating_process_id": electroplating_process_id if process == ELECTROPLATING_SERVICE_ID else None,
    }
    message = f"Materials retrieved successfully{f' for process: {process}' if process else ''}"
    return ResponseWrapper.success_response(data, message)


@app.get("/material_forms", tags=["Configuration"])
async def list_material_forms(
    material_id: str,
    service_id: Optional[str] = None,
    electroplating_process_id: Optional[str] = None,
):
    """List material_form options for a selected material.

    For electroplating_auto this also verifies that the material is compatible
    with the selected electroplating_process_id when that query parameter is
    provided. The returned forms are never synthesized; they come only from
    constants.MATERIALS[material_id]["forms"].
    """
    material_info = MATERIALS.get(material_id)
    if material_info is None:
        return ResponseWrapper.validation_error(
            field="material_id",
            message=f"Invalid material ID: {material_id}",
            value=material_id,
        )

    if service_id == ELECTROPLATING_SERVICE_ID:
        try:
            if electroplating_process_id:
                if get_electroplating_process(electroplating_process_id) is None:
                    return ResponseWrapper.validation_error(
                        field="electroplating_process_id",
                        message=f"Invalid electroplating process ID: {electroplating_process_id}",
                        value=electroplating_process_id,
                    )
                if not is_material_allowed_for_electroplating_process(
                    material_id, material_info, electroplating_process_id
                ):
                    material_family = infer_material_family(material_id, material_info)
                    process = get_electroplating_process(electroplating_process_id)
                    return ResponseWrapper.validation_error(
                        field="material_id",
                        message=(
                            f"Material {material_id} with electroplating_family={material_family} "
                            f"is not applicable for process {process.get('id') if process else electroplating_process_id}"
                        ),
                        value=material_id,
                    )
            elif not is_material_allowed_for_electroplating(material_id, material_info):
                return ResponseWrapper.validation_error(
                    field="material_id",
                    message=f"Material {material_id} is not applicable for service {service_id}",
                    value=material_id,
                )
        except ValueError as exc:
            return ResponseWrapper.validation_error(
                field="material_id",
                message=str(exc),
                value=material_id,
            )

    elif service_id and service_id not in material_info.get("applicable_processes", []):
        return ResponseWrapper.validation_error(
            field="material_id",
            message=f"Material {material_id} is not applicable for service {service_id}",
            value=material_id,
        )

    forms = _material_form_response_items(material_info, service_id=service_id)
    data = {
        "material_id": material_id,
        "service_id": service_id,
        "electroplating_process_id": electroplating_process_id if service_id == ELECTROPLATING_SERVICE_ID else None,
        "material_forms": forms,
    }
    return ResponseWrapper.success_response(data, "Material forms retrieved successfully")


@app.get("/services", tags=["Configuration"])
async def list_services():
    """List all available manufacturing services"""
    data = {
        "services": [v['service'] for k, v in AUTO_SERVICES.items()] + \
            [v['service'] for k, v in OTHER_SERVICES.items()] + \
            [v['service'] for k, v in NON_AUTO_SERVICES.items()]
    }
    return ResponseWrapper.success_response(data, "Services retrieved successfully")


@app.get("/auto_services", tags=["Configuration"])
async def list_services():
    """
    List available manufacturing services
    with auto price calculation
    """
    data = {
        "auto_services": [{"id": k, **v} for k, v in AUTO_SERVICES.items()],
    }
    return ResponseWrapper.success_response(data, "Services retrieved successfully")


@app.get("/other_services", tags=["Configuration"])
async def list_locations():
    """
    List available other manufacturing services 
    for other_services page
    without auto price calculations.
    """
    data = {
        "other_services": [{"id": k, **v} for k, v in OTHER_SERVICES.items()]
    }
    return ResponseWrapper.success_response(data, "Other services retrieved successfully")


@app.get("/all_services", tags=["Configuration"])
async def list_all_services():
    """
    Return all available services 
    from AUTO_SERVICES, NON_AUTO_SERVICES and OTHER_SERVICES
    """
    services = []

    # Add auto services
    services.extend([{"id": v["service"], "label": v["label"]} for v in AUTO_SERVICES.values()])

    # Add other services
    services.extend([{"id": v["service"], "label": v["label"]} for v in OTHER_SERVICES.values()])

    # Add non_auto services
    services.extend([{"id": v["service"], "label": v["label"]} for v in NON_AUTO_SERVICES.values()])

    data = {
        "all_services": services
    }
    return ResponseWrapper.success_response(data, "All services retrieved successfully")


@app.get("/coefficients", tags=["Configuration"])
async def list_coefficients():
    """List available coefficients and options"""
    data = {
        "tolerance": [{"id": k, **v} for k, v in TOLERANCE.items()],
        "finish": [{"id": k, **v} for k, v in FINISH.items()],
        "cover": [{"id": k, **v} for k, v in COVER.items()],
        "control_types": [{"id": k, **v} for k, v in CONTROL_TYPES.items()],
        "cert_costs": [{"id": k, **v} for k, v in CERT_COSTS.items()],
        "electroplating_processes": [{"id": k, **v} for k, v in get_process_params().items()],
        "electroplating_baths": [{"id": k, **v} for k, v in get_baths().items()]
    }
    return ResponseWrapper.success_response(data, "Coefficients retrieved successfully")


@app.get("/locations", tags=["Configuration"])
async def list_locations():
    """List available manufacturing locations"""
    data = {
        "locations": [{"id": k, **v} for k, v in LOCATIONS.items()]
    }
    return ResponseWrapper.success_response(data, "Locations retrieved successfully")


@app.get("/operations_available", tags=["Configuration"])
async def list_operations_available(service_id: str):
    """List available operations for different services to view on pages."""
    if service_id in (NON_AUTO_ELECTROPLATING_SERVICE, ELECTROPLATING_SERVICE_ID):
        operations = get_process_params().values()
        data = {
            "values": [
                {
                    "id": op["id"],
                    "group": op.get("group"),
                    "path": op.get("path") or [],
                    "label": " / ".join(
                        part for part in [str(op.get("group") or ""), *[str(x) for x in (op.get("path") or [])]] if part
                    ),
                    "max_part_size_mm": {
                        "length": op["max_part_size_mm"][0],
                        "width": op["max_part_size_mm"][1],
                        "height": op["max_part_size_mm"][2],
                    },
                    "max_part_size_label": "×".join(map(str, op["max_part_size_mm"])),
                    "max_weight_kg": op["max_weight_kg"],
                    "material_families": op.get("material_families", []),
                    "profile_key": op.get("profile_key"),
                }
                for op in operations
            ]
        }
        return ResponseWrapper.success_response(data, "Operations retrieved successfully")

    for service_data in NON_AUTO_SERVICES.values():
        if service_data.get("service") == service_id:
            operations = service_data.get("operations") or []
            data = {
                "values": [
                    {
                        "id": op["id"],
                        "group": op["group"],
                        "path": op["path"],
                        "label": " / ".join([op["group"], *op["path"]]),
                        "max_part_size_mm": {
                            "length": op["max_part_size_mm"][0],
                            "width": op["max_part_size_mm"][1],
                            "height": op["max_part_size_mm"][2],
                        },
                        "max_part_size_label": "×".join(map(str, op["max_part_size_mm"])),
                        "max_weight_kg": op["max_weight_kg"],
                    }
                    for op in operations
                ]
            }
            return ResponseWrapper.success_response(data, "Operations retrieved successfully")

    return ResponseWrapper.success_response({"values": []}, "Operations retrieved successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)
