"""Executor agent: invokes the real Python risk engine."""
from typing import Any, Mapping
from risk_engine import assess_transaction, TransactionValidationError

class ExecutorAgent:
    name = "Executor Agent"

    def run(self, transaction: Mapping[str, Any], research: Mapping[str, Any]) -> dict[str, Any]:
        research_handoff = research.get("handoff", {})
        if research.get("status") != "collected" or not research_handoff.get("facts"):
            return {
                "agent": self.name,
                "status": "failed",
                "error": "Research handoff is incomplete; scoring was not run.",
                "input_summary": {"research_status": research.get("status")},
                "tool": "risk_engine.assess_transaction",
            }

        try:
            result = assess_transaction(research_handoff["facts"])
            return {
                "agent": self.name,
                "status": "completed",
                "assessment": result,
                "input_summary": {
                    "research_status": research.get("status"),
                    "research_fact_fields": list(research_handoff["facts"]),
                },
                "handoff": {
                    "from_agent": self.name,
                    "to_agent": "Critic Agent",
                    "research_status": research.get("status"),
                    "research_facts": research_handoff["facts"],
                    "research_evidence": research_handoff.get("evidence", []),
                },
                "tool": "risk_engine.assess_transaction",
            }
        except (TransactionValidationError, TypeError, ValueError) as exc:
            return {"agent": self.name, "status": "failed", "error": str(exc),
                    "tool": "risk_engine.assess_transaction"}
