# src/analytics.py

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Sequence
from math import floor

import pandas as pd
import streamlit as st
import altair as alt
import numpy as np


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
SELECT COUNT(DISTINCT user_id) AS users_n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_id)s ) )
ORDER BY user_id;
"""

NUMBER_OF_SUBMISSIONS_IN_FIRST_AND_LATER_QUARTILES_SQL = """
SELECT user_id, COUNT(*) AS submissions_n
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

HOURS_SPENT_ON_EACH_EXAM_SQL = """
SELECT context, user_id, event_name, ts
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_id)s ) )
ORDER BY context, user_id, ts;
"""

NUMBER_OF_SUBMISSIONS_PER_CONTEXT_SQL = """
SELECT context, COUNT(*) AS submissions_n, COUNT(DISTINCT user_id) AS users_n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_id)s ) )
GROUP BY context
ORDER BY context;
"""

NUMBER_OF_UNIQUE_USERS_SQL= """
SELECT user_id, COUNT(DISTINCT context) AS total_users
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_id)s ) )
GROUP BY user_id
ORDER BY user_id;
"""

def adapt_dataframe_by_treshold(data: pl.DataFrame, treshold: int) -> pl.DataFrame:
    #deletes logs that are created within "treshold" minutes of each other by the same user
    treshold = str(treshold)+"m"
    df = data.clone()
    df = df.with_columns(pl.col("Aika").str.to_datetime(format="%d.%m.%Y, %H.%M.%S").alias("datetime"))
    df = df.with_columns(pl.col("datetime").dt.round(treshold).alias("datetime_rounded"))
    df = df.unique(subset=["Kayttaja_id", "datetime_rounded"], maintain_order=True)
    df = df.drop(["datetime", "datetime_rounded"])
    return df

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
    #compute how many distinct users did something on each x min interval
    start_ts, end_ts = _date_to_ts_range(start_date, end_date)

    names = list(events) if events else [] #check which events to include
    ids = list(file_ids) if file_ids else [] #check which file_ids to include

    params = {       
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    } #prepare query parameters
    df = pd.read_sql_query(USERS_AND_TIMES_IN_ORDER_SQL, conn, params=params) #execute query
    if len(df.index) <= 0: #no data
        return None
    if threshold <= 0: #if the treshold parameter is not given by the dashboard UI or it is smaller or equal to 0
        timeinterval = timedelta(minutes=interval) #use the interval parameter
    else: #otherwise
        timeinterval = timedelta(minutes=threshold) #use the treshold parameter
    numbers = [] #number of distinct users who did something by interval 
    counted_ids = [] #distinct users who did something in a given interval
    last_n = 0 #last interval

    for r in df.itertuples(index=False): #iterate over rows
        new_n = (r.ts-start_ts)/timeinterval #compute which interval we are in

        if new_n-last_n >= 2: #if there is a timeskip
            numbers.append(len(counted_ids)) #record the information of the last interval
            counted_ids = []
            n = floor(new_n-last_n)

            for i in range(0, n-1): #append zeros until the last interval before the end of the timeskip
                numbers.append(0)
    
        if new_n-last_n >= 1: #if we have arrived at the next interval
            numbers.append(len(counted_ids)) #record the information of the last interval
            counted_ids = []
            last_n = floor(new_n)
    
        if r.user_id not in counted_ids: #check if we have not already encoutered the user within a given interval
            counted_ids.append(r.user_id)

    numbers.append(len(counted_ids)) #finalize
    if len(numbers) > 0:
        x = [i for i in range(len(numbers))]
    else: #no data
        return None
    return pd.DataFrame({"x": pd.Series(x), "number_of_users": pd.Series(numbers)})

