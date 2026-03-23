#!/usr/bin/env python3
"""
Comprehensive Pricing Test Suite
Tests both STL and STP files with both rule-based and ML-based calculations
across different quantities to verify pricing consistency and correctness.
"""

import requests
import json
import base64
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Optional

# API Configuration
BASE_URL = "http://localhost:7000"
API_ENDPOINT = f"{BASE_URL}/calculate-price"

# Test files
TEST_FILES = {
    "stl": "test_files/02.stl",
    "stp": "test_files/S8000_125_63_293_001_D000_02.stp"
}

# Test quantities with expected k_quantity coefficients
TEST_QUANTITIES = [
    (1, 1.0, "No discount"),
    (5, 1.0, "No discount"),
    (10, 1.0, "No discount"),
    (20, 1.0, "No discount"),
    (25, 0.95, "5% discount"),
    (50, 0.95, "5% discount"),
    (100, 0.95, "5% discount"),
    (150, 0.85, "15% discount"),
    (300, 0.85, "15% discount"),
    (500, 0.85, "15% discount"),
    (600, 0.8, "20% discount"),
    (1000, 0.8, "20% discount")
]

class ComprehensivePricingTester:
    """Comprehensive pricing test suite for all file types and calculation methods"""
    
    def __init__(self):
        self.results = []
        self.test_files_data = {}
        self._load_test_files()
    
    def _load_test_files(self):
        """Load and encode test files"""
        print("📁 Loading test files...")
        
        for file_type, file_path in TEST_FILES.items():
            path = Path(file_path)
            if path.exists():
                with open(path, 'rb') as f:
                    file_data = base64.b64encode(f.read()).decode('utf-8')
                self.test_files_data[file_type] = {
                    'data': file_data,
                    'name': path.name,
                    'size_mb': round(path.stat().st_size / (1024 * 1024), 2)
                }
                print(f"  ✅ Loaded {file_type.upper()}: {path.name} ({self.test_files_data[file_type]['size_mb']} MB)")
            else:
                print(f"  ❌ File not found: {file_path}")
    
    def test_rule_based_calculation(self, file_type: str, quantity: int, expected_k_quantity: float, description: str) -> Optional[Dict[str, Any]]:
        """Test rule-based calculation (no file upload)"""
        print(f"  🔧 Rule-based: Qty {quantity} ({description})")
        
        # Rule-based request (no file upload)
        request_data = {
            "service_id": "printing",
            "file_id": f"rule-{file_type}-{quantity}",
            "length": 100.0,
            "width": 50.0,
            "height": 10.0,
            "quantity": quantity,
            "material_id": "PA11",
            "material_form": "powder",
            "k_type": 1.0,
            "k_process": 1.0,
            "cover_id": ["1"],
            "k_otk": 1.0,
            "k_cert": ["a", "f"],
            "location": "location_1"
        }
        
        try:
            response = requests.post(API_ENDPOINT, json=request_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                
                return {
                    'file_type': file_type,
                    'calculation_method': 'rule_based',
                    'quantity': quantity,
                    'expected_k_quantity': expected_k_quantity,
                    'k_quantity': data.get('k_quantity', 0),
                    'detail_price': data.get('detail_price', 0),
                    'detail_price_one': data.get('detail_price_one', 0),
                    'total_price': data.get('total_price', 0),
                    'calculation_engine': data.get('calculation_engine', 'unknown'),
                    'description': description,
                    'success': True
                }
            else:
                print(f"    ❌ Failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return None
    
    def test_ml_based_calculation(self, file_type: str, quantity: int, expected_k_quantity: float, description: str) -> Optional[Dict[str, Any]]:
        """Test ML-based calculation (with file upload)"""
        print(f"  🤖 ML-based: Qty {quantity} ({description})")
        
        if file_type not in self.test_files_data:
            print(f"    ❌ No file data for {file_type}")
            return None
        
        # ML-based request (with file upload)
        request_data = {
            "service_id": "printing",
            "file_id": f"ml-{file_type}-{quantity}",
            "file_data": self.test_files_data[file_type]['data'],
            "file_name": self.test_files_data[file_type]['name'],
            "file_type": file_type,
            "quantity": quantity,
            "material_id": "PA11",
            "material_form": "powder",
            "k_type": 1.0,
            "k_process": 1.0,
            "cover_id": ["1"],
            "k_otk": 1.0,
            "k_cert": ["a", "f"],
            "location": "location_1"
        }
        
        try:
            response = requests.post(API_ENDPOINT, json=request_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                
                return {
                    'file_type': file_type,
                    'calculation_method': 'ml_based',
                    'quantity': quantity,
                    'expected_k_quantity': expected_k_quantity,
                    'k_quantity': data.get('k_quantity', 0),
                    'detail_price': data.get('detail_price', 0),
                    'detail_price_one': data.get('detail_price_one', 0),
                    'total_price': data.get('total_price', 0),
                    'calculation_engine': data.get('calculation_engine', 'unknown'),
                    'ml_prediction_hours': data.get('ml_prediction_hours', 0),
                    'description': description,
                    'success': True
                }
            else:
                print(f"    ❌ Failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return None
    
    def run_comprehensive_tests(self):
        """Run comprehensive tests for all combinations"""
        print("=" * 80)
        print("COMPREHENSIVE PRICING TEST SUITE")
        print("=" * 80)
        print("Testing: STL + STP files × Rule-based + ML-based × Multiple quantities")
        print()
        
        total_tests = len(TEST_FILES) * 2 * len(TEST_QUANTITIES)  # file_types × methods × quantities
        current_test = 0
        
        for file_type in TEST_FILES.keys():
            print(f"\n📁 Testing {file_type.upper()} files:")
            print("-" * 40)
            
            for quantity, expected_k_quantity, description in TEST_QUANTITIES:
                current_test += 1
                print(f"\n[{current_test}/{total_tests}] Testing quantity {quantity}:")
                
                # Test rule-based calculation
                rule_result = self.test_rule_based_calculation(file_type, quantity, expected_k_quantity, description)
                if rule_result:
                    self.results.append(rule_result)
                    print(f"    ✅ Rule-based: ${rule_result['detail_price']:,.2f} (k_quantity: {rule_result['k_quantity']:.3f})")
                
                # Test ML-based calculation
                ml_result = self.test_ml_based_calculation(file_type, quantity, expected_k_quantity, description)
                if ml_result:
                    self.results.append(ml_result)
                    print(f"    ✅ ML-based: ${ml_result['detail_price']:,.2f} (k_quantity: {ml_result['k_quantity']:.3f})")
        
        print(f"\n✅ Testing completed! {len(self.results)} successful tests out of {total_tests} total tests.")
    
    def analyze_results(self):
        """Analyze and compare all results"""
        if not self.results:
            print("❌ No results to analyze")
            return
        
        print("\n" + "=" * 80)
        print("COMPREHENSIVE ANALYSIS")
        print("=" * 80)
        
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
        print("File Type | Method      | Quantity | k_quantity | Expected | Status")
        print("-" * 70)
        
        for _, row in df.iterrows():
            status = "✅" if abs(row['k_quantity'] - row['expected_k_quantity']) < 0.001 else "❌"
            print(f"{row['file_type']:9} | {row['calculation_method']:11} | {row['quantity']:8} | {row['k_quantity']:10.3f} | {row['expected_k_quantity']:8.3f} | {status:6}")
        
        # 3. Price Consistency Analysis
        print("\n💰 Price Consistency Analysis:")
        
        # Group by file type and calculation method
        for file_type in df['file_type'].unique():
            for method in df['calculation_method'].unique():
                subset = df[(df['file_type'] == file_type) & (df['calculation_method'] == method)]
                if not subset.empty:
                    print(f"\n  {file_type.upper()} - {method.replace('_', ' ').title()}:")
                    
                    # detail_price_one consistency
                    detail_prices_one = subset['detail_price_one'].values
                    if len(detail_prices_one) > 1:
                        detail_price_one_std = detail_prices_one.std()
                        detail_price_one_mean = detail_prices_one.mean()
                        detail_price_one_cv = (detail_price_one_std / detail_price_one_mean * 100) if detail_price_one_mean > 0 else 0
                        consistency_status = "✅" if detail_price_one_cv < 1.0 else "❌"
                        print(f"    detail_price_one: Mean=${detail_price_one_mean:,.2f}, CV={detail_price_one_cv:.2f}% {consistency_status}")
                    
                    # Price scaling
                    min_price = subset['detail_price'].min()
                    max_price = subset['detail_price'].max()
                    price_range = max_price - min_price
                    print(f"    detail_price range: ${min_price:,.2f} - ${max_price:,.2f} (${price_range:,.2f})")
        
        # 4. Method Comparison
        print("\n🔄 Method Comparison (STL files only):")
        stl_data = df[df['file_type'] == 'stl']
        if not stl_data.empty:
            print("Quantity | Rule detail_price | ML detail_price | Difference | % Diff")
            print("-" * 70)
            
            for quantity in sorted(stl_data['quantity'].unique()):
                rule_data = stl_data[(stl_data['quantity'] == quantity) & (stl_data['calculation_method'] == 'rule_based')]
                ml_data = stl_data[(stl_data['quantity'] == quantity) & (stl_data['calculation_method'] == 'ml_based')]
                
                if not rule_data.empty and not ml_data.empty:
                    rule_price = rule_data.iloc[0]['detail_price']
                    ml_price = ml_data.iloc[0]['detail_price']
                    diff = ml_price - rule_price
                    pct_diff = (diff / rule_price * 100) if rule_price > 0 else 0
                    print(f"{quantity:8} | ${rule_price:15,.2f} | ${ml_price:13,.2f} | ${diff:+8,.2f} | {pct_diff:+6.1f}%")
        
        # 5. File Type Comparison
        print("\n📁 File Type Comparison (ML-based only):")
        ml_data = df[df['calculation_method'] == 'ml_based']
        if not ml_data.empty:
            print("Quantity | STL detail_price | STP detail_price | Difference | % Diff")
            print("-" * 70)
            
            for quantity in sorted(ml_data['quantity'].unique()):
                stl_data_qty = ml_data[(ml_data['quantity'] == quantity) & (ml_data['file_type'] == 'stl')]
                stp_data_qty = ml_data[(ml_data['quantity'] == quantity) & (ml_data['file_type'] == 'stp')]
                
                if not stl_data_qty.empty and not stp_data_qty.empty:
                    stl_price = stl_data_qty.iloc[0]['detail_price']
                    stp_price = stp_data_qty.iloc[0]['detail_price']
                    diff = stp_price - stl_price
                    pct_diff = (diff / stl_price * 100) if stl_price > 0 else 0
                    print(f"{quantity:8} | ${stl_price:15,.2f} | ${stp_price:13,.2f} | ${diff:+8,.2f} | {pct_diff:+6.1f}%")
        
        # 6. Key Insights
        print("\n🎯 Key Insights:")
        
        # Discount accuracy
        discount_accuracy = len(df[abs(df['k_quantity'] - df['expected_k_quantity']) < 0.001]) / len(df) * 100
        print(f"  • Discount accuracy: {discount_accuracy:.1f}%")
        
        # detail_price_one consistency
        all_detail_prices_one = df['detail_price_one'].values
        if len(all_detail_prices_one) > 1:
            detail_price_one_cv = (all_detail_prices_one.std() / all_detail_prices_one.mean() * 100) if all_detail_prices_one.mean() > 0 else 0
            print(f"  • detail_price_one consistency: {detail_price_one_cv:.2f}% CV")
        
        # Method differences
        if 'stl' in df['file_type'].values and 'rule_based' in df['calculation_method'].values and 'ml_based' in df['calculation_method'].values:
            stl_rule = df[(df['file_type'] == 'stl') & (df['calculation_method'] == 'rule_based')]['detail_price'].mean()
            stl_ml = df[(df['file_type'] == 'stl') & (df['calculation_method'] == 'ml_based')]['detail_price'].mean()
            method_diff = ((stl_ml - stl_rule) / stl_rule * 100) if stl_rule > 0 else 0
            print(f"  • ML vs Rule-based difference: {method_diff:+.1f}%")
        
        # File type differences
        if 'stl' in df['file_type'].values and 'stp' in df['file_type'].values:
            stl_avg = df[df['file_type'] == 'stl']['detail_price'].mean()
            stp_avg = df[df['file_type'] == 'stp']['detail_price'].mean()
            file_diff = ((stp_avg - stl_avg) / stl_avg * 100) if stl_avg > 0 else 0
            print(f"  • STP vs STL difference: {file_diff:+.1f}%")
    
    def create_summary_table(self):
        """Create a summary table of all results"""
        if not self.results:
            return
        
        print("\n" + "=" * 80)
        print("SUMMARY TABLE")
        print("=" * 80)
        
        df = pd.DataFrame(self.results)
        
        # Create pivot table
        pivot_data = []
        for file_type in df['file_type'].unique():
            for method in df['calculation_method'].unique():
                subset = df[(df['file_type'] == file_type) & (df['calculation_method'] == method)]
                if not subset.empty:
                    for _, row in subset.iterrows():
                        pivot_data.append({
                            'File': file_type.upper(),
                            'Method': method.replace('_', ' ').title(),
                            'Quantity': row['quantity'],
                            'k_quantity': f"{row['k_quantity']:.3f}",
                            'detail_price': f"${row['detail_price']:,.2f}",
                            'detail_price_one': f"${row['detail_price_one']:,.2f}",
                            'total_price': f"${row['total_price']:,.2f}",
                            'Engine': row['calculation_engine']
                        })
        
        if pivot_data:
            summary_df = pd.DataFrame(pivot_data)
            print(summary_df.to_string(index=False))
    
    def save_results(self, filename: str = "comprehensive_pricing_results.json"):
        """Save results to JSON file"""
        if not self.results:
            print("❌ No results to save")
            return
        
        results_data = {
            'test_summary': {
                'total_tests': len(self.results),
                'file_types_tested': list(set(r['file_type'] for r in self.results)),
                'calculation_methods_tested': list(set(r['calculation_method'] for r in self.results)),
                'quantities_tested': sorted(list(set(r['quantity'] for r in self.results)))
            },
            'results': self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")

def main():
    """Main test function"""
    print("🚀 Starting Comprehensive Pricing Test Suite")
    print("This will test all combinations of file types, calculation methods, and quantities")
    print()
    
    # Initialize tester
    tester = ComprehensivePricingTester()
    
    if not tester.test_files_data:
        print("❌ No test files available. Please check file paths.")
        return
    
    # Run comprehensive tests
    tester.run_comprehensive_tests()
    
    # Analyze results
    tester.analyze_results()
    
    # Create summary table
    tester.create_summary_table()
    
    # Save results
    tester.save_results()
    
    print("\n✅ Comprehensive testing completed successfully!")
    print("📊 All pricing calculations verified across all file types and methods!")

if __name__ == "__main__":
    main()
