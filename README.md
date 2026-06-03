# MaaS Backend STL — Manufacturing Calculation API

FastAPI backend for automated manufacturing price calculations from uploaded CAD files. The service extracts geometric parameters from STL/STP/STEP files, applies material and cost-reference data from `constants.py`, and calculates prices for the currently active MaaS manufacturing services.

## Current active services

| `service_id` | Status | Calculation path |
|---|---|---|
| `printing` | active | rule-based calculation from geometry, material, quantity and coefficients |
| `electroplating_auto` | active | rule-based galvanic treatment calculation from STP/STEP surface area, volume, material family, selected operation and operation-specific time model |
| `cnc-milling` | active, ML-only | labor intensity from `ml_models.flexible_ensemble` bundle; special-equipment flag from XGBoost classifier |
| `composite` | active, ML-based | labor intensity from `ml_models.flexible_ensemble` bundle; tooling flag is supplied in the request |

Removed services:

| `service_id` | Status |
|---|---|
| `cnc-lathe` | removed legacy branch; mechanically machined parts must use `cnc-milling` |
| `painting` | removed from the active calculation API |

The API rejects removed services explicitly. They are also filtered out from service-list endpoints.

## Main calculation endpoint

```http
POST /calculate-price
```

Request model: `models.request_models.UnifiedCalculationRequest`.

Important fields:

| Field | Meaning |
|---|---|
| `service_id` | `printing`, `electroplating_auto`, `cnc-milling`, or `composite` |
| `file_data` | base64-encoded STL/STP/STEP file; required for `cnc-milling` ML calculation |
| `file_name` | original file name |
| `file_type` | `stl`, `stp`, or `step` |
| `material_id` | material key from `constants.MATERIALS` |
| `material_form` | material form, for example `powder`, `sheet`, `rod`, `hexagon`, `textile` |
| `quantity` | number of parts in the order |
| `location` | production location key from `constants.LOCATIONS` |
| `cover_id` | post-processing IDs; for `electroplating_auto` may also carry the galvanic process ID as the first item |
| `electroplating_process_id` | galvanic process ID for `electroplating_auto`; has priority over `cover_id[0]` |
| `coating_thickness_microns` | coating/layer thickness in microns for deposition and anodizing operations; if omitted, process default is used |
| `processing_depth_microns` | removal depth in microns for electropolishing/material-removal operations; if omitted, process default is used |
| `tolerance_id` | tolerance coefficient ID, used by CNC ML calculation |
| `finish_id` | finish coefficient ID, used by CNC ML calculation |
| `is_need_special_equipment` | explicit tooling flag for `composite`; CNC tooling flag is predicted by classifier |

## Active calculation logic

### 3D printing: `service_id="printing"`

The printing path is rule-based:

1. Read dimensions from the request or extracted file data.
2. Resolve material data from `constants.MATERIALS`.
3. Calculate material volume, material weight and material price.
4. Estimate printing work time and work price.
5. Apply coefficients: quantity, cover, type/process, quality control, certification.
6. Return a unified price response.

Implementation files:

- `calculators/printing_calculator.py`
- `calculations/printing.py`
- `calculations/core.py`

### Electroplating: `service_id="electroplating_auto"`

The electroplating path is rule-based and uses STP/STEP geometry from `extractors/stp_extractor.py`. The extractor returns `surface_area` in mm², `volume` in mm³ and OBB dimensions in mm. For galvanic calculation the code converts:

- surface area: mm² → dm²;
- volume: mm³ → dm³.

Calculation sequence:

1. Resolve the galvanic process from `electroplating_process_id` or, for backward compatibility, from `cover_id[0]`. Canonical process IDs and bath limits are read from `utils.electroplating_config.ELECTROPLATING_OPERATIONS`; short legacy IDs such as `zinc`, `cadmium`, `chrome`, `anodizing` are mapped to canonical operation IDs.
2. Read the material family from the explicit `constants.MATERIALS[*].electroplating_family` attribute. The code intentionally does not infer families from text. Supported families: `carbon_steel`, `stainless_steel`, `aluminum`, `copper`, `titanium`, `magnesium`.
3. Validate process compatibility with the material family.
4. Calculate part mass as `volume_dm3 * density_kg_dm3`, where fallback densities are steel 7.8, aluminum 2.7, copper 8.93, titanium 4.5 and magnesium 1.8 kg/dm³.
5. Read bath limits from the selected operation: `max_part_size_mm` for dimensions and `max_weight_kg` for maximum total load weight.
6. Try all axis-aligned OBB orientations in the selected bath and calculate geometric load capacity with a clearance.
7. For electrolytic processes, calculate current-limited capacity as `max_current_a / (current_density_a_dm2 * surface_area_dm2)`.
8. Calculate weight-limited capacity as `max_weight_kg / part_weight_kg`. This check uses the total mass of all parts in one bath load, not only the mass of a single part.
9. Calculate one-bath capacity as `min(geometric_capacity, current_capacity, weight_capacity)`. The actual formula parameter `n` is `min(requested_quantity, one_bath_capacity)`, so a larger order can reduce per-detail labor only up to geometry/current/weight limits.
10. Calculate the operation time component by the explicit process time model:
    - `faraday_deposition`: coating deposition by `T=(a*b)/(c*d*e)`, where `a` is `coating_thickness_microns`;
    - `faraday_layer_growth`: anodic oxide layer growth by the same configured formula, where `a` is oxide-layer thickness;
    - `faraday_material_removal`: electropolishing/material removal by the same configured formula, where `a` is `processing_depth_microns`, not coating thickness;
    - `fixed_time`: chemical/preparatory operations, where `fixed_operation_time_min` is used and layer thickness does not affect time.