def plot_number_of_submissions_in_first_and_later_quartiles_by_user_id(
    conn,
    start_date: date,
    end_date: date,
    *,
    file_id: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    threshold: int = 0, 
    interval: int = 30
) -> pd.DataFrame:
    #Note: plots both exercise and exam submissions
    if start_date > end_date: #validate the start and end dates
        st.error("Invalid date range: start_date > end_date")
        return pd.DataFrame(columns=["user_id", "n"])
    
    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    split_ts1 = start_ts + (end_ts-start_ts)*(1*(1/4)) #end of first quartile
    split_ts2 = start_ts + (end_ts-start_ts)*(2*(1/4)) #end of second quartile
    split_ts3 = start_ts + (end_ts-start_ts)*(3*(1/4)) #end of third quartile and start of fourth quartile

    names = ["Tenttivastaus palautettu", "Palautus on lähetetty"] #we are only interested in submissions, be they exam or exercise submissions
    ids = list(file_id) if file_id else [] #check which file_ids to include in the query

    if by_interval: #if we want to split the duration into x min intervals, we ignore the quartile partition done earlier
        df = compute_number_users_by_time_interval(conn, start_date, end_date, file_ids=ids, events=names, threshold=threshold, interval=interval)
        if df == None: #no data
            st.info("No data.")
            return pd.DataFrame(columns=["user_id", "n"])
        
        df_plot = df.set_index("x")[["number_of_users"]]
        st.bar_chart(df_plot, height=320, use_container_width=True) #plot a bar chart

        if show_table:
            with st.expander("Show aggregated counts", expanded=False):
                st.dataframe(df_plot, use_container_width=True)
        return df_plot

    averages = []
    for i in [(start_ts, split_ts1), (split_ts1, split_ts2), (split_ts2, split_ts3), (split_ts3, end_ts)]:
        params = {        
            "start_ts": i[0],
            "end_ts": i[1],
            "use_event_filter": len(names) > 0,
            "event_names": names,
            "use_file_scope": len(ids) > 0,
            "file_id": ids,
        } #prepare the query parameters

        df_quartile = pd.read_sql_query(NUMBER_OF_SUBMISSIONS_IN_FIRST_AND_LATER_QUARTILES_SQL, conn, params=params) #execute query
        if len(df_quartile.index) < 1: #if no data in quartile
            averages.append(0) #add zero and move on to the next iteration
            continue

        df_quartile["submissions_n"] = df_quartile["submissions_n"].astype(int) #extract numbers of submissions
        averages.append((df_quartile["submissions_n"].sum())/(len(df_quartile.index))) #add average number of submissions

    bar_names = ["1st quartile", "2nd quartile", "3rd quartile", "4th quartile"] #setup the x axis for bar plot
    df = pd.DataFrame({"quartile": pd.Series(bar_names), "average number of submissions": pd.Series(averages)})
    df_plot = df.set_index("quartile")[["average number of submissions"]] #set quartile as index
    st.bar_chart(df_plot, height=320, use_container_width=True) #plot a bar chart

    if show_table:
        with st.expander("Show aggregated counts", expanded=False):
            st.dataframe(df_plot, use_container_width=True)
    return df_plot

