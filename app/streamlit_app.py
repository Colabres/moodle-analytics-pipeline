import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import polars as pl
import pandas as pd
import io
import hashlib

from src.ingest import transfer_to_db, get_all_file_ids
from src.db import connect, fetch_events_by_file
from src.control_panel_new import render_control_panel
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
run_import = False
uploaded = st.file_uploader("Drop a Moodle CSV file here", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV to preview and filter it.")
else:
    uploaded_bytes = uploaded.getvalue()
    df = load_csv(io.BytesIO(uploaded_bytes))


if uploaded is not None:
    st.info("File uploaded. Please enter Course name and Course ID to start the import.")

    course_name = st.text_input("Course name", key="course_name_input")
    course_id = st.text_input("Course ID", key="course_id_input")

    run_import = st.button("Start import", type="primary")

if run_import:
    

    if not course_name.strip():
        st.warning("Please enter Course name before starting import.")
        st.stop()

    if not course_id.strip():
        st.warning("Please enter Course ID before starting import.")
        st.stop()

    try:
        course_id_int = int(course_id.strip())
    except ValueError:
        st.error("Course ID must be numeric.")
        st.stop()

    existing_ids = get_all_file_ids()

    if course_id_int in existing_ids:
        st.error("This Course ID already exists in the database.")
        st.stop()

    try:
        file_id, inserted, skipped = transfer_to_db(df,course_id_int,course_name)
        st.session_state["last_file_id"] = file_id
        st.session_state["last_ingest_stats"] = (inserted, skipped)
        st.session_state["last_course_id"] = course_id_int
        st.session_state["last_course_name"] = course_name.strip()
    except Exception as e:
        st.error(f"Transfer failed: {e}")
        st.stop()


    st.subheader("Preview (from database)")

    file_id = course_id_int
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

                cur.execute("""
                    SELECT file_id, filename, user_count, active_user_count
                    FROM moodle.ingest_file
                    WHERE file_id = %s
                """, (file_id,))

                ingest_file_row = cur.fetchone()

            
        if ingest_file_row is not None:
            _, filename_db, user_count_db, active_user_count_db = ingest_file_row

            st.subheader("Ingest file info")
            col1, col2 = st.columns(2)
            col1.metric("Total users", user_count_db)
            col2.metric("Active users", active_user_count_db)
            st.write(f"Filename: {filename_db}")

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

from src.analytics import (
    plot_daily_activity,
    plot_number_of_submissions_in_first_and_later_quartiles_by_user_id,
    plot_hours_spent_on_one_or_more_exams_at_a_time,
    plot_hourly_activity,    
    plot_weekly_activity,
    plot_weekday_activity,
    plot_component_distribution,
    plot_top_events,
    plot_hours_spent_on_each_exam,
    plot_number_of_submissions_per_context,
    plot_portion_of_users_per_context,
    plot_active_days_above_threshold,
    plot_last_activity_scatter,

)

from src.event_buckets import expand_buckets

PLOT_REGISTRY = {
    "daily_activity": plot_daily_activity,
    "hourly_activity": plot_hourly_activity,
    "weekly_trend": plot_weekly_activity,
    "weekday_activity": plot_weekday_activity,
    "component_distribution": plot_component_distribution,
    "top_event_types": plot_top_events,
    "active_days_above_threshold": plot_active_days_above_threshold,
    "last_activity_scatter": plot_last_activity_scatter,
}
PLOT_TITLES = {
    "daily_activity": "Daily activity (events per day)",
    "hourly_activity": "Hourly activity",
    "weekly_trend": "Weekly activity trend",
    "weekday_activity": "Weekday activity",
    "component_distribution": "Component distribution",
    "top_event_types": "Top event types",
    "active_days_above_threshold": "Active days above threshold",
    "last_activity_scatter": "Last activity scatter",
}
ADDITIONAL_ANALYSIS_REGISTRY = {
    "submissions_first_vs_later_quartile": plot_number_of_submissions_in_first_and_later_quartiles_by_user_id,
    "exam_hours_first_vs_later_quartile": plot_hours_spent_on_one_or_more_exams_at_a_time,
    "exam_hours_per_exam": plot_hours_spent_on_each_exam,
    "submissions_per_context": plot_number_of_submissions_per_context,
    "portion_of_users_per_context": plot_portion_of_users_per_context,
    
}
cfg = render_control_panel()
standard = cfg["standard"]
additional = cfg["additional"]

if standard.get("run_clicked"):
    #event_names = expand_buckets(standard.get("buckets", []))
    if standard.get("subevents"):
        event_names = standard["subevents"]
    else:
        event_names = expand_buckets(standard.get("buckets", []))
    if not standard.get("plots"):
        st.warning("Select at least one plot.")
    else:
        with connect() as conn:
            for plot_id in standard["plots"]:
                fn = PLOT_REGISTRY.get(plot_id)

                if fn is None:
                    st.error(f"Plot not implemented: {plot_id}")
                    continue

                title = PLOT_TITLES.get(plot_id, plot_id.replace("_", " ").title())
                st.subheader(title)

                fn(
                    conn,
                    standard["start_date"],
                    standard["end_date"],
                    event_names,
                    threshold=standard["threshold"],                    
                    file_ids = standard["course_ids"],
                    show_table=True,
                )

# -----------------------------
# Additional analyses
# -----------------------------

if additional.get("run_clicked"):
    if not additional.get("selected"):
        st.warning("Select at least one additional analysis.")
    else:
        with connect() as conn:
            for analysis_id in additional["selected"]:
                fn = ADDITIONAL_ANALYSIS_REGISTRY.get(analysis_id)

                if fn is None:
                    st.error(f"Additional analysis not implemented: {analysis_id}")
                    continue

                if analysis_id == "submissions_first_vs_later_quartile":
                    st.subheader("Average number of submissions per user in four quartiles over the selected duration (Note: users who made no submissions are not taken into account)")
                elif analysis_id == "exam_hours_first_vs_later_quartile":
                    st.subheader("Average total hours spent on at least one exam at a time per user in four quartiles over the selected duration (Note: users who spent no time on exams are not taken into account)")
                elif analysis_id == "exam_hours_per_exam":
                    st.subheader("Total hours spent by the average user on each exam (Note: users who spent no time on exams are not taken into account)")
                elif analysis_id == "submissions_per_context":
                    st.subheader("Number of submissions by the average user in each context (Note: users who made no submissions are not taken into account)")
                elif analysis_id == "portion_of_users_per_context":
                    st.subheader("Portion of all users who made at least one submission per context")
                else:
                    st.subheader(analysis_id.replace("_", " ").title())

                fn(
                    conn,
                    standard["start_date"],
                    standard["end_date"],
                    file_id=None,
                    show_table=True,
                )