from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "8451_The_Complete_Journey_2_Sample-2"
MINIMUM_DATASET_DIR = BASE_DIR / "data" / "uploads" / "azure_minimum"
DEFAULT_DB_PATH = BASE_DIR / "data" / "db" / "retail_analytics.db"


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Retail Analytics Cloud Project")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key")
    admin_token: str = os.getenv("ADMIN_TOKEN", "")
    auto_load_on_startup: bool = os.getenv("AUTO_LOAD_ON_STARTUP", "1") == "1"
    startup_transaction_limit: int | None = (
        int(os.getenv("STARTUP_TRANSACTION_LIMIT", "0")) or None
    )
    min_required_transactions: int = int(os.getenv("MIN_REQUIRED_TRANSACTIONS", "10000"))
    azure_blob_connection_string: str = os.getenv("AZURE_BLOB_CONNECTION_STRING", "")
    azure_blob_container: str = os.getenv("AZURE_BLOB_CONTAINER", "retail-datasets")
    azure_blob_households_blob: str = os.getenv("AZURE_BLOB_HOUSEHOLDS_BLOB", "400_households.csv")
    azure_blob_products_blob: str = os.getenv("AZURE_BLOB_PRODUCTS_BLOB", "400_products.csv")
    azure_blob_transactions_blob: str = os.getenv("AZURE_BLOB_TRANSACTIONS_BLOB", "400_transactions.csv")
    households_csv: Path = Path(os.getenv("HOUSEHOLDS_CSV", MINIMUM_DATASET_DIR / "400_households_min10k.csv"))
    products_csv: Path = Path(os.getenv("PRODUCTS_CSV", MINIMUM_DATASET_DIR / "400_products_min10k.csv"))
    transactions_csv: Path = Path(os.getenv("TRANSACTIONS_CSV", MINIMUM_DATASET_DIR / "400_transactions_min10k.csv"))
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    artifacts_dir: Path = BASE_DIR / "artifacts"

    @property
    def ml_dir(self) -> Path:
        return self.artifacts_dir / "ml"

    @property
    def analytics_dir(self) -> Path:
        return self.artifacts_dir / "analytics"

    @property
    def admin_token_required(self) -> bool:
        return bool(self.admin_token)

    @property
    def blob_configured(self) -> bool:
        return bool(self.azure_blob_connection_string and self.azure_blob_container)


settings = Settings()
