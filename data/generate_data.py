"""Generate a deterministic synthetic transaction dataset for FinGuard AI.

All records are fictional. The scenario fields are ordinary transaction
attributes; the generated data is not evidence of real fraud or fraud rates.
Run from any working directory with: python data/generate_data.py
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20261010
ROW_COUNT = 500
OUTPUT_PATH = Path(__file__).resolve().parent / "transactions.csv"

CITIES = [
    "Pune", "Mumbai", "Ahmedabad", "Bengaluru", "Hyderabad",
    "Delhi", "Jaipur", "Chennai", "Kolkata", "Surat",
]
CATEGORIES = [
    "groceries", "fuel", "food_delivery", "electronics", "travel",
    "utilities", "healthcare", "online_shopping", "entertainment",
]

FIELDS = [
    "transaction_id",
    "customer_id",
    "timestamp",
    "amount_inr",
    "customer_avg_amount_inr",
    "merchant_category",
    "location",
    "is_new_location",
    "transactions_last_10min",
    "is_new_beneficiary",
    "outside_usual_hours",
]


def _make_timestamp(rng: random.Random, outside_usual_hours: bool) -> str:
    base = datetime(2026, 10, 1, 0, 0, 0)
    offset_minutes = rng.randint(0, 9 * 24 * 60 + 23 * 60)
    value = base + timedelta(minutes=offset_minutes)
    if outside_usual_hours:
        value = value.replace(hour=rng.choice([0, 1, 2, 3, 4, 22, 23]))
    else:
        value = value.replace(hour=rng.randint(7, 21))
    return value.strftime("%Y-%m-%d %H:%M:%S")


def generate_transactions(row_count: int = ROW_COUNT, seed: int = SEED) -> list[dict[str, object]]:
    """Return fictional transaction records using a fixed random seed."""
    if row_count < 1:
        raise ValueError("row_count must be at least 1")

    rng = random.Random(seed)
    rows: list[dict[str, object]] = []

    for i in range(1, row_count + 1):
        avg_amount = rng.randint(500, 15_000)
        amount = round(min(rng.lognormvariate(7.4, 0.9), 120_000), 2)
        outside_hours = rng.random() < 0.12
        row: dict[str, object] = {
            "transaction_id": f"TXN{i:05d}",
            "customer_id": f"CUST{rng.randint(1, 125):04d}",
            "timestamp": _make_timestamp(rng, outside_hours),
            "amount_inr": amount,
            "customer_avg_amount_inr": avg_amount,
            "merchant_category": rng.choice(CATEGORIES),
            "location": rng.choice(CITIES),
            "is_new_location": rng.random() < 0.08,
            "transactions_last_10min": rng.choices(
                [1, 2, 3, 4, 5, 6], weights=[35, 27, 18, 10, 6, 4], k=1
            )[0],
            "is_new_beneficiary": rng.random() < 0.16,
            "outside_usual_hours": outside_hours,
        }
        rows.append(row)

    # Add several intentionally constructed scenarios for predictable demos.
    # These are suspicious-pattern examples, not labelled real-world fraud.
    if row_count >= 6:
        rows[0].update({
            "amount_inr": 1_250.00,
            "customer_avg_amount_inr": 3_000,
            "is_new_location": False,
            "transactions_last_10min": 1,
            "is_new_beneficiary": False,
            "outside_usual_hours": False,
            "timestamp": "2026-10-10 14:25:00",
        })
        rows[1].update({
            "amount_inr": 75_000.00,
            "customer_avg_amount_inr": 5_000,
            "is_new_location": False,
            "transactions_last_10min": 1,
            "is_new_beneficiary": False,
            "outside_usual_hours": False,
            "timestamp": "2026-10-10 15:10:00",
        })
        rows[2].update({
            "amount_inr": 96_500.00,
            "customer_avg_amount_inr": 4_000,
            "is_new_location": True,
            "transactions_last_10min": 5,
            "is_new_beneficiary": True,
            "outside_usual_hours": True,
            "timestamp": "2026-10-10 02:14:00",
        })
        rows[3].update({
            "amount_inr": 8_750.00,
            "customer_avg_amount_inr": 3_000,
            "is_new_location": True,
            "transactions_last_10min": 1,
            "is_new_beneficiary": True,
            "outside_usual_hours": False,
            "timestamp": "2026-10-09 16:05:00",
        })
        rows[4].update({
            "amount_inr": 6_200.00,
            "customer_avg_amount_inr": 4_500,
            "is_new_location": False,
            "transactions_last_10min": 4,
            "is_new_beneficiary": False,
            "outside_usual_hours": True,
            "timestamp": "2026-10-09 23:40:00",
        })
        rows[5].update({
            "amount_inr": 2_200.00,
            "customer_avg_amount_inr": 2_800,
            "is_new_location": False,
            "transactions_last_10min": 2,
            "is_new_beneficiary": False,
            "outside_usual_hours": False,
            "timestamp": "2026-10-09 11:20:00",
        })

    return rows


def write_csv(output_path: Path = OUTPUT_PATH, row_count: int = ROW_COUNT, seed: int = SEED) -> Path:
    rows = generate_transactions(row_count=row_count, seed=seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


if __name__ == "__main__":
    output = write_csv()
    print(f"Created {ROW_COUNT} synthetic transactions: {output}")
