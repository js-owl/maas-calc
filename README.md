# MaaS Backend Calculator — Manufacturing Calculation API

FastAPI backend for automated manufacturing price calculations from uploaded CAD files. The service extracts geometric parameters from STL/STP/STEP files and calculates prices for the currently active MaaS manufacturing services.

## Current active services

| `service_id` | Status | Calculation path |
|---|---|---|
| `printing` | active | rule-based calculation from geometry, material, quantity and coefficients |
| `electroplating_auto` | active | rule-based galvanic treatment calculation from STP/STEP surface area, volume, material family, selected operation and operation-specific time model |
| `cnc-milling` | active, ML-only | labor intensity from `ml_models.flexible_ensemble` bundle; special-equipment flag from XGBoost classifier |
| `composite` | active, ML-based | labor intensity from `ml_models.flexible_ensemble` bundle; tooling flag is supplied in the request |

Other services (return price equally 0 to estimate cost by specialists):

| `service_id` |
|---|
| `bending` |
| `handing` |
| `heating` |
| `laser-cutting` |
| `grinding` |
| `welding` |
| `casting` |
| `other` |
| `testing` |
| `rubber` |

## Unified automatic pricing

All automatic services use the same unit-price pipeline:

```text
base_cost = calculate_cost(mat_price, work_price, location)
detail_price_one = base_cost + price_special_equipment_to_quantity
detail_price = detail_price_one * k_quantity
total_price = detail_price * quantity
```

The detailed backend structure is stored in `total_price_breakdown`. The compact frontend/Bitrix view is stored in `detail_price_calculation` with six canonical fields: `material_price`, `salary_fund_with_taxes`, `price_special_equipment`, `price_without_vat`, `taxes`, `total`. See [`docs/internals/unified-pricing.md`](docs/internals/unified-pricing.md).

## Main calculation endpoint

```http
POST /calculate-price
```

Request model: `models.request_models.UnifiedCalculationRequest`.

General runtime-path of the automatic calculating:

1. `main.py::calculate_price` takes the request.
2. Checks whether `service_id` belongs to `AUTO_SERVICES` or `OTHER_SERVICES`.
3. For `OTHER_SERVICES` returns manual-pricing response with `0` price.
4. For `AUTO_SERVICES` checks validations.
5. If CAD-file was passed, `ParameterExtractor` chooses STL/STP extractor.
6. Retrival features merged with с request-params.
7. `SafeguardManager` fill `material_form` and `location` if these params is not valid.
8. `CalculationRouter` chooses active calculator.
9. Calculator returns `UnifiedCalculationResponse`.
10. Response is wrapped with `ResponseWrapper.success_response`.

## Documentation

Main page: [`docs/index.md`](docs/index.md).

Topics:

- [`docs/endpoints/`](docs/endpoints/) — individual `.md` for every endpoint.
- [`docs/service_ids/`](docs/service_ids/) — individual `.md` for every service id.
- [`docs/internals/`](docs/internals/) — validations, safeguards, routing, business constants, response wrapper.
- [`docs/extractors/`](docs/extractors/) — description of STP/STL extractors.

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
├── ml_models/ # TODO: need description, train code, and docs
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

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## 🛠️ Installation

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd maas-backend-stl
   ```

2. **Quick start with Docker**
   ```bash

   # Windows
   cd maas-backend-stl
   docker-compose -f docker-compose.yml up -d
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

## 🧪 Testing

Run the complete test suite:
```bash
python -m pytest tests/ -v
```
