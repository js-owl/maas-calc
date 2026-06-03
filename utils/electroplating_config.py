"""Reference data and helpers for service_id='electroplating_auto'.

All galvanic operation data lives in this module:

- available operations and bath limits are stored in ELECTROPLATING_OPERATIONS;
- process electrochemical coefficients are stored in PROCESS_PROFILE_LIBRARY;
- material families and default calculation parameters are stored here as well.

constants.py should only keep generic service/material dictionaries. It should not
store a second copy of galvanic operations, because two sources of truth quickly
become inconsistent.
"""

from __future__ import annotations

from itertools import permutations
from typing import Any, Dict, Mapping, Optional

ELECTROPLATING_SERVICE_ID = "electroplating_auto"
NON_AUTO_ELECTROPLATING_SERVICE = "electroplating"
NOT_APPLICABLE_ELECTROPLATING_FAMILY = "not_applicable"

ELECTROPLATING_SERVICE_CONFIG: Dict[str, Any] = {
    "service": ELECTROPLATING_SERVICE_ID,
    "label": "Гальваника",
}

# Canonical list of galvanic operations. This is the only source of bath
# dimensions and maximum batch weight for automatic electroplating calculation.
ELECTROPLATING_OPERATIONS: list[Dict[str, Any]] = [
    {
        "id": "aluminum_weld_etching",
        "group": "Обработка алюминиевых сплавов",
        "path": ["Травление под сварку"],
        "max_part_size_mm": (5800, 700, 1500),
        "max_weight_kg": 600,
    },
    {
        "id": "aluminum_chemical_oxidation",
        "group": "Обработка алюминиевых сплавов",
        "path": ["Химическая оксидация"],
        "max_part_size_mm": (5800, 700, 1500),
        "max_weight_kg": 600,
    },
    {
        "id": "aluminum_anodizing_strong",
        "group": "Обработка алюминиевых сплавов",
        "path": ["Твёрдая анодная оксидация"],
        "max_part_size_mm": (5800, 850, 1400),
        "max_weight_kg": 600,
    },
    {
        "id": "aluminum_anodizing_water",
        "group": "Обработка алюминиевых сплавов",
        "path": ["Анодная оксидация", "Наполнение в воде"],
        "max_part_size_mm": (5800, 830, 1400),
        "max_weight_kg": 600,
    },
    {
        "id": "aluminum_anodizing_chrome",
        "group": "Обработка алюминиевых сплавов",
        "path": ["Анодная оксидация", "Наполнение в хромпике"],
        "max_part_size_mm": (5800, 830, 1500),
        "max_weight_kg": 600,
    },
    {
        "id": "aluminum_anodizing_organic_black",
        "group": "Обработка алюминиевых сплавов",
        "path": [
            "Анодная оксидация",
            "Наполнение в органических красителях (чёрный/красный)",
        ],
        "max_part_size_mm": (800, 500, 1300),
        "max_weight_kg": 600,
    },
    {
        "id": "corrosion_resistant_steel_degreasing",
        "group": "Химическая обработка коррозионностойких сталей",
        "path": ["Химическая пассивация", "Обезжиривание"],
        "max_part_size_mm": (2800, 1000, 1100),
        "max_weight_kg": 500,
    },
    {
        "id": "corrosion_resistant_steel_loosening",
        "group": "Химическая обработка коррозионностойких сталей",
        "path": ["Химическая пассивация", "Рыхление"],
        "max_part_size_mm": (2800, 850, 1100),
        "max_weight_kg": 500,
    },
    {
        "id": "corrosion_resistant_steel_etching",
        "group": "Химическая обработка коррозионностойких сталей",
        "path": ["Химическая пассивация", "Травление"],
        "max_part_size_mm": (2800, 1000, 1100),
        "max_weight_kg": 500,
    },
    {
        "id": "corrosion_resistant_steel_passivation",
        "group": "Химическая обработка коррозионностойких сталей",
        "path": ["Химическая пассивация", "Пассивация"],
        "max_part_size_mm": (2800, 850, 1100),
        "max_weight_kg": 500,
    },
    {
        "id": "titanium_degreasing",
        "group": "Химическая обработка титана",
        "path": ["Обезжиривание"],
        "max_part_size_mm": (2800, 800, 900),
        "max_weight_kg": 400,
    },
    {
        "id": "titanium_loosening",
        "group": "Химическая обработка титана",
        "path": ["Рыхление"],
        "max_part_size_mm": (2800, 800, 900),
        "max_weight_kg": 400,
    },
    {
        "id": "titanium_etching",
        "group": "Химическая обработка титана",
        "path": ["Травление"],
        "max_part_size_mm": (2800, 800, 900),
        "max_weight_kg": 400,
    },
    {
        "id": "titanium_passivation",
        "group": "Химическая обработка титана",
        "path": ["Облагораживание"],
        "max_part_size_mm": (2800, 800, 900),
        "max_weight_kg": 400,
    },
    {
        "id": "magnium_chromating",
        "group": "Химическая обработка магния",
        "path": ["Хроматирование"],
        "max_part_size_mm": (1700, 600, 950),
        "max_weight_kg": 400,
    },
    {
        "id": "steel_phosphating_zinc",
        "group": "Фосфатирование сталей",
        "path": ["Фосфатирование в цинкфосфатной ванне"],
        "max_part_size_mm": (1800, 670, 900),
        "max_weight_kg": 400,
    },
    {
        "id": "steel_phosphating_oxide",
        "group": "Фосфатирование сталей",
        "path": ["Оксидное фосфатирование"],
        "max_part_size_mm": (1800, 670, 800),
        "max_weight_kg": 400,
    },
    {
        "id": "galvanization_zinc_phosphating",
        "group": "Цинкование",
        "path": ["С фосфатированием"],
        "max_part_size_mm": (2800, 700, 1000),
        "max_weight_kg": 400,
    },
    {
        "id": "galvanization_zinc_chromating",
        "group": "Цинкование",
        "path": ["С хроматированием"],
        "max_part_size_mm": (2800, 700, 1000),
        "max_weight_kg": 400,
    },
    {
        "id": "cadmium_plating_chlorine_phosphating",
        "group": "Кадмирование",
        "path": ["Хлористоаммонийное", "С фосфатированием"],
        "max_part_size_mm": (2800, 700, 1000),
        "max_weight_kg": 400,
    },
    {
        "id": "cadmium_plating_chlorine_chromating",
        "group": "Кадмирование",
        "path": ["Хлористоаммонийное", "С хроматированием"],
        "max_part_size_mm": (2800, 700, 1000),
        "max_weight_kg": 400,
    },
    {
        "id": "cadmium_plating_sulfuric_phosphating",
        "group": "Кадмирование",
        "path": ["Сернокислое", "С фосфатированием"],
        "max_part_size_mm": (1000, 190, 600),
        "max_weight_kg": 400,
    },
    {
        "id": "cadmium_plating_sulfuric_chromating",
        "group": "Кадмирование",
        "path": ["Сернокислое", "С хроматированием"],
        "max_part_size_mm": (1000, 190, 600),
        "max_weight_kg": 10,
    },
    {
        "id": "nickel_plating_sulfuric_phosphating",
        "group": "Никелирование",
        "path": ["Хлористое"],
        "max_part_size_mm": (1000, 190, 600),
        "max_weight_kg": 400,
    },
    {
        "id": "nickel_plating_sulfuric_chromating",
        "group": "Никелирование",
        "path": ["Сернокислое"],
        "max_part_size_mm": (1000, 190, 600),
        "max_weight_kg": 400,
    },
    {
        "id": "nickel_cadmium",
        "group": "Покрытие гальванотермический никель-кадмий",
        "path": [],
        "max_part_size_mm": (1000, 190, 600),
        "max_weight_kg": 10,
    },
    {
        "id": "tin_bismuth",
        "group": "Олово-висмут",
        "path": [],
        "max_part_size_mm": (1000, 190, 600),
        "max_weight_kg": 10,
    },
    {
        "id": "copper_plating",
        "group": "Меднение",
        "path": [],
        "max_part_size_mm": (1000, 190, 600),
        "max_weight_kg": 10,
    },
    {
        "id": "electropolishing",
        "group": "Электрополирование",
        "path": [],
        "max_part_size_mm": (1000, 190, 600),
        "max_weight_kg": 10,
    },
    {
        "id": "chrome_plating",
        "group": "Хромирование",
        "path": [],
        "max_part_size_mm": (1600, 400, 800),
        "max_weight_kg": 10,
    },
    {
        "id": "silvering",
        "group": "Серебрение",
        "path": [],
        "max_part_size_mm": (150, 150, 30),
        "max_weight_kg": 10,
    },
]
# Process time models:
# - faraday_deposition: electrolytic deposition; time uses T=(a*b)/(c*d*e).
# - faraday_layer_growth: electrolytic oxide-layer growth; time uses the same configured formula.
# - faraday_material_removal: electropolishing/material removal; input is removal depth, not coating thickness.
# - fixed_time: chemical/preparatory operation; configured fixed_operation_time_min is used.
# Current densities are in A/dm², max current is in A.
PROCESS_PROFILE_LIBRARY: Dict[str, Dict[str, Any]] = {
    'tin_bismuth': {'label': 'Олово-висмут',
                 'material_families': ['copper'],
                 'deposited_material': 'tin_bismuth',
                 'deposited_density_kg_dm3': 7.31,
                 'current_density_a_dm2': 0.5,
                 'max_current_a': 150.0,
                 'electrochemical_equivalent': 2.214,
                 'current_efficiency': 0.9,
                 'default_thickness_microns': 9.0,
                 'is_electrolytic': True,
                 'time_model': 'faraday_deposition',
                 'thickness_role': 'coating_thickness',
                 'requires_thickness_input': False,
                 'requires_processing_depth_input': False},
    'nickel_chloride': {'label': 'Никелирование хлористое',
                     'material_families': ['carbon_steel', 'copper'],
                     'deposited_material': 'nickel',
                     'deposited_density_kg_dm3': 8.9,
                     'current_density_a_dm2': 1.0,
                     'max_current_a': 150.0,
                     'electrochemical_equivalent': 1.095,
                     'current_efficiency': 0.95,
                     'default_thickness_microns': 12.0,
                     'is_electrolytic': True,
                     'time_model': 'faraday_deposition',
                     'thickness_role': 'coating_thickness',
                     'requires_thickness_input': False,
                     'requires_processing_depth_input': False},
    'nickel_sulfate': {'label': 'Никелирование сернокислое',
                    'material_families': ['carbon_steel', 'copper'],
                    'deposited_material': 'nickel',
                    'deposited_density_kg_dm3': 8.9,
                    'current_density_a_dm2': 1.0,
                    'max_current_a': 150.0,
                    'electrochemical_equivalent': 1.095,
                    'current_efficiency': 0.95,
                    'default_thickness_microns': 12.0,
                    'is_electrolytic': True,
                    'time_model': 'faraday_deposition',
                    'thickness_role': 'coating_thickness',
                    'requires_thickness_input': False,
                    'requires_processing_depth_input': False},
    'zinc': {'label': 'Цинкование',
          'material_families': ['carbon_steel'],
          'deposited_material': 'zinc',
          'deposited_density_kg_dm3': 7.14,
          'current_density_a_dm2': 2.0,
          'max_current_a': 1200.0,
          'electrochemical_equivalent': 1.22,
          'current_efficiency': 0.95,
          'default_thickness_microns': 9.0,
          'is_electrolytic': True,
          'time_model': 'faraday_deposition',
          'thickness_role': 'coating_thickness',
          'requires_thickness_input': False,
          'requires_processing_depth_input': False},
    'anodizing': {'label': 'Анодная оксидация',
               'material_families': ['aluminum'],
               'deposited_material': 'aluminum_oxide',
               'deposited_density_kg_dm3': 2.7,
               'current_density_a_dm2': 2.0,
               'max_current_a': 1200.0,
               'electrochemical_equivalent': 0.335,
               'current_efficiency': 0.7,
               'default_thickness_microns': 3.0,
               'is_electrolytic': True,
               'time_model': 'faraday_layer_growth',
               'thickness_role': 'oxide_layer_thickness',
               'requires_thickness_input': False,
               'requires_processing_depth_input': False},
    'hard_anodizing': {'label': 'Твёрдая анодная оксидация',
                    'material_families': ['aluminum'],
                    'deposited_material': 'aluminum_oxide',
                    'deposited_density_kg_dm3': 2.7,
                    'current_density_a_dm2': 2.0,
                    'max_current_a': 900.0,
                    'electrochemical_equivalent': 0.335,
                    'current_efficiency': 0.65,
                    'default_thickness_microns': 30.0,
                    'is_electrolytic': True,
                    'time_model': 'faraday_layer_growth',
                    'thickness_role': 'oxide_layer_thickness',
                    'requires_thickness_input': False,
                    'requires_processing_depth_input': False},
    'chrome': {'label': 'Хромирование',
            'material_families': ['carbon_steel', 'copper'],
            'deposited_material': 'chrome',
            'deposited_density_kg_dm3': 7.19,
            'current_density_a_dm2': 50.0,
            'max_current_a': 2500.0,
            'electrochemical_equivalent': 0.323,
            'current_efficiency': 0.18,
            'default_thickness_microns': 9.0,
            'is_electrolytic': True,
            'time_model': 'faraday_deposition',
            'thickness_role': 'coating_thickness',
            'requires_thickness_input': False,
            'requires_processing_depth_input': False},
    'cadmium': {'label': 'Кадмирование',
             'material_families': ['carbon_steel'],
             'deposited_material': 'cadmium',
             'deposited_density_kg_dm3': 8.65,
             'current_density_a_dm2': 0.5,
             'max_current_a': 100.0,
             'electrochemical_equivalent': 2.096,
             'current_efficiency': 0.9,
             'default_thickness_microns': 9.0,
             'is_electrolytic': True,
             'time_model': 'faraday_deposition',
             'thickness_role': 'coating_thickness',
             'requires_thickness_input': False,
             'requires_processing_depth_input': False},
    'electropolishing': {'label': 'Электрохимическое полирование',
                      'material_families': ['stainless_steel'],
                      'current_density_a_dm2': 50.0,
                      'max_current_a': 1000.0,
                      'electrochemical_equivalent': 1.042,
                      'current_efficiency': 0.8,
                      'is_electrolytic': True,
                      'removed_material': 'stainless_steel',
                      'removed_material_density_kg_dm3': 7.8,
                      'default_processing_depth_microns': 10.0,
                      'time_model': 'faraday_material_removal',
                      'thickness_role': 'removed_layer_depth',
                      'requires_thickness_input': False,
                      'requires_processing_depth_input': False},
    'copper': {'label': 'Меднение',
            'material_families': ['carbon_steel'],
            'deposited_material': 'copper',
            'deposited_density_kg_dm3': 8.96,
            'current_density_a_dm2': 1.0,
            'max_current_a': 150.0,
            'electrochemical_equivalent': 1.186,
            'current_efficiency': 0.95,
            'default_thickness_microns': 12.0,
            'is_electrolytic': True,
            'time_model': 'faraday_deposition',
            'thickness_role': 'coating_thickness',
            'requires_thickness_input': False,
            'requires_processing_depth_input': False},
    'nickel_cadmium': {'label': 'Гальванотермический никель-кадмий',
                    'material_families': ['carbon_steel'],
                    'deposited_material': 'nickel_cadmium',
                    'deposited_density_kg_dm3': 8.0,
                    'current_density_a_dm2': 0.5,
                    'max_current_a': 100.0,
                    'electrochemical_equivalent': 2.096,
                    'current_efficiency': 0.9,
                    'default_thickness_microns': 9.0,
                    'is_electrolytic': True,
                    'time_model': 'faraday_deposition',
                    'thickness_role': 'coating_thickness',
                    'requires_thickness_input': False,
                    'requires_processing_depth_input': False},
    'silvering': {'label': 'Серебрение',
               'material_families': [],
               'deposited_material': 'silver',
               'deposited_density_kg_dm3': 10.49,
               'current_density_a_dm2': 0.5,
               'max_current_a': 150.0,
               'electrochemical_equivalent': 4.025,
               'current_efficiency': 0.95,
               'default_thickness_microns': 9.0,
               'is_electrolytic': True,
               'time_model': 'faraday_deposition',
               'thickness_role': 'coating_thickness',
               'requires_thickness_input': False,
               'requires_processing_depth_input': False},
    'chemical_phosphating': {'label': 'Химическое фосфатирование',
                          'material_families': ['carbon_steel'],
                          'default_thickness_microns': 5.0,
                          'is_electrolytic': False,
                          'fixed_operation_time_min': 30.0,
                          'time_model': 'fixed_time',
                          'thickness_role': 'conversion_layer_reference',
                          'requires_thickness_input': False,
                          'requires_processing_depth_input': False},
    'pickling': {'label': 'Травление',
              'material_families': ['stainless_steel', 'aluminum', 'titanium'],
              'default_thickness_microns': 0.0,
              'is_electrolytic': False,
              'fixed_operation_time_min': 30.0,
              'time_model': 'fixed_time',
              'thickness_role': 'not_applicable',
              'requires_thickness_input': False,
              'requires_processing_depth_input': False},
    'degreasing': {'label': 'Обезжиривание',
                'material_families': ['stainless_steel', 'titanium'],
                'default_thickness_microns': 0.0,
                'is_electrolytic': False,
                'fixed_operation_time_min': 30.0,
                'time_model': 'fixed_time',
                'thickness_role': 'not_applicable',
                'requires_thickness_input': False,
                'requires_processing_depth_input': False},
    'loosening': {'label': 'Рыхление',
               'material_families': ['stainless_steel', 'titanium'],
               'default_thickness_microns': 0.0,
               'is_electrolytic': False,
               'fixed_operation_time_min': 30.0,
               'time_model': 'fixed_time',
               'thickness_role': 'not_applicable',
               'requires_thickness_input': False,
               'requires_processing_depth_input': False},
    'chemical_passivation': {'label': 'Химическая пассивация',
                          'material_families': ['stainless_steel', 'copper', 'titanium'],
                          'default_thickness_microns': 0.0,
                          'is_electrolytic': False,
                          'fixed_operation_time_min': 30.0,
                          'time_model': 'fixed_time',
                          'thickness_role': 'not_applicable',
                          'requires_thickness_input': False,
                          'requires_processing_depth_input': False},
    'chemical_oxidation': {'label': 'Химическая оксидация',
                        'material_families': ['aluminum'],
                        'default_thickness_microns': 3.0,
                        'is_electrolytic': False,
                        'fixed_operation_time_min': 30.0,
                        'time_model': 'fixed_time',
                        'thickness_role': 'conversion_layer_reference',
                        'requires_thickness_input': False,
                        'requires_processing_depth_input': False},
    'chromating': {'label': 'Хроматирование',
                'material_families': ['magnesium'],
                'default_thickness_microns': 3.0,
                'is_electrolytic': False,
                'fixed_operation_time_min': 30.0,
                'time_model': 'fixed_time',
                'thickness_role': 'conversion_layer_reference',
                'requires_thickness_input': False,
                'requires_processing_depth_input': False}
}

