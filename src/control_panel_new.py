import streamlit as st
from datetime import date, timedelta
from src.event_buckets import EVENT_BUCKETS

# Plot “IDs” are stable keys you can later map to real plotting functions
PLOT_OPTIONS = [
    ("daily_activity", "Daily activity (events per day)"),
    ("weekly_trend", "Weekly trend"),
    ("top_event_types", "Top event types"),
    ("component_distribution", "Component distribution"),
]

# Additional analyses (fixed analysis functions)
ADDITIONAL_ANALYSIS_OPTIONS = [
    ("submissions_first_vs_later_quartile", "Submissions: first vs later quartile"),
    ("exam_hours_first_vs_later_quartile", "Exam hours: first vs later quartile"),
]


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
    for opt in options:
        checked = st.checkbox(opt, key=f"{key_prefix}_{opt}")
        if checked:
            selected.append(opt)
    return selected


def _render_standard_controls() -> dict:
    col1, col2, col3 = st.columns(3, gap="large")

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

    # --------- 2) Event buckets ----------
    with col2:
        st.markdown("Event groups to include")

        bucket_names = list(EVENT_BUCKETS.keys())

        selected_buckets = _checkbox_multiselect(
            label="Select event buckets (empty = all later):",
            options=bucket_names,
            key_prefix="cp_bucket"
        )

        st.caption("UI-only now. Later: selected buckets expand into event_name filters.")

    # --------- 3) Analytics plots ----------
    with col3:
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
        "buckets": selected_buckets,
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


def render_control_panel() -> dict:
    st.subheader("Control Panel")

    standard_config = _render_standard_controls()

    st.divider()

    additional_config = _render_additional_analysis_controls()

    st.divider()

    config = {
        "standard": standard_config,
        "additional": additional_config,
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