def compute_total_hours_spent_on_one_or_more_exams_at_a_time(df:pd.DataFrame, colname:str):
    #the dataframe is assumed to be ordered first by user_id and then by timestamp
    total_times = []
    user_ids = []
    if len(df.index) == 0: #if there is no data
        return pd.DataFrame({"user_id": pd.Series([0]), colname: pd.Series([0])}) #return a dummy row which will be removed later
    
    cur_user = None #current user_id
    initial = True #whether or not we are at the first row
    
    for r in df.itertuples(index=False): #iterate over rows
        if r.user_id != cur_user: #Check if user has changed
            user_ids.append(r.user_id)
            cur_user = r.user_id
            counter = 0 #tracks how many exams are being worked at a time
            
            if initial: #check if we are in the first row
                initial = False #we are no longer in the first row, initialization complete
            else:
                total_times.append(total_time)
            
            total_time = 0 #total time spent by a user on one or more exams at a time
        
        if r.event_name == "Tenttiin vastaaminen aloitettu": #start of an exam
            if counter == 0:
                start = r.ts #last recorded exam start
            counter += 1
        
        else: #in other words, if r.event_name == "Tenttivastaus palautettu", end of an exam
            counter -= 1
        
            if counter == 0: #no more ongoing exams
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
    file_id: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    threshold: int = 0, 
    interval: int = 30
) -> pd.DataFrame:
    
    if start_date > end_date: #validate the start and end dates
        st.error("Invalid date range: start_date > end_date")
        return pd.DataFrame(columns=["user_id", "n"])
    
    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    split_ts1 = start_ts + (end_ts-start_ts)*(1*(1/4)) #end of first quartile
    split_ts2 = start_ts + (end_ts-start_ts)*(2*(1/4)) #end of second quartile
    split_ts3 = start_ts + (end_ts-start_ts)*(3*(1/4)) #end of third quartile and start of fourth quartile

    names = ["Tenttivastaus palautettu", "Tenttiin vastaaminen aloitettu"] #we are only interested in exam start and end times
    ids = list(file_id) if file_id else [] #check which file_ids to include in the query

    if by_interval: #if we want to split the duration into x min intervals, we ignore the quartile partition done earlier
        df = compute_number_users_by_time_interval(conn, start_date, end_date, file_ids=ids, events=names, threshold=threshold, interval=interval)
        if df == None: #no data
            st.info("No data.")
            return pd.DataFrame(columns=["user_id", "n"])
        
        df_plot = df.set_index("x")[["number_of_users"]]
        st.bar_chart(df_plot, height=320, use_container_width=True) #plot a bar chart

        if show_table:
            with st.expander("Show aggregated counts", expanded=False):
                st.dataframe(df_plot, use_container_width=True)
        return df_plot

    averages = []
    for i in [(start_ts, split_ts1), (split_ts1, split_ts2), (split_ts2, split_ts3), (split_ts3, end_ts)]:
        params = {        
            "start_ts": i[0],
            "end_ts": i[1],
            "use_event_filter": len(names) > 0,
            "event_names": names,
            "use_file_scope": len(ids) > 0,
            "file_id": ids,
        } #prepare the query parameters

        df_quartile = pd.read_sql_query(HOURS_SPENT_ON_ONE_OR_MORE_EXAMS_AT_A_TIME_IN_FIRST_AND_LATER_QUARTILES_SQL, conn, params=params) #execute query
        if len(df_quartile.index) < 1: #if no data in quartile
            averages.append(0) #add zero and move on to the next iteration
            continue

        df_quartile["ts"] = pd.to_datetime(df_quartile["ts"])
        total_times = compute_total_hours_spent_on_one_or_more_exams_at_a_time(df_quartile, "total hours") #perform computation
        averages.append((total_times["total hours"].sum())/(len(total_times.index))) #add average hours spent

    bar_names = ["1st quartile", "2nd quartile", "3rd quartile", "4th quartile"] #setup the x axis for bar plot
    df = pd.DataFrame({"quartile": pd.Series(bar_names), "average hours spent on at least one exam at a time": pd.Series(averages)})
    df_plot = df.set_index("quartile")[["average hours spent on at least one exam at a time"]] #set quartile as index
    st.bar_chart(df_plot, height=320, use_container_width=True) #plot a bar chart

    if show_table:
        with st.expander("Show aggregated counts", expanded=False):
            st.dataframe(df_plot, use_container_width=True)
    return df_plot

