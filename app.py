"""Streamlit UI for FinGuard AI with flexible CSV column mapping."""
from pathlib import Path
import json
import re
import pandas as pd
import streamlit as st
import plotly.express as px
from orchestrator import FinGuardOrchestrator

BASE = Path(__file__).resolve().parent
DEFAULT_DATA = BASE / "data" / "transactions.csv"
INVESTIGATION_RESULT_KEYS = {"validation_status", "decision", "assessment", "validation", "trace"}


def has_current_result_schema(result):
    """Return whether a saved Streamlit result has the fields used by this UI version."""
    return isinstance(result, dict) and INVESTIGATION_RESULT_KEYS.issubset(result)

CANONICAL_FIELDS = {
    "transaction_id": {"label": "Transaction ID", "aliases": ["transaction_id", "transaction id", "txn_id", "txn id", "txn ref", "txn_ref", "transaction ref", "transaction reference", "reference", "reference number", "reference id", "payment id", "id"]},
    "amount_inr": {"label": "Transaction amount", "aliases": ["amount_inr", "amount", "amount inr", "amount (inr)", "transaction amount", "txn amount", "transaction value", "value", "gross amount", "gross_amt", "total amount", "payment amount", "debit amount", "credit amount", "amt"]},
    "customer_avg_amount_inr": {"label": "Customer's average transaction amount", "aliases": ["customer_avg_amount_inr", "customer average amount", "customer avg amount", "customer_avg_amt", "customer avg amt", "average transaction amount", "avg amount", "avg_amt", "average amount", "average_amt", "mean transaction amount", "customer average", "avg_transaction_amount"]},
    "location": {"label": "Transaction location", "aliases": ["location", "city", "transaction city", "merchant city", "country", "country name", "transaction location", "geo location", "merchant location", "city name"]},
    "is_new_location": {"label": "New/unusual location flag", "aliases": ["is_new_location", "new location", "new geo", "new region", "unusual location", "location is new", "new location flag", "new city", "is unusual location", "location_flag", "new_geo"]},
    "transactions_last_10min": {"label": "Transaction count in last 10 minutes", "aliases": ["transactions_last_10min", "transactions last 10 min", "transactions last 10m", "count last 10 min", "count last 10m", "transaction count", "txn count", "transactions in 10 minutes", "frequency", "txn_frequency", "transaction frequency", "velocity count", "count_last_10m", "txns_last_10m", "transactions_last_10m"]},
    "is_new_beneficiary": {"label": "New beneficiary flag", "aliases": ["is_new_beneficiary", "new beneficiary", "beneficiary is new", "new payee", "new recipient", "first time beneficiary", "new beneficiary flag", "new_payee", "new_payee_flag", "is_new_payee", "payee is new", "recipient is new"]},
    "outside_usual_hours": {"label": "Outside usual hours flag", "aliases": ["outside_usual_hours", "outside usual hours", "unusual time", "after hours", "after_hours", "outside business hours", "odd hour transaction", "is_night_transaction", "outside normal hours", "out of hours", "night transaction"]},
}

st.set_page_config(page_title="FinGuard AI", page_icon="🛡️", layout="wide")
st.title("FinGuard AI")
st.caption("Multi-Agent Financial Transaction Investigation · Educational PoC using synthetic and user-supplied CSV data")

@st.cache_data
def load_default():
    return pd.read_csv(DEFAULT_DATA)

