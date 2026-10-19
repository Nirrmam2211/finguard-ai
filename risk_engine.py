"""Transparent, deterministic risk scoring engine for FinGuard AI.

The points are illustrative classroom rules, not a calibrated fraud model.
No network calls or paid APIs are used.
"""
from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Any, Mapping

RULES = (
    {
        "rule_id": "HIGH_AMOUNT",
        "label": "High transaction amount",
        "points": 25,
        "description": "Transaction amount exceeds the illustrative threshold of INR 50,000.",
    },
    {
        "rule_id": "NEW_LOCATION",
        "label": "Unusual location",
        "points": 20,
        "description": "Transaction is marked as originating from a new location for this customer.",
    },
    {
        "rule_id": "HIGH_FREQUENCY",
        "label": "High transaction frequency",
        "points": 25,
        "description": "At least four transactions occurred within the recent 10-minute window.",
    },
    {
        "rule_id": "NEW_BENEFICIARY",
        "label": "New beneficiary",
        "points": 15,
        "description": "The beneficiary is marked as new for this customer.",
    },
    {
        "rule_id": "UNUSUAL_TIME",
        "label": "Unusual transaction time",
        "points": 15,
        "description": "The transaction is marked as outside the customer's usual activity hours.",
    },
)

REQUIRED_FIELDS = (
    "transaction_id",
    "amount_inr",
    "customer_avg_amount_inr",
    "location",
    "is_new_location",
    "transactions_last_10min",
    "is_new_beneficiary",
    "outside_usual_hours",
)

RECOMMENDATIONS = {
    "Low": "Continue routine monitoring; do not escalate on this score alone.",
    "Medium": "Queue for analyst review and verify the supporting evidence.",
    "High": "Prioritize human investigation. Do not automatically block the account based on this score.",
}


class TransactionValidationError(ValueError):
    """Raised when a transaction does not meet the engine input contract."""


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    # Avoid importing pandas as a required runtime dependency.
    try:
        return bool(value != value)  # NaN compares unequal to itself
    except (TypeError, ValueError):
        return False


def _as_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    raise TransactionValidationError(
        f"Field '{field_name}' must be a boolean (true/false); got {value!r}."
    )


