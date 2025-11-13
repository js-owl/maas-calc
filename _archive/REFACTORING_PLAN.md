# Manufacturing API Refactoring Plan & Implementation

## Overview
This document outlines the comprehensive refactoring of the manufacturing calculation API, transitioning from multiple separate endpoints to a unified, JSON-based system with file upload capabilities and external service integration.

## 🎯 Goals Achieved

### ✅ **Unified API Endpoint**
- **Single Endpoint**: `/calculate-price` replaces all individual calculation endpoints
- **JSON-Based**: Eliminated form-based requests for cleaner API design
- **File Upload Support**: Base64-encoded file uploads for STL/STP analysis
- **File ID Tracking**: Integration with external service database tracking

### ✅ **Modular Architecture**
- **Clean Codebase**: Removed all commented-out legacy code
- **Reusable Scripts**: Created `/scripts` folder with test utilities
- **Helper Functions**: Organized parameter extraction and safeguard functions
- **Unified Models**: Consistent request/response models across all services

### ✅ **Service Integration**
- **Correct Service IDs**: Updated to match constants.py naming convention
- **Parameter Extraction**: Automatic dimension extraction from CAD files
- **Safeguard System**: Intelligent defaults for missing parameters
- **Comprehensive Logging**: File ID tracking throughout the process

## 📋 Service Mapping

| Service ID | Description | Materials | Forms |
|------------|-------------|-----------|-------|
| `printing` | 3D Printing | PA11, PA12 | powder |
| `cnc-milling` | CNC Milling | alum_D16, alum_AMC, steel_* | sheet, rod, hexagon |
| `cnc-lathe` | CNC Lathe | alum_D16, alum_AMC, steel_* | rod, hexagon |
| `painting` | Painting | All materials | All forms |

## 🔧 API Specification

### **Unified Endpoint: `/calculate-price`**

#### **Request Model**
```json
{
  "service_id": "printing",                    // Required: Service type
  "file_id": "abc123-def456",                 // Optional: External service tracking ID
  "file_data": "base64_encoded_content...",   // Optional: Base64 file data
  "file_name": "part.stl",                    // Optional: Original filename
  "file_type": "stl",                         // Optional: File type (stl/stp)
  
  // Override Parameters (optional - will be extracted from file if not provided)
  "dimensions": {
    "length": 100.0,
    "width": 50.0,
    "thickness": 10.0
  },
  "material_id": "PA11",
  "material_form": "powder",
  "quantity": 5,
  "id_cover": ["1"],
  "k_cert": ["a", "f"],
  
  // Service-specific parameters
  "n_dimensions": 1,                          // 3D Printing
  "k_type": 1.0,
  "k_process": 1.0,
  "k_otk": 1.0,
  "location": "location_1"
}
```

#### **Response Model**
```json
{
  "file_id": "abc123-def456",
  "filename": "part.stl",
  "service_id": "printing",
  "calculation_method": "3D Printing Price Calculation",
  
  // Core Results
  "detail_price": 1551.0,
  "detail_price_one": 1551.0,
  "total_price": 7754.0,
  "total_time": 2.5,
  
  // Material Information
  "mat_volume": 0.00005,
  "mat_weight": 0.051,
  "mat_price": 700.0,
  
  // Work Information
  "work_price": 2186.4,
  "work_time": 2.5,
  
  // Coefficients
  "k_quantity": 1.0,
  "k_complexity": 1.0,
  "k_cover": 1.05,
  "k_tolerance": 1.0,
  "k_finish": 1.0,
  
  // Manufacturing Details
  "manufacturing_cycle": 8.0,
  "suitable_machines": ["machine_301", "machine_302"],
  
  // Service-specific fields
  "n_dimensions": 1,
  "k_type": 1.0,
  "k_process": 1.0,
  
  // Extracted Parameters
  "extracted_dimensions": {
    "length": 100.0,
    "width": 50.0,
    "thickness": 10.0
  },
  "used_parameters": {...},
  
  // Metadata
  "timestamp": "2025-10-13T18:33:02.018289",
  "message": "Calculation completed successfully"
}
```

## 🏗️ Architecture Changes

### **Before Refactoring**
```
Multiple Endpoints:
├── /3dprinting
├── /cnc-milling  
├── /cnc-lathe
├── /painting
└── /analyze_base_stl_file/
```

### **After Refactoring**
```
Unified System:
├── /calculate-price (unified endpoint)
├── /coefficients (configuration)
├── /materials (configuration)
├── /services (configuration)
└── /analyze_base_stl_file/ (analysis only)
```

## 🔄 Data Flow

### **1. Request Processing**
```
Client Request → JSON Validation → File ID Logging → Parameter Extraction
```

