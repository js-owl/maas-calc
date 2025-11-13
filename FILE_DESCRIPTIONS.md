# Project File Descriptions

This document provides concise descriptions of all files in the Manufacturing Calculation API v3.3.0 project, organized by module and functional purpose.

## Root Files

### Core Application Files
- **`main.py`** - FastAPI application entry point with unified `/calculate-price` endpoint, middleware setup, and configuration endpoints
- **`constants.py`** - Central configuration file containing materials, machines, locations, coefficients, error messages, and cost structures
- **`requirements.txt`** - Python dependencies for production deployment
- **`requirements2.txt`** - Extended dependencies including ML libraries (XGBoost, pandas, scikit-learn)

### Development & Deployment
- **`recreate_venv.py`** - Virtual environment recreation script with dependency management
- **`free_port.py`** - Utility to find available ports for development
- **`howto.txt`** - Quick start instructions

### Docker Configuration
- **`Dockerfile`** - Production Docker image configuration
- **`Dockerfile.dev`** - Development Docker image with hot reload
- **`docker-compose.yml`** - Basic Docker Compose configuration
- **`docker-compose.dev.yml`** - Development environment with volume mounts
- **`docker-compose.prod.yml`** - Production environment with Caddy reverse proxy
- **`Caddyfile`** - Caddy web server configuration for reverse proxy
- **`.dockerignore`** - Files to exclude from Docker builds
- **`DOCKER.md`** - Comprehensive Docker deployment documentation

### Project Management
- **`README.md`** - Main project documentation with API usage examples
- **`test_results.md`** - Test execution results and performance metrics
- **`.gitignore`** - Git ignore patterns

## Models Module (`models/`)

### Data Models
- **`base_models.py`** - Base Pydantic models including `Dimensions`, `MaterialForm`, and `BaseModel`
- **`request_models.py`** - `UnifiedCalculationRequest` model for the main API endpoint
- **`response_models.py`** - `UnifiedCalculationResponse` model for API responses
- **`calculation_models.py`** - Internal calculation request models for each service type
- **`error_models.py`** - Error response models and validation schemas

## Calculators Module (`calculators/`)

### Base Calculator
- **`base_calculator.py`** - Abstract base class for all manufacturing calculators with common functionality

### Service-Specific Calculators
- **`printing_calculator.py`** - 3D printing price calculator using rule-based calculations
- **`cnc_milling_calculator.py`** - CNC milling price calculator with machine selection
- **`cnc_lathe_calculator.py`** - CNC lathe price calculator for cylindrical parts
- **`painting_calculator.py`** - Painting price calculator with surface area calculations

### ML Calculator
- **`ml_calculator.py`** - ML-based calculators for all services using XGBoost predictions

## Extractors Module (`extractors/`)

### File Analysis
- **`file_extractor.py`** - Base class for file parameter extraction with temporary file handling, base64 decoding, and cleanup utilities

### STL File Processing (`stl_extractor.py`)
- **Library**: Uses `trimesh` for comprehensive mesh analysis
- **Core Features**:
  - **Geometric Analysis**: Volume calculation, surface area, bounding box extraction
  - **Mesh Quality**: Watertight checking, winding consistency validation
  - **Surface Features**: Face count, vertex count, edge count, surface entropy calculation
  - **ML Features**: OBB dimensions, aspect ratios, size metrics, lathe suitability
- **Mathematical Formulas**:
  - Surface entropy: `log(face_count * surface_area)`
  - Aspect ratios: `obb_x/obb_y`, `obb_y/obb_z`, `obb_x/obb_z`
  - Size metrics: min, median, max of OBB dimensions
- **Error Handling**: Graceful fallback with default values on analysis failure
- **Performance**: Optimized for large STL files with memory-efficient processing

### STP File Processing (`stp_extractor.py`)
- **Library**: Uses `CADQuery` with `OpenCASCADE` backend for advanced CAD analysis
- **Core Features**:
  - **CAD Analysis**: Native STEP file support with full geometric fidelity
  - **Volume/Surface**: Precise volume and surface area calculations from CAD geometry
  - **Bounding Box**: Accurate bounding box extraction from CAD bounding box
  - **Surface Analysis**: Face, edge, vertex counting from CAD topology
  - **Fallback System**: Basic analysis when CADQuery fails
- **Technical Details**:
  - Uses `OCP.Bnd` and `OCP.BRepBndLib` for geometric operations
  - Imports via `cq.importers.importStep()` for STEP file loading
  - Surface entropy calculation: `log(face_count * surface_area)`
- **Error Handling**: Multi-level fallback from CADQuery → basic analysis → default values
- **Performance**: Handles complex CAD assemblies and parametric models

## Utils Module (`utils/`)

### Core Utilities
- **`parameter_extractor.py`** - Main coordinator for file parameter extraction
- **`calculation_router.py`** - Routes calculations to appropriate calculators (ML vs rule-based)
- **`safeguards.py`** - Parameter validation and default value application
- **`helpers.py`** - Helper functions for material, location, and coefficient lookups

### ML Integration
- **`ml_predictor.py`** - XGBoost model loader and feature preprocessing for ML predictions

### System Utilities
- **`logging_utils.py`** - Structured logging configuration and utilities
- **`response_utils.py`** - Response wrapper and metadata utilities
- **`validation_utils.py`** - Request validation and error handling
- **`middleware.py`** - FastAPI middleware for request tracking
- **`versioning.py`** - API versioning and metadata utilities