def _as_number(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TransactionValidationError(
            f"Field '{field_name}' must be numeric; got {value!r}."
        ) from exc
    if not isfinite(number):
        raise TransactionValidationError(f"Field '{field_name}' must be a finite number.")
    return number


def normalize_transaction(transaction: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize the fields needed by the risk rules."""
    if not isinstance(transaction, Mapping):
        raise TransactionValidationError("Transaction must be a mapping of field names to values.")

    missing = [field for field in REQUIRED_FIELDS if field not in transaction or _is_missing(transaction[field])]
    if missing:
        raise TransactionValidationError("Missing required field(s): " + ", ".join(missing))

    transaction_id = str(transaction["transaction_id"]).strip()
    location = str(transaction["location"]).strip()
    if not transaction_id:
        raise TransactionValidationError("Field 'transaction_id' cannot be blank.")
    if not location:
        raise TransactionValidationError("Field 'location' cannot be blank.")

    amount = _as_number(transaction["amount_inr"], "amount_inr")
    average = _as_number(transaction["customer_avg_amount_inr"], "customer_avg_amount_inr")
    count_float = _as_number(transaction["transactions_last_10min"], "transactions_last_10min")

    if amount <= 0:
        raise TransactionValidationError("Field 'amount_inr' must be greater than zero.")
    if average <= 0:
        raise TransactionValidationError("Field 'customer_avg_amount_inr' must be greater than zero.")
    if count_float < 1 or not count_float.is_integer():
        raise TransactionValidationError("Field 'transactions_last_10min' must be a positive whole number.")

    return {
        "transaction_id": transaction_id,
        "amount_inr": round(amount, 2),
        "customer_avg_amount_inr": round(average, 2),
        "location": location,
        "is_new_location": _as_bool(transaction["is_new_location"], "is_new_location"),
        "transactions_last_10min": int(count_float),
        "is_new_beneficiary": _as_bool(transaction["is_new_beneficiary"], "is_new_beneficiary"),
        "outside_usual_hours": _as_bool(transaction["outside_usual_hours"], "outside_usual_hours"),
        # Optional context is retained if supplied, but isn't used to add risk points.
        "customer_id": str(transaction.get("customer_id", "")).strip(),
        "timestamp": str(transaction.get("timestamp", "")).strip(),
        "merchant_category": str(transaction.get("merchant_category", "")).strip(),
    }


def classify_score(score: int) -> str:
    """Map a score in [0, 100] to the project's illustrative risk tier."""
    if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
        raise ValueError("score must be an integer between 0 and 100")
    if score < 30:
        return "Low"
    if score < 60:
        return "Medium"
    return "High"


def assess_transaction(transaction: Mapping[str, Any]) -> dict[str, Any]:
    """Score a transaction and return an explainable, structured assessment."""
    tx = normalize_transaction(transaction)

    triggered = {
        "HIGH_AMOUNT": tx["amount_inr"] > 50_000,
        "NEW_LOCATION": tx["is_new_location"],
        "HIGH_FREQUENCY": tx["transactions_last_10min"] >= 4,
        "NEW_BENEFICIARY": tx["is_new_beneficiary"],
        "UNUSUAL_TIME": tx["outside_usual_hours"],
    }

    indicators: list[dict[str, Any]] = []
    score = 0
    for rule in RULES:
        hit = triggered[rule["rule_id"]]
        points_awarded = rule["points"] if hit else 0
        score += points_awarded
        evidence = {
            "HIGH_AMOUNT": f"Amount INR {tx['amount_inr']:,.2f} {'exceeds' if hit else 'does not exceed'} INR 50,000.",
            "NEW_LOCATION": f"Location '{tx['location']}' is {'marked as new' if hit else 'not marked as new'}.",
            "HIGH_FREQUENCY": f"{tx['transactions_last_10min']} transactions in 10 minutes; threshold is 4.",
            "NEW_BENEFICIARY": f"Beneficiary is {'marked as new' if hit else 'not marked as new'}.",
            "UNUSUAL_TIME": f"Transaction time is {'marked outside' if hit else 'not marked outside'} usual activity hours.",
        }[rule["rule_id"]]
        indicators.append({
            "rule_id": rule["rule_id"],
            "label": rule["label"],
            "triggered": hit,
            "points_possible": rule["points"],
            "points_awarded": points_awarded,
            "evidence": evidence,
            "rule_description": rule["description"],
        })

    # Current rule weights total exactly 100, but cap defensively in case rules change.
    score = min(score, 100)
    risk_level = classify_score(score)
    risk_factors = [item["rule_id"] for item in indicators if item["triggered"]]

    return {
        "transaction_id": tx["transaction_id"],
        "risk_score": score,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "indicators": indicators,
        "recommendation": RECOMMENDATIONS[risk_level],
        "input_summary": {
            "amount_inr": tx["amount_inr"],
            "customer_avg_amount_inr": tx["customer_avg_amount_inr"],
            "location": tx["location"],
            "transactions_last_10min": tx["transactions_last_10min"],
            "is_new_location": tx["is_new_location"],
            "is_new_beneficiary": tx["is_new_beneficiary"],
            "outside_usual_hours": tx["outside_usual_hours"],
            "timestamp": tx["timestamp"],
            "customer_id": tx["customer_id"],
            "merchant_category": tx["merchant_category"],
        },
        "method": "Deterministic illustrative rules; not a machine-learned fraud probability.",
    }


def validate_assessment(transaction: Mapping[str, Any], assessment: Mapping[str, Any]) -> dict[str, Any]:
    """Independently recompute the expected assessment and report mismatches.

    This is the core of the Critic Agent's first validation pass. It fails closed:
    if the input or supplied assessment is malformed, validation is unsuccessful.
    """
    errors: list[str] = []
    try:
        expected = assess_transaction(transaction)
    except (TransactionValidationError, TypeError, ValueError) as exc:
        return {"valid": False, "errors": [f"Input validation failed: {exc}"]}

    if not isinstance(assessment, Mapping):
        return {"valid": False, "errors": ["Assessment must be a mapping."]}

    fields_to_check = ("transaction_id", "risk_score", "risk_level", "risk_factors", "recommendation", "indicators")
    for field in fields_to_check:
        if field not in assessment:
            errors.append(f"Assessment is missing '{field}'.")
        elif assessment[field] != expected[field]:
            errors.append(f"'{field}' does not match the independently recomputed result.")

    if "risk_score" in assessment:
        score = assessment["risk_score"]
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
            if "'risk_score' does not match the independently recomputed result." not in errors:
                errors.append("'risk_score' must be an integer between 0 and 100.")

    return {"valid": not errors, "errors": errors, "checks_performed": list(fields_to_check)}


def demo_transactions() -> list[dict[str, Any]]:
    """Return three easy-to-explain example cases for a command-line demo."""
    return [
        {
            "transaction_id": "DEMO-LOW",
            "amount_inr": 1250,
            "customer_avg_amount_inr": 3000,
            "location": "Pune",
            "is_new_location": False,
            "transactions_last_10min": 1,
            "is_new_beneficiary": False,
            "outside_usual_hours": False,
        },
        {
            "transaction_id": "DEMO-MEDIUM",
            "amount_inr": 75000,
            "customer_avg_amount_inr": 5000,
            "location": "Mumbai",
            "is_new_location": True,
            "transactions_last_10min": 1,
            "is_new_beneficiary": False,
            "outside_usual_hours": False,
        },
        {
            "transaction_id": "DEMO-HIGH",
            "amount_inr": 96500,
            "customer_avg_amount_inr": 4000,
            "location": "Delhi",
            "is_new_location": True,
            "transactions_last_10min": 5,
            "is_new_beneficiary": True,
            "outside_usual_hours": True,
        },
    ]


if __name__ == "__main__":
    for tx in demo_transactions():
        result = assess_transaction(tx)
        validation = validate_assessment(tx, result)
        print(
            f"{result['transaction_id']}: score={result['risk_score']}, "
            f"risk={result['risk_level']}, factors={len(result['risk_factors'])}, "
            f"validated={validation['valid']}"
        )
