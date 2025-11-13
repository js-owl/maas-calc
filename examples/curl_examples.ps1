# Manufacturing Calculations API - PowerShell Examples
# This script provides PowerShell examples for testing the API endpoints

$API_BASE = "http://localhost:7000"
$API_ENDPOINT = "$API_BASE/calculate-price"

Write-Host "🚀 Manufacturing Calculations API - PowerShell Examples" -ForegroundColor Green
Write-Host "API Base URL: $API_BASE" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan

# Health Check
Write-Host "1. Health Check" -ForegroundColor Magenta
Write-Host "---------------" -ForegroundColor Magenta
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/health" -Method GET -ContentType "application/json"
    Write-Host "✅ SUCCESS" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 3
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Services List
Write-Host "2. Services List" -ForegroundColor Magenta
Write-Host "----------------" -ForegroundColor Magenta
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/services" -Method GET -ContentType "application/json"
    Write-Host "✅ SUCCESS" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 3
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Materials List
Write-Host "3. Materials List" -ForegroundColor Magenta
Write-Host "-----------------" -ForegroundColor Magenta
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/materials" -Method GET -ContentType "application/json"
    Write-Host "✅ SUCCESS" -ForegroundColor Green
    Write-Host "Total Materials: $($response.materials.Count)"
    Write-Host "Sample Materials:"
    $response.materials[0..2] | ForEach-Object { Write-Host "  - $($_.id): $($_.label)" }
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# 3D Printing Calculation
Write-Host "4. 3D Printing Calculation" -ForegroundColor Magenta
Write-Host "--------------------------" -ForegroundColor Magenta
$printingData = @{
    service_id = "printing"
    file_id = "powershell-test-printing-001"
    dimensions = @{
        length = 100.0
        width = 50.0
        thickness = 10.0
    }
    quantity = 5
    material_id = "PA11"
    material_form = "powder"
    n_dimensions = 1
    k_type = 1.0
    k_process = 1.0
    cover_id = @("1")
    k_otk = 1.0
    k_cert = @("a", "f")
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri $API_ENDPOINT -Method POST -Body $printingData -ContentType "application/json"
    Write-Host "✅ SUCCESS" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 3
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# CNC Milling Calculation
Write-Host "5. CNC Milling Calculation" -ForegroundColor Magenta
Write-Host "-------------------------" -ForegroundColor Magenta
$millingData = @{
    service_id = "cnc-milling"
    file_id = "powershell-test-cnc-milling-001"
    dimensions = @{
        length = 80.0
        width = 60.0
        thickness = 15.0
    }
    quantity = 10
    material_id = "alum_D16"
    material_form = "sheet"
    tolerance_id = "1"
    finish_id = "1"
    cover_id = @("1")
    k_otk = 1.0
    cnc_complexity = "medium"
    cnc_setup_time = 2.0
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri $API_ENDPOINT -Method POST -Body $millingData -ContentType "application/json"
    Write-Host "✅ SUCCESS" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 3
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# CNC Lathe Calculation
Write-Host "6. CNC Lathe Calculation" -ForegroundColor Magenta
Write-Host "------------------------" -ForegroundColor Magenta
$latheData = @{
    service_id = "cnc-lathe"
    file_id = "powershell-test-cnc-lathe-001"
    dimensions = @{
        length = 120.0
        width = 25.0
        thickness = 25.0
    }
    quantity = 8
    material_id = "alum_AMC"
    material_form = "rod"
    tolerance_id = "2"
    finish_id = "3"
    cover_id = @("2")
    k_otk = 1.0
    cnc_complexity = "high"
    cnc_setup_time = 3.0
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri $API_ENDPOINT -Method POST -Body $latheData -ContentType "application/json"
    Write-Host "✅ SUCCESS" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 3
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Painting Calculation
Write-Host "7. Painting Calculation" -ForegroundColor Magenta
Write-Host "-----------------------" -ForegroundColor Magenta
$paintingData = @{
    service_id = "painting"
    file_id = "powershell-test-painting-001"
    dimensions = @{
        length = 100.0
        width = 80.0
        thickness = 5.0
    }
    quantity = 15
    material_id = "alum_D16"
    material_form = "sheet"
    paint_type = "acrylic"
    paint_prepare = "a"
    paint_primer = "b"
    paint_lakery = "a"
    control_type = "1"
    k_cert = @("a", "f", "g")
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri $API_ENDPOINT -Method POST -Body $paintingData -ContentType "application/json"
    Write-Host "✅ SUCCESS" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 3
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Error Case - Invalid Service
Write-Host "8. Error Case - Invalid Service" -ForegroundColor Magenta
Write-Host "-------------------------------" -ForegroundColor Magenta
$errorData = @{
    service_id = "invalid-service"
    file_id = "powershell-error-test-001"
    dimensions = @{
        length = 10.0
        width = 10.0
        thickness = 10.0
    }
    quantity = 1
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri $API_ENDPOINT -Method POST -Body $errorData -ContentType "application/json"
    Write-Host "✅ SUCCESS" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 3
} catch {
    Write-Host "❌ EXPECTED ERROR: $($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "✅ All PowerShell examples completed!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
