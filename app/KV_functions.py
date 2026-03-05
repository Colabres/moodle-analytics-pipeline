from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Sequence

import pandas as pd
import streamlit as st


HOURLY_ACTIVITY_SQL = """
SELECT EXTRACT(hour FROM ts) AS hour, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = %(file_id)s )
GROUP BY hour
ORDER BY hour;
"""


WEEKLY_ACTIVITY_SQL = """
SELECT EXTRACT(week FROM ts) AS week, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = %(file_id)s )
GROUP BY week
ORDER BY week;
"""


COMPONENT_DIST_SQL = """
SELECT component, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = %(file_id)s )
GROUP BY component
ORDER BY n DESC;
"""


TOP_EVENTS_SQL = """
SELECT event_name, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = %(file_id)s )
GROUP BY event_name
ORDER BY n DESC
LIMIT %(top_n)s;
"""


def _date_to_ts_range(start_date: date, end_date: date):
    start_ts = datetime.combine(start_date, datetime.min.time())
    end_ts = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    return start_ts, end_ts


def _build_params(start_ts, end_ts, event_names, file_id):
    names = list(event_names) if event_names else []

    return {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": file_id is not None,
        "file_id": file_id if file_id is not None else 0,
    }


def plot_hourly_activity(
    conn,
    start_date: date,
    end_date: date,
    event_names: Sequence[str] | None = None,
    *,
    file_id: Optional[int] = None
) -> pd.DataFrame:

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    params = _build_params(start_ts, end_ts, event_names, file_id)

    df = pd.read_sql_query(HOURLY_ACTIVITY_SQL, conn, params=params)

    if df.empty:
        st.info("No hourly activity data.")
        return df

    df["hour"] = df["hour"].astype(int)
    df["n"] = df["n"].astype(int)

    chart_df = df.set_index("hour")[["n"]]
    st.bar_chart(chart_df, height=320, use_container_width=True)

    return df


def plot_weekly_activity(
    conn,
    start_date: date,
    end_date: date,
    event_names: Sequence[str] | None = None,
    *,
    file_id: Optional[int] = None
) -> pd.DataFrame:

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    params = _build_params(start_ts, end_ts, event_names, file_id)

    df = pd.read_sql_query(WEEKLY_ACTIVITY_SQL, conn, params=params)

    if df.empty:
        st.info("No weekly activity data.")
        return df

    df["week"] = df["week"].astype(int)
    df["n"] = df["n"].astype(int)

    chart_df = df.set_index("week")[["n"]]
    st.line_chart(chart_df, height=320, use_container_width=True)

    return df


def plot_component_distribution(
    conn,
    start_date: date,
    end_date: date,
    event_names: Sequence[str] | None = None,
    *,
    file_id: Optional[int] = None
) -> pd.DataFrame:

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    params = _build_params(start_ts, end_ts, event_names, file_id)

    df = pd.read_sql_query(COMPONENT_DIST_SQL, conn, params=params)

    if df.empty:
        st.info("No component data.")
        return df

    df["percent"] = (df["n"] / df["n"].sum() * 100).round(1)

    chart_df = df.set_index("component")[["percent"]]
    st.bar_chart(chart_df, height=320, use_container_width=True)

    return df


def plot_top_events(
    conn,
    start_date: date,
    end_date: date,
    event_names: Sequence[str] | None = None,
    *,
    file_id: Optional[int] = None,
    top_n: int = 10
) -> pd.DataFrame:

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)

    params = _build_params(start_ts, end_ts, event_names, file_id)
    params["top_n"] = top_n

    df = pd.read_sql_query(TOP_EVENTS_SQL, conn, params=params)

    if df.empty:
        st.info("No event data.")
        return df

    chart_df = df.set_index("event_name")[["n"]]
    st.bar_chart(chart_df, height=320, use_container_width=True)

    return df


