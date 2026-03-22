# src/analytics.py

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Sequence
from math import floor

import pandas as pd
import streamlit as st


DAILY_ACTIVITY_SQL = """
SELECT date_trunc('day', ts) AS day, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_ids)s) )
GROUP BY day
ORDER BY day;
"""

NUMBER_OF_UNIQUE_USERS_WHO_DID_SOMETHING_WITHIN_INTERVAL_SQL= """
SELECT COUNT(DISTINCT user_id) AS %(columnname)s
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_id)s ) )
ORDER BY user_id;
"""

NUMBER_OF_SUBMISSIONS_IN_FIRST_AND_LATER_QUARTILES_SQL = """
SELECT user_id, COUNT(*) AS %(columnname)s
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_id)s ) )
GROUP BY user_id
ORDER BY user_id;
"""

HOURS_SPENT_ON_ONE_OR_MORE_EXAMS_AT_A_TIME_IN_FIRST_AND_LATER_QUARTILES_SQL = """
SELECT user_id, event_name, ts
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_id)s ) )
ORDER BY user_id, ts;
"""

USERS_AND_TIMES_IN_ORDER_SQL = """
SELECT user_id, ts
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_id)s ) )
ORDER BY ts;
"""

def compute_number_users_by_time_interval(
    conn,
    start_date: date,
    end_date: date,
    *,
    file_ids: list[int] | None = None,
    events: list[str] | None = None,
    threshold: int = 0,    
    interval: int = 30
) -> pd.DataFrame:
    start_ts, end_ts = _date_to_ts_range(start_date, end_date)

    names = list(events) if events else []
    ids = list(file_ids) if file_ids else []

    params = {       
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    }
    df = pd.read_sql_query(USERS_AND_TIMES_IN_ORDER_SQL, conn, params=params)
    timeinterval = timedelta(minutes=interval)
    numbers = []
    counted_ids = []
    last_n = 0

    for r in df.itertuples(index=False):
        new_n = (r.ts-start_ts)/timeinterval

        if new_n-last_n >= 2: #if there is a timeskip
            numbers.append(len(counted_ids))
            counted_ids = []
            n = floor(new_n-last_n)

            for i in range(0, n-1):
                numbers.append(0)
    
        if new_n-last_n >= 1:
            numbers.append(len(counted_ids))
            counted_ids = []
            last_n = floor(new_n)
    
        if r.user_id not in counted_ids:
            counted_ids.append(r.user_id)

    numbers.append(len(counted_ids))
    if len(numbers) > 0:
        x = [i for i in range(len(numbers))]
    else:
        return None
    return pd.DataFrame({"x": pd.Series(x), "number_of_users": pd.Series(numbers)})