ELECTROPLATING_MATERIAL_FAMILIES: Dict[str, Dict[str, Any]] = {
    'carbon_steel': {'label': 'Углеродистые стали', 'density_kg_dm3': 7.8},
    'stainless_steel': {'label': 'Коррозионностойкие стали', 'density_kg_dm3': 7.8},
    'aluminum': {'label': 'Алюминиевые сплавы', 'density_kg_dm3': 2.7},
    'copper': {'label': 'Медь и медные сплавы', 'density_kg_dm3': 8.93},
    'titanium': {'label': 'Титановые сплавы', 'density_kg_dm3': 4.5},
    'magnesium': {'label': 'Магниевые сплавы', 'density_kg_dm3': 1.8}
}

ELECTROPLATING_DEFAULTS: Dict[str, Any] = {
    'process_id': 'aluminum_anodizing_water',
    'coating_thickness_microns': None,
    'processing_depth_microns': None,
    'preparation_time_min': 30.0,
    'mount_unmount_time_min': 2.5,
    'clearance_mm': 20.0
}

LEGACY_PROCESS_ALIASES: Dict[str, str] = {
    'tin': 'tin_bismuth',
    'tin_bismuth': 'tin_bismuth',
    'nickel_chloride': 'nickel_plating_sulfuric_phosphating',
    'nickel_sulfate': 'nickel_plating_sulfuric_chromating',
    'zinc': 'galvanization_zinc_phosphating',
    'galvanization_zinc': 'galvanization_zinc_phosphating',
    'anodizing': 'aluminum_anodizing_water',
    'hard_anodizing': 'aluminum_anodizing_strong',
    'chrome': 'chrome_plating',
    'chromium': 'chrome_plating',
    'cadmium': 'cadmium_plating_chlorine_phosphating',
    'electropolishing': 'electropolishing',
    'chemical_phosphating': 'steel_phosphating_zinc',
    'pickling': 'corrosion_resistant_steel_etching',
    'chemical_passivation': 'corrosion_resistant_steel_passivation',
    'chemical_oxidation': 'aluminum_chemical_oxidation',
    'copper': 'copper_plating',
    'copper_plating': 'copper_plating',
    'silvering': 'silvering'
}

