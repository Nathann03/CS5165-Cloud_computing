from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".packages"))

from azure.storage.blob import BlobServiceClient

from app.config import settings


def main() -> None:
    if not settings.blob_configured:
        raise RuntimeError("Set AZURE_BLOB_CONNECTION_STRING and AZURE_BLOB_CONTAINER before uploading.")

    service = BlobServiceClient.from_connection_string(settings.azure_blob_connection_string)
    container = service.get_container_client(settings.azure_blob_container)
    container.create_container(exist_ok=True)

    uploads = {
        settings.azure_blob_households_blob: settings.households_csv,
        settings.azure_blob_products_blob: settings.products_csv,
        settings.azure_blob_transactions_blob: settings.transactions_csv,
    }

    for blob_name, path in uploads.items():
        with path.open("rb") as handle:
            container.upload_blob(blob_name, handle, overwrite=True)
        print({"uploaded_blob": blob_name, "source": str(path)})


if __name__ == "__main__":
    main()
