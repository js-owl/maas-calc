from typing import Dict, Any

APP_VERSION = "3.3.0"

# Centralized public pricing constants.
MATERIAL_MARKUP_RATE = 0.20
PRINTING_LOCATION = "location_3"
PRINTING_VOLUME_RESERVE_MM = 30.0
PRINTING_VOLUME_SPEED_L_PER_HOUR = 6.0
PRINTING_PREPARATION_TIME_HOURS = 2.0
VAT_RATE = 0.22
QUANTITY_DISCOUNT_CONTROL_POINTS = (
    (1, 1.00),
    (20, 0.98),
    (100, 0.95),
    (500, 0.85),
    (1000, 0.80),
)
ELECTROPLATING_WEIGHT_WORKER_RULES = (
    (8.0, 1),
    (16.0, 2),
    (30.0, 3),
)
ELECTROPLATING_LABOR_TIME_COEF = 1.18
ELECTROPLATING_BATH_CLEARANCE_MM = 50.0
DEFAULT_ELECTROPLATING_PROCESS_ID = "aluminum_anodizing_water"
PRACTICAL_GEOMETRIC_CAPACITY_FACTOR = 0.40

# Composite ML model configuration
COMPOSITE_BUNDLE_PATH = "ml_models/bundle_metalcomposite_lgbm_v0.1.pkl"
ENABLE_COMPOSITE_MODEL = True
COMPOSITE_SPECIAL_EQUIPMENT_MATERIAL = "mdf"
COMPOSITE_SPECIAL_EQUIPMENT_FORM = "plate"
COMPOSITE_SPECIAL_EQUIPMENT_MARGIN = 1.2

# ML Model Configuration
ML_CLASSIFIER_PATH = "ml_models/base_model_xgb_classification_v0.04.json" # predict bool feature for using special equipment
ML_SCALER_PATH = "ml_models/scaler_v0.04.joblib" 
CLASSIFIER_SCALER_FEATURES_PATH = "ml_models/train_features_v0.04.joblib" 
NUM_CORE_CLASSIFIER_FEATURES = 79 
CLASSIFIER_CATEGORICAL_FEATURES = ['material_bar'] 
ML_CLUSTERER_PATH = "ml_models/kmeans_v0.04.joblib"
ML_REDUCER_PATH = "ml_models/pca_v0.04.joblib"
ENCODER_PATH = "ml_models/ohe_v0.04.joblib"
SPECIAL_EQUIPMENT_COEF = 0.5
SPECIAL_EQUIPMENT_MATERIAL = "non_ferrous_Д16"
SPECIAL_EQUIPMENT_FORM = "sheet"
ENABLE_ML_MODELS = True

MATERIALS_UPDATE_TIMER_SEC = 60

# external materials for other needs, for example for special_equipment
DOP_MATERIALS = {
    "mdf": {
        "label": "МДФ",
        "family": "wood",
        "forms": {
            "plate": {
                "price" : 420.99, 
                "sizes" : "2800x2070x3"
            }
        }
    }
}

FINISH = {
    "1": {"label": "12.5", "value": 0.9},
    "2": {"label": "6.3", "value": 0.95},
    "3": {"label": "3.2", "value": 1},
    "4": {"label": "1.6", "value": 1.05},
    "5": {"label": "0.8", "value": 1.1},
}

COVER = {
    "1": {"label": "Покраска", "value": 1.05, "cycle_time": 1.0},
    "2": {"label": "Гальваника", "value": 1.15, "cycle_time": 2.0},
}

TOLERANCE = {
    "1": {"label": "IT7", "value": 1.15},
    "2": {"label": "IT8", "value": 1.1},
    "3": {"label": "IT9", "value": 1.05},
    "4": {"label": "IT10", "value": 1},
    "5": {"label": "IT11", "value": 0.95},
    "6": {"label": "IT12", "value": 0.9},
}

CONTROL_TYPES = {
    "1": {"label": "Изготовителя", "value": 1.0}, 
    "2": {"label": "Заказчика на площадке изготовителя", "value": 1.2}, 
    "3": {"label": "Независимой приёмкой", "value": 1.15}, 
}

CERT_COSTS = {
    "1": {"label": "a", "value": 0.0}, 
    "2": {"label": "b", "value": 0.0}, 
    "3": {"label": "c", "value": 0.0}, 
    "4": {"label": "d", "value": 0.0}, 
    "5": {"label": "d", "value": 0.0}, 
    "6": {"label": "e", "value": 0.0}, 
    "7": {"label": "f", "value": 0.0}, 
}

