from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".packages"))

from app.database import engine
from app.ml import train_basket_model, train_churn_model, train_clv_model


if __name__ == "__main__":
    print({"clv": train_clv_model(engine)})
    print({"basket": train_basket_model(engine)})
    print({"churn": train_churn_model(engine)})
