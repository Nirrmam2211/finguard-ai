# AGENTS.md

This repository is a small educational Python demo for a multi-agent fraud-risk prototype. Keep changes compatible with the existing deterministic workflow and the project’s explicit safety messaging.

## Project purpose

- The core logic lives in [risk_engine.py](risk_engine.py): it validates inputs, applies illustrative scoring rules, and returns explainable indicators.
- The orchestration flow lives in [orchestrator.py](orchestrator.py) and agents under [agents/](agents/): planner, research, executor, and critic.
- The dashboard entry point is [app.py](app.py): a Streamlit UI for CSV ingestion, column mapping, and investigation results.
- Test coverage is in [tests/test_risk_engine.py](tests/test_risk_engine.py) and [tests/test_agents.py](tests/test_agents.py).
- Use the design notes and setup steps in [README.md](README.md) as the default source of truth for run instructions.

## Operational conventions

- Keep the workflow deterministic and explainable. Do not introduce ML, external APIs, or opaque scoring changes without updating tests and documentation.
- Treat the output as a classroom prototype, not an operational fraud decision system. The code warns users that scores are illustrative and must not trigger automatic blocking.
- Fail closed: if validation fails, return to manual review instead of silently producing a confident result.
- Preserve the existing CSV contract and canonical field names used in the risk engine.
- Prefer small, targeted changes that keep the risk rules and Critic consistency checks aligned.

## Commands

- Run the full test suite:
  - `python -m unittest discover -s tests -v`
- Start the UI locally:
  - `streamlit run app.py`

## Architecture guardrails

- Risk evaluation belongs in [risk_engine.py](risk_engine.py). Keep rule weights, score thresholds, and validation logic there.
- Agent behavior belongs in [agents/](agents/). Updates should preserve the pipeline: planner → research → executor → critic.
- The Critic recomputes through the shared risk engine and checks Research evidence against the original input; it is not a separately implemented scorer. If scoring rules change, update the tests and documentation.
- Missing or malformed inputs should raise validation errors or return a manual-review state rather than manufacturing data.

## Editing guidance

- Before changing scoring logic, read [risk_engine.py](risk_engine.py) and the relevant tests in [tests/test_risk_engine.py](tests/test_risk_engine.py).
- Before changing agent flow, read [orchestrator.py](orchestrator.py) and [agents/](agents/).
- Keep field names, evidence strings, and risk classifications consistent with the repo’s existing contract.
- Do not silently override missing evidence with false values just to satisfy a score path.

## Repo-specific notes

- This project uses synthetic transaction data only.
- CSV headers may vary, but the application attempts to map them to the canonical FinGuard fields before processing.
- The tutorial/demo logic should remain explainable to a classroom audience; avoid hidden complexity or hard-to-debug behavior.
