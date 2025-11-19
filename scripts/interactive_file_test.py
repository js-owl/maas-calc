#!/usr/bin/env python3
"""
Interactive File Upload Test Script for Manufacturing Calculations API

This script allows users to:
1. Browse and select STL/STP files from the test_files directory
2. Choose manufacturing service type
3. Configure calculation parameters
4. Upload file to /calculate-price endpoint
5. View detailed results

Usage:
    python scripts/interactive_file_test.py
"""

import requests
import base64
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add parent directory to path to import constants
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import APP_VERSION, MATERIALS, TOLERANCE, FINISH, COVER, LOCATIONS

# API Configuration
BASE_URL = "http://localhost:7000"
API_ENDPOINT = f"{BASE_URL}/calculate-price"

# Service types mapping
SERVICES = {
    "1": {"id": "printing", "name": "3D Printing"},
    "2": {"id": "cnc-milling", "name": "CNC Milling"},
    "3": {"id": "cnc-lathe", "name": "CNC Lathe"},
    "4": {"id": "painting", "name": "Painting"}
}

# Default parameters for quick test mode
DEFAULT_PARAMS = {
    "printing": {
        "material_id": "PA11",
        "material_form": "powder",
        "quantity": 1,
        "n_dimensions": 1,
        "k_type": 1.0,
        "k_process": 1.0,
        "cover_id": ["1"],
        "k_otk": 1.0,
        "k_cert": ["a", "f"]
    },
    "cnc-milling": {
        "material_id": "alum_D16",
        "material_form": "sheet",
        "quantity": 1,
        "tolerance_id": "1",
        "finish_id": "1",
        "cover_id": ["1"],
        "k_otk": 1.0,
        "cnc_complexity": "medium",
        "cnc_setup_time": 2.0
    },
    "cnc-lathe": {
        "material_id": "alum_D16",
        "material_form": "rod",
        "quantity": 1,
        "tolerance_id": "1",
        "finish_id": "1",
        "cover_id": ["1"],
        "k_otk": 1.0,
        "cnc_complexity": "medium",
        "cnc_setup_time": 2.0
    },
    "painting": {
        "material_id": "alum_D16",
        "material_form": "sheet",
        "quantity": 1,
        "tolerance_id": "1",
        "finish_id": "1",
        "cover_id": ["1"],
        "k_otk": 1.0,
        "paint_type": "epoxy",
        "paint_prepare": "a",
        "paint_primer": "b",
        "paint_lakery": "a",
        "control_type": "1",
        "k_cert": ["a", "f", "g"]
    }
}

