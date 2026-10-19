# FinGuard AI — Results and Evaluation

## Evaluation data and method

- **Dataset:** `data/transactions.csv`
- **Records:** 500 synthetic transactions
- **Workflow:** each row passed through Planner → Research → Executor → Critic using the current deterministic rules.
- **Decision basis:** the risk tier maps to a review action; it is not a verified fraud/legitimate prediction.

## Risk score and review-action distribution

| Review action | Risk tier | Transactions | Share |
|---|---|---:|---:|
| Routine monitoring | Low (0–29) | 448 | 89.6% |
| Analyst review | Medium (30–59) | 48 | 9.6% |
| Priority analyst review | High (60–100) | 4 | 0.8% |
| **Total** | — | **500** | **100%** |

- **Mean score:** 11.15/100
- **Critic validation:** 500/500 passed (100% consistency checks on these records)
- **Unit tests:** 17 passed

The validation rate means that each assessment matched a recomputation by the implemented risk engine and the supplied Research facts matched the input. It does **not** mean that the system classified real fraud correctly.

## Example records

| Transaction | Score | Tier/action | Triggered rules |
|---|---:|---|---|
| `TXN00001` | 0 | Low / Routine monitoring | None |
| `TXN00003` | 100 | High / Priority analyst review | High amount, new location, high frequency, new beneficiary, unusual time |
| `TXN00004` | 35 | Medium / Analyst review | New location, new beneficiary |

## Accuracy and benchmark status

### Classification accuracy: not available

The synthetic CSV does not contain verified ground-truth labels for legitimate versus fraudulent transactions. Therefore accuracy, precision, recall, F1 score, ROC-AUC, false-positive rate, and false-negative rate cannot be calculated honestly from this dataset. The risk score is an illustrative rule score, not a probability of fraud.

To measure predictive accuracy in future work, evaluate against an appropriately governed, representative dataset with independently verified labels, using a held-out test set and suitable class-imbalance metrics.

### Performance benchmark: not measured

No controlled latency, throughput, memory, or competing-system benchmark was run. The successful 500-row workflow run confirms functional processing for the provided dataset only; it is not a performance benchmark.

## Reproduce

From the project root, run the dashboard and investigate rows from the default CSV:

```powershell
streamlit run app.py
```

Run the unit tests:

```powershell
python -m unittest discover -s tests -v
```

The dashboard shows per-record scores, triggered rule evidence, the review action, and Critic validation. The reported aggregate figures above were calculated by running the orchestrator on every row in `data/transactions.csv`.

## Limitations

- All records are synthetic; no conclusions about real customers or fraud can be drawn.
- Rule weights and thresholds are illustrative and were not calibrated against verified fraud outcomes.
- Research evidence is supplied by the CSV and is not a substitute for production customer-history sources.
- Critic recomputation uses the same scoring function as Executor, so shared scoring defects would not be caught by that recomputation.
- The system recommends human review and must not automatically block transactions or accounts.
