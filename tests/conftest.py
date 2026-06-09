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