def plot_number_of_submissions_in_first_and_later_quartiles_by_user_id(
    conn,
    start_date: date,
    end_date: date,
    *,
    file_ids: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    interval: int = 30,
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
    ids = list(file_ids) if file_ids else []

    if by_interval:
        df = compute_number_users_by_time_interval(conn, start_date, end_date, file_ids=ids, events=names, interval=interval)
        if df == None:
            st.info("No data.")
            return pd.DataFrame(columns=["user_id", "n"])
        df_plot = df.set_index("x")[["number_of_users"]]
        st.bar_chart(df_plot, height=320, use_container_width=True)
        if show_table:
            with st.expander("Show aggregated counts", expanded=False):
                st.dataframe(df_plot, use_container_width=True)
        return df_plot

    params = {    
        "columnname": "number_of_submissions_in_earlier_quartile",    
        "start_ts": start_ts,
        "end_ts": split_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    }

    df_early_quartile = pd.read_sql_query(NUMBER_OF_SUBMISSIONS_IN_FIRST_AND_LATER_QUARTILES_SQL, conn, params=params)
    df_early_quartile["number_of_submissions_in_earlier_quartile"] = df_early_quartile["number_of_submissions_in_earlier_quartile"].astype(int)  
    
    
    params = { 
        "columnname": "number_of_submissions_in_later_quartile",       
        "start_ts": split_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    }

    df_later_quartile = pd.read_sql_query(NUMBER_OF_SUBMISSIONS_IN_FIRST_AND_LATER_QUARTILES_SQL, conn, params=params)
    df_later_quartile["number_of_submissions_in_later_quartile"] = df_later_quartile["number_of_submissions_in_later_quartile"].astype(int)

    df_plot = df_early_quartile.merge(df_later_quartile, on="user_id", how="outer")
    df_plot = df_plot.fillna(0)

    df_plot = df_plot[["number_of_submissions_in_earlier_quartile", "number_of_submissions_in_later_quartile"]]
    st.scatter_chart(df_plot, x="number_of_submissions_in_earlier_quartile", y="number_of_submissions_in_later_quartile")

    if show_table:
        with st.expander("Show aggregated counts", expanded=False):
            st.dataframe(df_plot, use_container_width=True)
    return df_plot

def compute_total_hours_spent_on_one_or_more_exams_at_a_time(df:pd.DataFrame, colname:str):
    total_times = []
    user_ids = []
    if len(df.index) == 0: #if there is no data
        return pd.DataFrame({"user_id": pd.Series(["emptyrow"]), colname: pd.Series([0])})
    
    #Iterate over rows
    cur_user = None #current user_id
    initial = True #whether or not we are at the first row
    
    for r in df.itertuples(index=False):
        if r.user_id != cur_user: #Check if user has changed
            user_ids.append(r.user_id)
            cur_user = r.user_id
            counter = 0 #tracks how many exams are being worked at a time
            
            if initial:
                initial = False
            else:
                total_times.append(total_time)
            
            total_time = 0 #total time spent by a user on one or more exams at a time
        
        if r.event_name == "Tenttiin vastaaminen aloitettu":
            if counter == 0:
                start = r.ts #last recorded exam start
            counter += 1
        
        else: #in other words, if r.event_name == "Tenttivastaus palautettu"
            counter -= 1
        
            if counter == 0:
                total_time += (r.ts-start).total_seconds()/3600 #1h = 3600s
        
            elif counter < 0: #if event_name "Tenttivastaus palautettu" for any reason comes before a corresponding "Tenttiin vastaaminen aloitettu"
                counter = 0 #these cases are ignored
    
    total_times.append(total_time) #finalize
    
    return pd.DataFrame({"user_id": pd.Series(user_ids), colname: pd.Series(total_times)})

def plot_hours_spent_on_one_or_more_exams_at_a_time(
    conn,
    start_date: date,
    end_date: date,
    *,
    file_ids: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    interval: int = 30,
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

    names = ["Tenttivastaus palautettu", "Tenttiin vastaaminen aloitettu"]
    ids = list(file_ids) if file_ids else []

    if by_interval:
        df = compute_number_users_by_time_interval(conn, start_date, end_date, file_ids=ids, events=names, interval=interval)
        if df == None:
            st.info("No data.")
            return pd.DataFrame(columns=["user_id", "n"])
        df_plot = df.set_index("x")[["number_of_users"]]
        st.bar_chart(df_plot, height=320, use_container_width=True)
        if show_table:
            with st.expander("Show aggregated counts", expanded=False):
                st.dataframe(df_plot, use_container_width=True)
        return df_plot

    params = {
        "start_ts": start_ts,
        "end_ts": split_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    }
    df_early_quartile = pd.read_sql_query(HOURS_SPENT_ON_ONE_OR_MORE_EXAMS_AT_A_TIME_IN_FIRST_AND_LATER_QUARTILES_SQL, conn, params=params)
    df_early_quartile["ts"] = pd.to_datetime(df_early_quartile["ts"])
    x_name = "total_hours_spent_on_at_least_one_exam_at_a_time_in_earlier_quartile"
    early_total_times = compute_total_hours_spent_on_one_or_more_exams_at_a_time(df_early_quartile, x_name)

    params = {
        "start_ts": split_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    }
    df_later_quartile = pd.read_sql_query(HOURS_SPENT_ON_ONE_OR_MORE_EXAMS_AT_A_TIME_IN_FIRST_AND_LATER_QUARTILES_SQL, conn, params=params)
    df_later_quartile["ts"] = pd.to_datetime(df_later_quartile["ts"])
    y_name = "total_hours_spent_on_at_least_one_exam_at_a_time_in_later_quartile"
    later_total_times = compute_total_hours_spent_on_one_or_more_exams_at_a_time(df_later_quartile, y_name)

    df_plot = early_total_times.merge(later_total_times, on="user_id", how="outer")
    df_plot = df_plot.fillna(0)
    df_plot = df_plot[df_plot["user_id"] != "emptyrow"]

    df_plot = df_plot[[x_name, y_name]]
    st.scatter_chart(df_plot, x=x_name, y=y_name)

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
    threshold: int = 0,    
    file_ids: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    interval: int = 60 * 24 
) -> pd.DataFrame:
    if start_date > end_date:
        st.error("Invalid date range: start_date > end_date")
        return pd.DataFrame(columns=["day", "n"])
    
    if by_interval:
        df = compute_number_users_by_time_interval(
            conn,
            start_date,
            end_date,
            file_ids=file_ids,
            events=event_names,
            interval=interval
        )

        if df is None or df.empty:
            st.info("Daily activity: no data.")
            return pd.DataFrame()
        
        df_plot = df.set_index("x")[["number_of_users"]]
        st.bar_chart(df_plot, height=320, use_container_width=True)

        if show_table:
            with st.expander("Show aggregated counts", expanded=False):
                st.dataframe(df_plot, use_container_width=True)

        return df_plot

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)

    names = list(event_names) if event_names else []
    ids = list(file_ids) if file_ids else []
    params = {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_ids": ids,
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




HOURLY_ACTIVITY_SQL = """
SELECT EXTRACT(hour FROM ts) AS hour, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_ids)s) )
GROUP BY hour
ORDER BY hour;
"""


WEEKLY_ACTIVITY_SQL = """
SELECT EXTRACT(week FROM ts) AS week, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_ids)s) )
GROUP BY week
ORDER BY week;
"""


COMPONENT_DIST_SQL = """
SELECT component, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_ids)s) )
GROUP BY component
ORDER BY n DESC;
"""


TOP_EVENTS_SQL = """
SELECT event_name, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_ids)s) )
GROUP BY event_name
ORDER BY n DESC
LIMIT %(top_n)s;
"""


def _date_to_ts_range(start_date: date, end_date: date):
    start_ts = datetime.combine(start_date, datetime.min.time())
    end_ts = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    return start_ts, end_ts


def _build_params(start_ts, end_ts, event_names, ids):
    names = list(event_names) if event_names else []

    return {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_ids": ids,
    }


def plot_hourly_activity(
    conn,
    start_date: date,
    end_date: date,
    event_names: Sequence[str] | None = None,
    *,
    threshold: int = 0,    
    file_ids: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    interval: int = 60
) -> pd.DataFrame:
    if by_interval:
        df = compute_number_users_by_time_interval(
            conn,
            start_date,
            end_date,
            file_ids=file_ids,
            events=event_names,
            interval=interval
        )

        if df is None or df.empty:
            st.info("No hourly activity data.")
            return pd.DataFrame()

        df_plot = df.set_index("x")[["number_of_users"]]
        st.bar_chart(df_plot, height=320, use_container_width=True)

        if show_table:
            with st.expander("Show aggregated counts", expanded=False):
                st.dataframe(df_plot, use_container_width=True)

        return df_plot


    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    params = _build_params(start_ts, end_ts, event_names, file_ids)

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
    threshold: int = 0,    
    file_ids: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    interval: int = 60 * 24 * 7
) -> pd.DataFrame:
    if by_interval:
        df = compute_number_users_by_time_interval(
            conn,
            start_date,
            end_date,
            file_ids=file_ids,
            events=event_names,
            interval=interval
        )

        if df is None or df.empty:
            st.info("No weekly activity data.")
            return pd.DataFrame()
        
        df_plot = df.set_index("x")[["number_of_users"]]
        st.line_chart(df_plot, height=320, use_container_width=True)

        if show_table:
            with st.expander("Show aggregated counts", expanded=False):
                st.dataframe(df_plot, use_container_width=True)

        return df_plot

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    params = _build_params(start_ts, end_ts, event_names, file_ids)

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
    threshold: int = 0,    
    file_ids: list[int] | None = None,
    show_table: bool = True
) -> pd.DataFrame:

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    params = _build_params(start_ts, end_ts, event_names, file_ids)

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
    threshold: int = 0,    
    file_ids: list[int] | None = None,
    top_n: int = 10,
    show_table: bool = True
) -> pd.DataFrame:

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)

    params = _build_params(start_ts, end_ts, event_names, file_ids)
    params["top_n"] = top_n

    df = pd.read_sql_query(TOP_EVENTS_SQL, conn, params=params)

    if df.empty:
        st.info("No event data.")
        return df

    chart_df = df.set_index("event_name")[["n"]]
    st.bar_chart(chart_df, height=320, use_container_width=True)

    return df


