from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = BASE_DIR / "8451_The_Complete_Journey_2_Sample-2"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "azure_demo"


def _read_transactions(path: Path) -> pd.DataFrame:
    columns = {"BASKET_NUM", "HSHD_NUM", "PURCHASE_", "PRODUCT_NUM", "SPEND", "UNITS", "STORE_R", "WEEK_NUM", "YEAR"}
    frame = pd.read_csv(path, dtype=str, skipinitialspace=True, usecols=lambda name: name.strip() in columns)
    frame.columns = [column.strip().lower() for column in frame.columns]
    frame["hshd_num"] = frame["hshd_num"].astype(int)
    frame["purchase_date"] = pd.to_datetime(frame["purchase_"], format="%d-%b-%y")
    return frame


def _read_households(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, skipinitialspace=True)
    frame.columns = [column.strip().lower() for column in frame.columns]
    frame["hshd_num"] = frame["hshd_num"].astype(int)
    return frame


def _read_products(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, skipinitialspace=True)
    frame.columns = [column.strip().lower() for column in frame.columns]
    return frame


def _classify_households(transactions: pd.DataFrame) -> pd.DataFrame:
    final_date = transactions["purchase_date"].max()
    label_cutoff = final_date - pd.Timedelta(days=60)
    history_cutoff = label_cutoff - pd.Timedelta(days=90)

    history = transactions[transactions["purchase_date"] <= history_cutoff]
    future = transactions[transactions["purchase_date"] > label_cutoff]

    features = history.groupby("hshd_num", as_index=False).agg(
        tx_rows=("basket_num", "size"),
        baskets=("basket_num", "nunique"),
        last_purchase=("purchase_date", "max"),
    )
    future_counts = future.groupby("hshd_num", as_index=False).agg(future_baskets=("basket_num", "nunique"))
    dataset = features.merge(future_counts, on="hshd_num", how="left").fillna(0)
    dataset["churned"] = (dataset["future_baskets"] == 0).astype(int)
    return dataset.sort_values(["churned", "tx_rows", "hshd_num"], ascending=[False, True, True]).reset_index(drop=True)


def build_sample(
    households_path: Path,
    products_path: Path,
    transactions_path: Path,
    output_dir: Path,
    target_transactions: int,
    required_household: int,
) -> dict:
    households = _read_households(households_path)
    products = _read_products(products_path)
    transactions = _read_transactions(transactions_path)
    labeled = _classify_households(transactions)

    churned_households = labeled[labeled["churned"] == 1].copy()
    retained_households = labeled[labeled["churned"] == 0].copy()

    selected_households: list[int] = churned_households["hshd_num"].astype(int).tolist()
    selected_set = set(selected_households)
    if required_household not in selected_set:
        selected_households.append(required_household)
        selected_set.add(required_household)

    current_transactions = int(transactions[transactions["hshd_num"].isin(selected_set)].shape[0])
    retained_candidates = retained_households.sort_values(["tx_rows", "hshd_num"], ascending=[True, True])
    for household in retained_candidates["hshd_num"].astype(int).tolist():
        if current_transactions >= target_transactions:
            break
        if household in selected_set:
            continue
        household_rows = int(retained_candidates.loc[retained_candidates["hshd_num"] == household, "tx_rows"].iloc[0])
        selected_households.append(household)
        selected_set.add(household)
        current_transactions += household_rows

    sample_transactions = transactions[transactions["hshd_num"].isin(selected_set)].copy()
    sample_households = households[households["hshd_num"].isin(selected_set)].copy()
    product_ids = sample_transactions["product_num"].astype(str).unique().tolist()
    sample_products = products[products["product_num"].astype(str).isin(product_ids)].copy()

    output_dir.mkdir(parents=True, exist_ok=True)
    households_out = output_dir / "balanced_households.csv"
    products_out = output_dir / "balanced_products.csv"
    transactions_out = output_dir / "balanced_transactions.csv"

    sample_households.to_csv(households_out, index=False)
    sample_products.to_csv(products_out, index=False)
    sample_transactions.drop(columns=["purchase_date"]).to_csv(transactions_out, index=False)

    sample_labels = labeled[labeled["hshd_num"].isin(selected_set)].copy()
    report = {
        "households_rows": int(len(sample_households)),
        "products_rows": int(len(sample_products)),
        "transactions_rows": int(len(sample_transactions)),
        "required_household_present": bool(required_household in selected_set),
        "selected_households": int(len(selected_set)),
        "class_counts": {str(key): int(value) for key, value in sample_labels["churned"].value_counts().to_dict().items()},
        "transactions_by_class": {
            str(key): int(value)
            for key, value in sample_transactions.merge(
                sample_labels[["hshd_num", "churned"]], on="hshd_num", how="left"
            )["churned"].value_counts().to_dict().items()
        },
        "date_min": sample_transactions["purchase_date"].min().strftime("%Y-%m-%d"),
        "date_max": sample_transactions["purchase_date"].max().strftime("%Y-%m-%d"),
        "output_files": {
            "households": str(households_out),
            "products": str(products_out),
            "transactions": str(transactions_out),
        },
    }
    (output_dir / "balanced_sample_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a balanced Azure demo sample from the 84.51 source files.")
    parser.add_argument("--households", type=Path, default=SOURCE_DIR / "400_households.csv")
    parser.add_argument("--products", type=Path, default=SOURCE_DIR / "400_products.csv")
    parser.add_argument("--transactions", type=Path, default=SOURCE_DIR / "400_transactions.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-transactions", type=int, default=12000)
    parser.add_argument("--required-household", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_sample(
        households_path=args.households,
        products_path=args.products,
        transactions_path=args.transactions,
        output_dir=args.output_dir,
        target_transactions=args.target_transactions,
        required_household=args.required_household,
    )


if __name__ == "__main__":
    main()