def compute_total_hours_on_a_specific_exam(table:pd.DataFrame, colname:str, colname2:str):
    ac = [] #total hours spent on each exam
    contxs = [] #list of context names
    user_n = [] #number of unique users per exam
    if len(table.index) == 0: #no data
        return pd.DataFrame({"exam": pd.Series(["emptyrow"]), colname: pd.Series([0]), colname2: pd.Series([0])})
        #return dummy row to be removed later
    initial = True

    for r in table.itertuples(index=False):
        if initial: #Initialize
            initial = False
            context_hours = 0
            user_hours = 0
            cur_context = r.context
            cur_user = r.user_id
            n_users = 0
            counter = 0
        
        if r.context != cur_context: #Check if context has changed
            contxs.append(cur_context)
            context_hours += user_hours
            ac.append(context_hours)
            n_users += 1
            user_n.append(n_users)
            n_users = 0
            context_hours = 0
            cur_context = r.context
            cur_user = r.user_id
            user_hours = 0
            counter = 0
        
        if r.user_id != cur_user: #Check if user has changed
            context_hours += user_hours
            user_hours = 0
            counter = 0
            cur_user = r.user_id
            n_users += 1

        if r.event_name == "Tenttiin vastaaminen aloitettu":
            if counter == 0:
                start = r.ts #last recorded exam start
            counter += 1
        
        else: #in other words, if event_name == "Tenttivastaus palautettu"
            counter -= 1

            if counter == 0: #no more ongoing exams
                user_hours += (r.ts-start).total_seconds()/3600 #1h = 3600s
            
            elif counter < 0: #if event_name "Tenttivastaus palautettu" for any reason comes before a corresponding "Tenttiin vastaaminen aloitettu"
                counter = 0 #these cases are ignored
    contxs.append(cur_context) #finalize
    ac.append(context_hours)
    n_users += 1
    user_n.append(n_users)
    return pd.DataFrame({"exam": pd.Series(contxs), colname: pd.Series(ac), colname2: pd.Series(user_n)})

def plot_hours_spent_on_each_exam(
    conn,
    start_date: date,
    end_date: date,
    *,
    file_id: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    threshold: int = 0, 
    interval: int = 30
) -> pd.DataFrame:
    
    if start_date > end_date: #validate the start and end dates
        st.error("Invalid date range: start_date > end_date")
        return pd.DataFrame(columns=["user_id", "n"])
    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    
    names = ["Tenttivastaus palautettu", "Tenttiin vastaaminen aloitettu"] #we are only interested in exam start and end times
    ids = list(file_id) if file_id else [] #check which file_ids to include in the query

    params = {       
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    } #prepare query parameters
    df = pd.read_sql_query(HOURS_SPENT_ON_EACH_EXAM_SQL, conn, params=params) #execute query
    if len(df.index) <= 0: #no data
        return None
    
    df["ts"] = pd.to_datetime(df["ts"])
    df_plot = compute_total_hours_on_a_specific_exam(df, "total hours", "number of users") #perform computation
    df_plot["number of users"] = df_plot["number of users"].astype(int)
    df_plot = df_plot[df_plot["exam"] != "emptyrow"] #remove dummy rows
    df_plot["average hours spent per user"] = df_plot["total hours"]/df_plot["number of users"]
    df_plot = df_plot.drop(columns=["total hours", "number of users"])

    df_plot = df_plot.set_index("exam")[["average hours spent per user"]]
    st.bar_chart(df_plot, height=320, use_container_width=True)

    if show_table:
        with st.expander("Show aggregated counts", expanded=False):
            st.dataframe(df_plot, use_container_width=True)
    return df_plot

def plot_number_of_submissions_per_context(
    conn,
    start_date: date,
    end_date: date,
    *,
    file_id: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    threshold: int = 0, 
    interval: int = 30
) -> pd.DataFrame:
    
    if start_date > end_date: #validate the start and end dates
        st.error("Invalid date range: start_date > end_date")
        return pd.DataFrame(columns=["user_id", "n"])
    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    
    names = ["Tenttivastaus palautettu", "Palautus on lähetetty"] #we are only interested in submissions, be they exam or exercise submissions
    ids = list(file_id) if file_id else [] #check which file_ids to include in the query

    params = {       
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    } #prepare query parameters
    df = pd.read_sql_query(NUMBER_OF_SUBMISSIONS_PER_CONTEXT_SQL, conn, params=params) #execute query
    if len(df.index) <= 0: #no data
        return None
    
    df["submissions_n"] = df["submissions_n"].astype(int)
    df["users_n"] = df["users_n"].astype(int)
    df = df[df["users_n"] > 0] #to avoid dividing by zero
    df["average number of submissions per user"] = df["submissions_n"]/df["users_n"]

    df_plot = df.drop(columns=["users_n", "submissions_n"])
    df_plot = df_plot.set_index("context")[["average number of submissions per user"]]
    st.bar_chart(df_plot, height=320, use_container_width=True)

    if show_table:
        with st.expander("Show aggregated counts", expanded=False):
            st.dataframe(df_plot, use_container_width=True)
    return df_plot

