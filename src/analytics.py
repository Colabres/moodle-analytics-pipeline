# src/analytics.py

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Sequence

import pandas as pd
import streamlit as st


DAILY_ACTIVITY_SQL = """
SELECT date_trunc('day', ts) AS day, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = %(file_id)s )
GROUP BY day
ORDER BY day;
"""

NUMBER_OF_SUBMISSIONS_IN_FIRST_AND_LATER_QUARTILES_SQL = """
SELECT user_id, COUNT(*) AS %(colname)s
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = %(file_id)s )
GROUP BY user_id
ORDER BY user_id;
"""

def plot_number_of_submissions_in_first_and_later_quartiles_by_user_id(
    conn,
    start_date: date,
    end_date: date,
    *,
    file_id: Optional[int] = None,
    show_table: bool = True,
    quartile: float = 1/4 
) -> pd.DataFrame:
    #Note: plots both exercise and exam submissions
    if start_date > end_date:
        st.error("Invalid date range: start_date > end_date")
        return pd.DataFrame(columns=["user_id", "n"])
    
    if quartile >= 1 or quartile <= 0:
        st.error("Invalid quartile: must be larger than 0 and smaller than 1")
        return pd.DataFrame(columns=["user_id", "n"])
    
    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    split_ts = start_ts + (end_ts-start_ts)*quartile

    names = ["Tenttivastaus palautettu", "Palautus on lähetetty"]

    params = {
        "colname": "nx",
        "start_ts": start_ts,
        "end_ts": split_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": file_id is not None,
        "file_id": file_id if file_id is not None else 0,
    }

    df_early_quartile = pd.read_sql_query(NUMBER_OF_SUBMISSIONS_IN_FIRST_AND_LATER_QUARTILES_SQL, conn, params=params)
    df_early_quartile["nx"] = df_early_quartile["nx"].astype(int)

    params = {
        "colname": "ny",
        "start_ts": split_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": file_id is not None,
        "file_id": file_id if file_id is not None else 0,
    }

    df_later_quartile = pd.read_sql_query(NUMBER_OF_SUBMISSIONS_IN_FIRST_AND_LATER_QUARTILES_SQL, conn, params=params)
    df_later_quartile["ny"] = df_later_quartile["ny"].astype(int)

    df_plot = df_early_quartile.merge(df_later_quartile, on="user_id", how="outer")
    df_plot = df_plot.fillna(0)

    df_plot = df_plot.set_index("nx")[["nx", "ny"]]
    st.scatter_chart(df_plot, x="nx", y="ny")

    if show_table:
        with st.expander("Show aggregated counts", expanded=False):
            st.dataframe(df_plot, use_container_width=True)
    return df_plot

def _date_to_ts_range(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start_ts = datetime.combine(start_date, datetime.min.time())
    end_ts = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    return start_ts, end_ts


def plot_daily_activity(
    conn,
    start_date: date,
    end_date: date,
    event_names: Sequence[str] | None,
    *,
    file_id: Optional[int] = None,
    show_table: bool = True,
) -> pd.DataFrame:
    if start_date > end_date:
        st.error("Invalid date range: start_date > end_date")
        return pd.DataFrame(columns=["day", "n"])

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)

    names = list(event_names) if event_names else []
    params = {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": file_id is not None,
        "file_id": file_id if file_id is not None else 0,
    }

    df = pd.read_sql_query(DAILY_ACTIVITY_SQL, conn, params=params)

    if df.empty:
        st.info("Daily activity: no events for selected filters.")
        if show_table:
            with st.expander("Show aggregated daily counts", expanded=False):
                st.dataframe(df, use_container_width=True)
        return df

    # Types + format for Streamlit chart
    df = df.copy()
    df["day"] = pd.to_datetime(df["day"]).dt.date
    df["n"] = df["n"].astype(int)

    chart_df = df.set_index("day")[["n"]]
    st.bar_chart(chart_df, height=320, use_container_width=True)

    if show_table:
        with st.expander("Show aggregated daily counts", expanded=False):
            st.dataframe(df, use_container_width=True)

    return df