11. Add preparation time, 30 minutes by default.
12. Calculate labor for one part: `(1.18*x)/n + z*k`, where `x` is total operation time, `n` is the calculated one-bath load, `z` is workers by mass and `k` is mounting/dismounting time, 2.5 minutes by default.
13. Convert labor hours to price using `calculations.core.calculate_cost`.

The response exposes the batching decision through `requested_quantity`, `batch_quantity`, `bath_batch_capacity`, `bath_geometric_capacity`, `bath_current_capacity`, `bath_weight_capacity`, `bath_max_weight_kg`, `batch_weight_kg`, `batch_count` and `batch_quantity_limited_by`.

Implementation files:

- `calculators/electroplating_calculator.py`
- `calculations/electroplating.py`
- `utils/electroplating_config.py`
- `docs/electroplating_constants_patch.py`

`utils/electroplating_config.py` is the single source of truth for galvanic operations, bath sizes, maximum batch weights, material-family compatibility and process time models. `constants.py` should keep only general materials/services data.

### CNC milling: `service_id="cnc-milling"`

The CNC milling path is ML-only. There is no rule-based fallback.

Labor intensity:

- predicted by the `flexible_ensemble` bundle through `utils.composite_ml_predictor`;
- model artifact: `ml_models/bundle_metalcomposite_lgbm_base.pkl`;
- package code: `ml_models/flexible_ensemble/`.

Special-equipment flag:

- predicted separately by an XGBoost classifier through `utils.ml_predictor`;
- target: `is_need_special_equipment`;
- classifier artifact: `ml_models/base_model_xgb_classification_v0.04.json`;
- classifier preprocessing still uses scaler, encoder, clusterer and reducer assets configured in `constants.py`.

`ML_SCALER_PATH`, `ML_CLUSTERER_PATH` and `ML_REDUCER_PATH` are intentionally retained because they are part of the XGBoost classifier preprocessing pipeline.

Implementation files:

- `calculators/ml_calculator.py`
- `utils/composite_ml_predictor.py`
- `utils/ml_predictor.py`
- `utils/calculation_router.py`

### Composite: `service_id="composite"`

The composite path uses the same `flexible_ensemble` bundle for labor-intensity prediction. The tooling flag is not predicted by XGBoost; it is supplied by the request as `is_need_special_equipment`.

Composite tooling calculation uses an MDF plate assumption by default:

- default material key: `mdf`;
- default form: `plate`;
- the part OBB is expanded by a reserve coefficient;
- tooling material price is calculated from plate dimensions and required blank volume/layers.

Implementation files:

- `calculators/ml_calculator.py`, class `MLCompositeCalculator`
- `utils/composite_ml_predictor.py`
- `calculations/core.py`

## Quantity discount

The old step discount was replaced by a smooth logarithmic interpolation in `calculations/core.py::calculate_k_quantity`.

Control points:

| Quantity | `k_quantity` |
|---:|---:|
| 1 | 1.00 |
| 20 | 0.98 |
| 100 | 0.95 |
| 500 | 0.85 |
| 1000+ | 0.80 |

The coefficient is interpolated in log-space, so unit price decreases smoothly as order quantity grows.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | API information |
| `GET /health` | health check |
| `GET /version` | API version from `constants.APP_VERSION` |
| `POST /calculate-price` | unified price calculation |
| `POST /generate-previews` | render preview PNG images for STL/STP/STEP files |
| `GET /materials` | list materials, optionally filtered by process; for `electroplating_auto` also supports `electroplating_process_id` to return only materials compatible with the selected galvanic operation |
| `GET /material_forms` | list configured material forms for `material_id`; for `electroplating_auto` can also validate compatibility with `electroplating_process_id` |
| `GET /services` | list available service IDs |
| `GET /auto_services` | list automatically calculated services |
| `GET /other_services` | list other/manual service options |
| `GET /all_services` | list all non-removed services |
| `GET /coefficients` | tolerance, finish, cover, control and certification coefficients |
| `GET /locations` | manufacturing locations |
| `GET /operations_available` | available operations for non-auto services |

## Project structure