# Explicit operation-to-profile bindings. Do not infer these values from Russian
# labels/groups/path text: UI labels may change and different material families
# can share words such as "травление" or "пассивация". This mapping is the
# single source that defines which operation uses which calculation profile and
# which material families are allowed for that exact operation.
ELECTROPLATING_OPERATION_PROFILES: Dict[str, Dict[str, Any]] = {
    # Aluminum alloys.
    "aluminum_weld_etching": {"profile_key": "pickling", "material_families": ["aluminum"]},
    "aluminum_chemical_oxidation": {"profile_key": "chemical_oxidation", "material_families": ["aluminum"]},
    "aluminum_anodizing_strong": {"profile_key": "hard_anodizing", "material_families": ["aluminum"]},
    "aluminum_anodizing_water": {"profile_key": "anodizing", "material_families": ["aluminum"]},
    "aluminum_anodizing_chrome": {"profile_key": "anodizing", "material_families": ["aluminum"]},
    "aluminum_anodizing_organic_black": {"profile_key": "anodizing", "material_families": ["aluminum"]},

    # Corrosion-resistant steels.
    "corrosion_resistant_steel_degreasing": {"profile_key": "degreasing", "material_families": ["stainless_steel"]},
    "corrosion_resistant_steel_loosening": {"profile_key": "loosening", "material_families": ["stainless_steel"]},
    "corrosion_resistant_steel_etching": {"profile_key": "pickling", "material_families": ["stainless_steel"]},
    "corrosion_resistant_steel_passivation": {"profile_key": "chemical_passivation", "material_families": ["stainless_steel"]},
    "electropolishing": {"profile_key": "electropolishing", "material_families": ["stainless_steel"]},

    # Titanium alloys.
    "titanium_degreasing": {"profile_key": "degreasing", "material_families": ["titanium"]},
    "titanium_loosening": {"profile_key": "loosening", "material_families": ["titanium"]},
    "titanium_etching": {"profile_key": "pickling", "material_families": ["titanium"]},
    "titanium_passivation": {"profile_key": "chemical_passivation", "material_families": ["titanium"]},

    # Magnesium alloys.
    "magnium_chromating": {"profile_key": "chromating", "material_families": ["magnesium"]},

    # Carbon steels.
    "steel_phosphating_zinc": {"profile_key": "chemical_phosphating", "material_families": ["carbon_steel"]},
    "steel_phosphating_oxide": {"profile_key": "chemical_phosphating", "material_families": ["carbon_steel"]},
    "galvanization_zinc_phosphating": {"profile_key": "zinc", "material_families": ["carbon_steel"]},
    "galvanization_zinc_chromating": {"profile_key": "zinc", "material_families": ["carbon_steel"]},
    "cadmium_plating_chlorine_phosphating": {"profile_key": "cadmium", "material_families": ["carbon_steel"]},
    "cadmium_plating_chlorine_chromating": {"profile_key": "cadmium", "material_families": ["carbon_steel"]},
    "cadmium_plating_sulfuric_phosphating": {"profile_key": "cadmium", "material_families": ["carbon_steel"]},
    "cadmium_plating_sulfuric_chromating": {"profile_key": "cadmium", "material_families": ["carbon_steel"]},
    "copper_plating": {"profile_key": "copper", "material_families": ["carbon_steel"]},
    "nickel_cadmium": {"profile_key": "nickel_cadmium", "material_families": ["carbon_steel"]},

    # Operations allowed both for carbon steels and copper/copper alloys.
    "nickel_plating_sulfuric_phosphating": {"profile_key": "nickel_chloride", "material_families": ["carbon_steel", "copper"]},
    "nickel_plating_sulfuric_chromating": {"profile_key": "nickel_sulfate", "material_families": ["carbon_steel", "copper"]},
    "chrome_plating": {"profile_key": "chrome", "material_families": ["carbon_steel", "copper"]},

    # Copper/copper alloys.
    "tin_bismuth": {"profile_key": "tin_bismuth", "material_families": ["copper"]},
    "silvering": {"profile_key": "silvering", "material_families": ["copper", "carbon_steel"]},
}



