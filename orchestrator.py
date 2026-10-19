"""Sequential orchestration for the FinGuard multi-agent PoC."""
from datetime import datetime, timezone
from typing import Any, Mapping
from agents import PlannerAgent, ResearchAgent, ExecutorAgent, CriticAgent

class FinGuardOrchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.researcher = ResearchAgent()
        self.executor = ExecutorAgent()
        self.critic = CriticAgent()

    def investigate(self, transaction: Mapping[str, Any]) -> dict[str, Any]:
        trace = []
        plan = self.planner.run(transaction)
        trace.append(plan)
        research = self.researcher.run(transaction, plan)
        trace.append(research)
        execution = self.executor.run(transaction, research)
        trace.append(execution)
        assessment = execution.get("assessment") if execution.get("status") == "completed" else None
        critique = self.critic.run(transaction, assessment, execution.get("handoff"))
        trace.append(critique)
        valid = bool(critique.get("valid", False))
        approved_assessment = assessment if valid else None

        if not valid:
            decision = {
                "code": "manual_review_required",
                "label": "Manual review required",
                "recommended_action": "Resolve missing or inconsistent inputs before relying on a risk score.",
            }
        else:
            risk_level = approved_assessment["risk_level"]
            decision = {
                "Low": {
                    "code": "routine_monitoring",
                    "label": "Routine monitoring",
                    "recommended_action": "Continue routine monitoring; do not escalate on this score alone.",
                },
                "Medium": {
                    "code": "analyst_review",
                    "label": "Analyst review",
                    "recommended_action": "Queue for analyst review and verify the supporting evidence.",
                },
                "High": {
                    "code": "priority_analyst_review",
                    "label": "Priority analyst review",
                    "recommended_action": "Prioritize human investigation; do not automatically block the account.",
                },
            }[risk_level]

        return {
            "transaction_id": str(transaction.get("transaction_id", "UNKNOWN")),
            "status": "validated" if valid else "manual_review_required",
            "validation_status": "passed" if valid else "failed",
            "decision": decision,
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "plan": plan, "research": research, "execution": execution,
            "validation": critique, "assessment": approved_assessment,
            "trace": trace,
            "summary": (
                f"Assessment passed validation. Recommended action: {decision['label']}."
                if valid else "Assessment failed validation. Manual review is required before taking action."
            ),
        }
