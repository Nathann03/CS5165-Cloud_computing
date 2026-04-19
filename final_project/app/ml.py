from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, mean_absolute_error, mean_squared_error, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy.engine import Engine

from app.config import settings


def _load_joined_frame(engine: Engine) -> pd.DataFrame:
    query = """
        SELECT
            t.hshd_num,
            t.basket_num,
            t.purchase_date,
            t.product_num,
            t.spend,
            t.units,
            t.store_r,
            t.week_num,
            t.year,
            h.l,
            h.age_range,
            h.income_range,
            h.hh_size,
            h.children,
            p.department,
            p.commodity,
            p.brand_ty,
            p.natural_organic_flag
        FROM transactions t
        LEFT JOIN households h ON h.hshd_num = t.hshd_num
        LEFT JOIN products p ON p.product_num = t.product_num
    """
    with engine.connect() as connection:
        frame = pd.read_sql(query, connection, parse_dates=["purchase_date"])
    return frame


def _preprocessor(numeric_columns: list[str], categorical_columns: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric_columns),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_columns,
            ),
        ]
    )


def _normalize_categoricals(frame: pd.DataFrame, categorical_columns: list[str]) -> pd.DataFrame:
    copy = frame.copy()
    for column in categorical_columns:
        copy[column] = copy[column].fillna("Unknown").astype(str)
    return copy


def _save_metrics(filename: str, payload: dict) -> Path:
    settings.ml_dir.mkdir(parents=True, exist_ok=True)
    path = settings.ml_dir / filename
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _save_json(filename: str, payload: dict | list[dict]) -> Path:
    settings.ml_dir.mkdir(parents=True, exist_ok=True)
    path = settings.ml_dir / filename
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _stratify_or_none(values: pd.Series):
    counts = values.value_counts(dropna=False)
    if counts.empty or counts.min() < 2 or len(counts) < 2:
        return None
    return values


def _safe_regression_split(features: pd.DataFrame, target: pd.Series):
    if len(features) < 4:
        return features, features, target, target, "training_fallback"
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            features,
            target,
            test_size=0.25,
            random_state=42,
        )
        return X_train, X_test, y_train, y_test, "holdout"
    except ValueError:
        return features, features, target, target, "training_fallback"


def _safe_classification_split(features: pd.DataFrame, target: pd.Series):
    if len(features) < 4 or target.nunique() < 2:
        return features, features, target, target, "training_fallback"
    stratify = _stratify_or_none(target)
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            features,
            target,
            test_size=0.25,
            random_state=42,
            stratify=stratify,
        )
    except ValueError:
        X_train, X_test, y_train, y_test = features, features, target, target
        return X_train, X_test, y_train, y_test, "training_fallback"

    if y_train.nunique() < 2 or y_test.nunique() < 2:
        return features, features, target, target, "training_fallback"
    return X_train, X_test, y_train, y_test, "holdout"


def _classification_metrics(y_true: pd.Series, probabilities, evaluation_method: str) -> tuple[float | None, float | None]:
    if evaluation_method != "holdout":
        return None, None

    predictions = (probabilities >= 0.5).astype(int)
    accuracy = round(float(accuracy_score(y_true, predictions)), 3)
    roc_auc = round(float(roc_auc_score(y_true, probabilities)), 3) if y_true.nunique() > 1 else None
    return accuracy, roc_auc