def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def normalize_electroplating_process_id(process_id: Optional[str]) -> Optional[str]:
    if not process_id:
        return None
    return str(process_id).strip().lower().replace("-", "_").replace(" ", "_")


def normalize_material_family_id(family_id: Optional[str]) -> str:
    if not family_id:
        return NOT_APPLICABLE_ELECTROPLATING_FAMILY
    normalized = str(family_id).strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or NOT_APPLICABLE_ELECTROPLATING_FAMILY


def get_non_auto_electroplating_operations() -> list[Dict[str, Any]]:
    """Return canonical galvanic operations from ELECTROPLATING_OPERATIONS.

    The function name is kept for backward compatibility with older code. It no
    longer reads operations from constants.NON_AUTO_SERVICES.
    """
    result: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for operation in ELECTROPLATING_OPERATIONS:
        if not isinstance(operation, Mapping):
            continue
        source_id = str(operation.get("id") or "").strip()
        if not source_id:
            raise ValueError("Electroplating operation without id in ELECTROPLATING_OPERATIONS")
        operation_id = normalize_electroplating_process_id(source_id) or source_id
        if operation_id in seen:
            raise ValueError(f"Duplicate electroplating operation id: {operation_id}")
        seen.add(operation_id)
        item = dict(operation)
        item["source_id"] = source_id
        item["id"] = operation_id
        result.append(item)
    return result


