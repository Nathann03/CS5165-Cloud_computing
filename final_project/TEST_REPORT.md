# TEST_REPORT

## Summary
Local core functionality was tested successfully for data loading, joins, dashboard aggregation, ML training, and repeatable reload behavior. Final Azure deployment verification is blocked in this environment because Azure CLI is not logged in here.

## Tests Run

### 1. Data Load Test
- Command:
  ```bash
  PYTHONPATH=.packages:. python3 scripts/bootstrap_local.py
  ```
- Result: Pass
- Evidence:
  - `households = 400`
  - `products = 67,284`
  - `transactions = 922,008`

### 2. Search / Sample Pull Test
- Command:
  ```bash
  python3 scripts/regression_checks.py
  ```
- Result: Pass
- Evidence:
  - `HSHD_NUM 10` returned rows from the joined data pull
  - First joined row included `department = NON-FOOD` and `commodity = TOBACCO PRODUCTS`
  - Sort-compatible columns were populated

### 3. Dashboard Test
- Command:
  ```bash
  python3 scripts/regression_checks.py
  ```
- Result: Pass
- Evidence:
  - Dashboard summary metrics were generated
  - `monthly_spend` produced 25 time points in smoke-test validation
  - Top basket pair example: `GROCERY STAPLE + PRODUCE`

### 4. ML Test
- Command:
  ```bash
  python3 scripts/train_models.py
  ```
- Result: Pass on smoke-test database
- Evidence:
  - CLV metrics saved to `artifacts/ml/clv_metrics.json`
  - Basket metrics saved to `artifacts/ml/basket_metrics.json`
  - Churn metrics saved to `artifacts/ml/churn_metrics.json`
- Metrics:
  - CLV: `MAE 25.469`, `RMSE 33.155`
  - Basket: `Accuracy 0.93`, `ROC AUC 0.891`
  - Churn: `Accuracy 0.874`, `ROC AUC 0.843`

### 5. Data Refresh Test
- Command:
  ```bash
  python3 scripts/regression_checks.py
  ```
- Result: Pass
- Evidence:
  - The dataset was reloaded into fresh smoke-test databases multiple times
  - Search and analytics still worked after reload

### 6. Deployment Test
- Command:
  ```bash
  AZURE_CONFIG_DIR=.azure az account show --output json
  ```
- Result: Blocked
- Exact blocker:
  - Azure CLI returned `Please run 'az login' to setup account.`

### 7. Basic Regression Test
- Command:
  ```bash
  python3 scripts/regression_checks.py
  ```
- Result: Pass
- Evidence:
  - Load, search, dashboard, ML, and route-construction checks completed in one script

## Known Issues
- Local HTTP port binding is blocked in this sandbox, so browser-style page checks could not be performed here via `uvicorn` + `curl`.
- Azure deployment could not be executed from this session because Azure CLI is not authenticated.

## Output Artifacts
- Load report: `artifacts/analytics/load_report.json`
- Regression report: `artifacts/analytics/regression_report.json`
- ML metrics:
  - `artifacts/ml/clv_metrics.json`
  - `artifacts/ml/basket_metrics.json`
  - `artifacts/ml/churn_metrics.json`
