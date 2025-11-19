from typing import Dict, Any

APP_VERSION = "3.3.0"

# ML Model Configuration
ML_REGRESSOR_PATH = "ml_models/base_model_xgb_v0.04log.json"
ML_CLASSIFIER_PATH = "ml_models/base_model_xgb_classification_v0.04.json" # predict bool feature for using special equipment
ML_SCALER_PATH = "ml_models/scaler_v0.04.joblib"
SCALER_FEATURES_PATH = "ml_models/train_features_v0.04.joblib"
NUM_CORE_FEATURES = 79
CATEGORICALS_FEATURES = ['material_bar']
ML_CLUSTERER_PATH = "ml_models/kmeans_v0.04.joblib"
ML_REDUCER_PATH = "ml_models/pca_v0.04.joblib"
ENCODER_PATH = "ml_models/ohe_v0.04.joblib"
SPECIAL_EQUIPMENT_COEF = 0.5
SPECIAL_EQUIPMENT_MATERIAL = "alum_D16"
SPECIAL_EQUIPMENT_FORM = "sheet"
ENABLE_ML_MODELS = True
ML_FALLBACK_TO_RULES = True

# prices: https://fortis-steel.ru/   alum_6061 as fallback just in case
MATERIALS: Dict[str, Dict[str, Any]] = {
    "alum_D16": {
        "label": "Алюминий Д16",
        "family": "alum",
        "density": 2800.0,
        "k_handle": 0.03,
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 847.62,
                "applicable_processes": ["cnc-milling", "painting"],
            }, 
            "rod": {
                "price": 531.08,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            }, 
            "hexagon": {
                "price": 587.44,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            },
        },
        "material_name": "Д16",
        "material_name_main": "Алюминий",
        "material_coef": 1.0,
        "material_group": "Цветные",
        "material_name_group": "Алюминиевый деформируемый сплав",
        "hardness": 42,
        "strenghtness": 245,
        "thermal_conductivity": 160,
        "relative_coef": 1.0
    },
    "alum_AMC": {
        "label": "Алюминий АМц", 
        "family": "alum", 
        "density": 2800.0, 
        "k_handle": 0.03,
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 408.22,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            }, 
            "rod": {
                "price": 471.89,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            }
        },
        "material_name": "АМц",
        "material_name_main": "Алюминий",
        "material_coef": 0.8,
        "material_group": "Цветные",
        "material_name_group": "Алюминиевый деформируемый сплав",
        "hardness": 70,
        "strenghtness": 320,
        "thermal_conductivity": 140,
        "relative_coef": 1.20
    },
    "alum_AMG3": {
        "label": "Алюминий АМг3", 
        "family": "alum", 
        "density": 2800.0, 
        "k_handle": 0.03,
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 433.31,
                "applicable_processes": ["cnc-milling", "painting"],
            }, 
            "rod": {
                "price": 425.75,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            }, 
            "hexagon": {
                "price": 490.65,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            },
        },
        "material_name": "АМг3",
        "material_name_main": "Алюминий",
        "material_coef": 2.5,
        "material_group": "Цветные",
        "material_name_group": "Алюминиевый деформируемый сплав",
        "hardness": 60,
        "strenghtness": 300,
        "thermal_conductivity": 130,
        "relative_coef": 1.20
    },
    "alum_AMG6": {
        "label": "Алюминий АМг6", 
        "family": "alum", 
        "density": 2800.0, 
        "k_handle": 0.03,
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 675.13,
                "applicable_processes": ["cnc-milling", "painting"],
            }, 
            "rod": {
                "price": 560.12,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            }, 
            "hexagon": {
                "price": 705.20,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            },
        },
        "material_name": "АМг6",
        "material_name_main": "Алюминий",
        "material_coef": 2.5,
        "material_group": "Цветные",
        "material_name_group": "Алюминиевый деформируемый сплав",
        "hardness": 80,
        "strenghtness": 350,
        "thermal_conductivity": 120,
        "relative_coef": 1.15
    },
    "steel_12X18H10T": {
        "label": "Сталь 12Х18Н10Т", 
        "family": "steel", 
        "density": 7850.0, 
        "k_handle": 0.045, 
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 515.80,
                "applicable_processes": ["cnc-milling", "painting"],
            }, 
            "rod": {
                "price": 340.40,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            }
        },
        "material_name": "12Х18Н10Т",
        "material_name_main": "Сталь",
        "material_coef": 1.0,
        "material_group": "Труднообрабатываемые",
        "material_name_group": "Конструкционная жаропрочная",
        "hardness": 180,
        "strenghtness": 550,
        "thermal_conductivity": 14,
        "relative_coef": 0.55
    },
    "steel_30XGSA": {
        "label": "Сталь 30ХГСА", 
        "family": "steel", 
        "density": 7850.0, 
        "k_handle": 0.045,
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 263.81,
                "applicable_processes": ["cnc-milling", "painting"],
            }, 
            "rod": {
                "price": 244.63,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            }, 
            "hexagon": {
                "price": 244.63,
                "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
            },
        },
        "material_name": "30ХГСА",
        "material_name_main": "Сталь",
        "material_coef": 0.41,
        "material_group": "Углеродистые и легированные стали",
        "material_name_group": "Конструкционная легированная",
        "hardness": 220,
        "strenghtness": 900,
        "thermal_conductivity": 28,
        "relative_coef": 0.8
    },
    "PA11": {
        "label": "Порошок PA11", 
        "family": "plastic", 
        "density": 1020, 
        "k_handle": 0,
        "applicable_processes": ["printing", "painting"],
        "forms": {
            "powder": {
                "price": 14000,
                "applicable_processes": ["printing", "painting"],
            }
        },
        # "material_name": "",
        # "material_name_main": "",
        # "material_coef": 0,
        # "material_group": "",
        # "material_name_group": ""
    },
    "PA12": {
        "label": "Порошок PA12", 
        "family": "plastic", 
        "density": 930, 
        "k_handle": 0,
        "applicable_processes": ["printing", "painting"],
        "forms": {
            "powder": {
                "price": 9200,
                "applicable_processes": ["printing", "painting"],
            }
        },
        #"material_name": "",
        #"material_name_main": "",
        #"material_coef": 0,
        #"material_group": "",
        # "material_name_group": ""
    },
    "steel_14X17H2": {
        "label": "Сталь 14Х17Н2", 
        "family": "steel", 
        "density": 7850.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc_milling", "cnc_lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 2000,
                "applicable_processes": ["cnc-milling", "painting"],
            },
            "rod": {
                "price": 261.92,
                "applicable_processes": ["cnc-milling", "cnc_lathe"],
            }
        },
        "material_name": "14Х17Н2",
        "material_name_main": "Сталь",
        "material_coef": 0.6,
        "material_group": "Труднообрабатываемые",
        "material_name_group": "Коррозионно-стойкая жаропрочная",
        "hardness": 240,
        "strenghtness": 900,
        "thermal_conductivity": 20,
        "relative_coef": 0.65
    },
    "alum_1163": {
        "label": "Алюминий 1163", 
        "family": "alum", 
        "density": 2800.0, 
        "k_handle": 0.03,
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 1200,
                "applicable_processes": ["cnc-milling", "painting"],
            }
        },
        "material_name": "1163",
        "material_name_main": "Алюминий",
        "material_coef": 0.91,
        "material_group": "Цветные",
        "material_name_group": "Алюминиевый деформируемый сплав",
        "hardness": 130,
        "strenghtness": 470,
        "thermal_conductivity": 155,
        "relative_coef": 0.95
    },
    "alum_B95och": {
        "label": "Алюминий В95оч", 
        "family": "alum", 
        "density": 2800.0, 
        "k_handle": 0.03,
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 1300,
                "applicable_processes": ["cnc-milling", "painting"],
            }
        },
        "material_name": "В95оч",
        "material_name_main": "Алюминий",
        "material_coef": 0.83,
        "material_group": "Цветные",
        "material_name_group": "Алюминиевый деформируемый сплав",
        "hardness": 140,
        "strenghtness": 500,
        "thermal_conductivity": 150,
        "relative_coef": 0.9
    },
    "alum_ad31": {
        "label": "Алюминий АД31", 
        "family": "alum", 
        "density": 2710.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 267.09,
                "applicable_processes": ["cnc-milling", "painting"],
            },
            "rod": {
                "price": 509.17,
                "applicable_processes": ["cnc-lathe", "cnc-milling", "painting"],
            }
        },
        "material_name": "АД31",
        "material_name_main": "Алюминий",
        "material_coef": 0.0,
        "material_group": "Цветные",
        "material_name_group": "Алюминиевый деформируемый сплав",
        "hardness": 80,
        "strenghtness": 260,
        "thermal_conductivity": 170,
        "relative_coef": 1.30
    },
    "alum_ad1": {
        "label": "Алюминий АД1", 
        "family": "alum", 
        "density": 2710.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc-milling", "cnc-lathe", "painting"],
        "forms": {
            "sheet": {
                "price": 310.28,
                "applicable_processes": ["cnc-milling", "painting"],
            },
            "rod": {
                "price": 283.33,
                "applicable_processes": ["cnc-lathe", "cnc-milling", "painting"],
            }
        },
        "material_name": "АД1",
        "material_name_main": "Алюминий",
        "material_coef": 0.0,
        "material_group": "Цветные",
        "material_name_group": "Алюминий технический",
        "hardness": 35,
        "strenghtness": 150,
        "thermal_conductivity": 220,
        "relative_coef": 1.30
    },
    "alum_D16T": {
        "label": "Алюминий Д16Т",
        "family": "alum",
        "density": 2800.0,
        "k_handle": 0.0,
        "applicable_processes": ["cnc-milling", "cnc-lathe"],
        "forms": {
            "sheet": {
                "price": 465.6,
                "applicable_processes": ["cnc-milling"],
            }, 
            "rod": {
                "price": 545.9,
                "applicable_processes": ["cnc-milling", "cnc-lathe"],
            }
        },
        "material_name": "Д16",
        "material_name_main": "Алюминий",
        "material_coef": 0.0,
        "material_group": "Цветные",
        "material_name_group": "Алюминиевый деформируемый сплав",
        "hardness": 105,
        "strenghtness": 450,
        "thermal_conductivity": 160,
        "relative_coef": 0.9
    },
    "steel_40Х13": {
        "label": "Сталь 40Х13", 
        "family": "steel", 
        "density": 7770.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc_milling", "cnc_lathe"],
        "forms": {
            "rod": {
                "price": 196.89,
                "applicable_processes": ["cnc-milling", "cnc-lathe"],
            }
        },
        "material_name": "40Х13",
        "material_name_main": "Сталь",
        "material_coef": 0.0,
        "material_group": "Труднообрабатываемые",
        "material_name_group": "Коррозионно-стойкая жаропрочная",
        "hardness": 230,
        "strenghtness": 700,
        "thermal_conductivity": 25,
        "relative_coef": 0.6
    },
    "alum_АК4": {
        "label": "Алюминий АК4", 
        "family": "alum", 
        "density": 2770.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc-milling"],
        "forms": {
            "sheet": {
                "price": 856.53,
                "applicable_processes": ["cnc-milling"],
            }, 
        },
        "material_name": "АК4",
        "material_name_main": "Алюминий",
        "material_coef": 0.8,
        "material_group": "Цветные",
        "material_name_group": "Алюминиевый деформируемый сплав",
        "hardness": 100,
        "strenghtness": 335,
        "thermal_conductivity": 150,
        "relative_coef": 0.85
    },
    "latun_Л63": {
        "label": "Латунь Л63", 
        "family": "latun", 
        "density": 8440.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc-milling", "cnc-lathe"],
        "forms": {
            "rod": {
                "price": 428.52,
                "applicable_processes": ["cnc-milling", "cnc-lathe"],
            }, 
        },
        "material_name": "Л63",
        "material_name_main": "Латунь",
        "material_coef": 0.0,
        "material_group": "Цветные",
        "material_name_group": "Латунь, обрабатываемая давлением",
        "hardness": 70,
        "strenghtness": 290,
        "thermal_conductivity": 120,
        "relative_coef": 0.9
    },
    "bronze_БрАЖМц10-3-1.5": {
        "label": "Бронза БрАЖМц10-3-1.5", 
        "family": "bronze", 
        "density": 7500.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc-milling", "cnc-lathe"],
        "forms": {
            "rod": {
                "price": 610.21,
                "applicable_processes": ["cnc-milling", "cnc-lathe"],
            }, 
        },
        "material_name": "БрАЖМц10-3-1.5",
        "material_name_main": "Бронза",
        "material_coef": 0.0,
        "material_group": "Цветные",
        "material_name_group": "Бронза безоловянная, обрабатываемая давлением",
        "hardness": 130,
        "strenghtness": 590,
        "thermal_conductivity": 60,
        "relative_coef": 0.7
    },
    "steel_45": {
        "label": "Сталь 45", 
        "family": "steel", 
        "density": 7826.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc-milling", "cnc-lathe"],
        "forms": {
            "rod": {
                "price": 63.03,
                "applicable_processes": ["cnc-milling", "cnc-lathe"],
            }, 
        },
        "material_name": "Ст45",
        "material_name_main": "Сталь",
        "material_coef": 0.0,
        "material_group": "Конструкционная углеродистая качественная",
        "material_name_group": "Углеродистые и легированные стали",
        "hardness": 200,
        "strenghtness": 750,
        "thermal_conductivity": 45,
        "relative_coef": 0.85
    },
    "steel_20": {
        "label": "Сталь 20", 
        "family": "steel", 
        "density": 7859.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc-milling", "cnc-lathe"],
        "forms": {
            "sheet": {
                "price": 68.565,
                "applicable_processes": ["cnc-milling"],
            }, 
            "rod": {
                "price": 55.23,
                "applicable_processes": ["cnc-milling", "cnc-lathe"],
            }, 
        },
        "material_name": "Ст20",
        "material_name_main": "Сталь",
        "material_coef": 0.0,
        "material_group": "Конструкционная углеродистая качественная",
        "material_name_group": "Углеродистые и легированные стали",
        "hardness": 130,
        "strenghtness": 450,
        "thermal_conductivity": 48,
        "relative_coef": 0.95
    },
    "steel_40Х": {
        "label": "Сталь 40Х", 
        "family": "steel", 
        "density": 7820.0, 
        "k_handle": 0.0,
        "applicable_processes": ["cnc-milling", "cnc-lathe"],
        "forms": {
            "hexagon": {
                "price": 74.45,
                "applicable_processes": ["cnc-milling", "cnc-lathe"],
            }
        },
        "material_name": "40Х",
        "material_name_main": "Сталь",
        "material_coef": 0.0,
        "material_group": "Углеродистые и легированные стали",
        "material_name_group": "Конструкционная легированная",
        "hardness": 200,
        "strenghtness": 800,
        "thermal_conductivity": 45,
        "relative_coef": 1.25
    },
    # "alum_6061": {
    #     "label": "Алюминий 6061", "family": "alum", "density": 2700.0, "k_handle": 0.03,
    #     "applicable_processes": ["cnc_milling", "cnc_lathe", "painting"],
    #     "forms": {"plate": {"price": 544.0}, "rod": {"price": 115.0}, "hexagon": {"price": 594.0}}
    # },
    # "alum_D16T": {
    #     "label": "Алюминий Д16Т", 
    #     "family": "alum", 
    #     "density": 2800.0, 
    #     "k_handle": 0.03,
    #     "applicable_processes": ["cnc_milling", "cnc_lathe", "painting"],
    #     "forms": {"plate": {"price": 544.0}, "rod": {"price": 115.0}, "hexagon": {"price": 594.0}}
    # },
    # "plastic_default": {
    #     "label": "Пластик по умолчанию", "family": "plastic", "density": 1200.0, "k_handle": 0.055,
    #     "applicable_processes": ["printing", "cnc_milling", "cnc_lathe", "painting"],
    #     "forms": {"sheet": {"price": 110.0}, "rod": {"price": 110.0}}
    # },
    #"plastic_pvh": {
    #    "label": "Поливинилхлорид ПВХ", "family": "plastic", "density": 1080.0, "k_handle": 0.055,
    #    "applicable_processes": ["printing", "cnc_lathe", "painting"],
    #    "forms": {"sheet": {"price": 110.0}, "rod": {"price": 110.0}}
    #},
    #"plastic_pla": {
    #    "label": "Plastic PLA", "family": "plastic", "density": 1240.0, "k_handle": 0.055,
    #    "applicable_processes": ["printing", "cnc_milling", "cnc_lathe", "painting"],
    #    "forms": {"sheet": {"price": 110.0}, "rod": {"price": 110.0}}
    #},
    #"wood":  {
    #    "label": "Дерево",  "family": "wood", "density": 520.0, "k_handle": 0.03,
    #    "applicable_processes": ["cnc_milling", "cnc_lathe", "painting"],
    #    "forms": {"plate": {"price": 30.0}, "bar": {"price": 35.0}}
    #},
    #"wood_oak":   {
    #    "label": "Wood Oak",   "family": "wood", "density": 700.0, "k_handle": 0.03,
    #    "applicable_processes": ["cnc_milling", "cnc_lathe", "painting"],
    #    "forms": {"plate": {"price": 40.0}, "bar": {"price": 45.0}}
    #},
    #"wood_birch": {
    #    "label": "Wood Birch", "family": "wood", "density": 650.0, "k_handle": 0.03,
    #    "applicable_processes": ["cnc_milling", "cnc_lathe", "painting"],
    #    "forms": {"plate": {"price": 35.0}, "bar": {"price": 40.0}}
    #}
}

