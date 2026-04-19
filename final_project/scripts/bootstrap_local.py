from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".packages"))

from app.database import engine
from app.ingestion import run_full_load


if __name__ == "__main__":
    report = run_full_load(engine)
    print(report)
