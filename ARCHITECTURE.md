# FinGuard AI Architecture

## System overview

FinGuard AI is a deterministic, multi-agent transaction review prototype for a banking and finance use case. The system accepts a CSV of synthetic transactions, maps source columns to canonical FinGuard fields, and runs an investigation workflow that assigns a human-review priority. It does not determine whether a transaction is actually real or fraudulent.

## Architecture diagram

```mermaid
flowchart TD
    A[User / Analyst] --> B[Streamlit UI\nCSV upload + column mapping]
    B --> C[Raw transaction data]
    C --> D[Planner Agent]
    D -- Checklist + missing fields --> E[Research Agent]
    E -- Structured facts + evidence --> F[Executor Agent]
    F -- Research facts --> G[Risk Engine\nassess_transaction()]
    G -- Score + tier + rule evidence --> F
    F -- Assessment + facts + evidence --> H[Critic Agent]
    H -- Recompute + required-fact match check --> I{Validation passed?}
    I -- No --> J[Manual review required]
    I -- Yes --> K{Risk tier}
    K -- Low --> L[Routine monitoring]
    K -- Medium --> M[Analyst review]
    K -- High --> N[Priority analyst review]
    J --> O[Final report + agent trace]
    L --> O
    M --> O
    N --> O
    O --> P[JSON report + visible agent trace]

    Q[Synthetic transaction dataset] --> C
    R[Canonical field contract] --> B
```

## Component responsibilities

### Frontend layer
- The Streamlit application handles uploading CSV data, mapping columns, and presenting investigation results.
- It keeps the workflow explainable and transparent, rather than hiding the decision logic inside an opaque black box.

### Agent layer
- Planner Agent: checks required fields and hands Research a structured investigation checklist.
- Research Agent: follows the checklist and hands Executor supplied transaction facts and evidence; missing values are not invented.
- Executor Agent: scores the facts received from Research with the existing Python risk engine and hands the assessment, facts, and evidence to Critic.
- Critic Agent: uses the shared risk-engine scoring function to check the assessment, verifies required facts are present, and compares Research's facts with the original transaction input.
- Orchestrator: passes structured Python dictionaries between agents and converts validated risk tiers into review actions.

### Core logic layer
- `risk_engine.py` holds the rule definitions, validation rules, score thresholds, and recommendations.
- It is the authoritative source for the project’s risk logic and is intentionally deterministic.

### Decision flow
1. User uploads or selects a transaction dataset.
2. UI maps incoming CSV columns to standard FinGuard fields.
3. Planner sends Research a checklist and reports missing required fields.
4. Research sends Executor structured facts copied from supplied fields plus evidence summaries; missing data is not filled with assumed false values.
5. Executor calls the risk engine using the Research handoff; the scoring rules remain solely in `risk_engine.py`.
6. Executor sends Critic the assessment, research facts, and evidence. Critic checks the assessment and confirms required facts match the original transaction.
7. Failed validation routes the case to manual review. A validated Low, Medium, or High tier maps to routine monitoring, analyst review, or priority analyst review.
8. The UI displays each handoff, the final decision, validation status, and report export.

The agents communicate through structured Python dictionaries, not separate LLMs or free-form chat. Critic recomputation uses the same `assess_transaction()` implementation as Executor, so it can detect altered outputs and incomplete or mismatched evidence, but it is not an independently implemented scoring engine.

## Synthetic dataset run

The complete workflow was run on all 500 rows in `data/transactions.csv`. It produced 448 Routine monitoring, 48 Analyst review, and 4 Priority analyst review outcomes; Critic validation passed for all 500. These are illustrative results on synthetic records, not confirmed fraud labels.

## Design intent

The system is intentionally designed for a classroom PoC. It focuses on explainability, deterministic logic, and fail-closed review behavior rather than operational fraud decision-making.
