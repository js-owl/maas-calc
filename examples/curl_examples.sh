#!/bin/bash

# Manufacturing Calculations API - cURL Examples
# This script provides cURL examples for testing the API endpoints

API_BASE="http://localhost:7000"
API_ENDPOINT="$API_BASE/calculate-price"

echo "🚀 Manufacturing Calculations API - cURL Examples"
echo "API Base URL: $API_BASE"
echo "=================================================="

# Health Check
echo "1. Health Check"
echo "---------------"
curl -X GET "$API_BASE/health" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n\n"

# Services List
echo "2. Services List"
echo "----------------"
curl -X GET "$API_BASE/services" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n\n"

# Materials List
echo "3. Materials List"
echo "-----------------"
curl -X GET "$API_BASE/materials" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n\n"

# Coefficients List
echo "4. Coefficients List"
echo "--------------------"
curl -X GET "$API_BASE/coefficients" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n\n"

# 3D Printing Calculation
echo "5. 3D Printing Calculation"
echo "--------------------------"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "printing",
    "file_id": "curl-test-printing-001",
    "dimensions": {
      "length": 100.0,
      "width": 50.0,
      "thickness": 10.0
    },
    "quantity": 5,
    "material_id": "PA11",
    "material_form": "powder",
    "n_dimensions": 1,
    "k_type": 1.0,
    "k_process": 1.0,
    "cover_id": ["1"],
    "k_otk": 1.0,
    "k_cert": ["a", "f"]
  }' \
  -w "\nStatus: %{http_code}\n\n"

# CNC Milling Calculation
echo "6. CNC Milling Calculation"
echo "-------------------------"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "cnc-milling",
    "file_id": "curl-test-cnc-milling-001",
    "dimensions": {
      "length": 80.0,
      "width": 60.0,
      "thickness": 15.0
    },
    "quantity": 10,
    "material_id": "alum_D16",
    "material_form": "sheet",
    "tolerance_id": "1",
    "finish_id": "1",
    "cover_id": ["1"],
    "k_otk": 1.0,
    "cnc_complexity": "medium",
    "cnc_setup_time": 2.0
  }' \
  -w "\nStatus: %{http_code}\n\n"

# CNC Lathe Calculation
echo "7. CNC Lathe Calculation"
echo "------------------------"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "cnc-lathe",
    "file_id": "curl-test-cnc-lathe-001",
    "dimensions": {
      "length": 120.0,
      "width": 25.0,
      "thickness": 25.0
    },
    "quantity": 8,
    "material_id": "alum_AMC",
    "material_form": "rod",
    "tolerance_id": "2",
    "finish_id": "3",
    "cover_id": ["2"],
    "k_otk": 1.0,
    "cnc_complexity": "high",
    "cnc_setup_time": 3.0
  }' \
  -w "\nStatus: %{http_code}\n\n"

# Painting Calculation
echo "8. Painting Calculation"
echo "-----------------------"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "painting",
    "file_id": "curl-test-painting-001",
    "dimensions": {
      "length": 100.0,
      "width": 80.0,
      "thickness": 5.0
    },
    "quantity": 15,
    "material_id": "alum_D16",
    "material_form": "sheet",
    "paint_type": "acrylic",
    "paint_prepare": "a",
    "paint_primer": "b",
    "paint_lakery": "a",
    "control_type": "1",
    "k_cert": ["a", "f", "g"]
  }' \
  -w "\nStatus: %{http_code}\n\n"

# Error Case - Invalid Service
echo "9. Error Case - Invalid Service"
echo "-------------------------------"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "invalid-service",
    "file_id": "curl-error-test-001",
    "dimensions": {
      "length": 10.0,
      "width": 10.0,
      "thickness": 10.0
    },
    "quantity": 1
  }' \
  -w "\nStatus: %{http_code}\n\n"

# Error Case - Invalid Material
echo "10. Error Case - Invalid Material"
echo "--------------------------------"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "printing",
    "file_id": "curl-error-test-002",
    "dimensions": {
      "length": 10.0,
      "width": 10.0,
      "thickness": 10.0
    },
    "quantity": 1,
    "material_id": "invalid_material",
    "material_form": "powder"
  }' \
  -w "\nStatus: %{http_code}\n\n"

echo "✅ All cURL examples completed!"
echo "=================================================="
