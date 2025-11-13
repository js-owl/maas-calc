# API Testing Examples

This directory contains comprehensive testing examples for the Manufacturing Calculations API.

## Files

- **`api_test_examples.py`** - Main test suite with comprehensive examples
- **`run_tests.py`** - Test runner script for running specific test categories
- **`README.md`** - This documentation file

## Quick Start

### Prerequisites

1. **Start the API server**:
   ```bash
   # From the project root directory
   # First activate the virtual environment
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/macOS
   
   # Then start the server using uvicorn
   uvicorn main:app --reload --host 0.0.0.0 --port 7000
   ```

2. **Install required dependencies**:
   ```bash
   pip install requests
   ```

### Running Tests

#### Run All Tests
```bash
python api_test_examples.py
```

#### Run Specific Test Categories
```bash
# Basic API endpoints (health, services, materials, coefficients)
python run_tests.py --category basic

# Test different materials
python run_tests.py --category materials

# Test tolerance and finish combinations
python run_tests.py --category tolerance

# Test cover processing types
python run_tests.py --category cover

# Test paint types and processes
python run_tests.py --category paint

# Test file upload functionality
python run_tests.py --category file

# Test health endpoint only
python run_tests.py --category health
```

#### Run with Custom API URL
```bash
python run_tests.py --category all --url http://your-api-server:7000
```

## Test Categories

### 1. Basic API Tests
- **Health Check** - Verify API is running
- **Services List** - Get available manufacturing services
- **Materials List** - Get available materials and their properties
- **Coefficients List** - Get tolerance, finish, and cover options

### 2. Manufacturing Calculation Tests
- **3D Printing** - Test with PA11 and PA12 materials
- **CNC Milling** - Test with aluminum materials and various tolerances
- **CNC Lathe** - Test with rod materials and different finishes
- **Painting** - Test with different paint types and processes

### 3. Edge Case Tests
- **Minimal Parameters** - Test with only required fields
- **Large Quantities** - Test with high quantity values
- **Multiple Cover Types** - Test with multiple cover processing options
- **High Complexity CNC** - Test with complex machining parameters

### 4. Error Case Tests
- **Invalid Service** - Test with non-existent service ID
- **Invalid Material** - Test with non-existent material ID
- **Invalid Dimensions** - Test with negative or zero dimensions
- **Missing Required Fields** - Test with incomplete requests

### 5. Comprehensive Material Tests
- **PA11 vs PA12** - Compare different plastic materials
- **Aluminum Variants** - Test alum_D16 vs alum_AMC
- **Material Forms** - Test different material forms (powder, sheet, rod)

### 6. Tolerance and Finish Tests
- **IT7 + 12.5** - High precision, rough finish
- **IT9 + 3.2** - Medium precision, medium finish
- **IT11 + 0.8** - Low precision, fine finish

### 7. Cover Processing Tests
- **Покраска only** - Painting only
- **Гальваника only** - Galvanizing only
- **Both processes** - Painting + Galvanizing
- **No cover** - No surface treatment

### 8. Paint Type Tests
- **Acrylic** - Basic paint process
- **Epoxy** - Enhanced paint process
- **Polyurethane** - Premium paint process

## Real Constants Used

All test examples use real values from `constants.py`:

### Materials
- **PA11** - Порошок PA11 (plastic powder)
- **PA12** - Порошок PA12 (plastic powder)
- **alum_D16** - Алюминий Д16 (aluminum D16)
- **alum_AMC** - Алюминий АМц (aluminum AMC)

### Tolerances
- **1** - IT7 (highest precision)
- **2** - IT8
- **3** - IT9
- **4** - IT10
- **5** - IT11 (lowest precision)

### Finishes
- **1** - 12.5 (roughest)
- **2** - 6.3
- **3** - 3.2
- **4** - 1.6
- **5** - 0.8 (smoothest)

### Cover Processing
- **1** - Покраска (Painting)
- **2** - Гальваника (Galvanizing)

### Paint Types
- **acrylic** - Basic paint
- **epoxy** - Enhanced paint
- **polyurethane** - Premium paint

## Example Output

```
🚀 Starting Manufacturing Calculations API Test Suite
Testing against: http://localhost:7000

============================================================
TEST: Health Check
============================================================
Status Code: 200
Response: {
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z"
}

============================================================
TEST: Valid Printing Calculation
============================================================
Endpoint: http://localhost:7000/calculate-price
Request Data: {
  "service_id": "printing",
  "file_id": "test-printing-001",
  "dimensions": {
    "length": 100.0,
    "width": 50.0,
    "thickness": 10.0
  },
  "quantity": 5,
  "material_id": "PA11",
  "material_form": "powder"
}
Status Code: 200
✅ SUCCESS
Response: {
  "file_id": "test-printing-001",
  "service_id": "printing",
  "calculation_method": "3D Printing Price Calculation",
  "detail_price": 1250.0,
  "total_price": 6250.0,
  "total_time": 2.5,
  "timestamp": "2024-01-15T10:30:01.000Z"
}
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure the API server is running on the correct port
   - Check if the URL is correct (default: http://localhost:7000)

2. **Import Errors**
   - Ensure you're running from the examples directory
   - Install required dependencies: `pip install requests`

3. **Test Failures**
   - Check API server logs for detailed error information
   - Verify all required services are running
   - Ensure database connections are working (if applicable)

### Debug Mode

To run tests with more verbose output, modify the test functions to include additional logging or use Python's logging module.

## Contributing

When adding new test cases:

1. Use real values from `constants.py`
2. Include descriptive test names and comments
3. Test both success and failure scenarios
4. Update this README with new test categories
5. Ensure tests are independent and can run in any order