PAINT_COEFFICIENTS = {
    "epoxy": {"base_price": 25.0, "k_type": 1.2, "k_prepare": 1.1},
    "acrylic": {"base_price": 20.0, "k_type": 1.0, "k_prepare": 1.0},
    "polyurethane": {"base_price": 30.0, "k_type": 1.3, "k_prepare": 1.2},
}

MATERIAL_PREP = {
    "alum": {"k_material": 1.0, "k_clean": 1.1},
    "plastic": {"k_material": 0.8, "k_clean": 0.9},
    "steel": {"k_material": 1.2, "k_clean": 1.3},
    "wood": {"k_material": 0.9, "k_clean": 1.0},
}

PROCESS_COEFFICIENTS = {
    "paint_prepare": {"a": 1.0, "b": 1.1, "c": 1.2},
    "paint_primer": {"a": 1.0, "b": 1.15, "c": 1.3},
    "paint_lakery": {"a": 1.0, "b": 1.1, "c": 1.2},
}

FINISH = {
    "1": {"label": "12.5", "value": 0.9},
    "2": {"label": "6.3", "value": 0.95},
    "3": {"label": "3.2", "value": 1},
    "4": {"label": "1.6", "value": 1.05},
    "5": {"label": "0.8", "value": 1.1},
}