def _operation_binding(operation: Mapping[str, Any]) -> Dict[str, Any]:
    operation_id = normalize_electroplating_process_id(operation.get("source_id") or operation.get("id"))
    if not operation_id:
        raise ValueError(f"Electroplating operation without id: {operation!r}")

    binding = ELECTROPLATING_OPERATION_PROFILES.get(operation_id)
    if binding is None:
        raise ValueError(
            f"Electroplating operation {operation_id!r} has no explicit profile binding. "
            "Add it to ELECTROPLATING_OPERATION_PROFILES instead of relying on text heuristics."
        )

    profile_key = str(binding.get("profile_key") or "").strip()
    if profile_key not in PROCESS_PROFILE_LIBRARY:
        raise ValueError(
            f"Process profile {profile_key!r} is not configured for operation {operation_id!r}"
        )

    material_families = [
        normalize_material_family_id(family_id)
        for family_id in _as_list(binding.get("material_families"))
    ]
    material_families = [
        family_id
        for family_id in material_families
        if family_id and family_id != NOT_APPLICABLE_ELECTROPLATING_FAMILY
    ]
    if not material_families:
        raise ValueError(f"Operation {operation_id!r} must define at least one allowed material family")

    return {
        "profile_key": profile_key,
        "material_families": material_families,
    }


