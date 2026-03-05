import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import polars as pl
import io
import hashlib

from src.ingest import transfer_to_db
from src.db import connect, fetch_events_by_file
from src.control_panel import render_control_panel

st.set_page_config(page_title="Moodle Log Explorer", layout="wide")
st.title("Moodle Log Explorer")



def load_csv(file) -> pl.DataFrame:
    try:
        return pl.read_csv(file, separator=";", infer_schema_length=1000)
    except Exception:
        file.seek(0)
        return pl.read_csv(file, infer_schema_length=1000)
    

def session_fingerprint(file_bytes: bytes) -> str:
    # Prevents Streamlit reruns from inserting the same upload again
    return hashlib.sha256(file_bytes).hexdigest()

# --- UI ---
uploaded = st.file_uploader("Drop a Moodle CSV file here", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV to preview and filter it.")
    st.stop()

uploaded_bytes = uploaded.getvalue()
df = load_csv(io.BytesIO(uploaded_bytes))

fp = session_fingerprint(uploaded_bytes)

# Auto-transfer once per uploaded file (per session)
if st.session_state.get("last_upload_fp") != fp:
    st.session_state["last_upload_fp"] = fp

    try:
        file_id, inserted, skipped = transfer_to_db(df, uploaded.name)
        st.session_state["last_file_id"] = file_id
        st.session_state["last_ingest_stats"] = (inserted, skipped)
    except Exception as e:
        st.error(f"Transfer failed: {e}")
        st.stop()

st.subheader("Preview (from database)")

file_id = st.session_state.get("last_file_id", 0)
inserted, skipped = st.session_state.get("last_ingest_stats", (0, 0))

c1, c2, c3 = st.columns(3)
c1.metric("file_id", file_id)
c2.metric("Inserted", inserted)
c3.metric("Skipped", skipped)

if file_id != 0:
    with connect() as conn:
        with conn.cursor() as cur:
            rows = fetch_events_by_file(cur, file_id=file_id, limit=200)

    preview_df = pl.DataFrame(
        rows,
        schema=["id", "ts", "user_id", "context", "component", "event_name", "description", "origin"]
    )
    st.dataframe(preview_df.to_pandas(), use_container_width=True)
else:
    st.warning("No rows inserted.")



# -----------------------------
# Analytics Control Panel
# -----------------------------
st.divider()
st.header("Analytics")

from src.analytics import plot_daily_activity
from src.event_buckets import expand_buckets

PLOT_REGISTRY = {
    "daily_activity": plot_daily_activity,
}

cfg = render_control_panel()

if cfg.get("run_clicked"):
    event_names = expand_buckets(cfg.get("buckets", []))

    if not cfg.get("plots"):
        st.warning("Select at least one plot.")
    else:
        with connect() as conn:
            for plot_id in cfg["plots"]:
                fn = PLOT_REGISTRY.get(plot_id)

                if fn is None:
                    st.error(f"Plot not implemented: {plot_id}")
                    continue

                st.subheader("Daily activity (events per day)")

                fn(
                    conn,
                    cfg["start_date"],
                    cfg["end_date"],
                    event_names,
                    file_id=None,
                    show_table=True,
                )