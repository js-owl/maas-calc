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


class CalculationMethod(str, Enum):
    """Calculation methods"""
    PRINTING_PRICE = "3D Printing Price Calculation"
    CNC_MILLING_PRICE = "CNC Milling Price Calculation"
    COMPOSITE_ML = "Composite ML Prediction"
    ELECTROPLATING_AUTO = "Electroplating Auto Calculation"


"""
# MATERIALS specification/template:
MATERIALS: Dict[str, Dict[str, Any]] = {
    material_id: {
        "label": material_name_main + material_name,
        "family": MaterialFamily.X.value,
        "electroplating_family": MaterialFamily.X.value, # deprecated, similar to "family"
        "density": float("nan"),
        "applicable_processes": [ ServiceType.X.value, ... ],
        "forms": {
            MaterialForm.X.value: {
                "price": float("nan"),
                "price_units": [ MaterialPriceUnits.X.value, ... ],
                "applicable_processes": [ ServiceType.X.value, ... ],
                "one_layer_thickness": float("nan"),
            },
            ...
        },
        "material_name": str,
        "material_name_main": MaterialNameMain.X.value,
        "material_group": MaterialGroup.X.value,
        "material_name_group": MaterialNameGroup.X1.value + MaterialNameGroup.X2.value + ..., # concatenated values
        "minimum_order_quantity": float("nan"),
    },
    ...
}
"""

class MaterialNameMain(str, Enum):
    STEEL = "steel", # сталь
    NON_FERROUS = "non_ferrous", # цветные металлы
    COMPOSITE = "composite", # "композит"
    PLASTIC = "plastic" # "пластик"
    OTHER = "other"


class MaterialForm(str, Enum):
    """Material form enumeration"""
    POWDER = "powder" # "порошок"
    SHEET = "sheet" # "лист"
    ROD = "rod" # "пруток"
    HEXAGON = "hexagon" # "шестигранник"
    TEXTILE = "textile" # "ткань"
    PLATE = "plate" # "плита"
    PREPREG = "pre-preg" # "препрег"
    THREAD = "thread" # "нить"
    OTHER = "other" # "другое"

# MaterialForm obj value should be in Dict[MaterialName] list
MaterialForm_validation_dict: Dict[MaterialNameMain, List[MaterialForm]] = {
    MaterialNameMain.STEEL:         [ MaterialForm.SHEET, MaterialForm.ROD, MaterialForm.HEXAGON, MaterialForm.PLATE ],
    MaterialNameMain.NON_FERROUS:   [ MaterialForm.SHEET, MaterialForm.ROD, MaterialForm.HEXAGON, MaterialForm.PLATE ],
    MaterialNameMain.COMPOSITE:     [ MaterialForm.TEXTILE, MaterialForm.PREPREG ],
    MaterialNameMain.PLASTIC:       [ MaterialForm.POWDER, MaterialForm.THREAD ],
}


class ServiceType(str, Enum):
    """Manufacturing service types"""
    PRINTING = "printing" # "3D-печать"
    CNC_MILLING = "cnc-milling" # "механическая обработка"
    COMPOSITE = "composite" # ???
    ELECTROPLATING_AUTO = "electroplating_auto" # "гальваническая обработка"
    OTHER = "other"

# ServiceType obj value should be in Dict[MaterialName] list
ServiceType_validation_dict: Dict[MaterialNameMain, List[ServiceType]] = {
    MaterialNameMain.STEEL:       [ ServiceType.CNC_MILLING, ServiceType.ELECTROPLATING_AUTO, ],
    MaterialNameMain.NON_FERROUS: [ ServiceType.CNC_MILLING, ServiceType.ELECTROPLATING_AUTO, ],
    MaterialNameMain.COMPOSITE:   [ ServiceType.COMPOSITE, ],
    MaterialNameMain.PLASTIC:     [ ServiceType.PRINTING, ],
}


# deprecated, use MaterialFamily instead
class ElectroplatingFamily(str, Enum):
    CARBON = "carbon_steel"
    STAINLESS = "stainless_steel"
    ALUMINIUM = "aluminum"
    COPPER = "copper"
    TITANIUM = "titanium"
    MAGNESIUM = "magnesium"


class MaterialFamily(str, Enum):
    CARBON = "carbon_steel" # "углеродистая"
    STAINLESS = "stainless_steel" # "легированная"
    ALUMINIUM = "aluminium" # "алюминий"
    COPPER = "copper" # "медь"
    TITANIUM = "titanium" # "титан"
    MAGNESIUM = "magnesium" # "магний"
    BRONZE = "bronze", # "бронза"
    LATUN = "latun" # "латунь"
    NICKEL = "nickel" # "никель"
    ZINC = "zinc" # "цинк"
    PLASTIC_3D = "plastic_3d" # "пластик для 3D-печати"
    PCM = "polymer_composites" # "полимерный композиционный материал"
    OTHER = "other"

