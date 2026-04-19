# Retail Analytics Cloud Project

This project implements a retail analytics web application using the provided 84.51 / Kroger sample data. It includes the rubric-required data loading workflow, searchable household data pulls by `HSHD_NUM`, a retail dashboard, and ML workflows for CLV, basket analysis, and churn. The Azure deployment path now prioritizes reliable deployment over startup-heavy ingestion by using Blob Storage for raw CSV files and a separate load step into the managed database.

The repository defaults to the committed 10k-row sample under `data/uploads/azure_minimum/` so the app and tests can run from a fresh clone. The full raw `400_transactions.csv` is intentionally ignored because it is larger than GitHub's 100 MB file limit; set `TRANSACTIONS_CSV` locally if you have the full file and want to load it.

## Main Entry Point
- Local app entry: `app/main.py`
- Local data bootstrap: `scripts/bootstrap_local.py`
- ML training script: `scripts/train_models.py`
- Regression verification script: `scripts/regression_checks.py`

## Project Structure
- `app/`: FastAPI app, ingestion, analytics, ML, and repository code
- `templates/`: HTML templates
- `static/`: CSS assets
- `scripts/`: local bootstrap, training, regression, Blob upload, and Blob-to-database load scripts
- `deployment/`: Azure packaging and deployment scripts
- `artifacts/`: generated reports and ML metrics
- `8451_The_Complete_Journey_2_Sample-2/`: provided assignment materials and smaller raw reference CSVs
- `data/uploads/azure_minimum/`: committed 10k-row dataset used by default for local runs and tests

## Local Setup
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` if you want custom settings.
4. Load the dataset into the local database:
   ```bash
   python3 scripts/bootstrap_local.py
   ```
5. Run the app:
   ```bash
   uvicorn app.main:app --reload
   ```

## Local Verification
- Run regression checks:
  ```bash
  python3 scripts/regression_checks.py
  ```
- Train ML models:
  ```bash
  python3 scripts/train_models.py
  ```

## Core Features
- Home page with a lightweight demo login using `username`, `password`, and `email`
- Sample data pull for `HSHD_NUM 10`
- Search page for household-level joined data pulls
- Reload page for refreshed household, product, and transaction CSVs
- Dashboard for spend trends, brand mix, income patterns, region spend, and basket pairs
- ML results page for CLV, basket analysis, and churn

## Database Strategy
- Local development and tests use SQLite for speed and repeatability.
- Azure deployment uses a separate managed Azure Database for PostgreSQL Flexible Server.
- Azure deployment stores the raw CSV files in Azure Blob Storage and uses a separate loader script to populate PostgreSQL before app startup.
- The application uses the same normalized table shape in both environments.

## Azure Resources Used
- Azure App Service (Linux)
- Azure Database for PostgreSQL Flexible Server
- Azure Storage Account with Blob container
- Azure Resource Group

## Azure Deployment
The preferred Azure deployment path is:
1. create resources
2. upload the provided CSV files to Blob Storage
3. load Blob data into PostgreSQL
4. deploy the app
5. run the web app against the pre-populated managed database

### Required Environment Variables
- `POSTGRES_ADMIN_PASSWORD`
- Optionally:
  - `RESOURCE_GROUP`
  - `LOCATION`
  - `APP_SERVICE_PLAN`
  - `WEBAPP_NAME`
  - `POSTGRES_SERVER`
  - `POSTGRES_DB`
  - `POSTGRES_ADMIN_USER`
  - `STORAGE_ACCOUNT`
  - `BLOB_CONTAINER`

### Create Azure Resources
```bash
chmod +x deployment/*.sh
./deployment/create_azure_resources.sh
```

### Upload Raw Dataset Files To Blob Storage And Load PostgreSQL
If your PostgreSQL firewall is locked down, temporarily allow your current IP first:
```bash
export POSTGRES_SERVER=<your-postgres-server>
./deployment/allow_current_ip_for_postgres.sh
```

Then run the Blob upload and managed database load:
```bash
export STORAGE_ACCOUNT=<your-storage-account>
export RESOURCE_GROUP=cs5165-retail-rg
export DATABASE_URL="postgresql+psycopg://<user>:<password>@<server>.postgres.database.azure.com:5432/retailanalytics?sslmode=require"
./deployment/load_azure_data_from_blob.sh
```

This script:
- retrieves the storage account connection string
- uploads `400_households.csv`, `400_products.csv`, and `400_transactions.csv` to Blob Storage
- downloads those blobs and populates the managed PostgreSQL database

The equivalent Python commands are:
```bash
python3 scripts/upload_dataset_to_blob.py
python3 scripts/load_blob_to_db.py
```

After the load completes, remove the temporary local firewall rule:
```bash
export POSTGRES_SERVER=<your-postgres-server>
./deployment/remove_postgres_firewall_rule.sh
```

### Package The App
```bash
./deployment/package_for_azure.sh
```

### Deploy The App
```bash
WEBAPP_NAME=<your-webapp-name> ./deployment/deploy_app.sh
```

Important:
- keep `AUTO_LOAD_ON_STARTUP=0` in Azure
- do not rely on App Service startup to ingest the large CSV files
- the web app should start only after the managed database is already populated

### Cleanup
```bash
./deployment/cleanup_azure.sh
```

## Estimated Cost
- App Service B1: low monthly fixed cost
- PostgreSQL Flexible Server Burstable `Standard_B1ms`: low-cost managed database option
- Blob Storage `Standard_LRS`: very low cost for holding the raw CSV files
- Storage/network usage should remain small for coursework demo traffic

Use cleanup immediately after grading to avoid unnecessary charges.

## Cost Controls
- Minimal Azure service count
- No separate frontend hosting
- No managed ML service
- Smallest practical managed PostgreSQL tier
- Low-cost Blob Storage instead of keeping large raw files in the app package or re-ingesting them on every startup
- Explicit resource-group cleanup script

## Azure Reliability Note
- A startup-ingestion design was tested and proved unreliable on the low-cost App Service plan.
- The recommended architecture is now Blob Storage plus an explicit load step into PostgreSQL before the app is started for demo use.

## Submission Files
- Code: the application source under `app/`, `templates/`, `static/`, `scripts/`, and `deployment/`
- Model summaries: `ML_MODEL_WRITEUP.md`
- Project write-up: `WRITEUPS.md`
- Azure URL: the deployed Azure App Service link

## GitHub Cleanup Note
- Internal planning files such as `TODO.md`, `PROJECT_NOTES.md`, `DECISIONS.md`, and `FINAL_STATUS.md` are now listed in `.gitignore` so they do not need to be part of the public GitHub submission.