def train_clv_model(engine: Engine) -> dict:
    frame = _load_joined_frame(engine)
    cutoff = frame["purchase_date"].quantile(0.7)
    history = frame[frame["purchase_date"] <= cutoff]
    future = frame[frame["purchase_date"] > cutoff]

    features = (
        history.groupby("hshd_num", as_index=False)
        .agg(
            orders=("basket_num", "nunique"),
            spend_total=("spend", "sum"),
            spend_mean=("spend", "mean"),
            units_total=("units", "sum"),
            unique_departments=("department", "nunique"),
            unique_commodities=("commodity", "nunique"),
            avg_week=("week_num", "mean"),
            dominant_region=("store_r", lambda values: values.mode().iloc[0] if not values.mode().empty else None),
            age_range=("age_range", "first"),
            income_range=("income_range", "first"),
            loyalty=("l", "first"),
        )
    )
    target = future.groupby("hshd_num", as_index=False).agg(clv_target=("spend", "sum"))
    dataset = features.merge(target, on="hshd_num", how="inner")

    numeric_columns = ["orders", "spend_total", "spend_mean", "units_total", "unique_departments", "unique_commodities", "avg_week"]
    categorical_columns = ["dominant_region", "age_range", "income_range", "loyalty"]
    dataset = _normalize_categoricals(dataset, categorical_columns)

    X_train, X_test, y_train, y_test, evaluation_method = _safe_regression_split(
        dataset[numeric_columns + categorical_columns],
        dataset["clv_target"],
    )
    model = Pipeline(
        [
            ("prep", _preprocessor(numeric_columns, categorical_columns)),
            ("model", GradientBoostingRegressor(random_state=42)),
        ]
    )
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    payload = {
        "model": "GradientBoostingRegressor",
        "target_definition": "Household spend after the 70th percentile transaction date cutoff.",
        "mae": round(float(mean_absolute_error(y_test, predictions)), 3),
        "rmse": round(float(mean_squared_error(y_test, predictions) ** 0.5), 3),
        "records": int(len(dataset)),
        "evaluation_method": evaluation_method,
    }
    _save_metrics("clv_metrics.json", payload)
    return payload


def train_basket_model(engine: Engine) -> dict:
    frame = _load_joined_frame(engine)
    top_commodities = frame["commodity"].value_counts().head(6).index.tolist()
    primary = top_commodities[0]
    target_commodity = top_commodities[1]

    basket_level = (
        frame.groupby(["basket_num", "hshd_num"], as_index=False)
        .agg(
            total_spend=("spend", "sum"),
            total_units=("units", "sum"),
            item_count=("product_num", "count"),
            department_count=("department", "nunique"),
            month=("purchase_date", lambda values: values.min().month),
            region=("store_r", "first"),
            loyalty=("l", "first"),
            income_range=("income_range", "first"),
            commodities=("commodity", lambda values: sorted({value for value in values if pd.notna(value)})),
        )
    )
    basket_level = basket_level[basket_level["commodities"].apply(lambda values: primary in values)].copy()
    basket_level["has_cross_sell_target"] = basket_level["commodities"].apply(lambda values: target_commodity in values).astype(int)
    basket_level = basket_level.drop(columns=["commodities"])

    numeric_columns = ["total_spend", "total_units", "item_count", "department_count", "month"]
    categorical_columns = ["region", "loyalty", "income_range"]
    basket_level = _normalize_categoricals(basket_level, categorical_columns)
    X_train, X_test, y_train, y_test, evaluation_method = _safe_classification_split(
        basket_level[numeric_columns + categorical_columns],
        basket_level["has_cross_sell_target"],
    )
    model = Pipeline(
        [
            ("prep", _preprocessor(numeric_columns, categorical_columns)),
            ("model", RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)),
        ]
    )
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_test)[:, 1]
    accuracy, roc_auc = _classification_metrics(y_test, probabilities, evaluation_method)
    payload = {
        "model": "RandomForestClassifier",
        "primary_commodity": primary,
        "cross_sell_target_commodity": target_commodity,
        "accuracy": accuracy,
        "roc_auc": roc_auc,
        "records": int(len(basket_level)),
        "evaluation_method": evaluation_method,
    }
    _save_metrics("basket_metrics.json", payload)
    return payload


