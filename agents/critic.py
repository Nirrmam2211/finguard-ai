"""Critic agent: validates executor output and its evidence handoff."""
from typing import Any, Mapping
from risk_engine import REQUIRED_FIELDS, validate_assessment

class CriticAgent:
    name = "Critic Agent"

    def run(
        self,
        transaction: Mapping[str, Any],
        assessment: Mapping[str, Any] | None,
        executor_handoff: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        if assessment is None:
            return {"agent": self.name, "status": "failed", "valid": False,
                    "errors": ["Executor did not provide an assessment."], "action": "manual_review"}

        validation = validate_assessment(transaction, assessment)
        errors = list(validation["errors"])
        research_facts = executor_handoff.get("research_facts", {}) if executor_handoff else {}
        if not executor_handoff or executor_handoff.get("research_status") != "collected":
            errors.append("Executor did not provide a complete Research Agent handoff.")
        else:
            missing_fields = [field for field in REQUIRED_FIELDS if field not in research_facts]
            if missing_fields:
                errors.append("Research evidence is missing required field(s): " + ", ".join(missing_fields))
            mismatched_fields = [
                field for field, value in research_facts.items()
                if field not in transaction or not self._values_match(value, transaction[field])
            ]
            if mismatched_fields:
                errors.append("Research evidence does not match transaction input: " + ", ".join(sorted(set(mismatched_fields))))

        valid = not errors
        return {
            "agent": self.name,
            "status": "passed" if valid else "rejected",
            "valid": valid,
            "errors": errors,
            "checks_performed": validation.get("checks_performed", []) + ["research_evidence_matches_transaction"],
            "action": "generate_report" if valid else "manual_review",
            "input_summary": {
                "assessment_received": assessment is not None,
                "research_handoff_received": executor_handoff is not None,
            },
            "handoff": {
                "from_agent": self.name,
                "to_agent": "Orchestrator",
                "validation_passed": valid,
                "next_action": "generate_report" if valid else "manual_review",
            },
        }

    @staticmethod
    def _values_match(left: Any, right: Any) -> bool:
        try:
            return bool(left == right)
        except (TypeError, ValueError):
            return False