def _operation_profile_key(operation: Mapping[str, Any]) -> str:
    """Return the explicit calculation profile key for an operation.

    This function intentionally reads only the normalized operation id and
    ELECTROPLATING_OPERATION_PROFILES. It must not inspect labels, groups, or
    free-text path values.
    """
    return _operation_binding(operation)["profile_key"]


def _profile_for_operation(operation: Mapping[str, Any]) -> Dict[str, Any]:
    binding = _operation_binding(operation)
    profile_key = binding["profile_key"]
    profile = dict(PROCESS_PROFILE_LIBRARY[profile_key])
    profile["profile_key"] = profile_key
    profile["material_families"] = list(binding["material_families"])
    return profile


def _operation_bath(operation: Mapping[str, Any]) -> Dict[str, float]:
    dims = _as_list(operation.get("max_part_size_mm"))
    if len(dims) < 3:
        dims = [0.0, 0.0, 0.0]
    try:
        length, width, height = (float(dims[0]), float(dims[1]), float(dims[2]))
    except (TypeError, ValueError):
        length, width, height = 0.0, 0.0, 0.0

    try:
        max_weight_kg = float(operation.get("max_weight_kg") or 0.0)
    except (TypeError, ValueError):
        max_weight_kg = 0.0

    return {
        "length": length,
        "width": width,
        "height": height,
        "max_weight_kg": max_weight_kg,
    }