def plot_portion_of_users_per_context(
    conn,
    start_date: date,
    end_date: date,
    *,
    file_id: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    threshold: int = 0, 
    interval: int = 30
) -> pd.DataFrame:
    
    if start_date > end_date: #validate the start and end dates
        st.error("Invalid date range: start_date > end_date")
        return pd.DataFrame(columns=["user_id", "n"])
    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    
    names = ["Tenttivastaus palautettu", "Palautus on lähetetty"] #we are only interested in submissions, be they exam or exercise submissions
    ids = list(file_id) if file_id else [] #check which file_ids to include in the query

    params = {       
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    } #prepare query parameters
    df = pd.read_sql_query(NUMBER_OF_UNIQUE_USERS_SQL, conn, params=params) #execute query
    if len(df.index) <= 0: #no data
        return None
    n = len(df.index) #total number of all users in the interval

    params = {       
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
    } #prepare query parameters
    df = pd.read_sql_query(NUMBER_OF_SUBMISSIONS_PER_CONTEXT_SQL, conn, params=params) #execute query
    if len(df.index) <= 0: #no data
        return None
    
    df["users_n"] = df["users_n"].astype(int)
    df["portion of users who submitted"] = df["users_n"]/n

    df_plot = df.drop(columns=["users_n", "submissions_n"])
    df_plot = df_plot.set_index("context")[["portion of users who submitted"]]
    st.bar_chart(df_plot, height=320, use_container_width=True)
    string = "Total number of users within the given time interval: "+str(n)
    st.caption(string)

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
            threshold=threshold,
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
            threshold=threshold,
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
            threshold=threshold,
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
    by_interval: bool = False, 
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

    df = df[df["n"] >= threshold]

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
    by_interval: bool = False,
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
    
    df = df[df["n"] >= threshold]

    chart_df = df.set_index("event_name")[["n"]]
    st.bar_chart(chart_df, height=320, use_container_width=True)

    return df


def plot_active_days_above_threshold(
    conn,
    start_date: date,
    end_date: date,
    event_names: Sequence[str] | None = None,
    *,
    threshold: int = 0,  
    by_interval: bool = False,
    file_ids: list[int] | None = None,
    show_table: bool = True
) -> pd.DataFrame:

    if start_date > end_date:
        st.error("Invalid date range: start_date > end_date")
        return pd.DataFrame(columns=["day", "n"])

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
        st.info("No activity data.")
        return df

    df = df.copy()
    df["day"] = pd.to_datetime(df["day"]).dt.date
    df["n"] = df["n"].astype(int)

    df_filtered = df[df["n"] > threshold]

    if df_filtered.empty:
        st.info(f"No days exceed threshold ({threshold}).")
        return df_filtered

    chart_df = df_filtered.set_index("day")[["n"]]

    st.bar_chart(chart_df, height=320, use_container_width=True)

    if show_table:
        with st.expander("Show filtered days", expanded=False):
            st.dataframe(df_filtered, use_container_width=True)

    return df_filtered


WEEKDAY_ACTIVITY_SQL = """
SELECT EXTRACT(DOW FROM ts) AS weekday, COUNT(*) AS n
FROM moodle.event
WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
  AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
  AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_ids)s) )
GROUP BY weekday
ORDER BY weekday;
"""