def train_churn_model(engine: Engine) -> dict:
    frame = _load_joined_frame(engine)
    final_date = frame["purchase_date"].max()
    label_cutoff = final_date - pd.Timedelta(days=60)
    history_cutoff = label_cutoff - pd.Timedelta(days=90)

    history = frame[frame["purchase_date"] <= history_cutoff]
    label_window = frame[(frame["purchase_date"] > history_cutoff) & (frame["purchase_date"] <= label_cutoff)]
    future_window = frame[frame["purchase_date"] > label_cutoff]

    features = (
        history.groupby("hshd_num", as_index=False)
        .agg(
            spend_total=("spend", "sum"),
            baskets=("basket_num", "nunique"),
            items=("product_num", "count"),
            recency_reference=("purchase_date", "max"),
            region=("store_r", lambda values: values.mode().iloc[0] if not values.mode().empty else None),
            age_range=("age_range", "first"),
            income_range=("income_range", "first"),
            loyalty=("l", "first"),
        )
    )
    features["recency_days"] = (history_cutoff - features["recency_reference"]).dt.days
    activity = label_window.groupby("hshd_num", as_index=False).agg(label_window_baskets=("basket_num", "nunique"))
    future = future_window.groupby("hshd_num", as_index=False).agg(future_baskets=("basket_num", "nunique"))
    dataset = features.merge(activity, on="hshd_num", how="left").merge(future, on="hshd_num", how="left").fillna(0)
    dataset["churned"] = (dataset["future_baskets"] == 0).astype(int)

    numeric_columns = ["spend_total", "baskets", "items", "recency_days", "label_window_baskets"]
    categorical_columns = ["region", "age_range", "income_range", "loyalty"]
    dataset = _normalize_categoricals(dataset, categorical_columns)
    X_train, X_test, y_train, y_test, evaluation_method = _safe_classification_split(
        dataset[numeric_columns + categorical_columns],
        dataset["churned"],
    )
    model = Pipeline(
        [
            ("prep", _preprocessor(numeric_columns, categorical_columns)),
            ("model", GradientBoostingClassifier(random_state=42)),
        ]
    )
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_test)[:, 1]
    accuracy, roc_auc = _classification_metrics(y_test, probabilities, evaluation_method)
    scored = dataset.copy()
    scored["churn_risk_score"] = model.predict_proba(dataset[numeric_columns + categorical_columns])[:, 1]
    scored = scored.sort_values(["churn_risk_score", "recency_days", "baskets"], ascending=[False, False, True])
    top_risk = scored.head(25).copy()
    top_risk["risk_band"] = pd.cut(
        top_risk["churn_risk_score"],
        bins=[0, 0.4, 0.7, 1.0],
        labels=["Monitor", "Elevated", "High"],
        include_lowest=True,
    ).astype(str)
    payload = {
        "model": "GradientBoostingClassifier",
        "churn_definition": "No baskets in the final 60 days of the dataset.",
        "accuracy": accuracy,
        "roc_auc": roc_auc,
        "records": int(len(dataset)),
        "evaluation_method": evaluation_method,
        "evaluation_note": (
            "Holdout metrics are unavailable on the reduced Azure demo sample because the churn classes are too imbalanced."
            if evaluation_method != "holdout"
            else "Metrics are based on a holdout test split."
        ),
    }
    _save_metrics("churn_metrics.json", payload)
    _save_json(
        "at_risk_households.json",
        [
            {
                "hshd_num": int(row["hshd_num"]),
                "churn_risk_score": round(float(row["churn_risk_score"]), 3),
                "risk_band": row["risk_band"],
                "recency_days": int(row["recency_days"]),
                "historical_baskets": int(row["baskets"]),
                "recent_baskets": int(row["label_window_baskets"]),
                "spend_total": round(float(row["spend_total"]), 2),
                "income_range": row["income_range"],
                "loyalty": row["loyalty"],
            }
            for _, row in top_risk.iterrows()
        ],
    )
    return payload


