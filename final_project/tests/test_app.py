from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(".packages"))

import pytest
from fastapi.testclient import TestClient

from app.database import create_db_engine
from app.ingestion import LoadPaths, run_full_load
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def test_database():
    db_path = Path("data/db/test_retail_analytics.db")
    if db_path.exists():
      db_path.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.resolve()}"
    engine = create_db_engine(os.environ["DATABASE_URL"])
    paths = LoadPaths(
        households=Path("data/uploads/azure_minimum/400_households_min10k.csv"),
        products=Path("data/uploads/azure_minimum/400_products_min10k.csv"),
        transactions=Path("data/uploads/azure_minimum/400_transactions_min10k.csv"),
    )
    run_full_load(engine, paths=paths, limit_rows=15000)
    from app import main as main_module

    main_module.engine = engine
    yield


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database_ready"] is True


def test_sample_household_page():
    client = TestClient(app)
    response = client.get("/sample-household")
    assert response.status_code == 200
    assert "Household 10" in response.text


def test_search_page():
    client = TestClient(app)
    response = client.get("/search?hshd_num=10")
    assert response.status_code == 200
    assert "Results" in response.text