def plot_weekday_activity(
    conn,
    start_date: date,
    end_date: date,
    event_names: Sequence[str] | None = None,
    *,
    threshold: int = 0,
    file_ids: list[int] | None = None,
    show_table: bool = True,
    by_interval: bool = False,
    interval: int = 60 * 24   
) -> pd.DataFrame:

    if by_interval:
        df = compute_number_users_by_time_interval(
            conn,
            start_date,
            end_date,
            file_ids=file_ids,
            events=event_names,
            threshold=threshold,
            interval=interval
        )

        if df is None or df.empty:
            st.info("No weekday activity data.")
            return pd.DataFrame()

        df = df.copy()
        df["weekday"] = [i % 7 for i in df["x"]]

        df_grouped = df.groupby("weekday")["number_of_users"].mean().reset_index()

        weekday_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        df_grouped["weekday_name"] = df_grouped["weekday"].astype(int).map(lambda x: weekday_names[x])

        chart_df = df_grouped.set_index("weekday_name")[["number_of_users"]]
        st.bar_chart(chart_df, height=320, use_container_width=True)

        if show_table:
            with st.expander("Show aggregated counts", expanded=False):
                st.dataframe(df_grouped, use_container_width=True)

        return df_grouped

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)
    params = _build_params(start_ts, end_ts, event_names, file_ids)

    df = pd.read_sql_query(WEEKDAY_ACTIVITY_SQL, conn, params=params)

    if df.empty:
        st.info("No weekday activity data.")
        return df

    df["weekday"] = df["weekday"].astype(int)
    df["n"] = df["n"].astype(int)

    weekday_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    df["weekday_name"] = df["weekday"].map(lambda x: weekday_names[x])

    chart_df = df.set_index("weekday_name")[["n"]]
    st.bar_chart(chart_df, height=320, use_container_width=True)

    return df



USER_LAST_ACTIVITY_INTENSITY_SQL = """
WITH user AS 
(
    SELECT user_id, COUNT(*) AS activity, MAX(ts) AS latest_act
    FROM moodle.event
    WHERE ts >= %(start_ts)s AND ts < %(end_ts)s
        AND user_id IS NOT NULL
        AND ( %(use_event_filter)s = FALSE OR event_name = ANY(%(event_names)s) )
        AND ( %(use_file_scope)s = FALSE OR file_id = ANY(%(file_id)s ) )
    GROUP BY user_id
    HAVING COUNT(*) >= %(threshold)s
),

statistics AS 
(
    SELECT AVG(activity) AS ma, VAR_POP(activity) as var
    FROM user
)

SELECT 
    user.user_id, 
    user.latest_act, 
    (user.activity::float - statistics.ma) / NULLIF(SQRT(statistics.var), 0) AS intensity
FROM user
CROSS JOIN statistics
"""



def plot_last_activity_scatter(
    conn,
    start_date: date,
    end_date: date,
    event_names: Sequence[str] | None = None,
    *,
    threshold: int = 0,
    file_ids: list[int] | None = None,
    show_table: bool = True
) -> pd.DataFrame:

    if start_date > end_date:
        st.error("Invalid date range")
        return pd.DataFrame()

    start_ts, end_ts = _date_to_ts_range(start_date, end_date)

    names = list(event_names) if event_names else []
    ids = list(file_ids) if file_ids else []

    params = {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "use_event_filter": len(names) > 0,
        "event_names": names,
        "use_file_scope": len(ids) > 0,
        "file_id": ids,
        "threshold": threshold,
    }

    df = pd.read_sql_query(USER_LAST_ACTIVITY_INTENSITY_SQL, conn, params=params)

    if df.empty:
        st.info("No user activity data.")
        return df

    df = df.copy()
    df["latest_act"] = pd.to_datetime(df["latest_act"])
    df["intensity"] = df["intensity"].fillna(0)

    df["y"] = np.random.uniform(-0.05, 0.05, len(df))

    chart = alt.Chart(df).mark_circle(size=60).encode(
        x=alt.X("latest_act:T", title="Time (last activity)"),
        y=alt.Y("y:Q", axis=None),  
        color=alt.Color(
            "intensity:Q",
            scale=alt.Scale(scheme="viridis"),
            title="Activity intensity"
        ),
        tooltip=["user_id", "latest_act", "intensity"]
    ).properties(
        height=200
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    if show_table:
        with st.expander("Show user data", expanded=False):
            st.dataframe(df, use_container_width=True)

    return df
