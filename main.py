"""
Manufacturing Calculation API v3.0.0
Modular architecture with unified API
"""

import logging
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
    FINISH, CONTROL_TYPES, CERT_COSTS, AUTO_SERVICES,
    OTHER_SERVICES, APP_VERSION
)

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
    - CNC Milling (cnc-milling) 
    - CNC Lathe (cnc-lathe)
    - Painting (painting)
    
    Supports file upload via base64 encoding and automatic parameter extraction.
    """
    from utils.logging_utils import log_calculation_start, log_calculation_complete, log_error
    import time
    
    # Validate request before processing
    request_data = request.model_dump(exclude_unset=True, exclude_none=True)
    validation_errors = validate_calculation_request(request_data)
    
    if validation_errors:
        return create_validation_error_response(
            validation_errors,
            request_id=getattr(request, 'request_id', None)
        )
    
    start_time = time.time()
    log_calculation_start(
        logger=logger,
        service_type=request.service_id,
        file_id=request.file_id or "unknown",
        request_id=getattr(request, 'request_id', None)
    )

    AUTO_SERVICES_LIST = [v["service"] for v in AUTO_SERVICES.values()]

    if (request.service_id=="cnc-milling" and request.file_data is None) or\
        (request.service_id not in AUTO_SERVICES_LIST):
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
        
        # Add ML features to merged parameters
        if ml_features:
            merged_params['ml_features'] = ml_features
            
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
        logger.info('======================================= main.py calculate_price() result:', result.model_dump())
        
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

@app.get("/materials", tags=["Configuration"])
async def list_materials(process: Optional[str] = None):
    """List available materials, optionally filtered by process"""
    materials_list = []
    
    for material_id, material_info in MATERIALS.items():
        if process and process not in material_info.get("applicable_processes", []):
            continue
            
        materials_list.append({
            "id": material_id,
            "label": material_info.get("label", ""),
            "family": material_info.get("family", ""),
            "density": material_info.get("density", 0.0),
            "forms": material_info.get("forms", {}),
            "applicable_processes": material_info.get("applicable_processes", [])
        })
    
    materials_list = sorted(materials_list, key=lambda x: x['label'])
    
    data = {"materials": materials_list}
    message = f"Materials retrieved successfully{f' for process: {process}' if process else ''}"
    return ResponseWrapper.success_response(data, message)


@app.get("/services", tags=["Configuration"])
async def list_services():
    """List all available manufacturing services"""
    data = {
        "services": [v['service'] for k, v in AUTO_SERVICES.items()] + [v['service'] for k, v in OTHER_SERVICES.items()]
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
    without auto price calculations.
    """
    data = {
        "other_services": [{"id": k, **v} for k, v in OTHER_SERVICES.items()]
    }
    return ResponseWrapper.success_response(data, "Other services retrieved successfully")


@app.get("/all_services", tags=["Configuration"])
async def list_all_services():
    """Return all available services from AUTO_SERVICES and OTHER_SERVICES"""
    services = []

    # Add auto services
    services.extend([{"id": v["service"], "label": v["label"]} for v in AUTO_SERVICES.values()])

    # Add other services
    services.extend([{"id": v["service"], "label": v["label"]} for v in OTHER_SERVICES.values()])

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
        "cert_costs": [{"id": k, **v} for k, v in CERT_COSTS.items()]
    }
    return ResponseWrapper.success_response(data, "Coefficients retrieved successfully")


@app.get("/locations", tags=["Configuration"])
async def list_locations():
    """List available manufacturing locations"""
    data = {
        "locations": [{"id": k, **v} for k, v in LOCATIONS.items()]
    }
    return ResponseWrapper.success_response(data, "Locations retrieved successfully")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)