### **2. File Processing** (if file provided)
```
Base64 Decode → Temporary File → STL/STP Analysis → Dimension Extraction → Cleanup
```

### **3. Parameter Resolution**
```
Extracted Parameters + Request Parameters + Safeguards → Final Parameters
```

### **4. Calculation Routing**
```
Service ID → Route to Calculation Function → Unified Response
```

## 🛡️ Safeguard System

### **Default Values by Service**
- **Printing**: PA11 powder, n_dimensions=1, k_type=1.0
- **CNC**: alum_D16 sheet, location_1
- **All Services**: quantity=1, id_cover=["1"], k_otk=1.0

### **Dimension Safeguards**
- **Default**: 100x50x10 mm if not provided or extracted
- **Extraction Priority**: File analysis > Manual input > Defaults

## 📁 File Structure

```
stl/
├── main.py                    # Main application (cleaned)
├── constants.py               # Service definitions and materials
├── scripts/                   # Reusable test scripts
│   ├── test_unified_endpoint.py
│   ├── test_file_upload.py
│   ├── start_server.py
│   └── run_all_tests.py
├── tests/                     # Unit tests
├── models/                    # ML models
└── REFACTORING_PLAN.md        # This documentation
```

## 🧪 Testing Infrastructure

### **Test Scripts**
- **`test_unified_endpoint.py`**: JSON-only API testing
- **`test_file_upload.py`**: Base64 file upload testing
- **`start_server.py`**: Server startup utility
- **`run_all_tests.py`**: Master test runner

### **Test Coverage**
- ✅ JSON-only requests (all services)
- ✅ Base64 file uploads (STL/STP)
- ✅ Parameter safeguards
- ✅ File ID tracking
- ✅ Error handling

## 🚀 Usage Examples

### **1. Simple JSON Request**
```bash
curl -X POST "http://localhost:7000/calculate-price" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "printing",
    "file_id": "order-123",
    "quantity": 5,
    "dimensions": {"length": 100, "width": 50, "thickness": 10},
    "material_id": "PA11"
  }'
```

### **2. File Upload Request**
```bash
curl -X POST "http://localhost:7000/calculate-price" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "cnc-milling",
    "file_id": "part-456",
    "file_data": "base64_encoded_stl_content...",
    "file_name": "bracket.stl",
    "file_type": "stl",
    "quantity": 10,
    "material_id": "alum_D16"
  }'
```

### **3. Minimal Request (Safeguards)**
```bash
curl -X POST "http://localhost:7000/calculate-price" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "printing",
    "file_id": "quick-quote-789"
  }'
```

## 📊 Performance & Logging

### **Logging Features**
- **File ID Tracking**: Every request logged with file_id
- **Parameter Extraction**: File analysis progress logged
- **Safeguard Warnings**: Default value usage logged
- **Calculation Flow**: Service routing and completion logged

### **Performance Optimizations**
- **Temporary File Cleanup**: Automatic cleanup after processing
- **Base64 Efficiency**: Direct memory processing for small files
- **Parameter Caching**: Extracted parameters reused when possible

## 🔧 Configuration

### **Service Configuration**
- **Materials**: Defined in `constants.py` with `applicable_processes`
- **Locations**: `location_1`, `location_2`, `location_3`
- **Machines**: Mapped by location and type
- **Coefficients**: Tolerance, finish, cover processing

### **Environment Setup**
```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 7000

# Run tests
python scripts/run_all_tests.py
```

## 📈 Future Enhancements

### **Planned Improvements**
1. **API Documentation**: OpenAPI/Swagger documentation
2. **Rate Limiting**: Request throttling and quotas
3. **Caching**: Redis-based response caching
4. **Monitoring**: Metrics and health checks
5. **Authentication**: API key management

### **Integration Points**
1. **External Service**: File ID tracking integration
2. **Database**: Calculation history storage
3. **Queue System**: Async processing for large files
4. **Notifications**: Webhook support for completion

## ✅ Migration Checklist

- [x] Remove commented-out code
- [x] Create unified endpoint
- [x] Implement base64 file upload
- [x] Add file ID tracking
- [x] Create safeguard system
- [x] Update service IDs to match constants
- [x] Create test scripts
- [x] Test all functionality
- [x] Document API specification
- [x] Create refactoring documentation

## 🎉 Success Metrics

- **API Consistency**: Single endpoint for all calculations
- **File Integration**: Seamless STL/STP processing
- **External Tracking**: Complete file ID logging
- **Code Quality**: Clean, maintainable codebase
- **Test Coverage**: Comprehensive testing suite
- **Documentation**: Complete API specification

---

**Status**: ✅ **COMPLETED**  
**Date**: October 13, 2025  
**Version**: 2.3.0  
**Next Review**: TBD
