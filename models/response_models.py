"""
Response models for the unified API
"""

from pydantic import Field
from typing import Optional, List, Dict, Any
from .base_models import BaseModel, Dimensions


class UnifiedCalculationResponse(BaseModel):
    """Unified response model containing all calculation results"""
    # File tracking
    file_id: Optional[str] = Field(None, description="File ID from external service database")
    filename: Optional[str] = Field(None, description="Original filename if uploaded")
    
    # Core calculation results
    part_price: float = Field(..., description="Final calculated price per part")
    detail_price: float = Field(..., description="Final calculated price per detail, include needed special equipment, available by ml only")
    part_price_one: float = Field(..., description="Calculated price of one part in order")
    detail_price_one: float = Field(..., description="Calculated price of one detail in order, include needed special equipment, available by ml only")
    total_price: float = Field(..., description="Total price for all quantity of details")
    total_time: float = Field(..., description="Total work time predicted for one part")
    
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
    calculation_engine: Optional[str] = Field(None, description="Calculation engine used (ml_model or rule_based)")
    message: str = Field(default="Calculation completed successfully", description="Status message")
    timestamp: Optional[str] = Field(None, description="Calculation timestamp")
    
    # ML-specific fields
    ml_prediction_hours: Optional[float] = Field(None, description="Raw ML prediction in hours")
    features_extracted: Optional[Dict[str, Any]] = Field(None, description="Key features used in ML prediction")
    material_costs: Optional[Dict[str, Any]] = Field(None, description="Material cost breakdown")
    work_price_breakdown: Optional[Dict[str, Any]] = Field(None, description="Work price calculation breakdown")
    total_price_breakdown: Optional[Dict[str, Any]] = Field(None, description="Total price calculation breakdown")