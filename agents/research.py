"""Research agent: summarizes data-backed evidence without deciding fraud."""
from typing import Any, Mapping
from risk_engine import REQUIRED_FIELDS

class ResearchAgent:
    name = "Research Agent"
    FACT_FIELDS = (*REQUIRED_FIELDS, "customer_id", "timestamp", "merchant_category")

    def run(self, transaction: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
        plan_handoff = plan.get("handoff", {})
        checklist = plan_handoff.get("checklist", [])
        facts = {field: transaction[field] for field in self.FACT_FIELDS if field in transaction}
        missing_fields = [field for field in REQUIRED_FIELDS if field not in facts]
        missing_fields.extend(field for field in plan_handoff.get("missing_fields", []) if field not in missing_fields)
        evidence = []

        try:
            amount = float(facts.get("amount_inr"))
            average = float(facts.get("customer_avg_amount_inr"))
            if average > 0:
                ratio = round(amount / average, 2)
                evidence.append({"finding": "amount_vs_customer_average", "value": ratio,
                                 "detail": f"Transaction is {ratio}x the supplied customer average."})
            else:
                evidence.append({"finding": "customer_average_unavailable", "value": None,
                                 "detail": "Customer average is missing or invalid."})
        except (TypeError, ValueError):
            evidence.append({"finding": "amount_comparison_unavailable", "value": None,
                             "detail": "Amount or customer average is not numeric."})

        findings = (
            ("location", "location", "Location supplied in the transaction record."),
            ("new_location", "is_new_location", "Supplied new-location indicator; missing values are not treated as false."),
            ("transaction_frequency", "transactions_last_10min", "Supplied transaction count for the recent 10-minute window."),
            ("new_beneficiary", "is_new_beneficiary", "Supplied new-beneficiary indicator; missing values are not treated as false."),
            ("outside_usual_hours", "outside_usual_hours", "Supplied unusual-time indicator; missing values are not treated as false."),
        )
        for finding, field, detail in findings:
            evidence.append({
                "finding": finding,
                "value": facts.get(field),
                "available": field in facts,
                "detail": detail if field in facts else f"{field} was not supplied; no value was assumed.",
            })

        status = "collected" if not missing_fields and plan.get("status") == "planned" else "incomplete"
        handoff = {
            "from_agent": self.name,
            "to_agent": "Executor Agent",
            "facts": facts,
            "evidence": evidence,
            "missing_fields": missing_fields,
            "checklist_received": checklist,
        }
        return {
            "agent": self.name,
            "transaction_id": str(transaction.get("transaction_id", "UNKNOWN")),
            "input_summary": {"checklist_received": checklist, "fields_received": list(facts)},
            "evidence": evidence,
            "status": status,
            "handoff": handoff,
            "note": "Evidence describes supplied fields; it does not establish fraud.",
        }
