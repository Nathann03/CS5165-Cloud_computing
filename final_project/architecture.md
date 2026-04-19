# Architecture

## Final Architecture
- Frontend: FastAPI-rendered web UI with lightweight JavaScript and Plotly charts
- Backend: FastAPI
- Local database: SQLite for fast development, repeatable tests, and offline demo preparation
- Azure database: Azure Database for PostgreSQL Flexible Server
- Azure hosting: Azure App Service (Linux)
- ML/runtime libraries: pandas, numpy, scikit-learn

## Data Flow
1. CSV files are loaded from the provided 84.51 dataset or from uploaded replacement CSVs.
2. The ingestion layer normalizes column names, trims fixed-width values, parses dates, and loads three relational tables.
3. Search and sample-pull pages join `transactions`, `households`, and `products` by `HSHD_NUM` and `PRODUCT_NUM`.
4. Dashboard analytics aggregate spend, brand mix, income patterns, and basket combinations.
5. ML workflows engineer household/basket features and persist CLV, basket, and churn metrics under `artifacts/ml/`.
6. In Azure, the same app points to a managed PostgreSQL database via `DATABASE_URL`.

## Why This Works For The Class Project
- Minimal Azure footprint
- Separate managed database as requested
- Easy-to-demo web pages
- Fully based on the provided 84.51 data
- Repeatable ingestion and retraining steps
