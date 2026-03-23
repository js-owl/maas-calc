"""
Base models and common data structures
"""

from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum


class BaseModel(PydanticBaseModel):
    """Base model with common configuration"""
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True
    )


class MaterialForm(str, Enum):
    """Material form enumeration"""
    POWDER = "powder"
    SHEET = "sheet"
    ROD = "rod"
    HEXAGON = "hexagon"


class Dimensions(BaseModel):
    """Dimensions extracted from file or provided manually"""
    length: float = Field(..., gt=0, description="Length in mm")
    width: float = Field(..., gt=0, description="Width in mm")
    height: float = Field(..., gt=0, description="height in mm")
    
    def volume(self) -> float:
        """Calculate volume in cubic mm"""
        return self.length * self.width * self.height
    
    def __str__(self) -> str:
        return f"{self.length}x{self.width}x{self.height} mm"


class ServiceType(str, Enum):
    """Manufacturing service types"""
    PRINTING = "printing"
    CNC_MILLING = "cnc-milling"
    CNC_LATHE = "cnc-lathe"
    PAINTING = "painting"


class CalculationMethod(str, Enum):
    """Calculation methods"""
    PRINTING_PRICE = "3D Printing Price Calculation"
    CNC_MILLING_PRICE = "CNC Milling Price Calculation"
    CNC_LATHE_PRICE = "CNC Lathe Price Calculation"
    PAINTING_PRICE = "Painting Price Calculation"
