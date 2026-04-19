from __future__ import annotations

from pathlib import Path

from azure.storage.blob import BlobServiceClient

from app.config import settings
from app.ingestion import LoadPaths


def download_blob_datasets(target_dir: Path) -> LoadPaths:
    if not settings.blob_configured:
        raise RuntimeError("Azure Blob Storage is not configured.")

    target_dir.mkdir(parents=True, exist_ok=True)
    service = BlobServiceClient.from_connection_string(settings.azure_blob_connection_string)
    container = service.get_container_client(settings.azure_blob_container)

    blob_map = {
        "households": settings.azure_blob_households_blob,
        "products": settings.azure_blob_products_blob,
        "transactions": settings.azure_blob_transactions_blob,
    }
    local_paths: dict[str, Path] = {}
    for key, blob_name in blob_map.items():
        destination = target_dir / Path(blob_name).name
        with destination.open("wb") as handle:
            downloader = container.download_blob(blob_name)
            handle.write(downloader.readall())
        local_paths[key] = destination

    return LoadPaths(
        households=local_paths["households"],
        products=local_paths["products"],
        transactions=local_paths["transactions"],
    )