class InteractiveFileTester:
    """Interactive file upload tester for Manufacturing Calculations API"""
    
    def __init__(self):
        self.test_files_dir = Path("test_files")
        self.available_files = []
        self.selected_file = None
        self.selected_file_type = None
        self.selected_service = None
        self.parameters = {}
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")
    
    def print_separator(self):
        """Print a separator line"""
        print("-" * 60)
    
    def get_user_input(self, prompt: str, valid_options: List[str] = None) -> str:
        """Get user input with validation"""
        while True:
            try:
                user_input = input(f"\n{prompt}: ").strip()
                user_input = str(user_input)
                if valid_options and user_input not in valid_options:
                    print(f"❌ Invalid option. Please choose from: {', '.join(valid_options)}")
                    continue
                return user_input
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                sys.exit(0)
    
    def list_available_files(self) -> List[Dict[str, Any]]:
        """Scan test_files directory for STL/STP files"""
        files = []
        if not self.test_files_dir.exists():
            print(f"❌ Test files directory not found: {self.test_files_dir}")
            return files
        
        for file_path in self.test_files_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.stl', '.stp', '.step']:
                file_size = file_path.stat().st_size
                # Remove the dot from file extension for API compatibility
                file_type = file_path.suffix.lower()[1:]  # Remove the leading dot
                files.append({
                    'path': file_path,
                    'name': file_path.name,
                    'size': file_size,
                    'type': file_type,
                    'size_mb': round(file_size / (1024 * 1024), 2)
                })
        
        return sorted(files, key=lambda x: x['name'])
    
    def select_file(self) -> Optional[Dict[str, Any]]:
        """Interactive file selection"""
        self.print_header("File Selection")
        
        self.available_files = self.list_available_files()
        
        if not self.available_files:
            print("❌ No STL/STP files found in test_files directory")
            return None
        
        print("Available Files:")
        for i, file_info in enumerate(self.available_files, 1):
            print(f"  [{i}] {file_info['name']} ({file_info['size_mb']} MB, {file_info['type'].upper()})")
        
        print(f"  [0] Exit")
        
        while True:
            try:
                choice = int(self.get_user_input("Select file"))
                if choice == 0:
                    return None
                elif 1 <= choice <= len(self.available_files):
                    selected = self.available_files[choice - 1]
                    print(f"\n✅ Selected: {selected['name']} ({selected['type'].upper()}, {selected['size_mb']} MB)")
                    return selected
                else:
                    print(f"❌ Invalid choice. Please select 0-{len(self.available_files)}")
            except ValueError:
                print("❌ Please enter a valid number")
    
    def select_service(self) -> Optional[str]:
        """Interactive service selection"""
        self.print_header("Service Selection")
        
        print("Service Types:")
        for key, service in SERVICES.items():
            print(f"  [{key}] {service['name']}")
        print(f"  [0] Back to file selection")
        
        choice = self.get_user_input("Select service", [str(i) for i in range(len(SERVICES) + 1)])
        
        if choice == "0":
            return None
        
        service_id = SERVICES[choice]["id"]
        service_name = SERVICES[choice]["name"]
        print(f"\n✅ Selected: {service_name}")
        return service_id
    
    def get_material_options(self, service_id: str) -> List[Dict[str, Any]]:
        """Get available materials for the selected service"""
        materials = []
        for material_id, material_info in MATERIALS.items():
            if service_id in material_info.get("applicable_processes", []):
                materials.append({
                    'id': material_id,
                    'label': material_info.get('label', ''),
                    'forms': list(material_info.get('forms', {}).keys())
                })
        materials = sorted(materials, key=lambda x: x['label'])
        return materials
    
    def configure_parameters_quick(self, service_id: str, file_type: str) -> Dict[str, Any]:
        """Configure parameters using defaults for quick testing"""
        # Find service name from service_id
        service_name = "Unknown Service"
        for key, service_info in SERVICES.items():
            if service_info['id'] == service_id:
                service_name = service_info['name']
                break
        
        print(f"\n🚀 Quick Test Mode - Using default parameters for {service_name}")
        
        params = DEFAULT_PARAMS[service_id].copy()
        params['location'] = 'location_1'
        params['file_type'] = file_type
        
        print("Default Parameters:")
        for key, value in params.items():
            print(f"  {key}: {value}")
        
        return params
    
    def configure_parameters_custom(self, service_id: str) -> Dict[str, Any]:
        """Interactive custom parameter configuration"""
        self.print_header("Custom Parameter Configuration")
        
        params = {}
        
        # Get available materials
        materials = self.get_material_options(service_id)
        if not materials:
            print("❌ No materials available for this service")
            return {}
        
        # Material selection
        print("\nAvailable Materials:")
        for i, material in enumerate(materials, 1):
            print(f"  [{i}] {material['label']} ({material['id']})")
        
        while True:
            try:
                choice = int(self.get_user_input("Select material"))
                if 1 <= choice <= len(materials):
                    selected_material = materials[choice - 1]
                    params['material_id'] = selected_material['id']
                    print(f"✅ Selected: {selected_material['label']}")
                    break
                else:
                    print(f"❌ Invalid choice. Please select 1-{len(materials)}")
            except ValueError:
                print("❌ Please enter a valid number")
        
        # Material form selection
        material_info = MATERIALS[params['material_id']]
        forms = list(material_info.get('forms', {}).keys())
        if "sheet" not in forms:
            forms.append("sheet")
        if "rod" not in forms:
            forms.append("rod")
        if "hexagon" not in forms:
            forms.append("hexagon")
        
        if forms:
            print(f"\nAvailable Forms for {material_info['label']}:")
            for i, form in enumerate(forms, 1):
                print(f"  [{i}] {form}")
            
            while True:
                try:
                    choice = int(self.get_user_input("Select material form"))
                    if 1 <= choice <= len(forms):
                        params['material_form'] = forms[choice - 1]
                        print(f"✅ Selected: {forms[choice - 1]}")
                        break
                    else:
                        print(f"❌ Invalid choice. Please select 1-{len(forms)}")
                except ValueError:
                    print("❌ Please enter a valid number")
        else:
            params['material_form'] = "powder"  # Default fallback
        
        # Quantity
        while True:
            try:
                quantity = int(self.get_user_input("Enter quantity (1-1000)"))
                if 1 <= quantity <= 1000:
                    params['quantity'] = quantity
                    break
                else:
                    print("❌ Quantity must be between 1 and 1000")
            except ValueError:
                print("❌ Please enter a valid number")
        
        # Cover processing
        print(f"\nCover Processing Options:")
        for key, cover_info in COVER.items():
            print(f"  [{key}] {cover_info['label']}")
        
        cover_choice = self.get_user_input("Select cover processing (comma-separated for multiple)", list(COVER.keys()))
        params['cover_id'] = [c.strip() for c in cover_choice.split(',') if c.strip() in COVER]
        
        # Location
        print(f"\nAvailable Locations:")
        locations_id = []
        for id, location_info in enumerate(LOCATIONS.items()):
            locations_id.append(str(id+1))
            print(f"  [{id+1}] {location_info[1]['name']}")
        
        available_locations = list(LOCATIONS.keys())
        location_choice = self.get_user_input("Select location", locations_id)
        params['location'] = available_locations[int(location_choice)]
        
        # Service-specific parameters
        if service_id == "printing":
            self._configure_printing_params(params)
        elif service_id in ["cnc-milling", "cnc-lathe"]:
            self._configure_cnc_params(params)
        elif service_id == "painting":
            self._configure_painting_params(params)
        
        return params
    
    def _configure_printing_params(self, params: Dict[str, Any]):
        """Configure 3D printing specific parameters"""
        print(f"\n3D Printing Parameters:")
        
        # n_dimensions
        while True:
            try:
                n_dims = int(self.get_user_input("Enter number of dimensions (1-100)"))
                if 1 <= n_dims <= 100:
                    params['n_dimensions'] = n_dims
                    break
                else:
                    print("❌ Number of dimensions must be between 1 and 100")
            except ValueError:
                print("❌ Please enter a valid number")
        
        # k_type
        while True:
            try:
                k_type = float(self.get_user_input("Enter type coefficient (0.1-2.0)"))
                if 0.1 <= k_type <= 2.0:
                    params['k_type'] = k_type
                    break
                else:
                    print("❌ Type coefficient must be between 0.1 and 2.0")
            except ValueError:
                print("❌ Please enter a valid number")
        
        # k_process
        while True:
            try:
                k_process = float(self.get_user_input("Enter process coefficient (0.1-2.0)"))
                if 0.1 <= k_process <= 2.0:
                    params['k_process'] = k_process
                    break
                else:
                    print("❌ Process coefficient must be between 0.1 and 2.0")
            except ValueError:
                print("❌ Please enter a valid number")
        
        # k_otk
        while True:
            try:
                k_otk = float(self.get_user_input("Enter quality control coefficient (0.1-2.0)"))
                if 0.1 <= k_otk <= 2.0:
                    params['k_otk'] = k_otk
                    break
                else:
                    print("❌ Quality control coefficient must be between 0.1 and 2.0")
            except ValueError:
                print("❌ Please enter a valid number")
        
        # k_cert
        cert_options = ["a", "b", "c", "d", "e", "f", "g"]
        print(f"\nCertification Types: {', '.join(cert_options)}")
        cert_choice = self.get_user_input("Enter certification types (comma-separated)")
        params['k_cert'] = [c.strip() for c in cert_choice.split(',') if c.strip() in cert_options]
    
    def _configure_cnc_params(self, params: Dict[str, Any]):
        """Configure CNC specific parameters"""
        print(f"\nCNC Parameters:")
        
        # Tolerance
        print(f"\nTolerance Options:")
        for key, tolerance_info in TOLERANCE.items():
            print(f"  [{key}] {tolerance_info['label']}")
        
        tolerance_choice = self.get_user_input("Select tolerance", list(TOLERANCE.keys()))
        params['tolerance_id'] = tolerance_choice
        
        # Finish
        print(f"\nFinish Options:")
        for key, finish_info in FINISH.items():
            print(f"  [{key}] {finish_info['label']}")
        
        finish_choice = self.get_user_input("Select finish", list(FINISH.keys()))
        params['finish_id'] = finish_choice
        
        # CNC complexity
        # complexity_options = ["low", "medium", "high"]
        # print(f"\nCNC Complexity Options: {', '.join(complexity_options)}")
        # complexity_choice = self.get_user_input("Select CNC complexity", complexity_options)
        # params['cnc_complexity'] = complexity_choice
        
        # CNC setup time
        # while True:
        #     try:
        #         setup_time = float(self.get_user_input("Enter CNC setup time (0.5-10.0 hours)"))
        #         if 0.5 <= setup_time <= 10.0:
        #             params['cnc_setup_time'] = setup_time
        #             break
        #         else:
        #             print("❌ Setup time must be between 0.5 and 10.0 hours")
        #     except ValueError:
        #         print("❌ Please enter a valid number")
        
        # k_otk
        while True:
            try:
                k_otk = float(self.get_user_input("Enter quality control coefficient (0.1-2.0)"))
                if 0.1 <= k_otk <= 2.0:
                    params['k_otk'] = k_otk
                    break
                else:
                    print("❌ Quality control coefficient must be between 0.1 and 2.0")
            except ValueError:
                print("❌ Please enter a valid number")
    
    def _configure_painting_params(self, params: Dict[str, Any]):
        """Configure painting specific parameters"""
        print(f"\nPainting Parameters:")
        
        # Paint type
        paint_types = ["acrylic", "epoxy", "polyurethane"]
        print(f"\nPaint Types: {', '.join(paint_types)}")
        paint_choice = self.get_user_input("Select paint type", paint_types)
        params['paint_type'] = paint_choice
        
        # Process coefficients
        process_options = ["a", "b", "c"]
        print(f"\nProcess Options: {', '.join(process_options)}")
        
        prepare_choice = self.get_user_input("Select paint preparation", process_options)
        params['paint_prepare'] = prepare_choice
        
        primer_choice = self.get_user_input("Select paint primer", process_options)
        params['paint_primer'] = primer_choice
        
        lakery_choice = self.get_user_input("Select paint lakery", process_options)
        params['paint_lakery'] = lakery_choice
        
        # Control type
        control_choice = self.get_user_input("Enter control type (1-3)", ["1", "2", "3"])
        params['control_type'] = control_choice
        
        # k_cert
        cert_options = ["a", "b", "c", "d", "e", "f", "g"]
        print(f"\nCertification Types: {', '.join(cert_options)}")
        cert_choice = self.get_user_input("Enter certification types (comma-separated)")
        params['k_cert'] = [c.strip() for c in cert_choice.split(',') if c.strip() in cert_options]
        
        # k_otk
        while True:
            try:
                k_otk = float(self.get_user_input("Enter quality control coefficient (0.1-2.0)"))
                if 0.1 <= k_otk <= 2.0:
                    params['k_otk'] = k_otk
                    break
                else:
                    print("❌ Quality control coefficient must be between 0.1 and 2.0")
            except ValueError:
                print("❌ Please enter a valid number")
    
    def encode_file(self, file_path: Path) -> str:
        """Read file and encode to base64"""
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
                return base64.b64encode(file_data).decode('utf-8')
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return None
    
    def upload_file(self, file_info: Dict[str, Any], service_id: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upload file and parameters to API"""
        print(f"\n📤 Uploading file to API...")
        
        # Encode file
        file_data = self.encode_file(file_info['path'])
        if not file_data:
            return None
        
        # Construct request
        request_data = {
            "service_id": service_id,
            "file_id": f"test-{file_info['name']}-{service_id}",
            "file_data": file_data,
            "file_name": file_info['name'],
            "file_type": file_info['type'],
            **parameters
        }
        
        # Display request preview
        print(f"\n📋 Request Preview:")
        # Find service name from service_id
        service_name = "Unknown Service"
        for key, service_info in SERVICES.items():
            if service_info['id'] == service_id:
                service_name = service_info['name']
                break
        print(f"  Service: {service_name}")
        print(f"  File: {file_info['name']} ({file_info['size_mb']} MB)")
        print(f"  File ID: {request_data['file_id']}")
        print(f"  Parameters: {len(parameters)} configured")
        
        # Confirm upload
        confirm = self.get_user_input("Send request? (y/n)", ["y", "n", "yes", "no"])
        if confirm.lower() not in ["y", "yes"]:
            print("❌ Upload cancelled")
            return None
        
        # Send request
        try:
            response = requests.post(API_ENDPOINT, json=request_data, timeout=60)
            
            if response.status_code == 200:
                print("✅ Upload successful!")
                return response.json()
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                print(f"Error: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return None
    
    def display_results(self, results: Dict[str, Any]):
        """Display formatted results"""
        self.print_header("Calculation Results")
        
        if not results:
            print("❌ No results to display")
            return
        
        # Show full response by default
        print(f"📄 Full API Response:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
        # Ask if user wants brief summary
        show_brief = self.get_user_input("\nShow brief summary? (y/n)", ["y", "n", "yes", "no"])
        if show_brief.lower() in ["y", "yes"]:
            self._display_brief_summary(results)
    
    def _display_brief_summary(self, results: Dict[str, Any]):
        """Display a brief summary of key results"""
        print(f"\n📊 Brief Summary:")
        print(f"  Total Price: ${results.get('total_price', 0):,.2f}")
        print(f"  Detail Price: ${results.get('detail_price', 0):,.2f}")
        print(f"  Work Time: {results.get('total_time', 0):.2f} hours")
        print(f"  Manufacturing Cycle: {results.get('manufacturing_cycle', 0):.1f} days")
        
        # Calculation method
        calc_engine = results.get('calculation_engine', 'unknown')
        calc_method = results.get('calculation_method', 'unknown')
        print(f"\n🔧 Calculation Method:")
        print(f"  Engine: {calc_engine}")
        print(f"  Method: {calc_method}")
        
        # ML specific results
        if calc_engine == 'ml_model':
            ml_hours = results.get('ml_prediction_hours')
            if ml_hours:
                print(f"  ML Prediction: {ml_hours:.2f} hours")
            
            features = results.get('features_extracted', {})
            if features:
                print(f"  Features Used: {len(features)} geometric features")
        
        # Material costs
        mat_price = results.get('mat_price', 0)
        work_price = results.get('work_price', 0)
        if mat_price or work_price:
            print(f"\n💰 Cost Breakdown:")
            print(f"  Material Cost: ${mat_price:,.2f}")
            print(f"  Work Cost: ${work_price:,.2f}")
        
        # Manufacturing details
        suitable_machines = results.get('suitable_machines', [])
        if suitable_machines:
            print(f"\n🏭 Manufacturing:")
            print(f"  Suitable Machines: {', '.join(suitable_machines)}")
        
        # Coefficients
        print(f"\n📈 Applied Coefficients:")
        for key in ['k_quantity', 'k_complexity', 'k_cover', 'k_tolerance', 'k_finish']:
            value = results.get(key)
            if value is not None:
                print(f"  {key}: {value:.3f}")
    
    def save_results(self, results: Dict[str, Any], file_info: Dict[str, Any], service_id: str):
        """Save results to JSON file"""
        save_choice = self.get_user_input("\nSave results to file? (y/n)", ["y", "n", "yes", "no"])
        if save_choice.lower() not in ["y", "yes"]:
            return
        
        # Create results directory if it doesn't exist
        results_dir = Path("test_results")
        results_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_{file_info['name']}_{service_id}_{timestamp}.json"
        filepath = results_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"✅ Results saved to: {filepath}")
        except Exception as e:
            print(f"❌ Error saving results: {e}")
    
    def main_menu(self):
        """Main interactive loop"""
        self.clear_screen()
        print(f"🚀 Manufacturing Calculation File Upload Test v{APP_VERSION}")
        print(f"API Endpoint: {API_ENDPOINT}")
        
        while True:
            # File selection
            file_info = self.select_file()
            if not file_info:
                break
            
            # Service selection
            service_id = self.select_service()
            if not service_id:
                continue
            
            # Parameter mode selection
            self.print_header("Parameter Configuration")
            print("Parameter Modes:")
            print("  [1] Quick Test (default parameters)")
            print("  [2] Custom Parameters")
            print("  [0] Back to service selection")
            
            mode_choice = self.get_user_input("Select mode", ["0", "1", "2"])
            
            if mode_choice == "0":
                continue
            elif mode_choice == "1":
                parameters = self.configure_parameters_quick(service_id, file_info["type"].lower())
            else:
                parameters = self.configure_parameters_custom(service_id)
            
            if not parameters:
                print("❌ Parameter configuration failed")
                continue
            
            # Upload and get results
            results = self.upload_file(file_info, service_id, parameters)
            
            if results:
                self.display_results(results)
                self.save_results(results, file_info, service_id)
            
            # Continue or exit
            continue_choice = self.get_user_input("\nTest another file? (y/n)", ["y", "n", "yes", "no"])
            if continue_choice.lower() not in ["y", "yes"]:
                break
        
        print("\n👋 Thank you for using the Manufacturing Calculation File Upload Test!")

def main():
    """Main entry point"""
    try:
        tester = InteractiveFileTester()
        tester.main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
