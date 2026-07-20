from typing import Any, Dict


LOCATIONS = {
    "location_1": {
        "name": "rudnevo",
        "label": 'АО "Икар-Тех"'
    },
    "location_2": {
        "name": "dubna",
        "label": 'АО "ДМЗ"'
    },
    "location_3": {
        "name": "saransk",
        "label": 'АО "КТ-Спектр"'
    },
}

COST_STRUCTURE = {
    "location_1": {
        "price_of_hour": 732.91818,
        "dop_salary_coef": 0.1,
        "insurance_coef": 0.302,
        "overhead_expenses_coef": 0.8573,
        "administrative_expenses_coef": 0.8592,
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