# services with auto calculator
AUTO_SERVICES = {
    "1": {"label": "3D-печать", "service": "printing"},
    "2": {"label": "Механическая обработка", "service": "cnc-milling"},
    "3": {"label": "Изготовление деталей из ПКМ", "service": "composite"},
    "4": {"label": "Нанесение гальванических покрытий", "service": "electroplating_auto"}
}

# services with individual pages, save data and translate to bitrix only
NON_AUTO_SERVICES = {
    "1": {
            "label": "Гальваника", 
            "service": "electroplating",
    },
    "2": {
            "label": "Прочее", 
            "service": "other",
    }
}

# services for other_services page
OTHER_SERVICES = {
    "1": {"label": "Листогибочные работы", "service": "bending"},
    "2": {"label": "Слесарные работы", "service": "handing"},
    "3": {"label": "Термическая обработка", "service": "heating"},
    "4": {"label": "Лазерная резка", "service": "laser-cutting"},
    "5": {"label": "Шлифование", "service": "grinding"},
    "6": {"label": "Сварочные работы", "service": "welding"},
    "7": {"label": "Нанесение ЛКМ", "service": "painting"},
    "8": {"label": "Литьё", "service": "casting"},
    "9": {"label": "Другое", "service": "other"},
    "11": {"label": "Испытательные ресурсы", "service": "testing"},
    "12": {"label": "Производство из резины", "service": "rubber"}
}

# Default values for calculations
DEFAULTS = {
    "location": "location_1",
    "cover_id_list": ["1"],  # cover_id is a list
    "tolerance_id": "1",      # string ID
    "finish_id": "1",         # string ID
    "k_otk": 1.0,
    "k_type": 1.0,
    "k_cert_cnc": ["a", "f"],
    "k_cert_printing": ["a", "f"],
    "control_type": "1",
}

CYCLE_TIME_DEFAULTS = {
    "buying_material_time": 3,
    "developing_technology_time": 1,
    "developing_program_time": 3,
    "preparing_material_time": 1,
}


# Error messages
ERROR_MESSAGES = {
    "no_suitable_machines": "We don't have suitable machines",
    "unknown_manufacturing": "Unknown type of manufacturing",
    "validation_error": "Validation Error",
    "file_processing_error": "File Processing Error", 
    "calculation_error": "Calculation Error",
    "service_unavailable": "Service Unavailable",
    "not_found": "Resource Not Found",
    "invalid_material": "Invalid material ID or material not applicable for this process",
    "invalid_dimensions": "Invalid dimensions provided",
    "invalid_quantity": "Invalid quantity provided",
    "file_too_large": "File size exceeds maximum allowed limit",
    "unsupported_file_type": "Unsupported file type",
    "missing_required_field": "Missing required field",
    "invalid_parameter_value": "Invalid parameter value",
    "unknown_cover_id": "Invalid cover id"
}

# Error codes
ERROR_CODES = {
    "VALIDATION_ERROR": "VALIDATION_ERROR",
    "FILE_PROCESSING_ERROR": "FILE_PROCESSING_ERROR",
    "CALCULATION_ERROR": "CALCULATION_ERROR", 
    "SERVICE_UNAVAILABLE": "SERVICE_UNAVAILABLE",
    "NOT_FOUND": "NOT_FOUND",
    "INVALID_MATERIAL": "INVALID_MATERIAL",
    "INVALID_DIMENSIONS": "INVALID_DIMENSIONS",
    "INVALID_QUANTITY": "INVALID_QUANTITY",
    "FILE_TOO_LARGE": "FILE_TOO_LARGE",
    "UNSUPPORTED_FILE_TYPE": "UNSUPPORTED_FILE_TYPE",
    "MISSING_REQUIRED_FIELD": "MISSING_REQUIRED_FIELD",
    "INVALID_PARAMETER_VALUE": "INVALID_PARAMETER_VALUE"
}

# HTTP status codes mapping
HTTP_STATUS_CODES = {
    "VALIDATION_ERROR": 400,
    "FILE_PROCESSING_ERROR": 400,
    "INVALID_MATERIAL": 400,
    "INVALID_DIMENSIONS": 400,
    "INVALID_QUANTITY": 400,
    "FILE_TOO_LARGE": 413,
    "UNSUPPORTED_FILE_TYPE": 415,
    "MISSING_REQUIRED_FIELD": 400,
    "INVALID_PARAMETER_VALUE": 400,
    "NOT_FOUND": 404,
    "CALCULATION_ERROR": 500,
    "SERVICE_UNAVAILABLE": 503
}