# MaterialFamily obj value should be in Dict[MaterialName] list
MaterialFamily_validation_dict: Dict[MaterialNameMain, List[MaterialFamily]] = {
    MaterialNameMain.STEEL:       [ MaterialFamily.CARBON, MaterialFamily.STAINLESS, ],
    MaterialNameMain.NON_FERROUS: [ MaterialFamily.ALUMINIUM,
                                    MaterialFamily.BRONZE,
                                    MaterialFamily.LATUN,
                                    MaterialFamily.COPPER,
                                    MaterialFamily.TITANIUM,
                                    MaterialFamily.MAGNESIUM,
                                    MaterialFamily.NICKEL,
                                    MaterialFamily.ZINC, ],
    MaterialNameMain.COMPOSITE:   [ MaterialFamily.PCM, ],
    MaterialNameMain.PLASTIC:     [ MaterialFamily.PLASTIC_3D, ],
}


class MaterialGroup(str, Enum):
    STRUCT_STEEL = "конструкционная", # "structural_steel"
    TOOL_STEEL = "инструментальная", # "tool_steel"
    STRUCT_NON_FE = "деформируемый сплав", # "structural_non_ferrous" == "обрабатываемый давлением"
    CAST_ALLOY = "литейный сплав", # "cast_alloy"
    SI_FABRICS = "кремнеземная ткань", # "silica_fabrics"
    GLASS_FABRICS = "стеклянная ткань", # "glass_fabrics"
    ROVING_FABRICS = "ровинговая ткань", # "roving_fabrics"
    CARBON_FABRICS = "углеродная ткань", # "carbon_fabrics"
    QUARTZ_FABRICS = "кварцевая ткань", # "quartz_fabrics"
    OTHER = "другое", # "other"

# MaterialGroup obj value should be in Dict[MaterialName] list
# empty list means no restrictions
MaterialGroup_validation_dict: Dict[MaterialNameMain, List[MaterialGroup]] = {
    MaterialNameMain.STEEL:       [ MaterialGroup.STRUCT_STEEL, MaterialGroup.TOOL_STEEL, ],
    MaterialNameMain.NON_FERROUS: [ MaterialGroup.STRUCT_NON_FE, MaterialGroup.CAST_ALLOY, ],
    MaterialNameMain.COMPOSITE:   [ MaterialGroup.SI_FABRICS,
                                    MaterialGroup.GLASS_FABRICS,
                                    MaterialGroup.ROVING_FABRICS,
                                    MaterialGroup.CARBON_FABRICS,
                                    MaterialGroup.QUARTZ_FABRICS, ],
    MaterialNameMain.PLASTIC:     [],
}


class MaterialNameGroup(str, Enum):
    CORR_RESIST = "коррозионно-стойкая", # "corrosion_resistant"
    CREEP_RESIST = "жаропрочная", # "creep_resisting"
    SCALE_RESIST = "жаростойкая", # "scaling_resistant"
    HOT_WORK = "теплостойкая", # "hot_work_tool"
    LOW_FRICTION = "антифрикционная", # "low_friction"
    ELECTRO_STEEL = "электротехническая", # "electrical_steel"
    MAGNETIC_STEEL = "магнитная", # "magnetic_steel"
    HS_STEEL = "высокопрочная", # "high_strength_steel"
    UHS_STEEL = "сверхпрочная", # "ultra_high_strength_steel"
    WR_STEEL = "износостойкая", # "wear_resistant_steel"
    HIGH_PURITY = "высокочистый", # "high_purity" == "технический"
    QAULITY = "качественная", # "quality"
    HIGH_QAULITY = "высококачественная", # "high_quality"
    SUPER_QAULITY = "особо качественная", # "superior_quality"
    OTHER = "другое", # "other"

# MaterialNameGroup obj value should be in Dict[MaterialName] list
# empty list means no restrictions
MaterialNameGroup_validation_dict: Dict[MaterialNameMain, List[MaterialNameGroup]] = {
    MaterialNameMain.STEEL:       [ MaterialNameGroup.CORR_RESIST,
                                    MaterialNameGroup.CREEP_RESIST,
                                    MaterialNameGroup.SCALE_RESIST,
                                    MaterialNameGroup.HOT_WORK,
                                    MaterialNameGroup.LOW_FRICTION,
                                    MaterialNameGroup.ELECTRO_STEEL,
                                    MaterialNameGroup.MAGNETIC_STEEL,
                                    MaterialNameGroup.HS_STEEL,
                                    MaterialNameGroup.UHS_STEEL,
                                    MaterialNameGroup.WR_STEEL,
                                    MaterialNameGroup.QAULITY,
                                    MaterialNameGroup.HIGH_QAULITY,
                                    MaterialNameGroup.SUPER_QAULITY, ],
    MaterialNameMain.NON_FERROUS: [ MaterialNameGroup.CORR_RESIST,
                                    MaterialNameGroup.CREEP_RESIST,
                                    MaterialNameGroup.SCALE_RESIST,
                                    MaterialNameGroup.HOT_WORK,
                                    MaterialNameGroup.LOW_FRICTION,
                                    MaterialNameGroup.HIGH_PURITY, ],
    MaterialNameMain.COMPOSITE:   [],
    MaterialNameMain.PLASTIC:     [],
}


class MaterialPriceUnits(str, Enum):
    KG = "kg"
    M = "m"
    M2 = "m2"
