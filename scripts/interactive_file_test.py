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
from constants import APP_VERSION, TOLERANCE, FINISH, COVER
from MATERIALS_gen import MATERIALS
try:
    from commercial_constants import LOCATIONS
except ImportError:
    LOCATIONS = {"location_1": {"name": "location_1"}}
from utils.electroplating_config import (
    ELECTROPLATING_SERVICE_ID,
    get_material_families,
    get_process_params,
)

# API Configuration
BASE_URL = "http://localhost:7000"
API_ENDPOINT = f"{BASE_URL}/calculate-price"

# Service types mapping
SERVICES = {
    "1": {"id": "printing", "name": "3D Printing"},
    "2": {"id": "cnc-milling", "name": "CNC Milling"},
    "3": {"id": "composite", "name": "Composite"},
    "4": {"id": ELECTROPLATING_SERVICE_ID, "name": "Electroplating Auto"},
}

# Default parameters for quick test mode
DEFAULT_PARAMS = {
    "printing": {
        "material_id": "plastic_ABS",
        "material_form": "thread",
        "quantity": 1,
        "cover_id": ["1"],
        "k_otk": 1.0,
        "k_cert": ["a", "f"]
    },
    "cnc-milling": {
        "material_id": "non_ferrous_Д16",
        "material_form": "sheet",
        "quantity": 1,
        "tolerance_id": "1",
        "finish_id": "1",
        "cover_id": ["1"],
        "k_otk": 1.0,
        "cnc_complexity": "medium",
        "cnc_setup_time": 2.0
    },
    "composite": {
        "material_id": "pre-preg_kmks-2m",
        "quantity": 1,
    },
    ELECTROPLATING_SERVICE_ID: {
        "electroplating_family": "carbon_steel",
        "quantity": 10,
        "electroplating_process_id": "galvanization_zinc_phosphating",
        "cover_id": ["galvanization_zinc_phosphating"],
        "coating_thickness_microns": 9.0,
        "k_otk": 1.0,
    },
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

        if service_id == ELECTROPLATING_SERVICE_ID:
            return []

        for material_id, material_info in MATERIALS.items():
            if service_id in material_info.get("applicable_processes", []):
                materials.append({
                    'id': material_id,
                    'label': material_info.get('label', ''),
                    'forms': list(material_info.get('forms', {}).keys())
                })
        materials = sorted(materials, key=lambda x: x['label'])
        return materials
    
    def get_electroplating_family_options(self) -> List[Dict[str, Any]]:
        """Get available material families for electroplating_auto."""
        families = []
        for family_id, family_info in get_material_families().items():
            if family_info.get('allowed_processes'):
                families.append({
                    'id': family_id,
                    'label': family_info.get('label', family_id),
                    'density_kg_dm3': family_info.get('density_kg_dm3'),
                    'allowed_processes': family_info.get('allowed_processes', []),
                })
        return sorted(families, key=lambda x: x['label'])

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

        if service_id == ELECTROPLATING_SERVICE_ID:
            families = self.get_electroplating_family_options()
            if not families:
                print("❌ No electroplating material families configured")
                return {}

            print("\nAvailable Electroplating Material Families:")
            for i, family in enumerate(families, 1):
                print(f"  [{i}] {family['label']} ({family['id']}), density={family.get('density_kg_dm3')}")

            while True:
                try:
                    choice = int(self.get_user_input("Select electroplating material family"))
                    if 1 <= choice <= len(families):
                        selected_family = families[choice - 1]
                        params['electroplating_family'] = selected_family['id']
                        print(f"✅ Selected: {selected_family['label']}")
                        break
                    print(f"❌ Invalid choice. Please select 1-{len(families)}")
                except ValueError:
                    print("❌ Please enter a valid number")
        else:
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
                    print(f"❌ Invalid choice. Please select 1-{len(materials)}")
                except ValueError:
                    print("❌ Please enter a valid number")

            # Material form selection
            material_info = MATERIALS[params['material_id']]
            forms = list(material_info.get('forms', {}).keys())

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
                        print(f"❌ Invalid choice. Please select 1-{len(forms)}")
                    except ValueError:
                        print("❌ Please enter a valid number")
            else:
                print(f"❌ No material forms configured for {params['material_id']}")
                return {}

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
        
        if service_id == ELECTROPLATING_SERVICE_ID:
            self._configure_electroplating_params(params)
            self._configure_location_param(params)
            return params

        # Cover processing
        print(f"\nCover Processing Options:")
        for key, cover_info in COVER.items():
            print(f"  [{key}] {cover_info['label']}")
        
        cover_choice = self.get_user_input("Select cover processing (comma-separated for multiple)", list(COVER.keys()))
        params['cover_id'] = [c.strip() for c in cover_choice.split(',') if c.strip() in COVER]
        
        self._configure_location_param(params)
        
        # Service-specific parameters
        if service_id == "printing":
            self._configure_printing_params(params)
        elif service_id == "cnc-milling":
            self._configure_cnc_params(params)
        elif service_id == "composite":
            self._configure_composite_params(params)

        return params
    
    def _configure_location_param(self, params: Dict[str, Any]):
        """Configure manufacturing location."""
        print(f"\nAvailable Locations:")
        locations_id = []
        for id, location_info in enumerate(LOCATIONS.items()):
            locations_id.append(str(id + 1))
            print(f"  [{id + 1}] {location_info[1]['name']}")

        available_locations = list(LOCATIONS.keys())
        location_choice = self.get_user_input("Select location", locations_id)
        params['location'] = available_locations[int(location_choice) - 1]

    def _configure_electroplating_params(self, params: Dict[str, Any]):
        """Configure electroplating_auto specific parameters."""
        print(f"\nElectroplating Parameters:")

        material_family = params['electroplating_family']
        process_params = get_process_params()
        available_processes = []
        for process_id, process in process_params.items():
            if material_family in process.get("material_families", []):
                available_processes.append((process_id, process))

        if not available_processes:
            print(f"❌ No electroplating processes available for material family: {material_family}")
            return

        available_processes.sort(key=lambda item: (str(item[1].get('group') or ''), str(item[1].get('label') or item[0])))
        print(f"\nAvailable Operations for material family '{material_family}':")
        for i, (process_id, process) in enumerate(available_processes, 1):
            group = process.get('group') or 'Без группы'
            label = process.get('label') or process_id
            max_size = process.get('max_part_size_mm')
            max_weight = process.get('max_weight_kg')
            print(f"  [{i}] {group} / {label} ({process_id}); bath={max_size}, max_weight_kg={max_weight}")

        while True:
            try:
                choice = int(self.get_user_input("Select electroplating operation"))
                if 1 <= choice <= len(available_processes):
                    selected_process_id, selected_process = available_processes[choice - 1]
                    params['electroplating_process_id'] = selected_process_id
                    # Keep cover_id synchronized for backward compatibility with existing request shape.
                    params['cover_id'] = [selected_process_id]
                    print(f"✅ Selected: {selected_process.get('label') or selected_process_id}")
                    break
                else:
                    print(f"❌ Invalid choice. Please select 1-{len(available_processes)}")
            except ValueError:
                print("❌ Please enter a valid number")

        time_model = selected_process.get('time_model')
        thickness_role = selected_process.get('thickness_role')
        if time_model == 'faraday_material_removal':
            default_depth = float(selected_process.get('default_processing_depth_microns') or 10.0)
            while True:
                raw = self.get_user_input(f"Enter electropolishing removal depth in microns [default {default_depth:g}]")
                if raw == "":
                    params['processing_depth_microns'] = default_depth
                    params.pop('coating_thickness_microns', None)
                    break
                try:
                    depth = float(raw)
                    if depth > 0:
                        params['processing_depth_microns'] = depth
                        params.pop('coating_thickness_microns', None)
                        break
                    print("❌ Removal depth must be > 0")
                except ValueError:
                    print("❌ Please enter a valid number")
        elif time_model == 'fixed_time':
            fixed_time = selected_process.get('fixed_operation_time_min')
            print(f"  Fixed operation time model: {fixed_time} min; thickness is not used in the time formula")
            params.pop('coating_thickness_microns', None)
            params.pop('processing_depth_microns', None)
        else:
            default_thickness = float(selected_process.get('default_thickness_microns') or 9.0)
            prompt_label = "oxide layer thickness" if thickness_role == 'oxide_layer_thickness' else "coating thickness"
            while True:
                raw = self.get_user_input(f"Enter {prompt_label} in microns [default {default_thickness:g}]")
                if raw == "":
                    params['coating_thickness_microns'] = default_thickness
                    params.pop('processing_depth_microns', None)
                    break
                try:
                    thickness = float(raw)
                    if thickness > 0:
                        params['coating_thickness_microns'] = thickness
                        params.pop('processing_depth_microns', None)
                        break
                    print("❌ Thickness must be > 0")
                except ValueError:
                    print("❌ Please enter a valid number")

        while True:
            try:
                k_otk = float(self.get_user_input("Enter quality control coefficient (0.1-2.0)") or "1.0")
                if 0.1 <= k_otk <= 2.0:
                    params['k_otk'] = k_otk
                    break
                print("❌ Quality control coefficient must be between 0.1 and 2.0")
            except ValueError:
                print("❌ Please enter a valid number")

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
    
    
    def encode_file(self, file_path: Path) -> str:
        """Read file and encode to base64"""
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
                return base64.b64encode(file_data).decode('utf-8')
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return None
    
    def upload_file(self, file_info: Dict[str, Any], service_id: str, parameters: Dict[str, Any], show_request=False) -> Optional[Dict[str, Any]]:
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
        if service_id == "composite":
            print("  Debug: composite uses STP feature extraction + separate flexible_ensemble bundle")
        if service_id == ELECTROPLATING_SERVICE_ID:
            print("  Debug: electroplating_auto uses STP surface area, volume, OBB bath layout, current and weight batch limits")
        
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
                if show_request==True:
                    return response.json(), request_data
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                print(f"Error: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return None
    
    def display_results(self, results: Dict[str, Any], service_id: Optional[str] = None):
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
        
        # Electroplating-specific details
        if results.get('electroplating_process_id'):
            print(f"\n⚗️ Electroplating:")
            print(f"  Process: {results.get('electroplating_process_id')}")
            if results.get('processing_depth_microns') is not None:
                print(f"  Removal Depth: {results.get('processing_depth_microns')} µm")
            elif results.get('coating_thickness_microns') is not None:
                print(f"  Thickness: {results.get('coating_thickness_microns')} µm")
            print(f"  Time Model: {results.get('process_time_model')}")
            print(f"  Thickness Role: {results.get('thickness_role')}")
            print(f"  Surface Area: {results.get('coating_surface_area_dm2')} dm²")
            print(f"  Part Weight: {results.get('coating_mass_kg')} kg")
            print(f"  Requested Quantity: {results.get('requested_quantity')}")
            print(f"  Batch Quantity Used as n: {results.get('batch_quantity')}")
            print(f"  Batch Capacity: {results.get('bath_batch_capacity')}")
            print(f"  Geometric Capacity: {results.get('bath_geometric_capacity')}")
            print(f"  Current Capacity: {results.get('bath_current_capacity')}")
            print(f"  Weight Capacity: {results.get('bath_weight_capacity')}")
            print(f"  Max Batch Weight: {results.get('bath_max_weight_kg')} kg")
            print(f"  Batch Count: {results.get('batch_count')}")
            print(f"  Limited By: {results.get('batch_quantity_limited_by')}")

        # Manufacturing details
        suitable_machines = results.get('suitable_machines', [])
        if suitable_machines:
            print(f"\n🏭 Manufacturing:")
            print(f"  Suitable Machines: {', '.join(suitable_machines)}")
        
        # Coefficients
        print(f"\n📈 Applied Coefficients:")
        for key in ['k_quantity', 'k_cover', 'k_tolerance', 'k_finish']:
            value = results.get(key)
            if value is not None:
                print(f"  {key}: {value:.3f}")
    
    def _display_composite_debug_summary(self, results: Dict[str, Any]):
        """Display a focused debug summary for composite inference."""
        print("\n🧪 Composite Debug Summary:")
        print(f"  Calculation engine: {results.get('calculation_engine', 'unknown')}")
        print(f"  Calculation method: {results.get('calculation_method', 'unknown')}")
        print(f"  Predicted labor: {results.get('ml_prediction_hours', results.get('total_time', 0)):.4f} hours")

        dims = results.get('extracted_dimensions') or {}
        if dims:
            print("  Extracted dimensions:")
            for key, value in dims.items():
                print(f"    - {key}: {value}")

        features = results.get('features_extracted') or {}
        if features:
            print(f"  Extracted feature count: {len(features)}")
            for key in sorted(features.keys()):
                print(f"    - {key}: {features[key]}")
        else:
            print("  No features_extracted in response")

    def save_results(self, results: Dict[str, Any], file_info: Dict[str, Any], service_id: str, request: Dict):
        """Save results to JSON file"""
        save_choice = self.get_user_input("\nSave results to file? (y/n)", ["y", "n", "yes", "no"])
        if save_choice.lower() not in ["y", "yes"]:
            return
        
        # Create results directory if it doesn't exist
        results_dir = Path("test_results")
        results_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_{file_info['name']}_{service_id}_{timestamp}.txt"
        filepath = results_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('Request:\n')
                json.dump(request, f, indent=2)
                f.write('\nResponse:\n')
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
            
            if service_id == "composite" and file_info["type"].lower() not in ["stp", "step"]:
                print("❌ Composite debugging requires STP/STEP file input")
                continue
            if service_id == ELECTROPLATING_SERVICE_ID and file_info["type"].lower() not in ["stp", "step"]:
                print("❌ Electroplating auto requires STP/STEP file input")
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
            results, request_data = self.upload_file(file_info, service_id, parameters, show_request=True)
            
            if results:
                self.display_results(results, service_id=service_id)
                self.save_results(results, file_info, service_id, request_data)
            
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