def normalize_header(value):
    """Normalize headers for robust alias matching."""
    value = str(value).strip().lower()
    value = re.sub(r"[\(\)\[\]{}]", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def suggest_column(field, columns):
    aliases = {normalize_header(a) for a in CANONICAL_FIELDS[field]["aliases"]}
    aliases.add(normalize_header(field))
    normalized = {c: normalize_header(c) for c in columns}
    for col, name in normalized.items():
        if name in aliases:
            return col
    # Conservative partial matching for common header variants.
    for col, name in normalized.items():
        if any(alias and (alias in name or name in alias) for alias in aliases if len(alias) >= 8):
            return col
    return None


def auto_map_columns(columns):
    """Return a best-effort canonical mapping for a CSV with arbitrary field names."""
    return {field: suggest_column(field, columns) for field in CANONICAL_FIELDS}


def build_transaction_row(source_row, mapping):
    """Build a canonical transaction record from a raw CSV row using the active mapping."""
    transaction = {}
    for field, source in mapping.items():
        if source is None or source == "— Not available / choose manually —":
            continue
        if source in source_row:
            value = source_row[source]
            if pd.notna(value):
                transaction[field] = value
    if "transaction_id" not in transaction or str(transaction["transaction_id"]).strip() == "":
        transaction["transaction_id"] = "AUTO-ROW"
    return transaction


def ensure_transaction_ids(dataframe):
    """Return a copy with a nonblank transaction ID for every row."""
    working_df = dataframe.copy()
    if "transaction_id" not in working_df.columns:
        working_df["transaction_id"] = ""

    transaction_ids = working_df["transaction_id"].fillna("").astype(str)
    blank = transaction_ids.str.strip().eq("")
    working_df["transaction_id"] = transaction_ids
    if blank.any():
        generated_ids = [
            f"CSV-{position + 1:06d}"
            for position, is_blank in enumerate(blank)
            if is_blank
        ]
        working_df.loc[blank, "transaction_id"] = generated_ids
    return working_df


with st.sidebar:
    st.header("Transaction data")
    uploaded = st.file_uploader("Upload a transaction CSV", type=["csv"])
    st.caption("Column names can differ. FinGuard will suggest matches and let you correct them.")

try:
    raw_df = pd.read_csv(uploaded) if uploaded is not None else load_default()
except Exception as exc:
    st.error(f"Could not read CSV: {exc}")
    st.stop()

if raw_df.empty:
    st.error("The uploaded CSV has no transaction rows.")
    st.stop()
if len(raw_df.columns) == 0:
    st.error("No columns were detected. Check the CSV delimiter and file contents.")
    st.stop()

st.subheader("1. Review detected columns")
st.write(f"Loaded **{len(raw_df):,} rows** and **{len(raw_df.columns)} columns**.")
st.dataframe(raw_df.head(8), use_container_width=True, hide_index=True)

# Automatically suggest mappings, but keep the mapping explicit and user-editable.
source_columns = list(raw_df.columns)
NO_COLUMN = "— Not available / choose manually —"
initial_mapping = auto_map_columns(source_columns)

st.subheader("2. Auto-detected CSV mapping")
st.caption("FinGuard matches common schema aliases automatically from your upload. Review or adjust the mapping before running the investigation.")
if any(value is not None for value in initial_mapping.values()):
    detected_matches = [field for field, source in initial_mapping.items() if source is not None]
    st.success(f"Detected {len(detected_matches)} likely field matches automatically from the uploaded CSV.")

with st.form("column_mapping_form"):
    selected_mapping = {}
    grid = st.columns(2)
    for index, (field, spec) in enumerate(CANONICAL_FIELDS.items()):
        with grid[index % 2]:
            options = [NO_COLUMN] + source_columns
            suggestion = initial_mapping[field]
            default_index = options.index(suggestion) if suggestion in options else 0
            selected_mapping[field] = st.selectbox(
                spec["label"], options, index=default_index, key=f"map_{field}"
            )
    mapping_submitted = st.form_submit_button("Apply column mapping", type="primary", use_container_width=True)

# Use the uploaded CSV's detected aliases by default and reset the state whenever a new file arrives.
upload_signature = uploaded.getvalue() if uploaded is not None else None
if "finguard_upload_signature" not in st.session_state:
    st.session_state["finguard_upload_signature"] = None
if st.session_state.get("finguard_upload_signature") != upload_signature:
    st.session_state["finguard_upload_signature"] = upload_signature
    st.session_state["finguard_mapping"] = {k: v if v is not None else NO_COLUMN for k, v in initial_mapping.items()}
if mapping_submitted:
    st.session_state["finguard_mapping"] = selected_mapping
mapping = st.session_state.get("finguard_mapping", {k: v if v is not None else NO_COLUMN for k, v in initial_mapping.items()})

# An ID is useful but not essential; generate stable row-based IDs when absent.
working_df = raw_df.copy()
used_source_columns = {}
for field, source in mapping.items():
    if source != NO_COLUMN and source in working_df.columns:
        used_source_columns[field] = source
        working_df[field] = working_df[source]
if "transaction_id" not in used_source_columns:
    working_df["transaction_id"] = ""
    st.info("No transaction ID column was mapped. Generated temporary IDs from row numbers for this session.")

# Some risk factors require historical or contextual information that a CSV may not contain.
# Do not silently invent them or treat them as negative signals.
core_fields = ["amount_inr", "customer_avg_amount_inr", "location", "is_new_location",
               "transactions_last_10min", "is_new_beneficiary", "outside_usual_hours"]
unmapped = [f for f in core_fields if f not in used_source_columns]
if unmapped:
    st.error("Some fields required by the current scoring rules are not mapped: " + ", ".join(CANONICAL_FIELDS[f]["label"] for f in unmapped))
    st.warning("A different column name can be mapped above. If the information truly does not exist in the dataset, the current rule engine cannot calculate a fully comparable score yet. Do not replace missing evidence with false/zero just to make the error disappear.")
    with st.expander("What if my dataset does not contain these fields?"):
        st.markdown("""
- **Average amount** can sometimes be calculated from a customer's historical transactions if a customer ID and enough history are available.
- **Transaction frequency** can sometimes be derived from customer IDs and timestamps.
- **New location / new beneficiary** require transaction history to compare against; a single isolated transaction row is not enough.
- **Outside usual hours** requires a timestamp and a defined usual-hours policy.

The next enhancement is a data-adaptation step that derives fields where defensible and marks other rules as **Not assessable**, rather than assuming they are false.
""")
    st.stop()

# Keep canonical columns plus the original source columns for evidence and traceability.
working_df = ensure_transaction_ids(working_df)

# Dashboard metrics are descriptive, not fraud ground truth.
amounts = pd.to_numeric(working_df["amount_inr"], errors="coerce")
if amounts.notna().sum() == 0:
    st.error("The mapped transaction amount column contains no numeric values. Check the mapping or clean the amount values.")
    st.stop()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Transactions loaded", f"{len(working_df):,}")
col2.metric("Total transaction value", f"₹{amounts.fillna(0).sum():,.0f}")
col3.metric("New-location flags", int(working_df["is_new_location"].astype(str).str.lower().isin(["true", "1", "yes", "y"]).sum()))
frequency = pd.to_numeric(working_df["transactions_last_10min"], errors="coerce")
col4.metric("High-frequency flags", int((frequency >= 4).sum()))

left, right = st.columns([1.2, 1])
with left:
    st.subheader("Transaction explorer")
    st.dataframe(working_df.head(100), use_container_width=True, hide_index=True)
with right:
    st.subheader("Transaction amounts")
    chart_df = working_df.copy()
    chart_df["amount_inr"] = pd.to_numeric(chart_df["amount_inr"], errors="coerce")
    fig = px.histogram(chart_df, x="amount_inr", nbins=25, title="Transaction amount distribution")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("3. Run a multi-agent investigation")
options = working_df["transaction_id"].astype(str).tolist()
selected_id = st.selectbox("Choose a transaction", options)
row = working_df.loc[working_df["transaction_id"].astype(str) == selected_id].iloc[0].to_dict()
# Convert pandas scalar values to JSON-friendly Python values where possible.
row = {k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}
with st.expander("Selected transaction details"):
    st.json(row)

if st.button("Run investigation", type="primary", use_container_width=True):
    try:
        result = FinGuardOrchestrator().investigate(row)
        st.session_state["last_result"] = result
        st.session_state["last_result_id"] = selected_id
    except Exception as exc:
        st.error(f"Investigation could not be completed: {exc}")
        st.stop()

result = st.session_state.get("last_result")
if result and st.session_state.get("last_result_id") == selected_id and not has_current_result_schema(result):
    st.warning("This saved investigation uses an older result format. Run the investigation again to refresh it.")
    st.session_state.pop("last_result", None)
    st.session_state.pop("last_result_id", None)
    result = None

if result and st.session_state.get("last_result_id") == selected_id:
    st.divider()
    st.subheader("Investigation result")
    if result["validation_status"] == "passed":
        assessment = result["assessment"]
        a, b, c = st.columns(3)
        a.metric("Risk score", f"{assessment['risk_score']}/100")
        b.metric("Risk classification", assessment["risk_level"])
        c.metric("Critic validation", "PASSED")
        st.success(f"**Decision: {result['decision']['label']}**")
        st.write("**Recommended next action:**", result["decision"]["recommended_action"])
        st.caption("Risk indicators support human review; they do not establish whether a transaction is fraudulent.")
        st.write("**Evidence and rule results**")
        st.dataframe(pd.DataFrame(assessment["indicators"]), use_container_width=True, hide_index=True)
    else:
        st.error(f"**Decision: {result['decision']['label']}** — {result['decision']['recommended_action']}")
        st.write("**Critic validation:** FAILED")
        st.json(result["validation"])
    st.write("**Agent execution trace**")
    for item in result["trace"]:
        with st.expander(f"{item.get('agent', 'Agent')} — {item.get('status', 'completed')}"):
            st.json(item)
    report = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(selected_id))
    st.download_button("Download investigation report (JSON)", report,
                       file_name=f"finguard_{safe_id}_report.json", mime="application/json")

st.caption("Mock-model agents use deterministic Python logic. This prototype is for coursework, not operational banking decisions.")