def get_service_config() -> Dict[str, Any]:
    return dict(ELECTROPLATING_SERVICE_CONFIG)


def get_process_params() -> Dict[str, Dict[str, Any]]:
    """Build process params from canonical ELECTROPLATING_OPERATIONS."""
    processes: Dict[str, Dict[str, Any]] = {}
    for operation in get_non_auto_electroplating_operations():
        process_id = str(operation["id"])
        profile = _profile_for_operation(operation)
        bath = _operation_bath(operation)
        label_path = _as_list(operation.get("path"))
        operation_label = " / ".join(str(part) for part in label_path if part) or str(operation.get("group") or process_id)
        process = {
            **profile,
            "id": process_id,
            "source_id": operation.get("source_id", process_id),
            "label": operation_label,
            "group": operation.get("group"),
            "path": label_path,
            "max_part_size_mm": tuple(bath[key] for key in ("length", "width", "height")),
            "max_weight_kg": bath["max_weight_kg"],
        }
        processes[process_id] = process
    return processes


def get_baths() -> Dict[str, Dict[str, float]]:
    """Return bath limits synthesized from ELECTROPLATING_OPERATIONS."""
    baths: Dict[str, Dict[str, float]] = {}
    for process_id, process in get_process_params().items():
        dims = _as_list(process.get("max_part_size_mm"))
        if len(dims) >= 3:
            baths[process_id] = {
                "length": float(dims[0]),
                "width": float(dims[1]),
                "height": float(dims[2]),
                "max_weight_kg": float(process.get("max_weight_kg") or 0.0),
            }
    if baths:
        first_bath = next(iter(baths.values()))
        baths.setdefault("default", dict(first_bath))
    return baths


