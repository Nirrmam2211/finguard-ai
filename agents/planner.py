"""Planner agent: creates a deterministic investigation plan."""
from typing import Any, Mapping
from risk_engine import REQUIRED_FIELDS

class PlannerAgent:
    name = "Planner Agent"

    def run(self, transaction: Mapping[str, Any]) -> dict[str, Any]:
        missing = []
        for field in REQUIRED_FIELDS:
            value = transaction.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
            else:
                try:
                    if bool(value != value):
                        missing.append(field)
                except (TypeError, ValueError):
                    pass

        checklist = [
            {"field": field, "purpose": purpose}
            for field, purpose in (
                ("amount_inr", "Check the transaction amount against the illustrative threshold."),
                ("customer_avg_amount_inr", "Summarize the supplied customer average for context."),
                ("location", "Record the supplied transaction location."),
                ("is_new_location", "Check the supplied new-location indicator."),
                ("transactions_last_10min", "Check recent transaction frequency."),
                ("is_new_beneficiary", "Check the supplied new-beneficiary indicator."),
                ("outside_usual_hours", "Check the supplied unusual-time indicator."),
            )
        ]
        steps = [
            "Validate required transaction fields",
            "Collect transaction and customer-context evidence",
            "Calculate the illustrative risk score using Python rules",
            "Validate the assessment and evidence handoff",
            "Generate a report for analyst review",
        ]
        return {
            "agent": self.name,
            "transaction_id": str(transaction.get("transaction_id", "UNKNOWN")),
            "status": "needs_review" if missing else "planned",
            "missing_fields": missing,
            "input_summary": {
                "available_fields": [field for field in REQUIRED_FIELDS if field in transaction],
                "required_fields": list(REQUIRED_FIELDS),
            },
            "checklist": checklist,
            "steps": steps,
            "handoff": {
                "from_agent": self.name,
                "to_agent": "Research Agent",
                "checklist": checklist,
                "missing_fields": missing,
            },
            "note": "Mock-model planning: a deterministic workflow, not an LLM-generated plan.",
        }