COVER = {
    # "0": {"label": "Без покрытия", "value": 1.0, "cycle_time": 1.0},
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

CERT_COSTS = {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0, "e": 0.0, "f": 0.0, "g": 0.0}

# Default values for calculations
DEFAULTS = {
    "location": "location_1",
    "cover_id_list": ["1"],  # cover_id is a list
    "tolerance_id": "1",      # string ID
    "finish_id": "1",         # string ID
    "k_otk": 1.0,
    "k_type": 1.0,
    "k_process": 1.0,
    "k_complexity": 0.75,
    "n_dimensions": 1,
    "cnc_complexity": "medium",
    "cnc_setup_time": 2.0,
    "k_cert_cnc": ["a", "f"],
    "k_cert_printing": ["a", "f"],
    "k_cert_painting": ["a", "f", "g", "d"],
    "paint_prepare": "a",
    "paint_primer": "b",
    "paint_lakery": "a",
    "control_type": "1",
}

CYCLE_TIME_DEFAULTS = {
    "buying_material_time": 3,
    "developing_technology_time": 1,
    "developing_program_time": 3,
    "preparing_material_time": 1,
}

PAINT_PREP_BASE_COST = 15.0

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

LOCATIONS = {
    "location_1": {
        "name": "rudnevo"
    },
    "location_2": {
        "name": "dubna"
    },
    "location_3": {
        "name": "saransk"
    },
}

COST_STRUCTURE = {
    "location_1": {
        "price_of_hour": 874.57,
        "dop_salary_coef": 0.1124,
        "insurance_coef": 0.3170,
        "overhead_expenses_coef": 1.7568,
        "administrative_expenses_coef": 0.8731,
        "profit_material": 0.01,
        "other_profit": 0.25
    },
    "location_2": {
        "price_of_hour": 667.88,
        "dop_salary_coef": 0.11,
        "insurance_coef": 0.3170,
        "overhead_expenses_coef": 1.4097,
        "administrative_expenses_coef": 1.4208,
        "profit_material": 0.01,
        "other_profit": 0.25
    },
    "location_3": { 
        "price_of_hour": 469.03,
        "dop_salary_coef": 0.13,
        "insurance_coef": 0.2985,
        "overhead_expenses_coef": 2.328,
        "administrative_expenses_coef": 0.995,
        "profit_material": 0.01,
        "other_profit": 0.25
    }
}

MACHINES: Dict[str, Dict[str, Any]] = {
    "machine_101": {
        "name": "machine_101", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 3,
        "location": "location_1",
        "dimensions": {
            "x": 1000,
            "y": 1000,
            "z": 1000,
        }
    },
    "machine_102": {
        "name": "machine_102", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 3,
        "location": "location_1",
        "dimensions": {
            "x": 420,
            "y": 3200,
            "z": 1250,
        }
    },
    "machine_103": {
        "name": "machine_103", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 5,
        "location": "location_1",
        "dimensions": {
            "x": 800,
            "y": 800,
            "z": 800,
        }
    },
    "machine_104": {
        "name": "machine_104", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 5,
        "location": "location_1",
        "dimensions": {
            "x": 4200,
            "y": 3200,
            "z": 1250,
        }
    },
    "machine_105": {
        "name": "machine_105", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_1",
        "dimensions": {
            "x": 600,
            "y": 600,
            "z": 1000,
        }
    },
    "machine_106": {
        "name": "machine_106", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_1",
        "dimensions": {
            "x": 360,
            "y": 360,
            "z": 750,
        }
    },
    "machine_201": {
        "name": "CXK180", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_2",
        "dimensions": {
            "x": 1800,
            "y": 1800,
            "z": 1000,
        }
    },
    "machine_202": {
        "name": "C5116", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_2",
        "dimensions": {
            "x": 1600,
            "y": 1600,
            "z": 1000,
        }
    },
    "machine_203": {
        "name": "SGT-MC116", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 3,
        "location": "location_2",
        "dimensions": {
            "x": 1200,
            "y": 600,
            "z": 720,
        }
    },
    "machine_204": {
        "name": "SGT-MC64", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 3,
        "location": "location_2",
        "dimensions": {
            "x": 1200,
            "y": 600,
            "z": 720,
        }
    },
    "machine_205": {
        "name": "Uni.5 600U", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 5,
        "location": "location_2",
        "dimensions": {
            "x": 800,
            "y": 630,
            "z": 665,
        }
    },
    "machine_206": {
        "name": "Uni.5 800U", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 5,
        "location": "location_2",
        "dimensions": {
            "x": 800,
            "y": 630,
            "z": 665,
        }
    },
    "machine_207": {
        "name": "DMU 65", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 5,
        "location": "location_2",
        "dimensions": {
            "x": 800,
            "y": 800,
            "z": 500,
        }
    },
    "machine_208": {
        "name": "DMU 100 Р", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 5,
        "location": "location_2",
        "dimensions": {
            "x": 1100,
            "y": 1100,
            "z": 1600,
        }
    },
    "machine_209": {
        "name": "HURON K2X 10 FIVE", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 5,
        "location": "location_2",
        "dimensions": {
            "x": 800,
            "y": 800,
            "z": 500,
        }
    },
    "machine_210": {
        "name": "HURON K2X 8 FIVE", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 5,
        "location": "location_2",
        "dimensions": {
            "x": 800,
            "y": 800,
            "z": 500,
        }
    },
    "machine_211": {
        "name": "HURON KX 50 L", 
        "type": "milling",
        "CNC": True,
        "axes_numbers": 5,
        "location": "location_2",
        "dimensions": {
            "x": 3300,
            "y": 1250,
            "z": None,
        }
    },
    "machine_212": {
        "name": "DM 2000/500 M", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_2",
        "dimensions": {
            "x": 450,
            "y": 450,
            "z": 1000,
        }
    },
    "machine_213": {
        "name": "DM 2000/800 M", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_2",
        "dimensions": {
            "x": 450,
            "y": 450,
            "z": 1000,
        }
    },
    "machine_214": {
        "name": "DM 2500/1000 MY", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_2",
        "dimensions": {
            "x": 450,
            "y": 450,
            "z": 1000,
        }
    },
    "machine_215": {
        "name": "CKE61125/1500", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_2",
        "dimensions": {
            "x": 880,
            "y": 880,
            "z": 1500,
        }
    },
    "machine_216": {
        "name": "CKE6150Z/1000 (1500)", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_2",
        "dimensions": {
            "x": 280,
            "y": 280,
            "z": 1500,
        }
    },
    "machine_217": {
        "name": "Hanwha XP26S", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_2",
        "dimensions": {
            "x": 26,
            "y": 26,
            "z": None,
        }
    },
    "machine_218": {
        "name": "1М65", 
        "type": "lathe",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_2",
        "dimensions": {
            "x": 1600,
            "y": 1600,
            "z": 5000,
        }
    },
    "machine_301": {
        "name": "ONSINT SM300", 
        "type": "printing",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_3",
        "dimensions": {
            "x": 300,
            "y": 300,
            "z": 400,
        }
    },
    "machine_302": {
        "name": "ONSINT SM500", 
        "type": "printing",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_3",
        "dimensions": {
            "x": 530,
            "y": 530,
            "z": 550,
        }
    },
    "machine_303": {
        "name": "ONSINT SM800", 
        "type": "printing",
        "CNC": True,
        "axes_numbers": None,
        "location": "location_3",
        "dimensions": {
            "x": 870,
            "y": 520,
            "z": 550,
        }
    },
}

FEATURES_EXAMPLE_FROM_STEP = { 
  "filename": "temp_S8000.125.63.160.004.stp",
  "volume": 1368.687199211895,
  "surface_area": 955.4906989226236,
  "obb_x": 6.000020000073436,
  "obb_y": 6.000020000000001,
  "obb_z": 49.0000200009037,
  "aspect_ratio_xy": 1.000000000012239,
  "aspect_ratio_yz": 0.1224493377735222,
  "aspect_ratio_xz": 0.12244933777502086,
  "bbox_volume": 1764.0124800785238,
  "num_faces": 5,
  "num_edges": 7,
  "num_vertices": 4,
  "num_wires": 5,
  "euler_char": 2,
  "num_planar": 2,
  "num_cylindrical": 1,
  "num_conical": 2,
  "num_toroidal": 0,
  "num_spherical": 0,
  "num_bspline": 0,
  "surface_entropy": 1.5219280948873621,
  "ratio_planar": 0.4,
  "ratio_cylindrical": 0.2,
  "ratio_conical": 0.4,
  "ratio_toroidal": 0,
  "ratio_spherical": 0,
  "ratio_bspline": 0,
  "planar_area": 25.132741228718334,
  "cylindrical_area": 885.9291283123216,
  "conical_area": 44.42882938158367,
  "toroidal_area": 0,
  "spherical_area": 0,
  "bspline_area": 0,
  "other_area": -1.1368683772161603e-13,
  "ratio_planar_area": 0.026303491239691914,
  "ratio_cylindrical_area": 0.9271980661991404,
  "ratio_conical_area": 0.04649844256116778,
  "ratio_toroidal_area": 0,
  "ratio_spherical_area": 0,
  "ratio_bspline_area": 0,
  "ratio_other_area": -1.1898267335287006e-16,
  "ratio_planar_cylindrical": 0.7008945749594484,
  "num_unique_planar_normals": 2,
  "num_straight_edges": 0,
  "num_curved_edges": 7,
  "num_circles": 4,
  "num_bspline_edges": 3,
  "edge_entropy": 0.9852281360342515,
  "ratio_straight_edges": 0,
  "ratio_curved_edges": 1,
  "ratio_circles_edges": 0.5714285714285714,
  "ratio_bspline_edges": 0.42857142857142855,
  "length_all_edges": 112.66028019654203,
  "straight_length": 0,
  "curved_length": 112.66028019654203,
  "circle_length": 62.83185307179586,
  "bspline_edge_length": 49.82842712474619,
  "ratio_straight_edges_length": 0,
  "ratio_curved_edges_length": 1,
  "ratio_circles_edges_length": 0.5577107829146373,
  "ratio_bspline_edges_length": 0.4422892170853629,
  'ratio_bezier_edges_length': 0,
  "avg_face_area": 191.0981397845247,
  "avg_edge_length": 16.094325742363147,
  "surface_to_volume_ratio": 0.6981074269364144,
  "obb_compactness": 0.7758942834412196,
  "sphericity": 0.6239174480386556,
  "topology_complexity_score": 5.333333333333333,
  "removable_score": 0.7758942834412196
}

FEATURES_EXAMPLE_FROM_STL = {
  "x": 9,
  "y": 9,
  "z": 10
}