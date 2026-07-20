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
    detail_price: float = Field(..., description="Actual unit price for the current order after distributed tooling and k_quantity")
    part_price_one: float = Field(..., description="Calculated price of one part in order")
    detail_price_one: float = Field(..., description="Reference unit price before k_quantity; includes distributed special tooling when applicable")
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
    k_cover: Optional[float] = Field(None, description="Cover processing coefficient")
    k_tolerance: Optional[float] = Field(None, description="Tolerance coefficient")
    k_finish: Optional[float] = Field(None, description="Finish coefficient")
    
    # Manufacturing details
    manufacturing_cycle: Optional[float] = Field(None, description="Cycle of manufacturing in days")
    suitable_machines: Optional[List[str]] = Field(None, description="Suitable manufacturing machines")

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
    detail_price_calculation: Optional[Dict[str, Any]] = Field(None, description="Compact frontend calculation: material, labor, tooling, price without VAT, VAT, total")

    # Electroplating-specific fields
    electroplating_process_id: Optional[str] = Field(None, description="Galvanic process ID used in electroplating_auto")
    electroplating_family: Optional[str] = Field(None, description="Material family ID used in electroplating_auto")
    coating_thickness_microns: Optional[float] = Field(None, description="Coating/layer thickness in microns, if applicable")
    processing_depth_microns: Optional[float] = Field(None, description="Material removal depth in microns, if applicable")
    process_parameter_microns: Optional[float] = Field(None, description="Micron-scale process parameter actually used by the selected time model")
    process_parameter_name: Optional[str] = Field(None, description="Name of the micron-scale process parameter used by the selected time model")
    process_time_model: Optional[str] = Field(None, description="Time calculation model used for the selected electroplating operation")
    thickness_role: Optional[str] = Field(None, description="Meaning of the micron parameter: coating, oxide layer, removed layer, reference, or not applicable")
    coating_surface_area_dm2: Optional[float] = Field(None, description="Processed surface area in dm²")
    coating_mass_kg: Optional[float] = Field(None, description="Part mass used for electroplating labor norms")
    batch_quantity: Optional[int] = Field(None, description="Actual n used in electroplating labor formula: maximum practical parts that fit in one bath, or 1 in single-part fallback")
    requested_quantity: Optional[int] = Field(None, description="Requested order quantity from API request")
    bath_batch_capacity: Optional[int] = Field(None, description="Maximum number of parts that can be treated in one bath by practical geometry/current/weight limits")
    bath_geometric_capacity: Optional[int] = Field(None, description="Ideal number of parts that fit on the hanging plane by the two largest OBB dimensions")
    bath_practical_geometric_capacity: Optional[int] = Field(None, description="Practical hanging-plane capacity used for batch sizing after technological derating")
    bath_current_capacity: Optional[int] = Field(None, description="Maximum number of parts allowed by current limit")
    bath_weight_capacity: Optional[int] = Field(None, description="Maximum number of parts allowed by bath max_weight_kg")
    bath_max_weight_kg: Optional[float] = Field(None, description="Maximum total batch weight allowed for the selected galvanic operation")
    batch_weight_kg: Optional[float] = Field(None, description="Total weight of the selected one-bath batch quantity")
    batch_count: Optional[int] = Field(None, description="Estimated number of electroplating batches for requested quantity")
    batch_quantity_limited_by: Optional[str] = Field(None, description="What limited the formula n: geometry, current, weight, or a combined limit")