```text
.
├── main.py                         # FastAPI app and HTTP endpoints
├── calculations/
│   ├── core.py                     # shared pricing/math/material helpers
│   ├── printing.py                 # rule-based 3D printing calculation
│   ├── electroplating.py           # rule-based galvanic coating calculation
│   └── __init__.py
├── calculators/
│   ├── base_calculator.py          # common response/logging helpers
│   ├── printing_calculator.py      # active printing calculator
│   ├── electroplating_calculator.py # active galvanic coating calculator
│   ├── ml_calculator.py            # CNC milling ML and composite ML calculators
│   └── __init__.py
├── extractors/
│   ├── file_extractor.py           # common file extraction interface
│   ├── stl_extractor.py            # STL extraction
│   └── stp_extractor.py            # STP/STEP extraction
├── ml_models/
│   ├── base_model_xgb_classification_v0.04.json
│   ├── bundle_metalcomposite_lgbm*.pkl
│   ├── bundle_metalcomposite_lgbm*.pkl.manifest.json
│   └── flexible_ensemble/          # inference/training support package for bundle models
├── models/
│   ├── base_models.py              # common Pydantic models/enums
│   ├── request_models.py           # public request model
│   ├── response_models.py          # public response model
│   ├── calculation_models.py       # internal request models
│   └── error_models.py             # standardized error models
├── utils/
│   ├── calculation_router.py       # active service routing
│   ├── electroplating_config.py    # galvanic process/bath/material-family defaults
│   ├── composite_ml_predictor.py   # flexible_ensemble bundle inference
│   ├── ml_predictor.py             # XGBoost special-equipment classifier only
│   ├── parameter_extractor.py      # CAD feature extraction orchestration
│   ├── safeguards.py               # default values and request safeguards
│   ├── validation_utils.py         # request validation
│   ├── response_utils.py           # standardized response wrapper
│   ├── generate_previews.py        # preview generation
│   ├── logging_utils.py
│   └── versioning.py
├── scripts/                        # manual testing and service helper scripts
└── tests/                          # regression and endpoint tests
```

Removed legacy files are intentionally absent:

- `calculations/cnc.py`
- `calculators/cnc_milling_calculator.py`
- `calculators/cnc_lathe_calculator.py`
- `calculations/painting.py`
- `calculators/painting_calculator.py`

## Configuration

The app imports operational constants from `constants.py`. This file is expected to define reference data and model paths, including:

- `APP_VERSION`
- `MATERIALS`
- `LOCATIONS`
- `COST_STRUCTURE`
- `TOLERANCE`
- `FINISH`
- `COVER`
- `CERT_COSTS`
- `DEFAULTS`
- `AUTO_SERVICES`
- `NON_AUTO_SERVICES`
- `OTHER_SERVICES`
- `ENABLE_ML_MODELS`
- `ELECTROPLATING_SERVICE_CONFIG`
- `ELECTROPLATING_BATHS`
- `ELECTROPLATING_PROCESS_PARAMS`
- `ELECTROPLATING_MATERIAL_FAMILIES`
- `ELECTROPLATING_DEFAULTS`
- `ML_CLASSIFIER_PATH`
- `ML_SCALER_PATH`
- `CLASSIFIER_SCALER_FEATURES_PATH`
- `ML_CLUSTERER_PATH`
- `ML_REDUCER_PATH`
- `ENCODER_PATH`
- `NUM_CORE_CLASSIFIER_FEATURES`
- `CLASSIFIER_CATEGORICAL_FEATURES`
- `SPECIAL_EQUIPMENT_COEF`
- `SPECIAL_EQUIPMENT_MATERIAL`
- `SPECIAL_EQUIPMENT_FORM`
- optional `DOP_MATERIALS` for composite tooling materials

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## 🛠️ Installation

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd stl
   ```

2. **Quick start with Docker**
   ```bash

  # Windows
  cd maas-backend-stl
  docker-compose -f docker-compose.dev.yml up -d
   ```

3. **Access the API**
   - API Documentation: http://localhost:7000/docs
   - Health Check: http://localhost:7000/health

### Option 2: Local Development

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   # or
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 7000
   ```

## 🔧 API Usage
Open API docs:

```text
http://localhost:7000/docs
```

## Minimal CNC milling request shape

`cnc-milling` requires file data because the ML path needs extracted geometry features.

### **Unified Endpoint: `/calculate-price`**

#### **Request Format**
```json
{
  "service_id": "cnc-milling",
  "file_id": "example-001",
  "file_data": "<base64 step file>",
  "file_name": "part.stp",
  "file_type": "stp",
  "material_id": "alum_D16",
  "material_form": "plate",
  "quantity": 10,
  "tolerance_id": "4",
  "finish_id": "3",
  "cover_id": ["1"],
  "location": "location_1"
}
```

If ML assets or required geometry features are unavailable, the service returns a calculation error. It does not fall back to rule-based CNC.


## 🧪 Testing

Run the complete test suite:
```bash
python -m pytest tests/ -v
