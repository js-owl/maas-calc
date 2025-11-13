# main.py

import cadquery as cq
from collections import Counter
from joblib import load
from OCP.Bnd import Bnd_OBB
from OCP.BRepBndLib import BRepBndLib
import pandas as pd
from xgboost import XGBRegressor
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from stl import mesh
import numpy
import numpy as np
import os
import json
import math
import trimesh
from typing import List, Optional, Union, Dict, Any
from enum import Enum
import logging
from datetime import datetime
from constants import (
    APP_VERSION,
    MATERIALS,
    PAINT_COEFFICIENTS,
    MATERIAL_PREP,
    PROCESS_COEFFICIENTS,
    FINISH,
    COVER,
    TOLERANCE,
    CERT_COSTS,
    COST_STRUCTURE,
    MACHINES,
    FEATURES_EXAMPLE_FROM_STEP,
    FEATURES_EXAMPLE_FROM_STL
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Or DEBUG, TRACE
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

ENCODER_PATH = r".\models\ohe_v0.01.joblib"
ML_MODEL_PATH = r".\models\base_model_xgb_v0.01.json"

# 1. Initialize the FastAPI app
app = FastAPI(
    title="STL & STP Manufacturing Calculations API",
    description="A comprehensive FastAPI application that provides STL and STP file processing capabilities and manufacturing cost calculations for 3D printing, milling, CNC, and painting operations. Supports both STL and STP file formats with advanced geometric analysis and manufacturing complexity assessment.",
    version=APP_VERSION,
    contact={
        "name": "API Support",
        "url": "https://github.com/your-repo/stl-api",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# CORS configuration from environment variables
cors_origins = os.getenv("CORS_ORIGINS", '["*"]')
cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
cors_allow_methods = os.getenv("CORS_ALLOW_METHODS", '["*"]')
cors_allow_headers = os.getenv("CORS_ALLOW_HEADERS", '["*"]')

# Parse JSON strings from environment variables
try:
    cors_origins = json.loads(cors_origins)
    cors_allow_methods = json.loads(cors_allow_methods)
    cors_allow_headers = json.loads(cors_allow_headers)
except json.JSONDecodeError:
    # Fallback to default values if JSON parsing fails
    cors_origins = ["*"]
    cors_allow_methods = ["*"]
    cors_allow_headers = ["*"]

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=cors_allow_methods,
    allow_headers=cors_allow_headers,
)

# # 2. Define the response models for STL processing

# 3. Define the models for manufacturing calculations
class MaterialForm(str, Enum):
    ROD = "rod"
    PLATE = "plate"
    SHEET = "sheet"
    BAR = "bar"
    TUBE = "tube"
    POWDER = "powder"

class PaintType(str, Enum):
    EPOXY = "epoxy"
    ACRYLIC = "acrylic"
    POLYURETHANE = "polyurethane"

class ControlType(str, Enum):
    TYPE_1 = "1"
    TYPE_2 = "2"
    TYPE_3 = "3"

class Service_type(str):
    LATHE = "cnc-lathe"
    MILLING = "cnc-milling"
    PRINTING = "printing"
    PAINTING = "painting"

# Base request model for manufacturing
class BaseRequest(BaseModel):
    quantity: int = Field(..., ge=1, description="Quantity of items")
    material_id: str = Field(examples=["alum_D16"], description="Material grade id (e.g., alum_6061)")
    material_form: MaterialForm = Field(examples=[MaterialForm.SHEET], description="Stock form (rod, plate, sheet, bar, tube)")

#3D Printing Request
class PrintingRequest(BaseRequest):
   length: float = Field(..., gt=0, description="Length in mm")
   width: float = Field(..., gt=0, description="Width in mm")
   thickness: float = Field(..., gt=0, description="Thickness in mm")
   k_type: float = Field(default=1.0, ge=0, le=2, description="Type coefficient")
   k_process: float = Field(default=1.0, ge=0, le=2, description="Process coefficient")
   id_cover: List[str] = Field(default=["1"], description="Cover id (empty list = no cover processing)")
   k_otk: str = Field(default="1", description="OTK coefficient")
   k_cert: List[str] = Field(default=["a", "f"], description="Certification types")
   n_dimensions: int = Field(default=1, ge=1, description="Dimensions number")

#Milling Request
class CNCMillingRequest(BaseRequest):
   length: float = Field(..., gt=0, description="Length in mm")
   width: float = Field(..., gt=0, description="Width in mm")
   thickness: float = Field(..., gt=0, description="Thickness in mm")
   id_tolerance: str = Field(default="1", description="Tolerance id")
   id_finish: str = Field(default="1", description="Finish id")
   id_cover: List[str] = Field(default=["1"], description="Cover id (empty list = no cover processing)")
   k_otk: str = Field(default="1", description="OTK coefficient")
   k_cert: List[str] = Field(default=["a", "f"], description="Certification types")
   n_dimensions: int = Field(default=1, ge=1, description="Dimensions number")

# CNC Request
class CNCLatheRequest(BaseRequest):
    length: float = Field(..., gt=0, description="Length in mm")
    dia: float = Field(..., gt=0, description="Diameter in mm")
    id_tolerance: str = Field(default="1", description="Tolerance id")
    id_finish: str = Field(default="1", description="Finish id")
    id_cover: List[str] = Field(default=["1"], description="Cover id (empty list = no cover processing)")
    k_otk: str = Field(default="1", description="OTK coefficient")
    k_cert: List[str] = Field(default=["a", "f"], description="Certification types")
    n_dimensions: int = Field(default=1, ge=1, description="Dimensions number")

#Painting Request
class PaintingRequest(BaseRequest):
   paint_area: float = Field(..., gt=0, description="Paint area in sq cm")
   paint_type: PaintType = Field(..., description="Type of paint")
   paint_color: str = Field(..., description="Paint color code")
   control_type: ControlType = Field(default=ControlType.TYPE_1, description="Control type")
   paint_lakery: str = Field(default="a", description="Lakery type")
   paint_prepare: str = Field(default="a", description="Preparation type")
   paint_primer: str = Field(default="b", description="Primer type")
   k_cert: List[str] = Field(default=["a", "f", "g", "d"], description="Certificate types")

# Request for step analyze
class StepRequest(BaseRequest):
    location: str = Field(default="location_1", description="Location of manufacture (see constants.py)")
    service_id: str = Field(examples=[Service_type.MILLING], description="Type of paint")
    id_cover: List[str] = Field(default=["1"], description="Cover id (empty list = no cover processing)")
    k_otk: str = Field(default="1", description="OTK coefficient")
    features_dict: dict[str, Any] = Field(examples=[FEATURES_EXAMPLE_FROM_STEP], description="Features from ml model")

# Request for stl analyze
class StlRequest(BaseRequest):
    location: str = Field(default="location_1", description="Location of manufacture (see constants.py)")
    service_id: str = Field(examples=[Service_type.PRINTING], description="Type of paint")
    id_cover: List[str] = Field(default=["1"], description="Cover id (empty list = no cover processing)")
    k_otk: str = Field(default="1", description="OTK coefficient")
    features_dict: dict[str, Any] = Field(examples=[FEATURES_EXAMPLE_FROM_STL], description="Features from model")

# Manufacturing calculation response model
class CalculationResponse(BaseModel):
    detail_price: float = Field(..., description="Final calculated price")
    detail_price_one: float = Field(..., description="Calculated price of one detail in order")
    total_price: float = Field(..., description="Total price for all quantity")
    total_time: float = Field(..., description="Total work time for all quantity")
    mat_volume: Optional[float] = Field(None, description="Material volume")
    mat_weight: Optional[float] = Field(None, description="Material weight")
    mat_price: Optional[float] = Field(None, description="Material price")
    work_price: Optional[float] = Field(None, description="Work price")
    work_time: Optional[float] = Field(None, description="Work time")
    k_quantity: Optional[float] = Field(None, description="Quantity coefficient")
    k_complexity: Optional[float] = Field(None, description="Dimensions number coefficient")
    manufacturing_cycle: Optional[float] = Field(None, description="Cycle of manufacturing")
    suitable_machines: Optional[list] = Field(None, description="Suitable manufacturing machines in location")
    message: str = Field(default="Calculation completed successfully", description="Status message")

# Unified request and response models for the new /calculate-price endpoint

class Dimensions(BaseModel):
    """Dimensions extracted from file or provided manually"""
    length: float = Field(..., gt=0, description="Length in mm")
    width: float = Field(..., gt=0, description="Width in mm")
    thickness: float = Field(..., gt=0, description="Thickness in mm")

class UnifiedCalculationRequest(BaseModel):
    """Unified request model for price calculation with file_id tracking"""
    # Required fields
    service_id: str = Field(..., description="Manufacturing service ID (3dprinting, cnc_milling, cnc_lathe, etc.)")
    file_id: Optional[str] = Field(None, description="File ID from external service database for tracking")
    
    # File data (base64 encoded)
    file_data: Optional[str] = Field(None, description="Base64 encoded file data (STL/STP)")
    file_name: Optional[str] = Field(None, description="Original filename")
    file_type: Optional[str] = Field(None, description="File type (stl, stp)")
    
    # Optional override parameters (if not provided, will be extracted from file)
    dimensions: Optional[Dimensions] = Field(None, description="Override dimensions")
    material_id: Optional[str] = Field(None, description="Override material ID")
    material_form: Optional[MaterialForm] = Field(None, description="Override material form")
    quantity: Optional[int] = Field(None, ge=1, description="Override quantity")
    id_cover: Optional[List[str]] = Field(None, description="Override cover processing IDs")
    tolerance_id: Optional[str] = Field(None, description="Override tolerance ID")
    finish_id: Optional[str] = Field(None, description="Override finish ID")
    k_cert: Optional[List[str]] = Field(None, description="Override certification types")
    
    # Manufacturing-specific parameters
    n_dimensions: Optional[int] = Field(None, description="Number of dimensions for 3D printing")
    k_type: Optional[float] = Field(None, ge=0, le=2, description="Type coefficient")
    k_process: Optional[float] = Field(None, ge=0, le=2, description="Process coefficient")
    k_otk: Optional[float] = Field(None, ge=0, le=2, description="Quality control coefficient")
    
    # CNC-specific parameters
    cnc_complexity: Optional[str] = Field(None, description="CNC complexity level")
    cnc_setup_time: Optional[float] = Field(None, description="CNC setup time override")
    
    # Location and features
    location: Optional[str] = Field(None, description="Location of manufacture")
    features_dict: Optional[Dict[str, Any]] = Field(None, description="Features extracted from model")

class UnifiedCalculationResponse(BaseModel):
    """Unified response model containing all calculation results"""
    # File tracking
    file_id: Optional[str] = Field(None, description="File ID from external service database")
    filename: Optional[str] = Field(None, description="Original filename if uploaded")
    
    # Core calculation results
    detail_price: float = Field(..., description="Final calculated price per unit")
    detail_price_one: float = Field(..., description="Calculated price of one detail in order")
    total_price: float = Field(..., description="Total price for all quantity")
    total_time: float = Field(..., description="Total work time for all quantity")
    
    # Material information
    mat_volume: Optional[float] = Field(None, description="Material volume")
    mat_weight: Optional[float] = Field(None, description="Material weight")
    mat_price: Optional[float] = Field(None, description="Material price")
    
    # Work information
    work_price: Optional[float] = Field(None, description="Work price")
    work_time: Optional[float] = Field(None, description="Work time")
    
    # Coefficients and factors
    k_quantity: Optional[float] = Field(None, description="Quantity coefficient")
    k_complexity: Optional[float] = Field(None, description="Dimensions number coefficient")
    k_cover: Optional[float] = Field(None, description="Cover processing coefficient")
    k_tolerance: Optional[float] = Field(None, description="Tolerance coefficient")
    k_finish: Optional[float] = Field(None, description="Finish coefficient")
    
    # Manufacturing details
    manufacturing_cycle: Optional[float] = Field(None, description="Cycle of manufacturing in days")
    suitable_machines: Optional[List[str]] = Field(None, description="Suitable manufacturing machines")
    
    # Service-specific fields (optional based on service type)
    # 3D Printing specific
    n_dimensions: Optional[int] = Field(None, description="Number of dimensions (3D printing)")
    k_type: Optional[float] = Field(None, description="Type coefficient (3D printing)")
    k_process: Optional[float] = Field(None, description="Process coefficient (3D printing)")
    
    # CNC specific
    cnc_complexity: Optional[str] = Field(None, description="CNC complexity level")
    cnc_setup_time: Optional[float] = Field(None, description="CNC setup time")
    
    # Extracted parameters (for reference)
    extracted_dimensions: Optional[Dimensions] = Field(None, description="Dimensions extracted from file")
    used_parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters used in calculation")
    
    # Status and metadata
    service_id: str = Field(..., description="Manufacturing service used")
    calculation_method: str = Field(..., description="Method used for calculation")
    message: str = Field(default="Calculation completed successfully", description="Status message")
    timestamp: Optional[str] = Field(None, description="Calculation timestamp")

# 4. Manufacturing calculation functions

def calculate_mat_volume(length: float, width: float, thickness: float) -> float:
    """Calculate material volume in cubic meters"""
    volume = 0.000000001 * length * width * thickness
    return round(volume, 10)

def calculate_mat_volume_cylindrical(length: float, dia: float) -> float:
    """Calculate material volume in cubic meters (cylindrical)"""
    volume = 0.000000001 * length * math.pi * dia * dia / 4
    return round(volume, 10)

def calculate_mat_volume_printing(length: float, width: float, thickness: float, sifting_machine=False) -> float:
    """Calculate material volume in cubic meters (for printing)"""
    if not sifting_machine:
        volume = 0.000000001 * length * width * thickness
    else:
        volume = 0.000000001 * (length + 30) * (width + 30) * (thickness + 30)

    return round(volume, 10)

def calculate_mat_weight(volume: float, density: float) -> float:
    """Calculate material weight in kg"""
    weight = volume * density
    return round(weight, 4)

def calculate_mat_price(weight: float, price_per_kg: float) -> float:
    """Calculate material price with 20% markup"""
    price = weight * price_per_kg * 1.2
    return round(price, 2)

def resolve_material(material_id: str, material_form: Union[str, MaterialForm], process: str) -> Dict[str, Any]:
    """Resolve material properties by id and form; validate form and process compatibility.
    Raises HTTPException 422 on invalid input."""
    if material_id not in MATERIALS:
        raise HTTPException(status_code=422, detail=f"Unknown material_id '{material_id}'. Use /materials to list options.")
    mat = MATERIALS[material_id]
    # Validate material applicability to process
    if "applicable_processes" in mat and process not in mat["applicable_processes"]:
        allowed_proc = ", ".join(mat["applicable_processes"])
        raise HTTPException(status_code=422, detail=f"Material '{material_id}' is not applicable to '{process}'. Allowed: {allowed_proc}.")

    form_key = material_form.value if isinstance(material_form, MaterialForm) else material_form
    if form_key not in mat["forms"]:
        allowed = ", ".join(mat["forms"].keys())
        raise HTTPException(status_code=422, detail=f"Form '{form_key}' not allowed for {material_id}. Allowed: {allowed}.")
    # Process compatibility validation
    if process == "cnc-lathe" and form_key not in ("rod", "bar", "tube"):
        raise HTTPException(status_code=422, detail="cnc-lathe requires material_form to be 'rod', 'bar', or 'tube'.")
    price = mat["forms"][form_key]["price"]
    return {"price": price, "density": mat["density"], "k_handle": mat["k_handle"], "family": mat["family"]}

def calculate_work_price(weight: float, k_handle: float, n_dimensions: int, location: str) -> float:
    """Calculate work price based on weight and handling coefficient"""
    cost_structure = COST_STRUCTURE.get(location)
    k_p = n_dimensions / 3
    work_time = 10 + k_p * 5 + weight * 1000 * k_handle # minutes
    price = (work_time * cost_structure["price_of_hour"]) / 60
    return round(price, 3)

def calculate_work_time(weight: float, k_handle: float, n_dimensions: int) -> float:
    """Calculate work time in hours based on weight and handling coefficient"""
    k_p = n_dimensions / 3
    work_time = 10 + k_p * 5 + weight * 1000 * k_handle # minutes
    return round(work_time / 60, 3)

def calculate_k_complexity(n_dimensions: int) -> float:
    """Calculate complexity coefficient"""
    if n_dimensions <= 15:
        return 0.75
    elif n_dimensions <= 50:
        return 1.0
    elif n_dimensions > 50:
        return 1.25
    else:
        return 0.75

def calculate_k_quantity(quantity: int) -> float:
    """Calculate quantity discount coefficient"""
    if quantity < 21:
        return 1.0
    elif quantity < 101:
        return 0.95
    elif quantity < 501:
        return 0.85
    else:
        return 0.8

def calculate_printing_work_time(volume: float) -> float:
    """Calculate work time of printing process from liters per hour and volume in mm3"""
    V = 6 # liter per hour
    machine_time = volume * 1e6 / V
    pzv_time = 2
    full_time = machine_time + pzv_time

    return full_time

def calculate_cost(mat_price: float, work_price: float, location: str) -> float:
    """Calculate cost from material price and work price"""
    cost_structure = COST_STRUCTURE.get(location)
    dop_salary = cost_structure["dop_salary_coef"] * work_price 
    insurance_price = cost_structure["insurance_coef"] * (dop_salary + work_price)
    overhead_expenses = cost_structure["overhead_expenses_coef"] * work_price
    administrative_expenses = cost_structure["administrative_expenses_coef"] * work_price
    net_cost = mat_price +\
        work_price +\
        dop_salary +\
        insurance_price +\
        overhead_expenses +\
        administrative_expenses
    profit = mat_price * cost_structure["profit_material"] + \
        (net_cost - mat_price) * cost_structure["other_profit"]
    cost = net_cost + profit

    return float(cost)

def calculate_cycle(id_cover: List[str], quantity:int, k_otk: float) -> float:
    """Calculate cycle (time in days) of manufacturing"""
    buying_material_time = 3
    developing_technology_time = 1
    developing_program_time = 3
    preparing_material_time = 1
    quantity_coef = quantity // 40
    manufacturing_time = 2 + preparing_material_time + quantity_coef
    packaging_time = 1

    cycle = (
        max(buying_material_time, (developing_technology_time + developing_program_time)) + 
        preparing_material_time + 
        manufacturing_time + 
        packaging_time
    )

    # Add cover cycle time using helper function
    cycle += calculate_cover_cycle_time(id_cover)

    if k_otk==1.15: # УТОЧНИТЬ ID НИ
        cycle+=1 + quantity_coef
    
    return cycle

def calculate_cover_coefficient(id_cover_list: List[str]) -> float:
    """Calculate combined cover coefficient by multiplying all cover coefficients"""
    if not id_cover_list:
        return 1.0  # No cover processing - neutral coefficient
    
    # Check for duplicates
    if len(id_cover_list) != len(set(id_cover_list)):
        raise ValueError("Duplicate cover IDs are not allowed")
    
    # Validate all cover IDs exist
    for cover_id in id_cover_list:
        if cover_id not in COVER:
            raise ValueError(f"Invalid cover ID: {cover_id}")
    
    # Multiply all coefficients
    coefficient = 1.0
    for cover_id in id_cover_list:
        coefficient *= COVER[cover_id]['value']
    
    return coefficient

def calculate_cover_cycle_time(id_cover_list: List[str]) -> float:
    """Calculate additional cycle time by adding all cover cycle times"""
    if not id_cover_list:
        return 0.0  # No additional time if no covers
    
    # Check for duplicates
    if len(id_cover_list) != len(set(id_cover_list)):
        raise ValueError("Duplicate cover IDs are not allowed")
    
    # Validate all cover IDs exist
    for cover_id in id_cover_list:
        if cover_id not in COVER:
            raise ValueError(f"Invalid cover ID: {cover_id}")
    
    # Add all cycle times
    additional_time = 0.0
    for cover_id in id_cover_list:
        if cover_id == "1":  # покраска (painting)
            additional_time += 2
        elif cover_id == "2":  # гальваника (galvanizing)
            additional_time += 5
    
    return additional_time

def calculate_printing_price(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate 3D printing price"""
    location = "location_1" # see constants.py CHECK COST STRUCTURE

    length = request_data["length"]
    width = request_data["width"]
    thickness = request_data["thickness"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    k_complexity = request_data.get("k_complexity", 0.75)
    k_type = request_data.get("k_type", 1.0)
    k_process = request_data.get("k_process", 1.0)
    id_cover = request_data.get("id_cover", ["1"])
    k_otk = float(request_data.get("k_otk", "1"))
    n_dimensions = request_data.get("n_dimensions", 1)
    k_cert = request_data.get("k_cert", ["a", "f"])        
    
    material_props = resolve_material(material_id, material_form, process="printing")
    
    mat_volume = calculate_mat_volume(length, width, thickness)
    mat_weight = calculate_mat_weight(mat_volume, material_props["density"])
    mat_price = calculate_mat_price(mat_weight, material_props["price"])
    work_price = calculate_work_price(mat_weight, material_props["k_handle"], n_dimensions, location)
    k_quantity = calculate_k_quantity(quantity)
    work_time = calculate_work_time(mat_weight, material_props["k_handle"], n_dimensions)
    k_complexity = calculate_k_complexity(n_dimensions)
    k_cover = calculate_cover_coefficient(id_cover)
    cert_cost = sum(CERT_COSTS.get(cert, 0) for cert in k_cert)
    
    # Calculate work price with all coefficients for full quantity
    work_price_full = (
        work_price *
        k_complexity *
        k_type *
        k_process *
        k_cover *
        k_otk *
        k_quantity
    )
    
    # Calculate work price for one detail (quantity = 1)
    work_price_full_one_detail = (
        work_price *
        k_complexity *
        k_type *
        k_process *
        k_cover *
        k_otk *
        1  # quantity = 1 for one detail
    )
    
    # Calculate final prices using cost structure
    detail_price = calculate_cost(mat_price + cert_cost, work_price_full, location)
    detail_price_one = calculate_cost(mat_price + cert_cost, work_price_full_one_detail, location)
    
    # Calculate manufacturing cycle
    manufacturing_cycle = calculate_cycle(id_cover, quantity, k_otk)
    
    # Get suitable machines (for now, return default since printing doesn't use specific machines)
    suitable_machines = ["3D Printer Default"]  # Default for printing
    
    # Calculate total price and total time
    total_price = detail_price * quantity
    total_time = work_time * quantity
    
    return {
        "detail_price": round(detail_price, 0),
        "detail_price_one": round(detail_price_one, 0),
        "total_price": round(total_price, 0),
        "total_time": round(total_time, 3),
        "mat_volume": mat_volume,
        "mat_weight": mat_weight,
        "mat_price": mat_price,
        "work_price": work_price_full,
        "work_time": work_time,
        "k_quantity": k_quantity,
        "k_complexity": k_complexity,
        "manufacturing_cycle": manufacturing_cycle,
        "suitable_machines": suitable_machines
    }

def calculate_cnc_milling_price(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate milling price"""
    location = "location_1" # see constants.py

    length = request_data["length"]
    width = request_data["width"]
    thickness = request_data["thickness"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    id_tolerance = request_data.get("id_tolerance", "1")
    id_finish = request_data.get("id_finish", "1")
    id_cover = request_data.get("id_cover", ["1"])
    k_otk = float(request_data.get("k_otk", "1"))
    k_cert = request_data.get("k_cert", ["a", "f"])        
    n_dimensions = request_data.get("n_dimensions", 1)
    
    part_sizes = {
        "x": length,
        "y": width,
        "z": thickness
    }
    suitable_machines = check_machines(part_sizes, "milling", location)

    material_props = resolve_material(material_id, material_form, process="cnc-milling")
    
    mat_volume = calculate_mat_volume(length, width, thickness)
    mat_weight = calculate_mat_weight(mat_volume, material_props["density"])
    mat_price = calculate_mat_price(mat_weight, material_props["price"])
    work_price = calculate_work_price(mat_weight, material_props["k_handle"], n_dimensions, location)
    work_time = calculate_work_time(mat_weight, material_props["k_handle"], n_dimensions)

    k_quantity = calculate_k_quantity(quantity)
    k_complexity = calculate_k_complexity(n_dimensions)

    k_tolerance = TOLERANCE.get(id_tolerance, TOLERANCE["1"])['value']
    k_finish = FINISH.get(id_finish, FINISH["1"])['value']
    k_cover = calculate_cover_coefficient(id_cover)

    cert_cost = sum(CERT_COSTS.get(cert, 0) for cert in k_cert)
    
    work_price_full = (
        work_price *
        k_complexity *
        k_tolerance *
        k_finish *
        k_cover *
        k_otk *
        k_quantity
    )
    work_price_full_one_detail = (
        work_price *
        k_complexity *
        k_tolerance *
        k_finish *
        k_cover *
        k_otk *
        1
    )

    detail_price = calculate_cost(mat_price + cert_cost, work_price_full, location)
    detail_price_one = calculate_cost(mat_price + cert_cost, work_price_full_one_detail, location)

    manufacturing_cycle = calculate_cycle(id_cover, quantity, k_otk)

    # Calculate total price and total time
    total_price = detail_price * quantity
    total_time = work_time * quantity

    return {
        "detail_price": round(detail_price, 0),
        "detail_price_one": round(detail_price_one, 0),
        "total_price": round(total_price, 0),
        "total_time": round(total_time, 3),
        "mat_volume": mat_volume,
        "mat_weight": mat_weight,
        "mat_price": mat_price,
        "work_price": work_price_full,
        "work_time": work_time,
        "k_quantity": k_quantity,
        "k_complexity": k_complexity,
        "manufacturing_cycle": manufacturing_cycle,
        "suitable_machines": suitable_machines
    }

def calculate_cnc_lathe_price(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate CNC price"""
    location = "location_1" # see constants.py

    length = request_data["length"]
    dia = request_data["dia"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    n_dimensions = request_data.get("n_dimensions", 1)
    id_tolerance = request_data.get("id_tolerance", "1")
    id_finish = request_data.get("id_finish", "1")
    id_cover = request_data.get("id_cover", ["1"])
    k_otk = float(request_data.get("k_otk", "1"))
    k_cert = request_data.get("k_cert", ["a", "f"])

    part_sizes = {
        "x": dia,
        "y": dia,
        "z": length
    }
    suitable_machines = check_machines(part_sizes, "lathe", location)

    material_props = resolve_material(material_id, material_form, process="cnc-lathe")
    
    mat_volume = calculate_mat_volume_cylindrical(length, dia)
    mat_weight = calculate_mat_weight(mat_volume, material_props["density"])
    mat_price = calculate_mat_price(mat_weight, material_props["price"])
    work_price = calculate_work_price(mat_weight, material_props["k_handle"], n_dimensions, location)
    work_time = calculate_work_time(mat_weight, material_props["k_handle"], n_dimensions)

    k_quantity = calculate_k_quantity(quantity)
    k_complexity = calculate_k_complexity(n_dimensions)

    k_tolerance = TOLERANCE.get(id_tolerance, TOLERANCE["1"])['value']
    k_finish = FINISH.get(id_finish, FINISH["1"])['value']
    k_cover = calculate_cover_coefficient(id_cover)
    
    cert_cost = sum(CERT_COSTS.get(cert, 0) for cert in k_cert)

    work_price_full = (
        work_price *
        k_complexity *
        k_tolerance *
        k_finish *
        k_cover *
        k_otk *
        k_quantity
    )
    work_price_full_one_detail = (
        work_price *
        k_complexity *
        k_tolerance *
        k_finish *
        k_cover *
        k_otk *
        1
    )

    detail_price = calculate_cost(mat_price + cert_cost, work_price_full, location)
    detail_price_one = calculate_cost(mat_price + cert_cost, work_price_full_one_detail, location)

    manufacturing_cycle = calculate_cycle(id_cover, quantity, k_otk)

    # Calculate total price and total time
    total_price = detail_price * quantity
    total_time = work_time * quantity

    logger.info("cnc calc accessed.")
    return {
        "detail_price": round(detail_price, 0),
        "detail_price_one": round(detail_price_one, 0),
        "total_price": round(total_price, 0),
        "total_time": round(total_time, 3),
        "mat_volume": mat_volume,
        "mat_weight": mat_weight,
        "mat_price": mat_price,
        "work_price": work_price_full,
        "work_time": work_time,
        "k_quantity": k_quantity,
        "k_complexity": k_complexity,
        "manufacturing_cycle": manufacturing_cycle,
        "suitable_machines": suitable_machines
    }

def calculate_base_paint_price(paint_area: float, paint_type: str) -> float:
    """Calculate base paint price per area"""
    paint_coeff = PAINT_COEFFICIENTS.get(paint_type, PAINT_COEFFICIENTS["acrylic"])
    base_price = paint_area * paint_coeff["base_price"] * paint_coeff["k_type"]
    return round(base_price, 2)

def calculate_preparation_cost(paint_area: float, material: str, paint_type: str) -> float:
    """Calculate preparation cost"""
    material_coeff = MATERIAL_PREP.get(material, MATERIAL_PREP["alum"])
    paint_coeff = PAINT_COEFFICIENTS.get(paint_type, PAINT_COEFFICIENTS["acrylic"])
    
    prep_cost = paint_area * 15.0 * material_coeff["k_clean"] * paint_coeff["k_prepare"]
    return round(prep_cost, 2)

def calculate_process_coefficient(paint_prepare: str, paint_primer: str, paint_lakery: str) -> float:
    """Calculate process coefficient based on preparation, primer, and lakery types"""
    prep_coeff = PROCESS_COEFFICIENTS["paint_prepare"].get(paint_prepare, 1.0)
    primer_coeff = PROCESS_COEFFICIENTS["paint_primer"].get(paint_primer, 1.0)
    lakery_coeff = PROCESS_COEFFICIENTS["paint_lakery"].get(paint_lakery, 1.0)
    
    return prep_coeff * primer_coeff * lakery_coeff

# Helper to build calculation response

def build_calc_response(result: Dict[str, Any], message: str) -> CalculationResponse:
    return CalculationResponse(
        detail_price=result.get("detail_price"),
        detail_price_one=result.get("detail_price_one"),
        total_price=result.get("total_price"),
        total_time=result.get("total_time"),
        mat_volume=result.get("mat_volume"),
        mat_weight=result.get("mat_weight"),
        mat_price=result.get("mat_price"),
        work_price=result.get("work_price"),
        work_time=result.get("work_time"),
        k_quantity=result.get("k_quantity"),
        k_complexity=result.get("k_complexity"),
        manufacturing_cycle=result.get("manufacturing_cycle"),
        suitable_machines=result.get("suitable_machines"),
        message=message,
    )

def calculate_painting_price(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate painting price"""
    paint_area = request_data["paint_area"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    paint_type = request_data["paint_type"]
    paint_prepare = request_data.get("paint_prepare", "a")
    paint_primer = request_data.get("paint_primer", "b")
    paint_lakery = request_data.get("paint_lakery", "a")
    k_cert = request_data.get("k_cert", ["a", "f", "g", "d"])
    control_type = request_data.get("control_type", "1")
    
    base_paint_price = calculate_base_paint_price(paint_area, paint_type)
    props = resolve_material(material_id, material_form, process="painting")
    prep_cost = calculate_preparation_cost(paint_area, props["family"], paint_type)
    process_coeff = calculate_process_coefficient(paint_prepare, paint_primer, paint_lakery)
    cert_cost = sum(CERT_COSTS.get(cert, 0) for cert in k_cert)
    k_quantity = calculate_k_quantity(quantity)
    
    k_control = float(control_type) * 0.1 + 0.9
    
    total_base = (base_paint_price + prep_cost + cert_cost) * process_coeff
    detail_price = total_base * k_control * k_quantity
    
    # Calculate total price and total time (painting doesn't have work_time, so total_time = 0)
    total_price = detail_price * quantity
    total_time = 0.0  # Painting doesn't have work_time concept
    
    return {
        "detail_price": round(detail_price, 0),
        "detail_price_one": round(detail_price, 0),  # For painting, detail_price_one = detail_price
        "total_price": round(total_price, 0),
        "total_time": round(total_time, 3),
        "base_paint_price": base_paint_price,
        "prep_cost": prep_cost,
        "cert_cost": cert_cost,
        "process_coeff": process_coeff,
        "k_quantity": k_quantity,
        "k_control": k_control
    }

def check_repeats(part: dict) -> tuple[bool, list]:
    """Check repeated main sizes in detail"""
    part_sizes = part.values()
    part_sizes_list = list(part_sizes)
    unique_values = set(part_sizes_list)
    repeated = [value for value in unique_values if part_sizes_list.count(value) > 1]
    if len(repeated) >= 1:
        first_repeated = repeated[0]
        part_sizes = [first_repeated, first_repeated] + [value for value in part_sizes_list if value != first_repeated]
        return True, part_sizes
    else:
        return False, sorted(part_sizes_list, reverse=True)

# Manufacturing machines check
def check_machines(part: dict, processing_type: str, location: str, mode="default") -> list:
    """Return list of machines for given part dimensions"""
    if any(k not in part or part[k] is None for k in ("x", "y", "z")):
        raise ValueError("Sizes of detail must contain x, y, z. Also it all must not be None")
    
    suitable_machines = []
    
    if processing_type=="milling" or processing_type=="printing" or\
        processing_type=="cnc-milling":
        part_sizes = sorted(part.values(), reverse=True)
        for machine_id, vals in MACHINES.items():
            machine_type = vals.get("type")
            machine_location = vals.get("location")
            if (machine_type!=processing_type) or (machine_location!=location):
                continue
            dims = vals.get("dimensions", {})
            if any(k not in dims or dims[k] is None for k in ("x", "y", "z")):
                continue
            machine_sizes = sorted(dims.values(), reverse=True)
            if all(p <= m_size for p, m_size in zip(part_sizes, machine_sizes)):
                suitable_machines.append(vals["name"])
    elif processing_type=="lathe" or processing_type=="cnc-lathe":
        if mode!="auto":
            part_sizes = part.values()
            for machine_id, vals in MACHINES.items():
                machine_type = vals.get("type")
                machine_location = vals.get("location")
                
                if (machine_type!=processing_type) or (machine_location!=location):
                    continue
                dims = vals.get("dimensions", {})
                if any(k not in dims or dims[k] is None for k in ("x", "y", "z")):
                    continue
                machine_sizes = vals.get("dimensions", {}).values()
                if all(p <= m_size for p, m_size in zip(part_sizes, machine_sizes)):
                    suitable_machines.append(vals["name"])
        else:
            # check repeats (finding diameter)
            bool_feature, part_sizes = check_repeats(part)
            if not bool_feature:
                suitable_machines.append('check_next_machines')
            
            for machine_id, vals in MACHINES.items():
                machine_type = vals.get("type")
                machine_location = vals.get("location")
                if (machine_type!=processing_type) or (machine_location!=location):
                    continue
                
                dims = vals.get("dimensions", {})
                if any(k not in dims or dims[k] is None for k in ("x", "y", "z")):
                    continue
                
                machine_sizes = vals.get("dimensions", {}).values()
                if all(p <= m_size for p, m_size in zip(part_sizes, machine_sizes)):
                    suitable_machines.append(vals["name"])
    else:
        return ["Unknown type of manufacturing"]

    if not suitable_machines:
        return ["We don't have suitable machines"]
    
    return suitable_machines

def calculate_from_step(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate price from step model
    Supports cnc milling and lathe
    """
    # import data drom request
    location = request_data["location"] # see constants.py
    service_id = request_data["service_id"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    id_cover = request_data.get("id_cover", ["1"])
    k_otk = float(request_data.get("k_otk", "1"))
    
    features_df = pd.DataFrame(request_data["features_dict"], index=[0])

    k_cover = calculate_cover_coefficient(id_cover)

    # Add material features
    features_df['material_bar'] = material_form
    features_df['material_bar'].map({
        "plate": "Плита", "rod": "Пруток", "hexagon": "Шестигранник", "sheet": "Лист"
    })

    features_df['material_name_main'] = MATERIALS.get(material_id)["material_name_main"]
    features_df['material_name'] = MATERIALS.get(material_id)["material_name"]
    features_df['material_coef'] = MATERIALS.get(material_id)["material_coef"]
    features_df['material_group'] = MATERIALS.get(material_id)["material_group"]
    features_df['density_approximately'] = MATERIALS.get(material_id)["density"] * 1e-9
    features_df['density_approximately'] = MATERIALS.get(material_id)["density"] * 1e-9
    features_df['weight_approximately'] = features_df['density_approximately'] * features_df['volume']
    features_df['min_size'] = features_df[['obb_x', 'obb_y', 'obb_z']].min(axis=1)
    features_df['mid_size'] = features_df[['obb_x', 'obb_y', 'obb_z']].median(axis=1)
    features_df['max_size'] = features_df[['obb_x', 'obb_y', 'obb_z']].max(axis=1)
    features_df['check_sizes_for_lathe'] = features_df[['obb_x', 'obb_y', 'obb_z']].\
        apply(lambda row: 
              1 
              if (row['obb_x'].round() - row['obb_y'].round() == 0) or 
              (row['obb_x'].round() - row['obb_z'].round() == 0) or 
              (row['obb_y'].round() - row['obb_z'].round() == 0) 
              else 0, axis=1
              )
    features_df = features_df.drop(['obb_x', 'obb_y', 'obb_z'], axis=1)
    
    part_sizes = {
        "x": round(features_df['max_size'][0]),
        "y": round(features_df['mid_size'][0]),
        "z": round(features_df['min_size'][0]),
    }
    
    # Preprocessing categoricals
    ohe = load(f"{ENCODER_PATH}")
    categoricals = ['material_bar', 'material_name', 'material_name_main', 'material_group']
    features_df_ohe = ohe.transform(features_df[categoricals])
    features_df_ohe = pd.DataFrame(
        features_df_ohe,
        columns=ohe.get_feature_names_out(),
        index=features_df.index
    )
    features_df = pd.concat(
        [features_df.drop(categoricals, axis=1), features_df_ohe],
        axis=1
    )
    
    # load ml model and get prediction
    xgb_model = XGBRegressor()
    xgb_model.load_model(f"{ML_MODEL_PATH}")
    
    features_df_reindexed = features_df.drop(['filename', 'material_coef'], axis=1).\
        reindex(columns=xgb_model.feature_names_in_)
    prediction = round(xgb_model.predict(features_df_reindexed)[0], 2)
    
    service_to_processing_mapping = {
        "cnc-lathe": "lathe",
        "cnc-milling": "milling",
        "printing": "printing",
        "painting": "painting"
    }

    # calculate price
    processing_type = service_to_processing_mapping[service_id]
    
    suitable_machines = check_machines(part_sizes, processing_type, location, mode="auto")
    if service_id=="cnc-milling":
        #logger.info("here")
        mat_volume = calculate_mat_volume(
            part_sizes["x"], 
            part_sizes["y"], 
            part_sizes["z"]
        )
    elif service_id=="cnc-lathe":
        _, part_sizes_sorted_list = check_repeats(part_sizes)
        part_sizes = {
            "x": part_sizes_sorted_list[0],
            "y": part_sizes_sorted_list[1],
            "z": part_sizes_sorted_list[2],
        }
        mat_volume = calculate_mat_volume_cylindrical(
            part_sizes["z"], 
            part_sizes["x"]
        )
    
    material_props = resolve_material(material_id, material_form, process=service_id) 
    mat_weight = calculate_mat_weight(mat_volume, material_props["density"])
    mat_price = calculate_mat_price(mat_weight, material_props["price"])
    
    price_of_hour = COST_STRUCTURE.get(location)["price_of_hour"]
    work_price = prediction * price_of_hour

    k_quantity = calculate_k_quantity(quantity)

    work_price_full = (work_price * k_cover * k_otk * k_quantity)
    detail_price = calculate_cost(mat_price, work_price_full, location)
    detail_price_one = calculate_cost(mat_price, work_price * k_cover * k_otk, location)

    manufacturing_cycle = calculate_cycle(id_cover, quantity, k_otk)

    # Calculate total price and total time
    total_price = detail_price * quantity
    total_time = prediction * quantity

    return {
        "detail_price": round(detail_price, 2),
        "detail_price_one": round(detail_price_one, 2),
        "total_price": round(total_price, 2),
        "total_time": round(total_time, 3),
        "mat_volume": mat_volume,
        "mat_weight": mat_weight,
        "mat_price": mat_price,
        "work_price": work_price_full,
        "work_time": prediction,
        "k_quantity": k_quantity,
        "manufacturing_cycle": manufacturing_cycle,
        "suitable_machines": suitable_machines,
        "auto_sizes": part_sizes
    }

def calculate_from_stl(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate price from stl model
    Supports printing
    """
    # import data drom request
    location = request_data["location"] # see constants.py
    service_id = request_data["service_id"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    part_sizes = request_data["features_dict"]
    id_cover = request_data.get("id_cover", ["1"])
    k_otk = float(request_data.get("k_otk", "1"))
    k_cover = calculate_cover_coefficient(id_cover)
    processing_type = service_id
    
    suitable_machines = check_machines(part_sizes, processing_type, location)
    
    mat_volume = calculate_mat_volume_printing(
        part_sizes["x"], 
        part_sizes["y"], 
        part_sizes["z"]
    )

    material_props = resolve_material(material_id, material_form, process=service_id) 
    
    mat_weight = calculate_mat_weight(mat_volume, material_props["density"])
    mat_price = calculate_mat_price(mat_weight, material_props["price"])
    price_of_hour = COST_STRUCTURE.get(location)["price_of_hour"]
    
    work_time = calculate_printing_work_time(mat_volume)
    work_price = work_time * price_of_hour

    k_quantity = calculate_k_quantity(quantity)

    work_price_full = (work_price * k_cover * k_otk * k_quantity)
    detail_price = calculate_cost(mat_price, work_price_full, location)
    detail_price_one = calculate_cost(mat_price, work_price * k_cover * k_otk, location)

    manufacturing_cycle = calculate_cycle(id_cover, quantity, k_otk)

    # Calculate total price and total time
    total_price = detail_price * quantity
    total_time = work_time * quantity

    return {
        "detail_price": round(detail_price, 2),
        "detail_price_one": round(detail_price_one, 2),
        "total_price": round(total_price, 2),
        "total_time": round(total_time, 3),
        "mat_volume": mat_volume,
        "mat_weight": mat_weight,
        "mat_price": mat_price,
        "work_price": work_price_full,
        "work_time": work_time,
        "k_quantity": k_quantity,
        "manufacturing_cycle": manufacturing_cycle,
        "suitable_machines": suitable_machines,
        "auto_sizes": part_sizes
    }

# 4.1 Extract features from step file
def safe_geomtype(obj) -> str:
    """Function for safe loading and processing geomtypes"""
    try:
        return (obj.geomType() or "").upper()
    except Exception:
        return ""

def compute_entropy(types_count: Dict[str, int]) -> float:
    """Compute value to measure differentiate edges or faces"""
    total = sum(types_count.values())
    probs = [count / total for count in types_count.values() if count > 0]

    return -np.sum(probs * np.log2(probs)) if probs else 0.0

def analyze_step_file(file_path: str) -> List[Dict]:
    """Analysis of one detail file in .stp or .step"""
    try:
        wp = cq.importers.importStep(file_path) 
        print(f"Обработка файла: {file_path}")
        
        solids = wp.solids().vals()
        if not solids:
            print(f"Не найдено твердых тел")
            faces = wp.faces().vals()
            if not faces:
                print(f"Не найдено граней")
                return []
            volume = 0
            surface_area = sum(f.Area() for f in faces)
            
        else:
            volume = sum(s.Volume() for s in solids)
            surface_area = sum(s.Area() for s in solids)

        ## OBB
        shape = wp.val().wrapped
        obb = Bnd_OBB()
        BRepBndLib.AddOBB_s(
            shape,
            obb,
            theIsTriangulationUsed=True,
            theIsOptimal=True,
            theIsShapeToleranceUsed=True
        )
        obb_dimensions = {
            'x': 2 * obb.XHSize(),
            'y': 2 * obb.YHSize(),
            'z': 2 * obb.ZHSize()
        }
        aspect_ratio_xy = obb_dimensions['x'] / obb_dimensions['y']
        aspect_ratio_yz = obb_dimensions['y'] / obb_dimensions['z']
        aspect_ratio_xz = obb_dimensions['x'] / obb_dimensions['z']
        bbox_volume = obb_dimensions['x'] * obb_dimensions['y'] * obb_dimensions['z']

        # General
        faces = wp.faces().vals()
        edges = wp.edges().vals()
        vertices = wp.vertices().vals()
        num_faces = len(faces)
        num_edges = len(edges)
        num_vertices = len(vertices)
        num_wires = len(wp.wires().vals())
        euler_char = num_vertices - num_edges + num_faces

        # Faces
        face_types = Counter(safe_geomtype(f) for f in faces)
        num_planar = face_types.get('PLANE', 0)
        num_cylindrical = face_types.get('CYLINDER', 0)
        num_conical = face_types.get('CONE', 0)
        num_toroidal = face_types.get('TORUS', 0)
        num_spherical = face_types.get('SPHERE', 0)
        num_bspline = face_types.get('BSPLINE', 0)
        surface_entropy = compute_entropy(face_types)  # Сложность разнообразия поверхностей
        other_face_types = Counter(safe_geomtype(f) for f in faces if safe_geomtype(f) not in 
                                   ['PLANE', 'CYLINDER', 'CONE', 'TORUS', 'SPHERE', 'BSPLINE', 'BEZIER'])

        # Ratios for nums of faces
        ratio_planar = num_planar / num_faces
        ratio_cylindrical = num_cylindrical / num_faces
        ratio_conical = num_conical / num_faces
        ratio_toroidal = num_toroidal / num_faces
        ratio_spherical = num_spherical / num_faces
        ratio_bspline = num_bspline / num_faces

        # Areas by surface type (for machining complexity)
        planar_area = sum(f.Area() for f in faces if safe_geomtype(f) == 'PLANE')
        cylindrical_area = sum(f.Area() for f in faces if safe_geomtype(f) == 'CYLINDER')
        conical_area = sum(f.Area() for f in faces if safe_geomtype(f) == 'CONE')
        toroidal_area = sum(f.Area() for f in faces if safe_geomtype(f) == 'TORUS')
        spherical_area = sum(f.Area() for f in faces if safe_geomtype(f) == 'SPHERE')
        bspline_area = sum(f.Area() for f in faces if safe_geomtype(f) == 'BSPLINE')
        other_area = surface_area - \
            (planar_area + cylindrical_area + conical_area + \
             toroidal_area + spherical_area + bspline_area)

        # Ratios for areas of faces
        ratio_planar_area = planar_area / surface_area
        ratio_cylindrical_area = cylindrical_area / surface_area
        ratio_conical_area = conical_area / surface_area
        ratio_toroidal_area = toroidal_area / surface_area
        ratio_spherical_area = spherical_area / surface_area
        ratio_bspline_area = bspline_area / surface_area
        ratio_other_area = other_area / surface_area
        ratio_planar_cylindrical = (ratio_cylindrical_area - ratio_planar_area) + \
            (ratio_cylindrical - ratio_planar)
        
        # Planar normals clustering (unique directions, rounded)
        planar_normals = [tuple(round(c, 3) for c in f.normalAt().toTuple()) for f in faces if safe_geomtype(f) == 'PLANE']
        num_unique_planar_normals = len(set(planar_normals)) if planar_normals else 0

        # Edges
        edge_types = Counter(safe_geomtype(e) for e in edges)
        num_straight_edges = edge_types.get('LINE', 0)
        num_curved_edges = num_edges - num_straight_edges
        num_circles = edge_types.get('CIRCLE', 0)
        num_bspline_edges = edge_types.get('BSPLINE', 0)
        edge_entropy = compute_entropy(edge_types)

        # Ratios for nums of edges
        ratio_straight_edges = num_straight_edges / num_edges
        ratio_curved_edges = num_curved_edges / num_edges
        ratio_circles_edges = num_circles / num_edges
        ratio_bspline_edges = num_bspline_edges / num_edges

        # Lengths by edge type
        length_all_edges = sum(e.Length() for e in edges)
        straight_length = sum(e.Length() for e in edges if safe_geomtype(e) == 'LINE')
        curved_length = length_all_edges - straight_length
        circle_length = sum(e.Length() for e in edges if safe_geomtype(e) == 'CIRCLE')
        bspline_edge_length = sum(e.Length() for e in edges if safe_geomtype(e) == 'BSPLINE')

        # Ratios for lengths of edges
        ratio_straight_edges_length = straight_length / length_all_edges
        ratio_curved_edges_length = curved_length / length_all_edges
        ratio_circles_edges_length = circle_length / length_all_edges
        ratio_bspline_edges_length = bspline_edge_length / length_all_edges
        bezier_edge_length = sum(e.Length() for e in edges if safe_geomtype(e) == 'BEZIER')
        ratio_bezier_edges_length = bezier_edge_length / length_all_edges # unuseful - delete!

        # Average metrics
        avg_face_area = surface_area / num_faces if num_faces > 0 else 0
        avg_edge_length = sum(e.Length() for e in edges) / num_edges if num_edges > 0 else 0

        # Compactness and ratios
        surface_to_volume_ratio = surface_area / volume if volume > 0 else 0
        obb_compactness = volume / bbox_volume if bbox_volume > 0 else 0

        # Sphericity (1 for sphere, <1 for irregular)
        sphericity = (np.pi ** (1/3) * (6 * volume) ** (2/3)) / surface_area if surface_area > 0 and volume > 0 else 0

        topology_complexity_score = (num_faces + num_edges + num_vertices) / 3  # Базовая топологическая сложность
        removable_score = volume / bbox_volume

        return [{
            'filename': file_path,
            'volume': volume,
            'surface_area': surface_area,
            'obb_x': obb_dimensions['x'],
            'obb_y': obb_dimensions['y'],
            'obb_z': obb_dimensions['z'],
            'aspect_ratio_xy': aspect_ratio_xy,
            'aspect_ratio_yz': aspect_ratio_yz,
            'aspect_ratio_xz': aspect_ratio_xz,
            'bbox_volume': bbox_volume,
            'num_faces': num_faces,
            'num_edges': num_edges,
            'num_vertices': num_vertices,
            'num_wires': num_wires,
            'euler_char': euler_char,
            'num_planar': num_planar,
            'num_cylindrical': num_cylindrical,
            'num_conical': num_conical,
            'num_toroidal': num_toroidal,
            'num_spherical': num_spherical,
            'num_bspline': num_bspline,
            'surface_entropy': surface_entropy,
            'ratio_planar': ratio_planar,
            'ratio_cylindrical': ratio_cylindrical,
            'ratio_conical': ratio_conical,
            'ratio_toroidal': ratio_toroidal,
            'ratio_spherical': ratio_spherical,
            'ratio_bspline': ratio_bspline,
            'planar_area': planar_area,
            'cylindrical_area': cylindrical_area,
            'conical_area': conical_area,
            'toroidal_area': toroidal_area,
            'spherical_area': spherical_area,
            'bspline_area': bspline_area,
            'other_area': other_area,
            'ratio_planar_area': ratio_planar_area,
            'ratio_cylindrical_area': ratio_cylindrical_area,
            'ratio_conical_area': ratio_conical_area,
            'ratio_toroidal_area': ratio_toroidal_area,
            'ratio_spherical_area': ratio_spherical_area,
            'ratio_bspline_area': ratio_bspline_area,
            'ratio_other_area': ratio_other_area,
            'ratio_planar_cylindrical': ratio_planar_cylindrical,
            'num_unique_planar_normals': num_unique_planar_normals,
            'num_straight_edges': num_straight_edges,
            'num_curved_edges': num_curved_edges,
            'num_circles': num_circles,
            'num_bspline_edges': num_bspline_edges,
            'edge_entropy': edge_entropy,
            'ratio_straight_edges': ratio_straight_edges,
            'ratio_curved_edges': ratio_curved_edges,
            'ratio_circles_edges': ratio_circles_edges,
            'ratio_bspline_edges': ratio_bspline_edges,
            'length_all_edges': length_all_edges,
            'straight_length': straight_length,
            'curved_length': curved_length,
            'circle_length': circle_length,
            'bspline_edge_length': bspline_edge_length,
            'ratio_straight_edges_length': ratio_straight_edges_length,
            'ratio_curved_edges_length': ratio_curved_edges_length,
            'ratio_circles_edges_length': ratio_circles_edges_length,
            'ratio_bspline_edges_length': ratio_bspline_edges_length,
            'ratio_bezier_edges_length': ratio_bezier_edges_length, # unuseful - delete!
            'avg_face_area': avg_face_area,
            'avg_edge_length': avg_edge_length,
            'surface_to_volume_ratio': surface_to_volume_ratio,
            'obb_compactness': obb_compactness,
            'sphericity': sphericity,
            'topology_complexity_score': topology_complexity_score,
            'removable_score': removable_score
        }]
    except Exception as e:
        print(f"Error: {e}")
        return []

def analyze_stl_file(file_path: str) -> List[Dict]:
    """Analysis of one detail file in .stl"""
    try:
        mesh = trimesh.load_mesh(file_path)
        oriented_bounding_box = mesh.bounding_box_oriented
        dimensions = oriented_bounding_box.extents
        
        part_sizes = {
            "x": round(dimensions[0]),
            "y": round(dimensions[1]),
            "z": round(dimensions[2]),
        }
        return [part_sizes]

    except Exception as e:
        print(f"Error: {e}")
        return []

# Helper functions for unified calculation endpoint

async def extract_parameters_from_base64_file(file_data: str, file_name: str, file_type: Optional[str], file_id: Optional[str] = None) -> Dict[str, Any]:
    """Extract parameters from base64 encoded CAD file (STL/STP)"""
    logger.info(f"Extracting parameters from base64 file: {file_name} (file_id: {file_id})")
    
    extracted_params = {}
    
    try:
        import base64
        
        # Decode base64 data
        file_bytes = base64.b64decode(file_data)
        
        # Save to temporary file for processing
        temp_file_path = f"temp_{file_name}"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file_bytes)
        
        # Determine file type and extract parameters
        if file_type and file_type.lower() in ["stl"] or file_name.lower().endswith(".stl"):
            # Extract from STL file
            stl_features = analyze_stl_file(temp_file_path)
            if stl_features:
                features_df = pd.DataFrame(stl_features)
                features_dict = features_df.iloc[0, :].to_dict()
                
                # Extract dimensions from STL
                if 'length' in features_dict and 'width' in features_dict and 'thickness' in features_dict:
                    extracted_params['dimensions'] = {
                        'length': features_dict['length'],
                        'width': features_dict['width'],
                        'thickness': features_dict['thickness']
                    }
                
                # Store features for later use
                extracted_params['features_dict'] = features_dict
                
                logger.info(f"STL analysis completed for file_id: {file_id}")
                
        elif file_type and file_type.lower() in ["stp", "step"] or file_name.lower().endswith((".stp", ".step")):
            # Extract from STP file
            stp_features = analyze_step_file(temp_file_path)
            if stp_features:
                features_df = pd.DataFrame(stp_features)
                features_dict = features_df.iloc[0, :].to_dict()
                
                # Extract dimensions from STP
                if 'length' in features_dict and 'width' in features_dict and 'thickness' in features_dict:
                    extracted_params['dimensions'] = {
                        'length': features_dict['length'],
                        'width': features_dict['width'],
                        'thickness': features_dict['thickness']
                    }
                
                # Store features for later use
                extracted_params['features_dict'] = features_dict
                
                logger.info(f"STP analysis completed for file_id: {file_id}")
        
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error extracting parameters from base64 file {file_name} (file_id: {file_id}): {e}")
        # Clean up temporary file if it exists
        temp_file_path = f"temp_{file_name}"
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    
    return extracted_params

async def extract_parameters_from_file(file: UploadFile, file_id: Optional[str] = None) -> Dict[str, Any]:
    """Extract parameters from uploaded CAD file (STL/STP)"""
    logger.info(f"Extracting parameters from file: {file.filename} (file_id: {file_id})")
    
    extracted_params = {}
    
    try:
        # Save uploaded file temporarily for processing
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Determine file type and extract parameters
        if file.filename.lower().endswith((".stl")):
            # Extract from STL file
            stl_features = analyze_stl_file(temp_file_path)
            if stl_features:
                features_df = pd.DataFrame(stl_features)
                features_dict = features_df.iloc[0, :].to_dict()
                
                # Extract dimensions from STL
                if 'length' in features_dict and 'width' in features_dict and 'thickness' in features_dict:
                    extracted_params['dimensions'] = {
                        'length': features_dict['length'],
                        'width': features_dict['width'],
                        'thickness': features_dict['thickness']
                    }
                
                # Store features for later use
                extracted_params['features_dict'] = features_dict
                
                logger.info(f"STL analysis completed for file_id: {file_id}")
                
        elif file.filename.lower().endswith((".stp", ".step")):
            # Extract from STP file
            stp_features = analyze_step_file(temp_file_path)
            if stp_features:
                features_df = pd.DataFrame(stp_features)
                features_dict = features_df.iloc[0, :].to_dict()
                
                # Extract dimensions from STP
                if 'length' in features_dict and 'width' in features_dict and 'thickness' in features_dict:
                    extracted_params['dimensions'] = {
                        'length': features_dict['length'],
                        'width': features_dict['width'],
                        'thickness': features_dict['thickness']
                    }
                
                # Store features for later use
                extracted_params['features_dict'] = features_dict
                
                logger.info(f"STP analysis completed for file_id: {file_id}")
        
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error extracting parameters from file {file.filename} (file_id: {file_id}): {e}")
        # Clean up temporary file if it exists
        temp_file_path = f"temp_{file.filename}"
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    
    return extracted_params

def apply_parameter_safeguards(params: Dict[str, Any], service_id: str) -> Dict[str, Any]:
    """Apply safeguards and default values for missing parameters"""
    logger.info(f"Applying parameter safeguards for service: {service_id}")
    
    # Default dimensions if not provided
    if 'dimensions' not in params or not params['dimensions']:
        params['dimensions'] = {
            'length': 100.0,  # Default 100mm
            'width': 50.0,    # Default 50mm
            'thickness': 10.0  # Default 10mm
        }
        logger.warning("Using default dimensions: 100x50x10 mm")
    
    # Default quantity
    if 'quantity' not in params or not params['quantity']:
        params['quantity'] = 1
        logger.warning("Using default quantity: 1")
    
    # Default material based on service
    if 'material_id' not in params or not params['material_id']:
        if service_id == "printing":
            params['material_id'] = "PA11"  # Default plastic for 3D printing
            params['material_form'] = "powder"
        elif service_id in ["cnc-milling", "cnc-lathe"]:
            params['material_id'] = "alum_D16"  # Default aluminum for CNC
            params['material_form'] = "sheet"
        else:
            params['material_id'] = "alum_D16"
            params['material_form'] = "sheet"
        logger.warning(f"Using default material for {service_id}: {params['material_id']}")
    
    # Default cover processing
    if 'id_cover' not in params or not params['id_cover']:
        params['id_cover'] = ["1"]  # Default painting
        logger.warning("Using default cover processing: painting")
    
    # Default location
    if 'location' not in params or not params['location']:
        params['location'] = "location_1"
        logger.warning("Using default location: location_1")
    
    # Service-specific defaults
    if service_id == "printing":
        if 'n_dimensions' not in params or not params['n_dimensions']:
            params['n_dimensions'] = 1
            logger.warning("Using default n_dimensions: 1")
        if 'k_type' not in params or not params['k_type']:
            params['k_type'] = 1.0
            logger.warning("Using default k_type: 1.0")
        if 'k_process' not in params or not params['k_process']:
            params['k_process'] = 1.0
            logger.warning("Using default k_process: 1.0")
    
    # Default quality control
    if 'k_otk' not in params or not params['k_otk']:
        params['k_otk'] = 1.0
        logger.warning("Using default k_otk: 1.0")
    
    # Default certification
    if 'k_cert' not in params or not params['k_cert']:
        params['k_cert'] = []
        logger.warning("Using default k_cert: no certification")
    
    return params

async def route_calculation(service_id: str, params: Dict[str, Any], file_id: Optional[str] = None) -> UnifiedCalculationResponse:
    """Route calculation to appropriate service based on service_id"""
    logger.info(f"Routing calculation to service: {service_id} (file_id: {file_id})")
    
    try:
        # Extract dimensions for calculation
        dimensions = params.get('dimensions', {})
        length = dimensions.get('length', 100.0)
        width = dimensions.get('width', 50.0)
        thickness = dimensions.get('thickness', 10.0)
        
        # Route to appropriate calculation function
        if service_id == "printing":
            result = await calculate_printing_unified(params, file_id)
        elif service_id == "cnc-milling":
            result = await calculate_cnc_milling_unified(params, file_id)
        elif service_id == "cnc-lathe":
            result = await calculate_cnc_lathe_unified(params, file_id)
        elif service_id == "painting":
            result = await calculate_painting_unified(params, file_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown service_id: {service_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in calculation routing for service {service_id} (file_id: {file_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

async def calculate_printing_unified(params: Dict[str, Any], file_id: Optional[str] = None) -> UnifiedCalculationResponse:
    """Unified 3D printing calculation"""
    logger.info(f"Calculating 3D printing price (file_id: {file_id})")
    
    # Extract parameters
    dimensions = params.get('dimensions', {})
    length = dimensions.get('length', 100.0)
    width = dimensions.get('width', 50.0)
    thickness = dimensions.get('thickness', 10.0)
    quantity = params.get('quantity', 1)
    material_id = params.get('material_id', 'PA11')
    material_form = params.get('material_form', 'powder')
    n_dimensions = params.get('n_dimensions', 1)
    k_type = params.get('k_type', 1.0)
    k_process = params.get('k_process', 1.0)
    id_cover = params.get('id_cover', ['1'])
    k_cert = params.get('k_cert', [])
    
    # Use existing calculation logic
    request_data = {
        'length': length,
        'width': width,
        'thickness': thickness,
        'quantity': quantity,
        'material_id': material_id,
        'material_form': material_form,
        'n_dimensions': n_dimensions,
        'k_type': k_type,
        'k_process': k_process,
        'id_cover': id_cover,
        'k_cert': k_cert
    }
    
    result = calculate_printing_price(request_data)
    
    # Convert to unified response
    return UnifiedCalculationResponse(
        file_id=file_id,
        service_id="printing",
        calculation_method="3D Printing Price Calculation",
        detail_price=result['detail_price'],
        detail_price_one=result['detail_price_one'],
        total_price=result['total_price'],
        total_time=result['total_time'],
        mat_volume=result.get('mat_volume'),
        mat_weight=result.get('mat_weight'),
        mat_price=result.get('mat_price'),
        work_price=result.get('work_price'),
        work_time=result.get('work_time'),
        k_quantity=result.get('k_quantity'),
        k_complexity=result.get('k_complexity'),
        manufacturing_cycle=result.get('manufacturing_cycle'),
        suitable_machines=result.get('suitable_machines'),
        n_dimensions=n_dimensions,
        k_type=k_type,
        k_process=k_process,
        extracted_dimensions=Dimensions(length=length, width=width, thickness=thickness),
        used_parameters=params,
        timestamp=datetime.now().isoformat()
    )

async def calculate_cnc_milling_unified(params: Dict[str, Any], file_id: Optional[str] = None) -> UnifiedCalculationResponse:
    """Unified CNC milling calculation"""
    logger.info(f"Calculating CNC milling price (file_id: {file_id})")
    
    # Extract parameters
    dimensions = params.get('dimensions', {})
    length = dimensions.get('length', 100.0)
    width = dimensions.get('width', 50.0)
    thickness = dimensions.get('thickness', 10.0)
    quantity = params.get('quantity', 1)
    material_id = params.get('material_id', 'alum_D16')
    material_form = params.get('material_form', 'sheet')
    id_cover = params.get('id_cover', ['1'])
    k_cert = params.get('k_cert', [])
    
    # Use existing calculation logic
    request_data = {
        'length': length,
        'width': width,
        'thickness': thickness,
        'quantity': quantity,
        'material_id': material_id,
        'material_form': material_form,
        'id_cover': id_cover,
        'k_cert': k_cert
    }
    
    result = calculate_cnc_milling_price(request_data)
    
    # Convert to unified response
    return UnifiedCalculationResponse(
        file_id=file_id,
        service_id="cnc-milling",
        calculation_method="CNC Milling Price Calculation",
        detail_price=result['detail_price'],
        detail_price_one=result['detail_price_one'],
        total_price=result['total_price'],
        total_time=result['total_time'],
        mat_volume=result.get('mat_volume'),
        mat_weight=result.get('mat_weight'),
        mat_price=result.get('mat_price'),
        work_price=result.get('work_price'),
        work_time=result.get('work_time'),
        k_quantity=result.get('k_quantity'),
        k_complexity=result.get('k_complexity'),
        manufacturing_cycle=result.get('manufacturing_cycle'),
        suitable_machines=result.get('suitable_machines'),
        extracted_dimensions=Dimensions(length=length, width=width, thickness=thickness),
        used_parameters=params,
        timestamp=datetime.now().isoformat()
    )

async def calculate_cnc_lathe_unified(params: Dict[str, Any], file_id: Optional[str] = None) -> UnifiedCalculationResponse:
    """Unified CNC lathe calculation"""
    logger.info(f"Calculating CNC lathe price (file_id: {file_id})")
    
    # Extract parameters
    dimensions = params.get('dimensions', {})
    length = dimensions.get('length', 100.0)
    width = dimensions.get('width', 50.0)
    thickness = dimensions.get('thickness', 10.0)
    quantity = params.get('quantity', 1)
    material_id = params.get('material_id', 'alum_D16')
    material_form = params.get('material_form', 'rod')
    id_cover = params.get('id_cover', ['1'])
    k_cert = params.get('k_cert', [])
    
    # Use existing calculation logic
    request_data = {
        'length': length,
        'width': width,
        'thickness': thickness,
        'quantity': quantity,
        'material_id': material_id,
        'material_form': material_form,
        'id_cover': id_cover,
        'k_cert': k_cert
    }
    
    result = calculate_cnc_lathe_price(request_data)
    
    # Convert to unified response
    return UnifiedCalculationResponse(
        file_id=file_id,
        service_id="cnc-lathe",
        calculation_method="CNC Lathe Price Calculation",
        detail_price=result['detail_price'],
        detail_price_one=result['detail_price_one'],
        total_price=result['total_price'],
        total_time=result['total_time'],
        mat_volume=result.get('mat_volume'),
        mat_weight=result.get('mat_weight'),
        mat_price=result.get('mat_price'),
        work_price=result.get('work_price'),
        work_time=result.get('work_time'),
        k_quantity=result.get('k_quantity'),
        k_complexity=result.get('k_complexity'),
        manufacturing_cycle=result.get('manufacturing_cycle'),
        suitable_machines=result.get('suitable_machines'),
        extracted_dimensions=Dimensions(length=length, width=width, thickness=thickness),
        used_parameters=params,
        timestamp=datetime.now().isoformat()
    )

async def calculate_painting_unified(params: Dict[str, Any], file_id: Optional[str] = None) -> UnifiedCalculationResponse:
    """Unified painting calculation"""
    logger.info(f"Calculating painting price (file_id: {file_id})")
    
    # Extract parameters
    dimensions = params.get('dimensions', {})
    length = dimensions.get('length', 100.0)
    width = dimensions.get('width', 50.0)
    thickness = dimensions.get('thickness', 10.0)
    quantity = params.get('quantity', 1)
    material_id = params.get('material_id', 'alum_D16')
    material_form = params.get('material_form', 'sheet')
    id_cover = params.get('id_cover', ['1'])
    k_cert = params.get('k_cert', [])
    
    # Use existing calculation logic
    request_data = {
        'length': length,
        'width': width,
        'thickness': thickness,
        'quantity': quantity,
        'material_id': material_id,
        'material_form': material_form,
        'id_cover': id_cover,
        'k_cert': k_cert
    }
    
    result = calculate_painting_price(request_data)
    
    # Convert to unified response
    return UnifiedCalculationResponse(
        file_id=file_id,
        service_id="painting",
        calculation_method="Painting Price Calculation",
        detail_price=result['detail_price'],
        detail_price_one=result['detail_price_one'],
        total_price=result['total_price'],
        total_time=result['total_time'],
        mat_volume=result.get('mat_volume'),
        mat_weight=result.get('mat_weight'),
        mat_price=result.get('mat_price'),
        work_price=result.get('work_price'),
        work_time=result.get('work_time'),
        k_quantity=result.get('k_quantity'),
        k_complexity=result.get('k_complexity'),
        manufacturing_cycle=result.get('manufacturing_cycle'),
        suitable_machines=result.get('suitable_machines'),
        extracted_dimensions=Dimensions(length=length, width=width, thickness=thickness),
        used_parameters=params,
        timestamp=datetime.now().isoformat()
    )

# 5. Create the API endpoints

# Analyzing endpoints

@app.post("/analyze_base_stp_file/", tags=["Analyzing CAD"]) 
async def analyze_stp_file_endpoint(
    file: UploadFile = File(..., description="STP file to be analyzed.")
    ) -> dict:
    """Accepts an STP file and analyzes topology and complexity."""

    # Check if the uploaded file is an STP file
    if not file.filename.lower().endswith((".stp", ".step")):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .stp or .step file.")

    try:
        # Save uploaded file temporarily for processing
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Analyze STP file
        topology_features_list = analyze_step_file(temp_file_path)
        features_df = pd.DataFrame(topology_features_list)
        features_df = features_df.iloc[0, :].to_dict()

        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        return features_df
    
    except Exception as e:
        # Clean up temporary file if it exists
        temp_file_path = f"temp_{file.filename}"
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=400, detail=f"Error analyzing STP file: {e}")

@app.post("/analyze_base_stl_file/", tags=["Analyzing CAD"]) 
async def analyze_stl_file_endpoint(
    file: UploadFile = File(..., description="STL file to be analyzed.")
    ) -> dict:
    """Accepts an STL file and analyzes topology and complexity."""

    # Check if the uploaded file is an STL file
    if not file.filename.lower().endswith((".stl")):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .stl file.")

    try:
        # Save uploaded file temporarily for processing
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Analyze STL file
        topology_features_list = analyze_stl_file(temp_file_path)
        features_df = pd.DataFrame(topology_features_list)
        features_df = features_df.iloc[0, :].to_dict()

        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        return features_df

    except Exception as e:
        # Clean up temporary file if it exists
        temp_file_path = f"temp_{file.filename}"
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=400, detail=f"Error analyzing STL file: {e}")

# Manufacturing Calculation Endpoints
@app.post("/3dprinting", response_model=CalculationResponse, tags=["Manufacturing Calculations"])
async def calculate_3d_printing(request: PrintingRequest) -> CalculationResponse:
    """
    Calculate 3D printing price based on dimensions and parameters
    """
    try:
        request_data = request.model_dump()
        result = calculate_printing_price(request_data)
        
        return build_calc_response(result, "3D printing calculation completed successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": f"Calculation error (3dprinting): {str(e)}"})

@app.post("/cnc-milling", response_model=CalculationResponse, tags=["Manufacturing Calculations"])
async def calculate_cnc_milling(request: CNCMillingRequest) -> CalculationResponse:
    """
    Calculate milling price based on dimensions and parameters
    """
    try:
        request_data = request.model_dump()
        result = calculate_cnc_milling_price(request_data)
        
        return build_calc_response(result, "CNC milling calculation completed successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": f"Calculation error (cnc-milling): {str(e)}"})

@app.post("/cnc-lathe", response_model=CalculationResponse, tags=["Manufacturing Calculations"])
async def calculate_cnc_lathe(request: CNCLatheRequest) -> CalculationResponse:
    """
    Calculate CNC price based on dimensions and parameters
    """
    try:
        request_data = request.model_dump()
        result = calculate_cnc_lathe_price(request_data)
        logger.info(result)
        return build_calc_response(result, "CNC lathe calculation completed successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": f"Calculation error (cnc-lathe): {str(e)}"})

@app.post("/cnc_auto", response_model=CalculationResponse, tags=["Manufacturing Calculations"])
async def calculate_cnc_auto(request: StepRequest) -> CalculationResponse:
    """
    Calculate CNC price automatically
    """
    try:
        request_data = request.model_dump()
        result = calculate_from_step(request_data)
        return build_calc_response(result, "CNC automatically calculation completed successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": f"Calculation error (cnc): {str(e)}"})

@app.post("/printing_auto", response_model=CalculationResponse, tags=["Manufacturing Calculations"])
async def calculate_printing_auto(request: StlRequest) -> CalculationResponse:
    """
    Calculate 3D-printing price automatically
    """
    try:
        request_data = request.model_dump()
        result = calculate_from_stl(request_data)
        return build_calc_response(result, "Printing automatically calculation completed successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": f"Calculation error (printing_auto): {str(e)}"})

@app.post("/painting", response_model=CalculationResponse, tags=["Manufacturing Calculations"])
async def calculate_painting(request: PaintingRequest) -> CalculationResponse:
    """
    Calculate painting price based on area and parameters
    """
    try:
        request_data = request.model_dump()
        result = calculate_painting_price(request_data)
        
        return build_calc_response(result, "Painting calculation completed successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": f"Calculation error (painting): {str(e)}"})

@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint
    """
    return {"status": "healthy", "message": "STL & STP Manufacturing calculations API is running"}

@app.get("/", tags=["System"])
def read_root():
    return {
        "message": "Welcome to the STL & STP Manufacturing Calculations API",
        "version": APP_VERSION,
        "endpoints": {
            "Analyzing CAD": {
                "Stp files": "/analyze_base_stp_file/",
                "Stl files": "/analyze_base_stl_file/"
            },
            "Manufacturing Calculations": {
                "3D Printing": "/3dprinting",
                "CNC Milling": "/cnc-milling", 
                "CNC Lathe": "/cnc-lathe",
                "Painting": "/painting"
            },
            "System": {
                "Health Check": "/health"
            },
            "Configuration": {
                "Coefficients": "/coefficients",
                "Services": "/services",
                "materials": "/materials"
            },
            "Documentation": "/docs"
        }
    }

# Options endpoint for coefficients
@app.get("/coefficients", tags=["Configuration"])
async def list_coefficients() -> Dict[str, Any]:
    return {
        "tolerance": [{"id": k, "value": v["label"]} for k, v in TOLERANCE.items()],
        "finish":    [{"id": k, "value": v["label"]} for k, v in FINISH.items()],
        "cover":     [{"id": k, "value": v["label"]} for k, v in COVER.items()],
        "paint_types": [{"id": k, "value": k.capitalize()} for k in PAINT_COEFFICIENTS.keys()],
        "paint_prepare": [{"id": k, "value": k.upper()} for k in PROCESS_COEFFICIENTS["paint_prepare"].keys()],
        "paint_primer":  [{"id": k, "value": k.upper()} for k in PROCESS_COEFFICIENTS["paint_primer"].keys()],
        "paint_lakery":  [{"id": k, "value": k.upper()} for k in PROCESS_COEFFICIENTS["paint_lakery"].keys()],
        "cert_types": [{"id": k, "value": k.upper()} for k in CERT_COSTS.keys()],
    }

@app.get("/materials", tags=["Configuration"])
async def list_materials(process: Optional[str] = None) -> dict:
    """Return structured list of materials for given service"""
    materials_list = []
    for mat_id, mat in MATERIALS.items():
        # Check if this material is applicable to the requested process
        is_applicable = False
        if process:
            for form in mat.get("forms", {}).values():
                price = form.get("price", 0)
                processes = form.get("applicable_processes", [])
                if price > 0 and process in processes:
                    is_applicable = True
                    break
        else:
            # If no process specified, include all materials
            is_applicable = True
        
        if is_applicable:
            # Calculate average price from available forms
            form_prices = [form.get("price", 0) for form in mat.get("forms", {}).values() if form.get("price", 0) > 0]
            avg_price = sum(form_prices) / len(form_prices) if form_prices else 0
            
            material_info = {
                "id": mat_id,
                "name": mat.get("label", mat_id),
                "category": mat.get("family", "unknown"),
                "density": mat.get("density", 0),
                "forms": list(mat.get("forms", {}).keys()),
                "processes": mat.get("applicable_processes", []),
                "price_per_kg": round(avg_price, 2)
            }
            materials_list.append(material_info)
    
    return {"materials": materials_list}

@app.get("/services", tags=["Configuration"])
async def list_services(tag="Manufacturing Calculations") -> List[str]:
    """Return list of services by tag"""
    services_list = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if "POST" not in route.methods:
            continue
        route_tags = route.tags or []
        if tag in route_tags:
            services_list.append(route.path.replace("/", ""))

    return services_list

# Unified calculation endpoint
@app.post("/calculate-price", response_model=UnifiedCalculationResponse, tags=["Manufacturing Calculations"])
async def calculate_price(request: UnifiedCalculationRequest):
    """
    Unified price calculation endpoint that:
    1. Accepts file upload + file_id for tracking
    2. Extracts parameters from file if not provided
    3. Applies safeguards for missing parameters
    4. Routes to appropriate calculation flow based on service_id
    5. Returns unified response with all calculated values
    
    **File Upload**: Upload a CAD file (STL/STP) for automatic parameter extraction
    **File ID Tracking**: Provide file_id from external service database for logging
    **Parameter Override**: Override any extracted parameters with manual values
    **Safeguards**: Missing parameters are filled with sensible defaults
    """
    
    # Log file processing with file_id
    if request.file_id:
        logger.info(f"Processing file_id: {request.file_id} for service: {request.service_id}")
    
    # Process file if provided
    extracted_params = {}
    if request.file_data and request.file_name:
        logger.info(f"Analyzing file: {request.file_name} (file_id: {request.file_id})")
        extracted_params = await extract_parameters_from_base64_file(
            request.file_data, 
            request.file_name, 
            request.file_type,
            request.file_id
        )
    
    # Convert request to dict and merge with extracted parameters
    request_dict = request.dict(exclude_none=True)
    final_params = {**extracted_params, **request_dict}
    
    # Apply safeguards for missing parameters
    final_params = apply_parameter_safeguards(final_params, request.service_id)
    
    # Route to appropriate calculation flow
    result = await route_calculation(request.service_id, final_params, request.file_id)
    
    # Add filename to response if file was provided
    if request.file_name:
        result.filename = request.file_name
    
    logger.info(f"Calculation completed for service: {request.service_id} (file_id: {request.file_id})")
    return result
