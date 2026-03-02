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