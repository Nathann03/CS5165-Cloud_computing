from __future__ import annotations

import json

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from app.config import settings


def build_dashboard_payload(engine: Engine) -> dict:
    if engine.dialect.name == "postgresql":
        monthly_spend_sql = text(
            """
            SELECT TO_CHAR(purchase_date, 'YYYY-MM') AS month, ROUND(SUM(spend)::numeric, 2) AS spend
            FROM transactions
            GROUP BY TO_CHAR(purchase_date, 'YYYY-MM')
            ORDER BY month
            """
        )
    else:
        monthly_spend_sql = text(
            """
            SELECT substr(purchase_date, 1, 7) AS month, ROUND(SUM(spend), 2) AS spend
            FROM transactions
            GROUP BY substr(purchase_date, 1, 7)
            ORDER BY month
            """
        )
    with engine.connect() as connection:
        monthly_spend = pd.read_sql(monthly_spend_sql, connection)
        department_spend = pd.read_sql(
            text(
                """
                SELECT p.department, SUM(t.spend) AS spend
                FROM transactions t
                LEFT JOIN products p ON p.product_num = t.product_num
                GROUP BY p.department
                ORDER BY spend DESC
                LIMIT 10
                """
            ),
            connection,
        )
        brand_mix = pd.read_sql(
            text(
                """
                SELECT p.brand_ty, SUM(t.spend) AS spend
                FROM transactions t
                LEFT JOIN products p ON p.product_num = t.product_num
                GROUP BY p.brand_ty
                ORDER BY spend DESC
                """
            ),
            connection,
        )
        income_spend = pd.read_sql(
            text(
                """
                SELECT COALESCE(h.income_range, 'Unknown') AS income_range, SUM(t.spend) AS spend
                FROM transactions t
                LEFT JOIN households h ON h.hshd_num = t.hshd_num
                GROUP BY COALESCE(h.income_range, 'Unknown')
                ORDER BY spend DESC
                LIMIT 10
                """
            ),
            connection,
        )
        region_spend = pd.read_sql(
            text(
                """
                SELECT store_r, SUM(spend) AS spend
                FROM transactions
                GROUP BY store_r
                ORDER BY spend DESC
                """
            ),
            connection,
        )
        transaction_count = int(pd.read_sql(text("SELECT COUNT(*) AS count FROM transactions"), connection)["count"].iloc[0])
        basket_summary = pd.read_sql(
            text(
                """
                SELECT
                    t.basket_num,
                    t.hshd_num,
                    SUM(t.spend) AS total_spend,
                    COUNT(t.product_num) AS item_count,
                    COUNT(DISTINCT p.commodity) AS unique_commodities
                FROM transactions t
                LEFT JOIN products p ON p.product_num = t.product_num
                GROUP BY t.basket_num, t.hshd_num
                """
            ),
            connection,
        )
        top_pairs = pd.read_sql(
            text(
                """
                WITH top_commodities AS (
                    SELECT p.commodity
                    FROM transactions t
                    LEFT JOIN products p ON p.product_num = t.product_num
                    WHERE p.commodity IS NOT NULL
                    GROUP BY p.commodity
                    ORDER BY COUNT(*) DESC
                    LIMIT 18
                ),
                basket_commodity AS (
                    SELECT DISTINCT t.basket_num, p.commodity
                    FROM transactions t
                    LEFT JOIN products p ON p.product_num = t.product_num
                    WHERE p.commodity IN (SELECT commodity FROM top_commodities)
                )
                SELECT
                    bc1.commodity AS "left",
                    bc2.commodity AS "right",
                    COUNT(*) AS count
                FROM basket_commodity bc1
                JOIN basket_commodity bc2
                  ON bc1.basket_num = bc2.basket_num
                 AND bc1.commodity < bc2.commodity
                GROUP BY bc1.commodity, bc2.commodity
                ORDER BY count DESC
                LIMIT 10
                """
            ),
            connection,
        )

    engagement_summary = {
        "avg_basket_spend": round(float(basket_summary["total_spend"].mean()), 2),
        "avg_items_per_basket": round(float(basket_summary["item_count"].mean()), 2),
        "avg_unique_commodities": round(float(basket_summary["unique_commodities"].mean()), 2),
        "households": int(basket_summary["hshd_num"].nunique()),
        "transactions": transaction_count,
    }

    return {
        "monthly_spend": monthly_spend.to_dict(orient="records"),
        "department_spend": department_spend.round({"spend": 2}).to_dict(orient="records"),
        "brand_mix": brand_mix.round({"spend": 2}).to_dict(orient="records"),
        "income_spend": income_spend.round({"spend": 2}).to_dict(orient="records"),
        "region_spend": region_spend.round({"spend": 2}).to_dict(orient="records"),
        "engagement_summary": engagement_summary,
        "top_pairs": top_pairs.to_dict(orient="records"),
    }


def persist_dashboard_payload(engine: Engine) -> dict:
    payload = build_dashboard_payload(engine)
    settings.analytics_dir.mkdir(parents=True, exist_ok=True)
    (settings.analytics_dir / "dashboard_payload.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def latest_dashboard_payload() -> dict | None:
    path = settings.analytics_dir / "dashboard_payload.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
