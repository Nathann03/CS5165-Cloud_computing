from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.analytics import build_dashboard_payload, latest_dashboard_payload, persist_dashboard_payload
from app.config import settings
from app.database import engine
from app.ingestion import LoadPaths, latest_load_report, run_full_load, validate_required_tables
from app.ml import (
    fallback_at_risk_households,
    latest_at_risk_households,
    latest_metrics,
    train_basket_model,
    train_churn_model,
    train_clv_model,
)
from app.repository import fetch_household_pull, fetch_table_counts


app = FastAPI(title=settings.app_name)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def require_admin_token(token: str | None) -> None:
    if settings.admin_token and token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token.")


def is_demo_logged_in(request: Request) -> bool:
    return bool(request.session.get("demo_user"))


def require_demo_login(request: Request) -> RedirectResponse | None:
    if is_demo_logged_in(request):
        return None
    return RedirectResponse(url="/", status_code=303)


def ensure_seed_data() -> None:
    tables_ready = validate_required_tables(engine)
    counts = fetch_table_counts(engine) if tables_ready else {}
    transaction_count = counts.get("transactions", 0)
    has_minimum_transactions = transaction_count >= settings.min_required_transactions
    if tables_ready and has_minimum_transactions:
        return
    if settings.auto_load_on_startup:
        run_full_load(engine, limit_rows=settings.startup_transaction_limit)


@app.on_event("startup")
def startup_event() -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.analytics_dir.mkdir(parents=True, exist_ok=True)
    settings.ml_dir.mkdir(parents=True, exist_ok=True)
    ensure_seed_data()


@app.get("/health")
def health() -> dict:
    tables_ready = validate_required_tables(engine)
    counts = fetch_table_counts(engine) if tables_ready else {}
    ready = tables_ready and counts.get("transactions", 0) >= settings.min_required_transactions
    return {"status": "ok", "database_ready": ready, "counts": counts}


@app.head("/health")
def health_head() -> dict:
    return health()


@app.get("/")
def home(request: Request):
    counts = fetch_table_counts(engine) if validate_required_tables(engine) else {}
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.app_name,
            "counts": counts,
            "demo_user": request.session.get("demo_user"),
            "login_error": request.session.pop("login_error", None),
            "admin_token_required": settings.admin_token_required,
        },
    )


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
):
    if not username.strip() or not password or "@" not in email:
        request.session["login_error"] = "Enter a username, password, and valid email to open the demo."
        return RedirectResponse(url="/", status_code=303)

    request.session["demo_user"] = {"username": username.strip(), "email": email.strip()}
    return RedirectResponse(url="/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.pop("demo_user", None)
    return RedirectResponse(url="/", status_code=303)


@app.get("/sample-household")
def sample_household(request: Request):
    redirect = require_demo_login(request)
    if redirect:
        return redirect
    frame = fetch_household_pull(engine, 10)
    preview = frame.head(250).to_dict(orient="records")
    return templates.TemplateResponse(
        request,
        "sample_pull.html",
        {
            "rows": preview,
            "row_count": len(frame),
            "hshd_num": 10,
        },
    )


@app.get("/search")
def search(request: Request, hshd_num: int | None = None):
    redirect = require_demo_login(request)
    if redirect:
        return redirect
    rows = []
    row_count = 0
    if hshd_num is not None:
        frame = fetch_household_pull(engine, hshd_num)
        row_count = len(frame)
        rows = frame.head(500).to_dict(orient="records")
    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "rows": rows,
            "row_count": row_count,
            "hshd_num": hshd_num,
        },
    )


@app.get("/dashboard")
def dashboard(request: Request):
    redirect = require_demo_login(request)
    if redirect:
        return redirect
    counts = fetch_table_counts(engine) if validate_required_tables(engine) else {}
    has_transactions = counts.get("transactions", 0) > 0
    payload = {
        "monthly_spend": [],
        "department_spend": [],
        "brand_mix": [],
        "income_spend": [],
        "region_spend": [],
        "engagement_summary": {
            "households": counts.get("households", 0),
            "transactions": counts.get("transactions", 0),
            "avg_basket_spend": 0,
            "avg_items_per_basket": 0,
        },
        "top_pairs": [],
    }
    if has_transactions:
        payload = latest_dashboard_payload() or {}
        cached_summary = payload.get("engagement_summary", {})
        cache_matches_db = (
            cached_summary.get("transactions") == counts.get("transactions")
            and cached_summary.get("households") == counts.get("households")
        )
        if not payload or not cache_matches_db:
            payload = persist_dashboard_payload(engine)
    at_risk_households = (latest_at_risk_households() or fallback_at_risk_households(engine)) if has_transactions else []
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "dashboard": payload,
            "dashboard_json": json.dumps(payload),
            "at_risk_households": at_risk_households,
        },
    )


@app.get("/admin")
def admin(request: Request):
    redirect = require_demo_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "report": latest_load_report(),
            "admin_token_required": settings.admin_token_required,
        },
    )


def _persist_upload(file: UploadFile | None, target_name: str, fallback: Path) -> Path:
    if file is None or not file.filename:
        return fallback
    if not file.filename.lower().endswith(".csv"):
        raise ValueError(f"{target_name} must be a CSV file.")
    destination = settings.upload_dir / f"{target_name}.csv"
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return destination


@app.post("/admin/reload")
async def admin_reload(
    request: Request,
    admin_token: str | None = Form(default=None),
    households_file: UploadFile | None = File(default=None),
    products_file: UploadFile | None = File(default=None),
    transactions_file: UploadFile | None = File(default=None),
):
    redirect = require_demo_login(request)
    if redirect:
        return redirect
    require_admin_token(admin_token)
    paths = LoadPaths(
        households=_persist_upload(households_file, "households", settings.households_csv),
        products=_persist_upload(products_file, "products", settings.products_csv),
        transactions=_persist_upload(transactions_file, "transactions", settings.transactions_csv),
    )
    run_full_load(engine, paths=paths)
    return RedirectResponse(url="/admin", status_code=303)


@app.get("/ml")
def ml_page(request: Request):
    redirect = require_demo_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "ml.html",
        {
            "metrics": latest_metrics(),
            "admin_token_required": settings.admin_token_required,
        },
    )


@app.post("/ml/run")
def ml_run(request: Request, admin_token: str | None = Form(default=None)):
    redirect = require_demo_login(request)
    if redirect:
        return redirect
    require_admin_token(admin_token)
    train_clv_model(engine)
    train_basket_model(engine)
    train_churn_model(engine)
    return RedirectResponse(url="/ml", status_code=303)
