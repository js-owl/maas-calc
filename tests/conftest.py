# Slim review archives may omit confidential enterprise tables from constants.py.
# Provide minimal test stubs early, before test modules import calculators.
import commercial_constants

if not hasattr(commercial_constants, "COST_STRUCTURE"):
    commercial_constants.COST_STRUCTURE = {
        "location_1": {
            "price_of_hour": 1000.0,
            "dop_salary_coef": 0.1,
            "insurance_coef": 0.3,
            "overhead_expenses_coef": 0.2,
            "administrative_expenses_coef": 0.1,
            "profit_material": 0.2,
            "other_profit": 0.3,
        },
        "location_3": {
            "price_of_hour": 900.0,
            "dop_salary_coef": 0.1,
            "insurance_coef": 0.3,
            "overhead_expenses_coef": 0.2,
            "administrative_expenses_coef": 0.1,
            "profit_material": 0.2,
            "other_profit": 0.3,
        },
    }

if not hasattr(commercial_constants, "MACHINES"):
    commercial_constants.MACHINES = {
        "test_mill": {
            "type": "milling",
            "location": "location_1",
            "max_x": 10_000.0,
            "max_y": 10_000.0,
            "max_z": 10_000.0,
            "name": "test_mill",
        },
        "test_printer": {
            "type": "3d_printer",
            "location": "location_3",
            "max_x": 10_000.0,
            "max_y": 10_000.0,
            "max_z": 10_000.0,
            "name": "test_printer",
        },
    }

if not hasattr(commercial_constants, "LOCATIONS"):
    commercial_constants.LOCATIONS = {
        "location_1": {"label": "Test location 1"},
        "location_3": {"label": "Test location 3"},
    }

from typing import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    # Import app lazily. This lets pure unit tests for calculation modules run
    # even when a slim archive does not contain all constants required by the
    # full FastAPI application startup.
    from main import app

    with TestClient(app) as c:
        yield c
