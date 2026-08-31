"""
Request models for the unified API
"""

from pydantic import ConfigDict, Field
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
    k_otk: Optional[float] = Field(None, ge=0, le=2, description="Quality control coefficient")
    
    
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
    material_snapshot: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Optional material catalog entry from backend materials sync. "
            "When present, overrides constants.MATERIALS for this request."
        ),
    )


class TotalPriceBreakdownInput(BaseModel):
    """Editable detailed price-calculation values."""

    model_config = ConfigDict(extra="allow")

    mat_price: Optional[float] = None
    dop_mat_price: Optional[float] = None
    price_of_hour_with_others: Optional[float] = None
    price_special_equipment_to_quantity: Optional[float] = None
    administrative_expenses: Optional[float] = None
    cost: Optional[float] = None
    detail_price: Optional[float] = None
    dop_salary: Optional[float] = None
    insurance_price: Optional[float] = None
    is_need_special_equipment: Optional[bool] = None
    material_price_special_equipment: Optional[float] = None
    net_cost: Optional[float] = None
    overhead_expenses: Optional[float] = None
    price_of_hour: Optional[float] = None
    price_special_equipment: Optional[float] = None
    profit: Optional[float] = None
    total_time: Optional[float] = None
    work_price: Optional[float] = None


class DetailPriceCalculationInput(BaseModel):
    """Editable compact frontend price-calculation values."""

    model_config = ConfigDict(extra="allow")

    material_price: Optional[float] = None
    price_special_equipment: Optional[float] = None
    price_without_vat: Optional[float] = None
    salary_fund_with_taxes: Optional[float] = None
    taxes: Optional[float] = None
    total: Optional[float] = None


class PriceRecalculationRequest(BaseModel):
    """An order product and its editable calculation snapshot."""

    model_config = ConfigDict(extra="allow")

    order_id: Optional[Any] = None
    order_name: Optional[str] = None
    order_code: Optional[str] = None
    service_id: Optional[str] = None
    material_id: Optional[str] = None
    finish_id: Optional[str] = None
    tolerance_id: Optional[str] = None
    cover_id: Optional[List[str]] = None
    k_otk: Optional[float] = None
    manufacturing_cycle: Optional[float] = None
    coating_thickness_microns: Optional[float] = None
    electroplating_family: Optional[str] = None
    electroplating_process_id: Optional[str] = None
    is_need_special_equipment: Optional[bool] = None
    k_quantity: Optional[float] = None
    mat_price: Optional[float] = None
    material_form: Optional[str] = None
    processing_depth_microns: Optional[float] = None
    special_instructions: Optional[str] = None
    work_price: Optional[float] = None
    file_id: Optional[Any] = None
    document_ids: Optional[List[Any]] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    mat_volume: Optional[float] = None
    mat_weight: Optional[float] = None
    total_time: Optional[float] = None
    detail_price_one: Optional[float] = None
    quantity: int = Field(..., ge=1)
    total_price_breakdown: TotalPriceBreakdownInput
    detail_price_calculation: DetailPriceCalculationInput
    