def get_material_families() -> Dict[str, Dict[str, Any]]:
    """Return material families with allowed process ids derived from operations."""
    families = {key: dict(value) for key, value in ELECTROPLATING_MATERIAL_FAMILIES.items()}
    for family in families.values():
        family["allowed_processes"] = []

    for process_id, process in get_process_params().items():
        for family_id in process.get("material_families") or []:
            normalized_family_id = normalize_material_family_id(str(family_id))
            family = families.setdefault(
                normalized_family_id,
                {"label": normalized_family_id, "density_kg_dm3": 0.0},
            )
            family.setdefault("allowed_processes", [])
            family["allowed_processes"].append(process_id)

    return families


def get_defaults() -> Dict[str, Any]:
    return dict(ELECTROPLATING_DEFAULTS)


def get_electroplating_process(process_id: Optional[str]) -> Optional[Dict[str, Any]]:
    normalized = normalize_electroplating_process_id(process_id)
    if not normalized:
        return None

    processes = get_process_params()
    canonical_id = LEGACY_PROCESS_ALIASES.get(normalized, normalized)
    process = processes.get(canonical_id)
    if process is None:
        return None
    result = dict(process)
    result["id"] = canonical_id
    if canonical_id != normalized:
        result["requested_id"] = normalized
    return result


def infer_material_family(material_id: str, material_info: Mapping[str, Any]) -> str:
    """Return explicit galvanic material family configured in constants.MATERIALS.

    The historical function name is kept to avoid touching all imports, but this
    is no longer a heuristic. Every material must define electroplating_family.
    Non-galvanic materials must use None, empty value, or 'not_applicable'.
    """
    if "electroplating_family" not in material_info:
        raise ValueError(
            f"MATERIALS[{material_id!r}]['electroplating_family'] is not configured. "
            "Set an explicit family or None for non-galvanic materials."
        )
    family_id = normalize_material_family_id(material_info.get("electroplating_family"))
    if family_id in {"none", "null", "false", "no", "not_applicable", "n/a"}:
        return NOT_APPLICABLE_ELECTROPLATING_FAMILY
    return family_id


def is_material_allowed_for_electroplating(material_id: str, material_info: Mapping[str, Any]) -> bool:
    family_id = infer_material_family(material_id, material_info)
    if family_id == NOT_APPLICABLE_ELECTROPLATING_FAMILY:
        return False
    family = get_material_families().get(family_id)
    return bool(family and family.get("allowed_processes"))


def is_material_allowed_for_electroplating_process(
    material_id: str,
    material_info: Mapping[str, Any],
    process_id: Optional[str],
) -> bool:
    """Return whether a material is allowed for a concrete galvanic operation.

    This is intentionally based only on the explicit electroplating_family field
    in constants.MATERIALS and the explicit material_families binding of the
    operation in ELECTROPLATING_OPERATION_PROFILES. No text heuristics are used.
    """
    process = get_electroplating_process(process_id)
    if process is None:
        return False

    family_id = infer_material_family(material_id, material_info)
    if family_id == NOT_APPLICABLE_ELECTROPLATING_FAMILY:
        return False

    allowed_families = {
        normalize_material_family_id(family_id)
        for family_id in (process.get("material_families") or [])
    }
    return family_id in allowed_families


def get_allowed_material_forms(material_info: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return forms explicitly configured for a material.

    For electroplating_auto the form is a compatibility/input field, not a
    process selector. Therefore the only safe source of allowed values is
    MATERIALS[material_id]["forms"].
    """
    forms = material_info.get("forms") or {}
    if not isinstance(forms, Mapping):
        return {}
    return {str(form_id): dict(form_info or {}) for form_id, form_info in forms.items()}


def all_orientations(dimensions_mm: tuple[float, float, float]) -> list[tuple[float, float, float]]:
    """Return all unique axis-aligned orientations of a rectangular envelope."""
    return sorted(set(tuple(float(x) for x in p) for p in permutations(dimensions_mm, 3)))
