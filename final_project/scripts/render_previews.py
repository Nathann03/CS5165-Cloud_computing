from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".packages"))

import httpx

from app import main as main_module
from app.database import create_db_engine


async def main() -> None:
    preview_dir = BASE_DIR / "artifacts" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    main_module.engine = create_db_engine("sqlite:///data/db/retail_analytics.db")
    transport = httpx.ASGITransport(app=main_module.app)

    pages = {
        "home.html": "/",
        "sample_household.html": "/sample-household",
        "search_household_10.html": "/search?hshd_num=10",
        "dashboard.html": "/dashboard",
        "admin.html": "/admin",
        "ml.html": "/ml",
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for filename, route in pages.items():
            response = await client.get(route)
            response.raise_for_status()
            (preview_dir / filename).write_text(response.text, encoding="utf-8")
            print(f"wrote {preview_dir / filename}")


if __name__ == "__main__":
    asyncio.run(main())
