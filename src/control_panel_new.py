import streamlit as st
import polars as pl
import io
from datetime import date, timedelta
from src.event_buckets import EVENT_BUCKETS
from src.ingest import get_ingest_files
from zombie_remover.data_verifying_functions import good_for_training, good_for_predictions 

# Plot “IDs” are stable keys you can later map to real plotting functions
PLOT_OPTIONS = [
    ("daily_activity", "Daily activity (events per day)"),
    ("hourly_activity", "Hourly activity"),
    ("weekly_trend", "Weekly trend"),
    ("top_event_types", "Top event types"),
    ("component_distribution", "Component distribution"),
]

# Additional analyses (fixed analysis functions)
ADDITIONAL_ANALYSIS_OPTIONS = [
    ("submissions_first_vs_later_quartile", "Submissions: first vs later quartile"),
    ("exam_hours_first_vs_later_quartile", "Exam hours: first vs later quartile"),
]

def load_csv(file) -> pl.DataFrame:
    df = pl.read_csv(file, separator=";", infer_schema_length=1000)

    if len(df.columns) == 1:
        file.seek(0)
        df = pl.read_csv(file, infer_schema_length=1000)

    return df
    
def _checkbox_multiselect(label: str, options: list[str], key_prefix: str) -> list[str]:
    """
    Renders a checkbox list and returns selected option strings.
    """
    st.markdown(label)

    b1, b2 = st.columns(2)
    if b1.button("Select all", key=f"{key_prefix}_all"):
        for opt in options:
            st.session_state[f"{key_prefix}_{opt}"] = True
    if b2.button("Clear", key=f"{key_prefix}_clear"):
        for opt in options:
            st.session_state[f"{key_prefix}_{opt}"] = False

    selected = []
    container = st.container(height=220)

    with container:
        for opt in options:
            checked = st.checkbox(opt, key=f"{key_prefix}_{opt}")
            if checked:
                selected.append(opt)
    return selected


def _render_standard_controls() -> dict:
    col1, col2, col3, col4 = st.columns(4, gap="large")

    # --------- 1) Time Range ----------
    with col1:
        st.markdown("Time Range")

        today = date.today()
        default_start = today - timedelta(days=14)
        default_end = today

        start_date = st.date_input("Start date", value=default_start, key="cp_start_date")
        end_date = st.date_input("End date", value=default_end, key="cp_end_date")

        if start_date > end_date:
            st.error("Start date must be on or before end date.")
    
    # --------- 2) Course sellector ----------
    with col2:
        st.markdown("Course")

        course_search = st.text_input("Search course", key="cp_course_search")

        course_items = get_ingest_files(course_search)

        course_labels = [f"{file_id} — {filename}" for file_id, filename in course_items]
        label_to_id = {
            f"{file_id} — {filename}": file_id
            for file_id, filename in course_items
        }

        selected_course_labels = _checkbox_multiselect(
            label="Select courses:",
            options=course_labels,
            key_prefix="cp_course"
        )

        selected_course_ids = [label_to_id[label] for label in selected_course_labels]

        st.caption(f"{len(course_items)} matching courses.")

    # --------- 3) Event buckets ----------
    with col3:
        st.markdown("Event groups to include")

        bucket_names = list(EVENT_BUCKETS.keys())

        selected_buckets = _checkbox_multiselect(
            label="Select event buckets:",
            options=bucket_names,
            key_prefix="cp_bucket"
        )
      
        dedup_minutes = st.slider(
            "Event uniqueness threshold (minutes)",
            min_value=0,
            max_value=60,
            value=5,
            step=1
        )

        selected_subevents = []

        if selected_buckets:
            with st.expander("Expand selected buckets into specific events"):
                expanded_events = []
                for bucket in selected_buckets:
                    expanded_events.extend(EVENT_BUCKETS.get(bucket, []))

                expanded_events = sorted(set(expanded_events))

                selected_subevents = _checkbox_multiselect(
                    label="Select specific events (optional):",
                    options=expanded_events,
                    key_prefix="cp_subevent"
                )
        st.caption("UI-only now. Later: selected buckets expand into event_name filters.")

    # --------- 4) Analytics plots ----------
    with col4:
        st.markdown("Analytics graphs to display")

        plot_labels = [label for (_id, label) in PLOT_OPTIONS]
        label_to_id = {label: _id for (_id, label) in PLOT_OPTIONS}

        selected_plot_labels = _checkbox_multiselect(
            label="Select plots to render:",
            options=plot_labels,
            key_prefix="cp_plot"
        )

        selected_plot_ids = [label_to_id[x] for x in selected_plot_labels]

        run_clicked = st.button(
            "Run analysis",
            type="primary",
            use_container_width=True,
            key="cp_run"
        )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "course_ids": selected_course_ids,
        "buckets": selected_buckets,
        "threshold": dedup_minutes,
        "subevents": selected_subevents,
        "plots": selected_plot_ids,
        "run_clicked": run_clicked,
    }


