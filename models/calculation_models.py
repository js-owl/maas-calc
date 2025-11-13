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
    n_dimensions: int
    k_type: float
    k_process: float
    k_otk: float
    k_cert: List[str]
    service_id: str


class CNCMillingCalculationRequest(BaseModel):
    """Internal model for CNC milling calculations"""
    file_id: str
    dimensions: Dimensions
    material_id: str
    material_form: MaterialForm
    quantity: int
    cover_id: List[str]
    tolerance_id: str
    finish_id: str
    location: str
    k_otk: float
    cnc_complexity: str
    cnc_setup_time: float


class CNCLatheCalculationRequest(BaseModel):
    """Internal model for CNC lathe calculations"""
    file_id: str
    dimensions: Dimensions
    material_id: str
    material_form: MaterialForm
    quantity: int
    cover_id: List[str]
    tolerance_id: str
    finish_id: str
    location: str
    k_otk: float
    cnc_complexity: str
    cnc_setup_time: float


class PaintingCalculationRequest(BaseModel):
    """Internal model for painting calculations"""
    file_id: str
    dimensions: Dimensions
    material_id: str
    material_form: MaterialForm
    quantity: int
    cover_id: List[str]
    tolerance_id: str
    finish_id: str
    location: str
    k_otk: float
    paint_type: Optional[str] = "epoxy"
    paint_prepare: Optional[str] = "a"
    paint_primer: Optional[str] = "b"
    paint_lakery: Optional[str] = "a"
    control_type: Optional[str] = "1"
    k_cert: List[str] = []