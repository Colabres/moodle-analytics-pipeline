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
from src.event_buckets import EVENT_BUCKETS
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
    admin_bucket_names = EVENT_BUCKETS.get("Admin activity", [])

    with connect() as conn:
        with conn.cursor() as cur:

            # normal preview
            rows = fetch_events_by_file(cur, file_id=file_id, limit=200)

            # DEBUG: events whose event_name is in the "Admin activity" bucket
            # plus whether that user_id is marked admin in user_dim
            cur.execute("""
                SELECT e.id, e.ts, e.user_id, u.is_admin,
                       e.context, e.component, e.event_name, e.description, e.origin
                FROM moodle.event e
                LEFT JOIN moodle.user_dim u
                  ON e.user_id = u.user_id
                WHERE e.file_id = %s
                  AND e.event_name = ANY(%s)
                ORDER BY e.id
                LIMIT 200
            """, (file_id, admin_bucket_names))

            admin_bucket_event_rows = cur.fetchall()

    # normal preview
    preview_df = pl.DataFrame(
        rows,
        schema=["id","ts","user_id","context","component","event_name","description","origin"]
    )
    st.subheader("Event preview")
    st.dataframe(preview_df.to_pandas(), use_container_width=True)

    # admin-bucket debug table
    admin_bucket_df = pl.DataFrame(
        admin_bucket_event_rows,
        schema=["id","ts","user_id","is_admin","context","component","event_name","description","origin"]
    )

    st.subheader("DEBUG: events with event_name in 'Admin activity' bucket (should be empty OR show new ids)")
    st.dataframe(admin_bucket_df.to_pandas(), use_container_width=True)

else:
    st.warning("No rows inserted.")

if st.button("Reset session"):
    st.session_state.clear()
    st.rerun()

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