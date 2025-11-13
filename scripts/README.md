# Interactive File Upload Test Scripts

This directory contains interactive testing scripts for the Manufacturing Calculation API, allowing users to upload STL/STP files and test the `/calculate-price` endpoint with various parameters.

## Scripts Overview

### 1. `interactive_file_test.py`
The main interactive script that provides a user-friendly interface for:
- Browsing and selecting STL/STP files from the `test_files/` directory
- Choosing manufacturing service types (3D Printing, CNC Milling, CNC Lathe, Painting)
- Configuring calculation parameters (Quick Test or Custom mode)
- Uploading files to the API and viewing detailed results

### 2. `run_file_test.py`
A launcher script that:
- Checks system requirements and API connectivity
- Validates test files availability
- Launches the interactive test with proper error handling

## Prerequisites

1. **API Server Running**: The Manufacturing Calculation API must be running on `http://localhost:7000`
2. **Test Files**: Place STL/STP files in the `test_files/` directory
3. **Python Dependencies**: Install required packages:
   ```bash
   pip install requests
   ```

## Quick Start

### Option 1: Using the Launcher (Recommended)
```bash
# From project root directory
python scripts/run_file_test.py
```

### Option 2: Direct Execution
```bash
# From project root directory
python scripts/interactive_file_test.py
```

## Usage Guide

### 1. File Selection
- The script scans the `test_files/` directory for STL/STP files
- Displays file names, sizes, and types
- Select files by number or choose 0 to exit

### 2. Service Selection
Choose from available manufacturing services:
- **3D Printing**: For additive manufacturing calculations
- **CNC Milling**: For subtractive manufacturing with milling
- **CNC Lathe**: For cylindrical part manufacturing
- **Painting**: For surface treatment calculations

### 3. Parameter Configuration

#### Quick Test Mode
- Uses default parameters for rapid testing
- Minimal user input required
- Good for basic functionality testing

#### Custom Parameters Mode
- Full control over all calculation parameters
- Interactive selection of:
  - Materials and forms
  - Quantities and dimensions
  - Cover processing options
  - Service-specific parameters
  - Quality control coefficients

### 4. File Upload and Results
- Preview request before sending
- Upload file with base64 encoding
- View detailed calculation results including:
  - Total and detail prices
  - Work time and manufacturing cycle
  - Calculation method (ML vs rule-based)
  - Material and work cost breakdown
  - Applied coefficients
  - Suitable manufacturing machines

### 5. Result Management
- Option to save results to JSON files
- Results saved in `test_results/` directory
- Timestamped filenames for easy tracking

## Example Session

```
=== Manufacturing Calculation File Upload Test ===

Available Files:
  [1] 02.stl (0.12 MB, STL)
  [2] S8000_125_63_293_001_D000_02.stp (0.23 MB, STP)
  [0] Exit

Select file: 1

Selected: 02.stl (STL file, 0.12 MB)

Service Types:
  [1] 3D Printing
  [2] CNC Milling
  [3] CNC Lathe
  [4] Painting

Select service: 1

Parameter Modes:
  [1] Quick Test (default parameters)
  [2] Custom Parameters

Select mode: 1

🚀 Quick Test Mode - Using default parameters for 3D Printing

Default Parameters:
  material_id: PA11
  material_form: powder
  quantity: 1
  n_dimensions: 1
  k_type: 1.0
  k_process: 1.0
  cover_id: ['1']
  k_otk: 1.0
  k_cert: ['a', 'f']

📋 Request Preview:
  Service: 3D Printing
  File: 02.stl (0.12 MB)
  File ID: test-02.stl-printing
  Parameters: 8 configured

Send request? (y/n): y

📤 Uploading file to API...
✅ Upload successful!

📊 Key Results:
  Total Price: $1,551.00
  Detail Price: $1,551.00
  Work Time: 2.50 hours
  Manufacturing Cycle: 10.0 days

🔧 Calculation Method:
  Engine: ml_model
  Method: 3D Printing ML Prediction
  ML Prediction: 2.50 hours
  Features Used: 15 geometric features

💰 Cost Breakdown:
  Material Cost: $120.00
  Work Cost: $1,431.00

🏭 Manufacturing:
  Suitable Machines: 3D Printer Default

📈 Applied Coefficients:
  k_quantity: 1.000
  k_complexity: 0.750
  k_cover: 1.050
  k_tolerance: 1.000
  k_finish: 1.000

Show full response? (y/n): n

Save results to file? (y/n): y
✅ Results saved to: test_results/result_02.stl_printing_20241215_143022.json

Test another file? (y/n): n

👋 Thank you for using the Manufacturing Calculation File Upload Test!
```

## Features

### File Support
- **STL Files**: Triangular mesh files for 3D printing
- **STP/STEP Files**: Parametric CAD files with full geometric fidelity
- **Automatic Detection**: File type detection and appropriate processing

### Service-Specific Parameters

#### 3D Printing
- Material selection (PA11, PA12, etc.)
- Number of dimensions
- Type and process coefficients
- Quality control parameters

#### CNC Milling/Lathe
- Material and form selection
- Tolerance and finish specifications
- CNC complexity levels
- Setup time configuration

#### Painting
- Paint type selection (acrylic, epoxy, polyurethane)
- Process coefficients (preparation, primer, lakery)
- Control type specifications

### Advanced Features
- **ML Integration**: Automatic ML model usage when features are available
- **Fallback Handling**: Graceful fallback to rule-based calculations
- **Error Recovery**: Clear error messages and retry options
- **Batch Testing**: Test multiple files in sequence
- **Result Persistence**: Save results for later analysis

## Troubleshooting

### Common Issues

1. **API Not Running**
   ```
   ❌ API not running or not accessible at http://localhost:7000
   ```
   **Solution**: Start the API server with `python main.py` or `uvicorn main:app --reload`

2. **No Test Files Found**
   ```
   ❌ No STL/STP files found in test_files directory
   ```
   **Solution**: Add STL/STP files to the `test_files/` directory

3. **Import Errors**
   ```
   ❌ Error importing interactive test
   ```
   **Solution**: Run from the project root directory, not from the scripts directory

4. **File Upload Errors**
   ```
   ❌ Upload failed with status 422
   ```
   **Solution**: Check parameter validation - some combinations may not be valid

### Debug Mode
For detailed error information, check the API server logs when running the interactive test.

## Integration with API

The script integrates with the Manufacturing Calculation API v3.3.0:
- Uses the unified `/calculate-price` endpoint
- Supports all service types and parameters
- Handles both ML and rule-based calculations
- Provides comprehensive result display

## Contributing

To extend the interactive test script:
1. Add new parameter validation in the `_configure_*_params` methods
2. Extend the `DEFAULT_PARAMS` for new services
3. Add new result display options in `display_results`
4. Enhance error handling in `upload_file`

## License

This script is part of the Manufacturing Calculation API project and follows the same license terms.