def latest_metrics() -> dict[str, dict]:
    metrics: dict[str, dict] = {}
    for filename in ["clv_metrics.json", "basket_metrics.json", "churn_metrics.json"]:
        path = settings.ml_dir / filename
        if path.exists():
            metrics[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return metrics


def latest_at_risk_households() -> list[dict]:
    path = settings.ml_dir / "at_risk_households.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def fallback_at_risk_households(engine: Engine, limit: int = 25) -> list[dict]:
    if engine.dialect.name == "postgresql":
        query = text(
            """
            WITH last_dates AS (
                SELECT MAX(purchase_date) AS final_date FROM transactions
            ),
            household_features AS (
                SELECT
                    t.hshd_num,
                    MAX(t.purchase_date) AS last_purchase_date,
                    COUNT(DISTINCT t.basket_num) AS historical_baskets,
                    SUM(t.spend) AS spend_total,
                    COUNT(DISTINCT CASE
                        WHEN t.purchase_date >= ((SELECT final_date FROM last_dates) - INTERVAL '90 day')
                        THEN t.basket_num
                    END) AS recent_baskets,
                    h.income_range,
                    h.l AS loyalty
                FROM transactions t
                LEFT JOIN households h ON h.hshd_num = t.hshd_num
                GROUP BY t.hshd_num, h.income_range, h.l
            )
            SELECT
                hshd_num,
                CAST(DATE_PART('day', (SELECT final_date FROM last_dates) - last_purchase_date) AS INTEGER) AS recency_days,
                historical_baskets,
                recent_baskets,
                ROUND(spend_total::numeric, 2) AS spend_total,
                COALESCE(income_range, 'Unknown') AS income_range,
                COALESCE(loyalty, 'Unknown') AS loyalty
            FROM household_features
            ORDER BY recency_days DESC, recent_baskets ASC, historical_baskets ASC, spend_total ASC
            LIMIT :limit
            """
        )
    else:
        query = text(
            """
            WITH last_dates AS (
                SELECT MAX(purchase_date) AS final_date FROM transactions
            ),
            household_features AS (
                SELECT
                    t.hshd_num,
                    MAX(t.purchase_date) AS last_purchase_date,
                    COUNT(DISTINCT t.basket_num) AS historical_baskets,
                    SUM(t.spend) AS spend_total,
                    COUNT(DISTINCT CASE
                        WHEN t.purchase_date >= DATE((SELECT final_date FROM last_dates), '-90 day')
                        THEN t.basket_num
                    END) AS recent_baskets,
                    h.income_range,
                    h.l AS loyalty
                FROM transactions t
                LEFT JOIN households h ON h.hshd_num = t.hshd_num
                GROUP BY t.hshd_num, h.income_range, h.l
            )
            SELECT
                hshd_num,
                CAST(JULIANDAY((SELECT final_date FROM last_dates)) - JULIANDAY(last_purchase_date) AS INTEGER) AS recency_days,
                historical_baskets,
                recent_baskets,
                ROUND(spend_total, 2) AS spend_total,
                COALESCE(income_range, 'Unknown') AS income_range,
                COALESCE(loyalty, 'Unknown') AS loyalty
            FROM household_features
            ORDER BY recency_days DESC, recent_baskets ASC, historical_baskets ASC, spend_total ASC
            LIMIT :limit
            """
        )
    with engine.connect() as connection:
        rows = [dict(row._mapping) for row in connection.execute(query, {"limit": limit}).fetchall()]
    if not rows:
        return []
    max_recency = max(float(row["recency_days"] or 0) for row in rows) or 1.0
    max_baskets = max(float(row["historical_baskets"] or 0) for row in rows) or 1.0
    max_recent = max(float(row["recent_baskets"] or 0) for row in rows) or 1.0
    scored_rows = []
    for row in rows:
        score = min(
            1.0,
            max(
                0.0,
                0.55 * (float(row["recency_days"] or 0) / max_recency)
                + 0.25 * (1 - (float(row["recent_baskets"] or 0) / max_recent))
                + 0.20 * (1 - (float(row["historical_baskets"] or 0) / max_baskets)),
            ),
        )
        if score >= 0.7:
            risk_band = "High"
        elif score >= 0.4:
            risk_band = "Elevated"
        else:
            risk_band = "Monitor"
        scored_rows.append(
            {
                "hshd_num": int(row["hshd_num"]),
                "churn_risk_score": round(score, 3),
                "risk_band": risk_band,
                "recency_days": int(row["recency_days"] or 0),
                "historical_baskets": int(row["historical_baskets"] or 0),
                "recent_baskets": int(row["recent_baskets"] or 0),
                "spend_total": round(float(row["spend_total"] or 0), 2),
                "income_range": row["income_range"],
                "loyalty": row["loyalty"],
            }
        )
    scored_rows.sort(key=lambda item: (item["churn_risk_score"], item["recency_days"]), reverse=True)
    return scored_rows
