#!/usr/bin/env python3
"""
Interactive Pricing Tester
Allows interactive selection of test files and calculation types for comprehensive pricing testing
"""

import requests
import json
import base64
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Optional
import os
import sys

# API Configuration
BASE_URL = "http://localhost:7000"
API_ENDPOINT = f"{BASE_URL}/calculate-price"

class InteractivePricingTester:
    """Interactive pricing test suite with file and method selection"""
    
    def __init__(self):
        self.results = []
        self.test_files_data = {}
        self.available_files = []
        self.selected_files = []
        self.calculation_methods = []
        self.test_quantities = [
            (1, 1.0, "Single unit"),
            (5, 1.0, "Small batch"),
            (10, 1.0, "Small batch"),
            (20, 1.0, "Small batch"),
            (25, 0.95, "5% discount"),
            (50, 0.95, "5% discount"),
            (100, 0.95, "5% discount"),
            (150, 0.85, "15% discount"),
            (300, 0.85, "15% discount"),
            (500, 0.85, "15% discount"),
            (600, 0.8, "20% discount"),
            (1000, 0.8, "20% discount")
        ]
    
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
                if valid_options and user_input not in valid_options:
                    print(f"❌ Invalid option. Please choose from: {', '.join(valid_options)}")
                    continue
                return user_input
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                sys.exit(0)
    
    def scan_test_files(self):
        """Scan test_files directory for available files"""
        test_files_dir = Path("test_files")
        if not test_files_dir.exists():
            print(f"❌ Test files directory not found: {test_files_dir}")
            return []
        
        files = []
        for file_path in test_files_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.stl', '.stp', '.step']:
                file_size = file_path.stat().st_size
                file_type = file_path.suffix.lower()[1:]  # Remove the leading dot
                files.append({
                    'path': file_path,
                    'name': file_path.name,
                    'type': file_type,
                    'size_mb': round(file_size / (1024 * 1024), 2)
                })
        
        return sorted(files, key=lambda x: x['name'])
    
    def select_files(self):
        """Interactive file selection"""
        self.print_header("File Selection")
        
        self.available_files = self.scan_test_files()
        
        if not self.available_files:
            print("❌ No STL/STP files found in test_files directory")
            return False
        
        print("Available Files:")
        for i, file_info in enumerate(self.available_files, 1):
            print(f"  [{i}] {file_info['name']} ({file_info['size_mb']} MB, {file_info['type'].upper()})")
        
        print(f"  [a] Select all files")
        print(f"  [0] Skip file testing (rule-based only)")
        
        while True:
            choice = self.get_user_input("Select files (comma-separated numbers, 'a' for all, or '0' to skip)")
            
            if choice == "0":
                self.selected_files = []
                print("✅ Skipping file testing - will test rule-based calculations only")
                return True
            elif choice.lower() == "a":
                self.selected_files = self.available_files.copy()
                print(f"✅ Selected all {len(self.selected_files)} files")
                return True
            else:
                try:
                    selected_indices = [int(x.strip()) for x in choice.split(',')]
                    self.selected_files = []
                    for idx in selected_indices:
                        if 1 <= idx <= len(self.available_files):
                            self.selected_files.append(self.available_files[idx - 1])
                        else:
                            print(f"❌ Invalid index: {idx}")
                            break
                    else:
                        if self.selected_files:
                            print(f"✅ Selected {len(self.selected_files)} files")
                            return True
                except ValueError:
                    print("❌ Please enter valid numbers separated by commas")
    
    def select_calculation_methods(self):
        """Interactive calculation method selection"""
        self.print_header("Calculation Method Selection")
        
        print("Available Methods:")
        print("  [1] Rule-based only (no file upload)")
        print("  [2] ML-based only (with file upload)")
        print("  [3] Both methods")
        
        choice = self.get_user_input("Select calculation method", ["1", "2", "3"])
        
        if choice == "1":
            self.calculation_methods = ["rule_based"]
            print("✅ Selected: Rule-based calculations only")
        elif choice == "2":
            self.calculation_methods = ["ml_based"]
            print("✅ Selected: ML-based calculations only")
        else:
            self.calculation_methods = ["rule_based", "ml_based"]
            print("✅ Selected: Both rule-based and ML-based calculations")
        
        return True
    
    def select_quantities(self):
        """Interactive quantity selection"""
        self.print_header("Quantity Selection")
        
        print("Available Quantity Options:")
        print("  [1] Quick test (1, 25, 150, 600)")
        print("  [2] Full test (all 12 quantities)")
        print("  [3] Custom selection")
        
        choice = self.get_user_input("Select quantity test mode", ["1", "2", "3"])
        
        if choice == "1":
            self.test_quantities = [
                (1, 1.0, "Single unit"),
                (25, 0.95, "5% discount"),
                (150, 0.85, "15% discount"),
                (600, 0.8, "20% discount")
            ]
            print("✅ Selected: Quick test (4 quantities)")
        elif choice == "2":
            print("✅ Selected: Full test (12 quantities)")
        else:
            # Custom selection
            print("\nAvailable quantities:")
            for i, (qty, k_qty, desc) in enumerate(self.test_quantities, 1):
                print(f"  [{i}] {qty} units ({desc})")
            
            choice = self.get_user_input("Select quantities (comma-separated numbers)")
            try:
                selected_indices = [int(x.strip()) for x in choice.split(',')]
                custom_quantities = []
                for idx in selected_indices:
                    if 1 <= idx <= len(self.test_quantities):
                        custom_quantities.append(self.test_quantities[idx - 1])
                if custom_quantities:
                    self.test_quantities = custom_quantities
                    print(f"✅ Selected: {len(self.test_quantities)} custom quantities")
                else:
                    print("❌ No valid quantities selected, using default")
            except ValueError:
                print("❌ Invalid selection, using default")
        
        return True
    
    def load_selected_files(self):
        """Load and encode selected files"""
        if not self.selected_files:
            return True
        
        print(f"\n📁 Loading {len(self.selected_files)} selected files...")
        
        for file_info in self.selected_files:
            try:
                with open(file_info['path'], 'rb') as f:
                    file_data = base64.b64encode(f.read()).decode('utf-8')
                
                self.test_files_data[file_info['type']] = {
                    'data': file_data,
                    'name': file_info['name'],
                    'size_mb': file_info['size_mb']
                }
                print(f"  ✅ Loaded {file_info['type'].upper()}: {file_info['name']} ({file_info['size_mb']} MB)")
            except Exception as e:
                print(f"  ❌ Failed to load {file_info['name']}: {e}")
                return False
        
        return True
    
    def test_rule_based_calculation(self, file_type: str, quantity: int, expected_k_quantity: float, description: str) -> Optional[Dict[str, Any]]:
        """Test rule-based calculation (no file upload)"""
        print(f"    🔧 Rule-based: Qty {quantity} ({description})")
        
        request_data = {
            "service_id": "printing",
            "file_id": f"rule-{file_type}-{quantity}",
            "length": 100.0, "width": 50.0, "height": 10.0,
            "quantity": quantity, "material_id": "PA11", "material_form": "powder",
            "k_type": 1.0, "k_process": 1.0,
            "cover_id": ["1"], "k_otk": 1.0, "k_cert": ["a", "f"], "location": "location_1"
        }
        
        try:
            response = requests.post(API_ENDPOINT, json=request_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                
                # Show detailed pricing info
                detail_price = data.get('detail_price', 0) or 0
                detail_price_one = data.get('detail_price_one', 0) or 0
                total_price = data.get('total_price', 0) or 0
                k_quantity = data.get('k_quantity', 0) or 0
                mat_price = data.get('mat_price', 0) or 0
                work_price = data.get('work_price', 0) or 0
                total_time = data.get('total_time', 0) or 0
                
                print(f"      ✅ ${detail_price:,.2f} (k_quantity: {k_quantity:.3f})")
                if mat_price > 0 or work_price > 0 or total_time > 0:
                    print(f"         Material: ${mat_price:,.2f}, Work: ${work_price:,.2f}, Time: {total_time:.1f}h")
                
                return {
                    'file_type': file_type,
                    'calculation_method': 'rule_based',
                    'quantity': quantity,
                    'expected_k_quantity': expected_k_quantity,
                    'k_quantity': data.get('k_quantity', 0) or 0,
                    'detail_price': data.get('detail_price', 0) or 0,
                    'detail_price_one': data.get('detail_price_one', 0) or 0,
                    'total_price': data.get('total_price', 0) or 0,
                    'total_time': data.get('total_time', 0) or 0,
                    'mat_volume': data.get('mat_volume', 0) or 0,
                    'mat_weight': data.get('mat_weight', 0) or 0,
                    'mat_price': data.get('mat_price', 0) or 0,
                    'work_price': data.get('work_price', 0) or 0,
                    'work_time': data.get('work_time', 0) or 0,
                    'k_complexity': data.get('k_complexity', 0) or 0,
                    'k_cover': data.get('k_cover', 0) or 0,
                    'k_otk': data.get('k_otk', 0) or 0,
                    'manufacturing_cycle': data.get('manufacturing_cycle', 0) or 0,
                    'calculation_engine': data.get('calculation_engine', 'unknown'),
                    'description': description,
                    'success': True
                }
            else:
                print(f"      ❌ Failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            return None
    
    def test_ml_based_calculation(self, file_type: str, quantity: int, expected_k_quantity: float, description: str) -> Optional[Dict[str, Any]]:
        """Test ML-based calculation (with file upload)"""
        print(f"    🤖 ML-based: Qty {quantity} ({description})")
        
        if file_type not in self.test_files_data:
            print(f"      ❌ No file data for {file_type}")
            return None
        
        request_data = {
            "service_id": "printing",
            "file_id": f"ml-{file_type}-{quantity}",
            "file_data": self.test_files_data[file_type]['data'],
            "file_name": self.test_files_data[file_type]['name'],
            "file_type": file_type,
            "quantity": quantity, "material_id": "PA11", "material_form": "powder",
            "k_type": 1.0, "k_process": 1.0,
            "cover_id": ["1"], "k_otk": 1.0, "k_cert": ["a", "f"], "location": "location_1"
        }
        
        try:
            response = requests.post(API_ENDPOINT, json=request_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                
                # Show detailed pricing info
                detail_price = data.get('detail_price', 0) or 0
                detail_price_one = data.get('detail_price_one', 0) or 0
                total_price = data.get('total_price', 0) or 0
                k_quantity = data.get('k_quantity', 0) or 0
                mat_price = data.get('mat_price', 0) or 0
                work_price = data.get('work_price', 0) or 0
                total_time = data.get('total_time', 0) or 0
                ml_hours = data.get('ml_prediction_hours', 0) or 0
                
                print(f"      ✅ ${detail_price:,.2f} (k_quantity: {k_quantity:.3f})")
                if mat_price > 0 or work_price > 0 or total_time > 0:
                    print(f"         Material: ${mat_price:,.2f}, Work: ${work_price:,.2f}, Time: {total_time:.1f}h")
                if ml_hours > 0:
                    print(f"         ML Prediction: {ml_hours:.2f}h")
                
                return {
                    'file_type': file_type,
                    'calculation_method': 'ml_based',
                    'quantity': quantity,
                    'expected_k_quantity': expected_k_quantity,
                    'k_quantity': data.get('k_quantity', 0) or 0,
                    'detail_price': data.get('detail_price', 0) or 0,
                    'detail_price_one': data.get('detail_price_one', 0) or 0,
                    'total_price': data.get('total_price', 0) or 0,
                    'total_time': data.get('total_time', 0) or 0,
                    'mat_volume': data.get('mat_volume', 0) or 0,
                    'mat_weight': data.get('mat_weight', 0) or 0,
                    'mat_price': data.get('mat_price', 0) or 0,
                    'work_price': data.get('work_price', 0) or 0,
                    'work_time': data.get('work_time', 0) or 0,
                    'k_complexity': data.get('k_complexity', 0) or 0,
                    'k_cover': data.get('k_cover', 0) or 0,
                    'k_otk': data.get('k_otk', 0) or 0,
                    'manufacturing_cycle': data.get('manufacturing_cycle', 0) or 0,
                    'calculation_engine': data.get('calculation_engine', 'unknown'),
                    'ml_prediction_hours': data.get('ml_prediction_hours', 0) or 0,
                    'features_extracted': data.get('features_extracted', {}) or {},
                    'description': description,
                    'success': True
                }
            else:
                print(f"      ❌ Failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            return None
    
    def run_tests(self):
        """Run the selected tests"""
        self.print_header("Running Tests")
        
        total_tests = len(self.test_quantities) * len(self.calculation_methods)
        if self.selected_files:
            total_tests *= len(self.test_files_data)
        else:
            # Rule-based only, use default file type
            total_tests *= 1
        
        print(f"Running {total_tests} tests...")
        print(f"Quantities: {len(self.test_quantities)}")
        print(f"Methods: {', '.join(self.calculation_methods)}")
        if self.selected_files:
            print(f"Files: {len(self.test_files_data)} ({', '.join(self.test_files_data.keys())})")
        else:
            print("Files: Rule-based only (no file upload)")
        
        self.print_separator()
        
        current_test = 0
        
        # Determine file types to test
        if self.selected_files:
            file_types_to_test = list(self.test_files_data.keys())
        else:
            file_types_to_test = ["default"]  # For rule-based only
        
        for file_type in file_types_to_test:
            if file_type != "default":
                print(f"\n📁 Testing {file_type.upper()} files:")
            else:
                print(f"\n📁 Testing rule-based calculations:")
            
            for quantity, expected_k_quantity, description in self.test_quantities:
                current_test += 1
                print(f"\n[{current_test}/{total_tests}] Quantity {quantity} ({description}):")
                
                # Test rule-based if selected
                if "rule_based" in self.calculation_methods:
                    result = self.test_rule_based_calculation(file_type, quantity, expected_k_quantity, description)
                    if result:
                        self.results.append(result)
                
                # Test ML-based if selected and file available
                if "ml_based" in self.calculation_methods and file_type in self.test_files_data:
                    result = self.test_ml_based_calculation(file_type, quantity, expected_k_quantity, description)
                    if result:
                        self.results.append(result)
        
        print(f"\n✅ Testing completed! {len(self.results)} successful tests out of {total_tests} total tests.")
    
    def analyze_results(self):
        """Analyze and display results"""
        if not self.results:
            print("❌ No results to analyze")
            return
        
        self.print_header("Test Results Analysis")
        
        df = pd.DataFrame(self.results)
        
        # 1. Overall Success Rate
        print("\n📊 Overall Success Rate:")
        total_tests = len(df)
        successful_tests = len(df[df['success'] == True])
        print(f"  Total Tests: {total_tests}")
        print(f"  Successful: {successful_tests}")
        print(f"  Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        # 2. Quantity Discount Verification
        print("\n📈 Quantity Discount Verification:")
        correct_discounts = len(df[abs(df['k_quantity'] - df['expected_k_quantity']) < 0.001])
        print(f"  Correct Discounts: {correct_discounts}/{total_tests} ({correct_discounts/total_tests*100:.1f}%)")
        
        # 3. Detailed Price Analysis by Method
        print("\n💰 Detailed Price Analysis by Method:")
        for method in df['calculation_method'].unique():
            method_data = df[df['calculation_method'] == method]
            if not method_data.empty:
                print(f"\n  {method.replace('_', ' ').title()}:")
                print(f"    detail_price range: ${method_data['detail_price'].min():,.2f} - ${method_data['detail_price'].max():,.2f}")
                print(f"    detail_price_one consistency: {method_data['detail_price_one'].std():.2f} std dev")
                print(f"    total_price range: ${method_data['total_price'].min():,.2f} - ${method_data['total_price'].max():,.2f}")
                
                # Material costs
                if 'mat_price' in method_data.columns and method_data['mat_price'].notna().any() and method_data['mat_price'].sum() > 0:
                    print(f"    Material costs: ${method_data['mat_price'].min():,.2f} - ${method_data['mat_price'].max():,.2f}")
                
                # Work costs
                if 'work_price' in method_data.columns and method_data['work_price'].notna().any() and method_data['work_price'].sum() > 0:
                    print(f"    Work costs: ${method_data['work_price'].min():,.2f} - ${method_data['work_price'].max():,.2f}")
                
                # Time analysis
                if 'total_time' in method_data.columns and method_data['total_time'].notna().any() and method_data['total_time'].sum() > 0:
                    print(f"    Total time: {method_data['total_time'].min():.2f} - {method_data['total_time'].max():.2f} hours")
                
                # Manufacturing cycle
                if 'manufacturing_cycle' in method_data.columns and method_data['manufacturing_cycle'].notna().any() and method_data['manufacturing_cycle'].sum() > 0:
                    print(f"    Manufacturing cycle: {method_data['manufacturing_cycle'].min():.1f} - {method_data['manufacturing_cycle'].max():.1f} days")
                
                # Coefficients
                if 'k_quantity' in method_data.columns:
                    print(f"    k_quantity range: {method_data['k_quantity'].min():.3f} - {method_data['k_quantity'].max():.3f}")
                if 'k_cover' in method_data.columns and method_data['k_cover'].notna().any() and method_data['k_cover'].sum() > 0:
                    print(f"    k_cover range: {method_data['k_cover'].min():.3f} - {method_data['k_cover'].max():.3f}")
                if 'k_otk' in method_data.columns and method_data['k_otk'].notna().any() and method_data['k_otk'].sum() > 0:
                    print(f"    k_otk range: {method_data['k_otk'].min():.3f} - {method_data['k_otk'].max():.3f}")
                
                # ML-specific fields
                if method == 'ml_based' and 'ml_prediction_hours' in method_data.columns:
                    ml_hours = method_data['ml_prediction_hours'].iloc[0] if not method_data.empty else 0
                    print(f"    ML prediction: {ml_hours:.2f} hours (consistent)")
        
        # 4. File Type Comparison (if multiple file types)
        if 'file_type' in df.columns and df['file_type'].nunique() > 1:
            print("\n📁 File Type Comparison:")
            for file_type in df['file_type'].unique():
                file_data = df[df['file_type'] == file_type]
                if not file_data.empty:
                    print(f"  {file_type.upper()}: ${file_data['detail_price'].mean():,.2f} average")
        
        # 5. Method Comparison (if both methods tested)
        if df['calculation_method'].nunique() > 1:
            print("\n🔄 Method Comparison:")
            rule_data = df[df['calculation_method'] == 'rule_based']
            ml_data = df[df['calculation_method'] == 'ml_based']
            if not rule_data.empty and not ml_data.empty:
                rule_avg = rule_data['detail_price'].mean()
                ml_avg = ml_data['detail_price'].mean()
                diff_pct = ((ml_avg - rule_avg) / rule_avg * 100) if rule_avg > 0 else 0
                print(f"  Rule-based average: ${rule_avg:,.2f}")
                print(f"  ML-based average: ${ml_avg:,.2f}")
                print(f"  Difference: {diff_pct:+.1f}%")
        
        # 6. Detailed Results Table
        print("\n📊 Detailed Results Table:")
        print("File | Method    | Qty | detail_price | detail_price_one | total_price | k_quantity | mat_price | work_price | total_time | cycle")
        print("-" * 100)
        
        for _, row in df.iterrows():
            file_type = row.get('file_type', 'default')[:4].upper()
            method = row['calculation_method'][:4]
            qty = row['quantity']
            detail_price = f"${row['detail_price']:,.0f}"
            detail_price_one = f"${row['detail_price_one']:,.0f}"
            total_price = f"${row['total_price']:,.0f}"
            k_quantity = f"{row['k_quantity']:.3f}"
            mat_price_val = row.get('mat_price', 0) or 0
            work_price_val = row.get('work_price', 0) or 0
            total_time_val = row.get('total_time', 0) or 0
            cycle_val = row.get('manufacturing_cycle', 0) or 0
            
            mat_price = f"${mat_price_val:,.0f}" if mat_price_val > 0 else "N/A"
            work_price = f"${work_price_val:,.0f}" if work_price_val > 0 else "N/A"
            total_time = f"{total_time_val:.1f}h" if total_time_val > 0 else "N/A"
            cycle = f"{cycle_val:.1f}d" if cycle_val > 0 else "N/A"
            
            print(f"{file_type:4} | {method:8} | {qty:3} | {detail_price:12} | {detail_price_one:15} | {total_price:10} | {k_quantity:10} | {mat_price:9} | {work_price:10} | {total_time:9} | {cycle:5}")
        
        # 7. Key Insights
        print("\n🎯 Key Insights:")
        
        # Discount accuracy
        discount_accuracy = correct_discounts / total_tests * 100
        print(f"  • Discount accuracy: {discount_accuracy:.1f}%")
        
        # detail_price_one consistency
        if 'detail_price_one' in df.columns:
            detail_price_one_cv = (df['detail_price_one'].std() / df['detail_price_one'].mean() * 100) if df['detail_price_one'].mean() > 0 else 0
            print(f"  • detail_price_one consistency: {detail_price_one_cv:.2f}% CV")
        
        # Price range
        price_range = df['detail_price'].max() - df['detail_price'].min()
        print(f"  • Price range: ${df['detail_price'].min():,.2f} - ${df['detail_price'].max():,.2f} (${price_range:,.2f})")
        
        # Material cost analysis
        if 'mat_price' in df.columns and df['mat_price'].notna().any() and df['mat_price'].sum() > 0:
            mat_cost_range = df['mat_price'].max() - df['mat_price'].min()
            print(f"  • Material cost range: ${df['mat_price'].min():,.2f} - ${df['mat_price'].max():,.2f} (${mat_cost_range:,.2f})")
        
        # Work cost analysis
        if 'work_price' in df.columns and df['work_price'].notna().any() and df['work_price'].sum() > 0:
            work_cost_range = df['work_price'].max() - df['work_price'].min()
            print(f"  • Work cost range: ${df['work_price'].min():,.2f} - ${df['work_price'].max():,.2f} (${work_cost_range:,.2f})")
        
        # Time analysis
        if 'total_time' in df.columns and df['total_time'].notna().any() and df['total_time'].sum() > 0:
            time_range = df['total_time'].max() - df['total_time'].min()
            print(f"  • Time range: {df['total_time'].min():.1f} - {df['total_time'].max():.1f} hours ({time_range:.1f}h)")
        
        # Manufacturing cycle analysis
        if 'manufacturing_cycle' in df.columns and df['manufacturing_cycle'].notna().any() and df['manufacturing_cycle'].sum() > 0:
            cycle_range = df['manufacturing_cycle'].max() - df['manufacturing_cycle'].min()
            print(f"  • Manufacturing cycle: {df['manufacturing_cycle'].min():.1f} - {df['manufacturing_cycle'].max():.1f} days ({cycle_range:.1f}d)")
    
    def save_results(self):
        """Save results to file"""
        if not self.results:
            print("❌ No results to save")
            return
        
        filename = "interactive_pricing_results.json"
        results_data = {
            'test_summary': {
                'total_tests': len(self.results),
                'file_types_tested': list(set(r.get('file_type', 'default') for r in self.results)),
                'calculation_methods_tested': list(set(r['calculation_method'] for r in self.results)),
                'quantities_tested': sorted(list(set(r['quantity'] for r in self.results)))
            },
            'results': self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")
    
    def main_menu(self):
        """Main interactive menu"""
        self.clear_screen()
        print("🚀 Interactive Pricing Tester")
        print("Test quantity-based pricing across different file types and calculation methods")
        
        while True:
            # Step 1: Select files
            if not self.select_files():
                return
            
            # Step 2: Select calculation methods
            if not self.select_calculation_methods():
                return
            
            # Step 3: Select quantities
            if not self.select_quantities():
                return
            
            # Step 4: Load files
            if not self.load_selected_files():
                return
            
            # Step 5: Run tests
            self.run_tests()
            
            # Step 6: Analyze results
            self.analyze_results()
            
            # Step 7: Save results
            save_choice = self.get_user_input("Save results to file? (y/n)", ["y", "n", "yes", "no"])
            if save_choice.lower() in ["y", "yes"]:
                self.save_results()
            
            # Step 8: Continue or exit
            continue_choice = self.get_user_input("Run another test? (y/n)", ["y", "n", "yes", "no"])
            if continue_choice.lower() not in ["y", "yes"]:
                break
            
            # Reset for next test
            self.results = []
            self.test_files_data = {}
            self.selected_files = []
            self.calculation_methods = []
        
        print("\n👋 Thank you for using the Interactive Pricing Tester!")

def main():
    """Main entry point"""
    try:
        tester = InteractivePricingTester()
        tester.main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