def _render_additional_analysis_controls() -> dict:
    st.markdown("### Additional analyses")

    analysis_labels = [label for (_id, label) in ADDITIONAL_ANALYSIS_OPTIONS]
    label_to_id = {label: _id for (_id, label) in ADDITIONAL_ANALYSIS_OPTIONS}

    selected_analysis_labels = _checkbox_multiselect(
        label="Select analyses to run:",
        options=analysis_labels,
        key_prefix="cp_additional"
    )

    selected_analysis_ids = [label_to_id[x] for x in selected_analysis_labels]

    run_clicked = st.button(
        "Run additional analyses",
        use_container_width=True,
        key="cp_additional_run"
    )

    return {
        "selected": selected_analysis_ids,
        "run_clicked": run_clicked,
    }

def _render_zombie_remover_controls() -> dict:
    st.markdown("### Zombie Remover")

    advanced_mode = st.checkbox("Advanced training", key="zr_advanced")

    train_uploaded = st.file_uploader(
        "Upload labeled training CSV",
        type=["csv"],
        key="zr_train_upload",
    )

    if train_uploaded is not None:
        train_df = load_csv(io.BytesIO(train_uploaded.getvalue()))
        st.write("Detected columns:", train_df.columns)
        st.write("Validator result:", good_for_training(train_df))
        st.write("First column repr:", repr(train_df.columns[0]))
        train_valid = good_for_training(train_df)

        if train_valid:
            st.success("Training file verified.")
        else:
            st.error("Training file format is invalid.")

    predict_uploaded = st.file_uploader(
        "Upload prediction CSV",
        type=["csv"],
        key="zr_predict_upload",
    )

    if predict_uploaded is not None:
        predict_df = load_csv(io.BytesIO(predict_uploaded.getvalue()))
        predict_valid = good_for_predictions(predict_df)

        if predict_valid:
            st.success("Prediction file verified.")
        else:
            st.error("Prediction file format is invalid.")

    return {
        "advanced_mode": advanced_mode,
        "train_uploaded": train_uploaded,
        "predict_uploaded": predict_uploaded,
    }

def render_control_panel() -> dict:
    st.subheader("Control Panel")

    standard_config = _render_standard_controls()

    st.divider()

    #additional_config = _render_additional_analysis_controls()
    left_col, right_col = st.columns(2, gap="large")

    with left_col:
        additional_config = _render_additional_analysis_controls()

    with right_col:
        zombie_config = _render_zombie_remover_controls()

    st.divider()

    config = {
        "standard": standard_config,
        "additional": additional_config,
        "zombie": zombie_config
    }

    # UI-only feedback for standard controls
    if standard_config["run_clicked"]:
        if standard_config["start_date"] > standard_config["end_date"]:
            st.warning("Fix the date range first.")
        elif not standard_config["plots"]:
            st.warning("Select at least one plot to run.")
        else:
            st.info("UI-only mode: these plots would run (no DB yet).")
            st.write(
                {
                    "time_window": f"{standard_config['start_date']} .. {standard_config['end_date']}",
                    "event_buckets": standard_config["buckets"] if standard_config["buckets"] else "(ALL later)",
                    "plots": standard_config["plots"],
                }
            )

    # UI-only feedback for additional analyses
    if additional_config["run_clicked"]:
        if not additional_config["selected"]:
            st.warning("Select at least one additional analysis to run.")
        else:
            st.info("UI-only mode: these additional analyses would run later.")
            st.write(
                {
                    "additional_analyses": additional_config["selected"],
                }
            )

    return config