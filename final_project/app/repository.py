from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


HOUSEHOLD_PULL_SQL = text(
    """
    SELECT
        t.hshd_num,
        t.basket_num,
        t.purchase_date,
        t.purchase_,
        t.product_num,
        p.department,
        p.commodity,
        p.brand_ty,
        p.natural_organic_flag,
        t.spend,
        t.units,
        t.store_r,
        t.week_num,
        t.year,
        h.l,
        h.age_range,
        h.marital,
        h.income_range,
        h.homeowner,
        h.hshd_composition,
        h.hh_size,
        h.children
    FROM transactions t
    LEFT JOIN households h ON h.hshd_num = t.hshd_num
    LEFT JOIN products p ON p.product_num = t.product_num
    WHERE t.hshd_num = :hshd_num
    ORDER BY t.hshd_num, t.basket_num, t.purchase_date, t.product_num, p.department, p.commodity
    """
)


def fetch_household_pull(engine: Engine, hshd_num: int) -> pd.DataFrame:
    with engine.connect() as connection:
        frame = pd.read_sql(HOUSEHOLD_PULL_SQL, connection, params={"hshd_num": hshd_num})
    return frame


def fetch_table_counts(engine: Engine) -> dict[str, int]:
    queries = {
        "households": "SELECT COUNT(*) AS count FROM households",
        "products": "SELECT COUNT(*) AS count FROM products",
        "transactions": "SELECT COUNT(*) AS count FROM transactions",
    }
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for name, query in queries.items():
            counts[name] = int(connection.execute(text(query)).scalar_one())
    return counts
