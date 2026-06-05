"""
Internal calculation models for specific manufacturing processes
"""

from pydantic import Field
from typing import Optional, List, Dict, Any
from .base_models import BaseModel, Dimensions, MaterialForm


class PrintingCalculationRequest(BaseModel):
    """Internal model for 3D printing calculations"""
    file_id: str
    dimensions: Dimensions
    material_id: str
    material_form: MaterialForm
    quantity: int
    cover_id: List[str]
    location: str
    k_type: float
    k_process: float
    k_otk: float
    k_cert: List[str]
    service_id: str

class ElectroplatingCalculationRequest(BaseModel):
    """Internal model for automatic galvanic coating calculations"""
    file_id: str
    ml_features: Dict[str, Any]
    material_id: Optional[str] = None
    material_form: Optional[MaterialForm] = None
    electroplating_family: Optional[str] = None
    quantity: int
    location: str
    cover_id: Optional[List[str]] = None
    electroplating_process_id: Optional[str] = None
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
    k_otk: float = 1.0
    filename: Optional[str] = None
    service_id: str = "electroplating_auto"

