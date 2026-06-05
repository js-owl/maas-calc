"""
Request models for the unified API
"""

from pydantic import Field
from typing import Optional, List, Dict, Any
from .base_models import BaseModel, Dimensions, MaterialForm


class UnifiedCalculationRequest(BaseModel):
    """Unified request model for price calculation with file_id tracking"""
    # Required fields
    service_id: str = Field(..., description="Manufacturing service ID (printing, cnc-milling, composite, electroplating_auto)")
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
    cover_id: Optional[List[str]] = Field(None, description="Override cover processing IDs")
    tolerance_id: Optional[str] = Field(None, description="Override tolerance ID")
    finish_id: Optional[str] = Field(None, description="Override finish ID")
    k_cert: Optional[List[str]] = Field(None, description="Override certification types")

    # Manufacturing-specific parameters
    k_type: Optional[float] = Field(None, ge=0, le=2, description="Type coefficient")
    k_process: Optional[float] = Field(None, ge=0, le=2, description="Process coefficient")
    k_otk: Optional[float] = Field(None, ge=0, le=2, description="Quality control coefficient")
    
    # CNC-specific parameters
    cnc_complexity: Optional[str] = Field(None, description="CNC complexity level")
    cnc_setup_time: Optional[float] = Field(None, description="CNC setup time override")
    
    # Location and features
    location: Optional[str] = Field(None, description="Location of manufacture")
    features_dict: Optional[Dict[str, Any]] = Field(None, description="Features extracted from model")

    # Composite-specific parameters
    is_need_special_equipment: Optional[int] = Field(
        None,
        ge=0,
        le=1,
        description="Whether composite technological tooling is needed: 0 - no, 1 - yes"
    )

    # Electroplating-specific parameters
    electroplating_process_id: Optional[str] = Field(
        None,
        description="Galvanic process ID for service_id='electroplating_auto'. If omitted, first cover_id is used."
    )
    electroplating_family: Optional[str] = Field(
        None,
        description=(
            "Material family ID for service_id='electroplating_auto' "
            "(for example: carbon_steel, stainless_steel, aluminum, copper, titanium). "
            "This is preferred over material_id for electroplating pricing."
        )
    )
    coating_thickness_microns: Optional[float] = Field(
        None,
        ge=0,
        description="Coating/layer thickness in microns for coating or anodizing processes"
    )
    processing_depth_microns: Optional[float] = Field(
        None,
        ge=0,
        description="Material removal depth in microns for electropolishing/material-removal processes"
    )
    