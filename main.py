"""
Manufacturing Calculation API v3.0.0
Modular architecture with unified API
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import our modular components
from models import UnifiedCalculationRequest, UnifiedCalculationResponse
from utils import ParameterExtractor, SafeguardManager, CalculationRouter
from utils.response_utils import ResponseWrapper, add_response_metadata
from utils.logging_utils import get_logger, set_request_id
from utils.middleware import RequestTrackingMiddleware
from utils.versioning import VersioningMiddleware, get_version_info
from utils.validation_utils import validate_calculation_request, create_validation_error_response
from constants import MATERIALS, LOCATIONS, COVER, TOLERANCE, FINISH, APP_VERSION

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
        
        # Step 5: Add file information and calculation engine info
        if request.file_name:
            result.filename = request.file_name
        if extracted_params.get('extracted_dimensions'):
            result.extracted_dimensions = extracted_params['extracted_dimensions']
        
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
    """List available manufacturing services"""
    data = {
        "services": ["printing", "cnc-milling", "cnc-lathe", "painting"]
    }
    return ResponseWrapper.success_response(data, "Services retrieved successfully")


@app.get("/coefficients", tags=["Configuration"])
async def list_coefficients():
    """List available coefficients and options"""
    data = {
        "tolerance": [{"id": k, **v} for k, v in TOLERANCE.items()],
        "finish": [{"id": k, **v} for k, v in FINISH.items()],
        "cover": [{"id": k, **v} for k, v in COVER.items()]
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
