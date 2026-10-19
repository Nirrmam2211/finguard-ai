import unittest
from unittest.mock import patch
from orchestrator import FinGuardOrchestrator
from agents.critic import CriticAgent
from agents.executor import ExecutorAgent
from agents.planner import PlannerAgent
from agents.research import ResearchAgent
from app import has_current_result_schema
from risk_engine import assess_transaction, demo_transactions

SAMPLE = {
    "transaction_id": "TEST-001", "amount_inr": 75000, "customer_avg_amount_inr": 5000,
    "location": "Pune", "is_new_location": True, "transactions_last_10min": 5,
    "is_new_beneficiary": True, "outside_usual_hours": True,
    "customer_id": "CUST-TEST", "timestamp": "2026-10-10 23:00:00", "merchant_category": "retail"
}

class AgentWorkflowTests(unittest.TestCase):
    def test_result_schema_detects_stale_streamlit_session_data(self):
        legacy_result = {"status": "validated", "assessment": {}, "validation": {}, "trace": []}
        current_result = FinGuardOrchestrator().investigate(SAMPLE)
        self.assertFalse(has_current_result_schema(legacy_result))
        self.assertTrue(has_current_result_schema(current_result))

    def test_workflow_executes_all_four_agents_and_validates(self):
        result = FinGuardOrchestrator().investigate(SAMPLE)
        self.assertEqual(result["status"], "validated")
        self.assertEqual([x["agent"] for x in result["trace"]],
                         ["Planner Agent", "Research Agent", "Executor Agent", "Critic Agent"])
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(result["assessment"]["risk_score"], 100)
        self.assertEqual(result["plan"]["handoff"]["to_agent"], "Research Agent")
        self.assertEqual(result["research"]["handoff"]["to_agent"], "Executor Agent")
        self.assertEqual(result["execution"]["handoff"]["to_agent"], "Critic Agent")
        self.assertEqual(result["validation"]["handoff"]["to_agent"], "Orchestrator")
        self.assertEqual(result["execution"]["handoff"]["research_facts"]["amount_inr"], 75000)
        self.assertTrue(result["execution"]["handoff"]["research_evidence"])
        self.assertEqual(result["decision"]["code"], "priority_analyst_review")
        self.assertEqual(result["validation_status"], "passed")

    def test_missing_field_fails_closed(self):
        tx = dict(SAMPLE); del tx["amount_inr"]
        result = FinGuardOrchestrator().investigate(tx)
        self.assertEqual(result["status"], "manual_review_required")
        self.assertEqual(result["validation_status"], "failed")
        self.assertEqual(result["decision"]["code"], "manual_review_required")
        self.assertIsNone(result["assessment"])

    def test_risk_tiers_map_to_review_actions(self):
        low, medium, high = [
            FinGuardOrchestrator().investigate(transaction)
            for transaction in demo_transactions()
        ]
        self.assertEqual(low["decision"]["code"], "routine_monitoring")
        self.assertEqual(medium["decision"]["code"], "analyst_review")
        self.assertEqual(high["decision"]["code"], "priority_analyst_review")
        self.assertTrue(all(result["validation_status"] == "passed" for result in (low, medium, high)))

    def test_critic_rejects_research_evidence_mismatch(self):
        assessment = assess_transaction(SAMPLE)
        handoff = {
            "research_status": "collected",
            "research_facts": {**SAMPLE, "amount_inr": 1},
        }
        result = CriticAgent().run(SAMPLE, assessment, handoff)
        self.assertFalse(result["valid"])
        self.assertTrue(any("Research evidence does not match" in error for error in result["errors"]))

    def test_critic_rejects_incomplete_research_evidence(self):
        assessment = assess_transaction(SAMPLE)
        handoff = {
            "research_status": "collected",
            "research_facts": {key: value for key, value in SAMPLE.items() if key != "location"},
        }
        result = CriticAgent().run(SAMPLE, assessment, handoff)
        self.assertFalse(result["valid"])
        self.assertTrue(any("missing required field" in error for error in result["errors"]))

    def test_executor_scores_research_handoff(self):
        plan = PlannerAgent().run(SAMPLE)
        research = ResearchAgent().run(SAMPLE, plan)
        changed_input = {**SAMPLE, "amount_inr": 1000}
        result = ExecutorAgent().run(changed_input, research)
        self.assertEqual(result["assessment"]["risk_score"], 100)
        self.assertEqual(result["assessment"]["input_summary"]["amount_inr"], 75000)

    def test_failed_critic_forces_manual_review(self):
        with patch(
            "agents.critic.validate_assessment",
            return_value={"valid": False, "errors": ["Tampered assessment."], "checks_performed": []},
        ):
            result = FinGuardOrchestrator().investigate(SAMPLE)
        self.assertEqual(result["decision"]["code"], "manual_review_required")
        self.assertEqual(result["validation_status"], "failed")
        self.assertIsNone(result["assessment"])

if __name__ == "__main__": unittest.main()