## Calculations Module (`calculations/`)

### Core Functions
- **`core.py`** - Fundamental calculation functions (volume, weight, price, work time, coefficients)
- **`printing.py`** - 3D printing specific calculations
- **`cnc.py`** - CNC milling and lathe calculations
- **`painting.py`** - Painting process calculations

## Tests Module (`tests/`)

### Test Suites
- **`conftest.py`** - Pytest configuration and fixtures
- **`test_calc_endpoints.py`** - Main calculation endpoint tests
- **`test_ml_calculations.py`** - ML model integration tests
- **`test_support_endpoints.py`** - Configuration endpoint tests
- **`test_invalid_cases.py`** - Error handling and validation tests
- **`test_stp_endpoints.py`** - STP file processing tests
- **`test_comprehensive_scenarios.py`** - End-to-end integration tests

## Examples Module (`examples/`)

### Usage Examples
- **`api_test_examples.py`** - API usage examples with real file uploads
- **`run_tests.py`** - Test execution script for different scenarios
- **`curl_examples.sh`** - Bash curl examples for API testing
- **`curl_examples.ps1`** - PowerShell curl examples for Windows
- **`README.md`** - Examples documentation

## Scripts Module (`scripts/`)

### Utility Scripts
- **`start_server.py`** - Development server startup script
- **`test_file_upload.py`** - File upload testing utility
- **`test_unified_endpoint.py`** - Unified endpoint testing script
- **`run_all_tests.py`** - Complete test suite execution

## ML Models (`ml_models/`)

### Machine Learning Assets
- **`base_model_xgb_v0.01.json`** - Trained XGBoost model for work time prediction
- **`ohe_v0.01.joblib`** - One-hot encoder for categorical feature preprocessing

## Archive (`_archive/`)

### Legacy Code
- Contains deprecated or legacy code files for reference

## Test Files (`test_files/`)

### Test Assets
- Contains sample STL/STP files and test data for development and testing

## File Extraction Pipeline

### Base64 File Processing
1. **Upload**: Client sends base64-encoded file data via API
2. **Decoding**: `file_extractor._save_temp_file()` decodes base64 to binary
3. **Temporary Storage**: Creates temporary file with `stl311_` prefix
4. **Analysis**: Passes file path to appropriate extractor
5. **Cleanup**: `_cleanup_temp_file()` removes temporary file after analysis

### STL Processing Pipeline
1. **File Loading**: `trimesh.load()` loads STL mesh
2. **Basic Geometry**: Extract bounds, volume, surface area
3. **OBB Calculation**: Calculate oriented bounding box dimensions
4. **Derived Features**: Compute aspect ratios, size metrics
5. **Surface Analysis**: Extract face/vertex/edge counts
6. **Quality Checks**: Validate watertight and winding consistency
7. **ML Features**: Prepare features for ML model prediction
8. **Error Handling**: Fallback to default values on failure

### STP Processing Pipeline
1. **CAD Loading**: `cadquery.importers.importStep()` loads STEP file
2. **Geometric Analysis**: Extract bounding box from CAD geometry
3. **Volume/Surface**: Calculate precise volume and surface area
4. **Topology Analysis**: Count faces, edges, vertices from CAD topology
5. **Feature Extraction**: Compute aspect ratios and size metrics
6. **Fallback Handling**: Basic analysis if CADQuery fails
7. **Error Recovery**: Default values if all analysis fails

### ML Feature Preparation
Both STL and STP extractors prepare features for ML prediction:
- **Geometric**: Volume, surface area, OBB dimensions
- **Aspect Ratios**: XY, YZ, XZ ratios for shape analysis
- **Size Metrics**: Min, median, max dimensions
- **Complexity**: Face count, vertex count, surface entropy
- **Manufacturing**: Lathe suitability check

## Key Functional Purposes

### Request Processing Flow
1. **Entry Point**: `main.py` receives requests via FastAPI
2. **File Analysis**: `extractors/` modules analyze uploaded CAD files
3. **Parameter Extraction**: `utils/parameter_extractor.py` coordinates extraction
4. **Validation**: `utils/safeguards.py` applies parameter validation
5. **Routing**: `utils/calculation_router.py` determines ML vs rule-based calculation
6. **Calculation**: `calculators/` modules perform price calculations
7. **Response**: `models/response_models.py` structures the response

### ML Integration
- **Feature Extraction**: `extractors/` extract geometric features from CAD files
- **ML Prediction**: `utils/ml_predictor.py` uses XGBoost for work time prediction
- **Fallback**: Automatic fallback to rule-based calculations when ML fails

### Configuration Management
- **Constants**: `constants.py` centralizes all configuration data
- **Materials**: Material properties, prices, and process compatibility
- **Machines**: Available manufacturing equipment and capabilities
- **Locations**: Cost structures and pricing by location

### Testing & Quality
- **Comprehensive Tests**: Full test coverage for all endpoints and scenarios
- **ML Testing**: Specific tests for ML model integration
- **Error Handling**: Validation of error cases and edge conditions
- **Performance**: Response time and accuracy testing

This modular architecture enables easy maintenance, testing, and extension of the manufacturing calculation system while providing both traditional rule-based and modern ML-based pricing capabilities.
