from copy import deepcopy
from pathlib import Path
import sys
import unittest

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import build_transaction_row, ensure_transaction_ids, suggest_column
from risk_engine import (  # noqa: E402
    TransactionValidationError,
    assess_transaction,
    classify_score,
    demo_transactions,
    validate_assessment,
)


class RiskEngineTests(unittest.TestCase):
    def test_demo_scenarios_have_expected_tiers(self):
        low, medium, high = [assess_transaction(tx) for tx in demo_transactions()]
        self.assertEqual((low["risk_score"], low["risk_level"]), (0, "Low"))
        self.assertEqual((medium["risk_score"], medium["risk_level"]), (45, "Medium"))
        self.assertEqual((high["risk_score"], high["risk_level"]), (100, "High"))

    def test_combined_indicators_make_medium_risk(self):
        tx = {
            "transaction_id": "TEST-MEDIUM",
            "amount_inr": 8000,
            "customer_avg_amount_inr": 5000,
            "location": "Surat",
            "is_new_location": True,
            "transactions_last_10min": 1,
            "is_new_beneficiary": True,
            "outside_usual_hours": False,
        }
        result = assess_transaction(tx)
        self.assertEqual(result["risk_score"], 35)
        self.assertEqual(result["risk_level"], "Medium")

    def test_critic_accepts_correct_assessment(self):
        tx = demo_transactions()[2]
        result = assess_transaction(tx)
        validation = validate_assessment(tx, result)
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["errors"], [])

    def test_critic_rejects_tampered_score(self):
        tx = demo_transactions()[2]
        result = deepcopy(assess_transaction(tx))
        result["risk_score"] = 12
        validation = validate_assessment(tx, result)
        self.assertFalse(validation["valid"])
        self.assertTrue(any("risk_score" in error for error in validation["errors"]))

    def test_auto_mapping_handles_alternative_csv_headers(self):
        columns = [
            "txn_ref",
            "gross_amount",
            "avg_amt",
            "merchant_city",
            "new_geo",
            "count_last_10m",
            "new_payee",
            "after_hours",
        ]
        mapping = {
            field: suggest_column(field, columns)
            for field in (
                "transaction_id",
                "amount_inr",
                "customer_avg_amount_inr",
                "location",
                "is_new_location",
                "transactions_last_10min",
                "is_new_beneficiary",
                "outside_usual_hours",
            )
        }
        self.assertEqual(mapping["transaction_id"], "txn_ref")
        self.assertEqual(mapping["amount_inr"], "gross_amount")
        self.assertEqual(mapping["customer_avg_amount_inr"], "avg_amt")
        self.assertEqual(mapping["location"], "merchant_city")
        self.assertEqual(mapping["is_new_location"], "new_geo")
        self.assertEqual(mapping["transactions_last_10min"], "count_last_10m")
        self.assertEqual(mapping["is_new_beneficiary"], "new_payee")
        self.assertEqual(mapping["outside_usual_hours"], "after_hours")

        row = {
            "txn_ref": "TXN-204",
            "gross_amount": 75000,
            "avg_amt": 30000,
            "merchant_city": "Surat",
            "new_geo": True,
            "count_last_10m": 4,
            "new_payee": True,
            "after_hours": False,
        }
        normalized = build_transaction_row(row, mapping)
        self.assertEqual(normalized["transaction_id"], "TXN-204")
        self.assertEqual(normalized["amount_inr"], 75000)
        self.assertEqual(normalized["is_new_location"], True)
        self.assertEqual(normalized["transactions_last_10min"], 4)

    def test_transaction_ids_are_generated_when_column_is_missing_or_blank(self):
        without_ids = ensure_transaction_ids(pd.DataFrame({"amount": [10, 20]}))
        self.assertEqual(
            without_ids["transaction_id"].tolist(), ["CSV-000001", "CSV-000002"]
        )

        with_blank_ids = ensure_transaction_ids(
            pd.DataFrame({"transaction_id": ["TXN-1", None, "  "]})
        )
        self.assertEqual(
            with_blank_ids["transaction_id"].tolist(),
            ["TXN-1", "CSV-000002", "CSV-000003"],
        )

    def test_missing_required_field_is_rejected(self):
        tx = demo_transactions()[0]
        del tx["is_new_location"]
        with self.assertRaises(TransactionValidationError):
            assess_transaction(tx)

    def test_invalid_transaction_count_is_rejected(self):
        tx = demo_transactions()[0]
        tx["transactions_last_10min"] = 2.5
        with self.assertRaises(TransactionValidationError):
            assess_transaction(tx)

    def test_classification_boundaries(self):
        self.assertEqual(classify_score(0), "Low")
        self.assertEqual(classify_score(29), "Low")
        self.assertEqual(classify_score(30), "Medium")
        self.assertEqual(classify_score(59), "Medium")
        self.assertEqual(classify_score(60), "High")
        self.assertEqual(classify_score(100), "High")


if __name__ == "__main__":
    unittest.main(verbosity=2)
