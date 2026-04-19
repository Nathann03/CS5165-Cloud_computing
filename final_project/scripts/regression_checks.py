from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".packages"))

from app import main as main_module
from app.analytics import build_dashboard_payload
from app.database import create_db_engine
from app.ingestion import LoadPaths, run_full_load
from app.ml import train_basket_model, train_churn_model, train_clv_model
from app.repository import fetch_household_pull


def main() -> None:
    db_path = Path("data/db/regression.db")
    if db_path.exists():
        db_path.unlink()

    engine = create_db_engine(f"sqlite:///{db_path.resolve()}")
    paths = LoadPaths(
        households=Path("8451_The_Complete_Journey_2_Sample-2/400_households.csv"),
        products=Path("8451_The_Complete_Journey_2_Sample-2/400_products.csv"),
        transactions=Path("8451_The_Complete_Journey_2_Sample-2/400_transactions.csv"),
    )
    load_report = run_full_load(engine, paths=paths, limit_rows=20000)
    pull = fetch_household_pull(engine, 10)
    dashboard = build_dashboard_payload(engine)
    clv = train_clv_model(engine)
    basket = train_basket_model(engine)
    churn = train_churn_model(engine)

    main_module.engine = engine
    route_status = {"health": main_module.health()["database_ready"]}

    report = {
        "load_report": load_report,
        "sample_pull_rows": int(len(pull)),
        "sample_pull_first_row": pull[
            ["hshd_num", "basket_num", "purchase_", "product_num", "department", "commodity"]
        ].head(1).to_dict(orient="records")[0],
        "dashboard_summary": dashboard["engagement_summary"],
        "dashboard_top_pair": dashboard["top_pairs"][0],
        "ml_metrics": {"clv": clv, "basket": basket, "churn": churn},
        "route_status": route_status,
    }

    output_path = Path("artifacts/analytics/regression_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
