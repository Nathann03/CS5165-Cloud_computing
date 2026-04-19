from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.analytics import persist_dashboard_payload
from app.config import settings


@dataclass(slots=True)
class LoadPaths:
    households: Path
    products: Path
    transactions: Path


def default_load_paths() -> LoadPaths:
    return LoadPaths(
        households=settings.households_csv,
        products=settings.products_csv,
        transactions=settings.transactions_csv,
    )


def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame.columns = [column.strip().lower() for column in frame.columns]
    for column in frame.columns:
        frame[column] = frame[column].map(lambda value: value.strip() if isinstance(value, str) else value)
    frame = frame.replace({"null": None, "NULL": None, "nan": None, "None": None})
    return frame


def load_households(path: Path, limit_rows: int | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, nrows=limit_rows, skipinitialspace=True)
    frame = _clean_frame(frame)
    frame["hshd_num"] = frame["hshd_num"].astype(int)
    return frame


def load_products(path: Path, limit_rows: int | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, nrows=limit_rows, skipinitialspace=True)
    frame = _clean_frame(frame)
    return frame


def load_transactions(path: Path, limit_rows: int | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, nrows=limit_rows, skipinitialspace=True)
    frame = _clean_frame(frame)
    frame["hshd_num"] = frame["hshd_num"].astype(int)
    frame["purchase_date"] = pd.to_datetime(frame["purchase_"], format="%d-%b-%y")
    frame["spend"] = pd.to_numeric(frame["spend"], errors="coerce").fillna(0.0)
    frame["units"] = pd.to_numeric(frame["units"], errors="coerce").fillna(0.0)
    frame["week_num"] = pd.to_numeric(frame["week_num"], errors="coerce").fillna(0).astype(int)
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce").fillna(0).astype(int)
    return frame


def _write_table(frame: pd.DataFrame, engine: Engine, table_name: str) -> None:
    chunksize = 1000
    if engine.dialect.name == "sqlite":
        chunksize = 5000
    frame.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=chunksize, method="multi")


def _create_indexes(engine: Engine) -> None:
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_households_hshd_num ON households(hshd_num)",
        "CREATE INDEX IF NOT EXISTS idx_products_product_num ON products(product_num)",
        (
            "CREATE INDEX IF NOT EXISTS idx_transactions_sort "
            "ON transactions(hshd_num, basket_num, purchase_date, product_num)"
        ),
        "CREATE INDEX IF NOT EXISTS idx_transactions_product_num ON transactions(product_num)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_purchase_date ON transactions(purchase_date)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def validate_required_tables(engine: Engine) -> bool:
    inspector = inspect(engine)
    return {"households", "products", "transactions"}.issubset(set(inspector.get_table_names()))


def run_full_load(engine: Engine, paths: LoadPaths | None = None, limit_rows: int | None = None) -> dict:
    active_paths = paths or default_load_paths()
    started = perf_counter()
    households = load_households(active_paths.households)
    transactions = load_transactions(active_paths.transactions, limit_rows=limit_rows)
    products = load_products(active_paths.products)
    if limit_rows is not None:
        product_nums = set(transactions["product_num"].astype(str).unique().tolist())
        products = products[products["product_num"].astype(str).isin(product_nums)].copy()

    _write_table(households, engine, "households")
    _write_table(products, engine, "products")
    _write_table(transactions, engine, "transactions")
    _create_indexes(engine)
    persist_dashboard_payload(engine)

    report = {
        "households_rows": int(len(households)),
        "products_rows": int(len(products)),
        "transactions_rows": int(len(transactions)),
        "household_10_rows": int((transactions["hshd_num"] == 10).sum()),
        "date_min": transactions["purchase_date"].min().strftime("%Y-%m-%d"),
        "date_max": transactions["purchase_date"].max().strftime("%Y-%m-%d"),
        "elapsed_seconds": round(perf_counter() - started, 2),
        "paths": {
            "households": str(active_paths.households),
            "products": str(active_paths.products),
            "transactions": str(active_paths.transactions),
        },
    }
    settings.analytics_dir.mkdir(parents=True, exist_ok=True)
    (settings.analytics_dir / "load_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def latest_load_report() -> dict | None:
    path = settings.analytics_dir / "load_report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
