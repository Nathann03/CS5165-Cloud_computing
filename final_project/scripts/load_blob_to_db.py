from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".packages"))

from app.blob_storage import download_blob_datasets
from app.database import engine
from app.ingestion import run_full_load


def main() -> None:
    temp_dir = BASE_DIR / "data" / "uploads" / "blob_sync"
    paths = download_blob_datasets(temp_dir)
    print(run_full_load(engine, paths=paths))


if __name__ == "__main__":
    main()
