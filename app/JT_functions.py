import pandas as pd
import numpy as np
import datetime as dt

def compute_earlier_and_later_submission_activity(df:pd.DataFrame, file_ids, per_day:bool=False, first_portion:float=1/4):
    """
    Note: the datatype of "ts" column in "df" is assumed to be datetime

    Inputs:
       df: pandas Dataframe of all moodle activity
       file_ids: numpy array or list of all course ids to be included
       per_day: boolean designating whether or not to average over days, default False
       first_portion: a float in exclusive range [0, 1] designating the portion of overall course duration to be designated for early activity, default 1/4 == 0.25
    
    Outputs:
       earlier_activity: numpy array of earlier submission activity
       later_activity: numpy array of later submission activity
    """
    if first_portion >= 1 or first_portion <= 0:
        raise ValueError("Input 'first portion' must be in exclusive range [0, 1]")
    df1 = df[df["description"].isin(["Tenttivastaus palautettu", "Palautus on lähetetty"])]
    earlier_activity = np.empty(shape=0)
    later_activity = np.empty(shape=0)
    for course_id in file_ids:
        activity = df1[df1["file_id"] == course_id]
        neljannes = ((activity["ts"].max()-activity["ts"].min()))*first_portion
        early = activity[activity["ts"]-activity["ts"].min() <= neljannes]
        later = activity[activity["ts"]-activity["ts"].min() > neljannes]
        user_ids = activity["user_id"].unique()
        for i in user_ids:
            early_activity = len(early[early["user_id"] == i].index)
            late_activity = len(later[later["user_id"] == i].index)
            if per_day:
                earlier_activity = np.append(earlier_activity, early_activity/neljannes.days)
                later_activity = np.append(later_activity, late_activity/((activity["ts"].max()-activity["ts"].min()).days-neljannes.days))
            else:
                earlier_activity = np.append(earlier_activity, early_activity)
                later_activity = np.append(later_activity, late_activity)
    return earlier_activity, later_activity

def compute_earlier_and_later_time_spent_on_exams(df:pd.DataFrame, file_ids, first_portion:float=1/4):
    """
    Note: the datatype of "ts" column in "df" is assumed to be datetime

    Inputs:
       df: pandas Dataframe of all moodle activity
       file_ids: numpy array or list of all course ids to be included
       per_day: boolean designating whether or not to average over days, default False
       first_portion: a float in exclusive range [0, 1] designating the portion of overall course duration to be designated for early activity, default 1/4 == 0.25
    
    Outputs:
       earlier_activity: numpy array of earlier time spent on exams
       later_activity: numpy array of later time spent on exams
    """
    if first_portion >= 1 or first_portion <= 0:
        raise ValueError("Input 'first portion' must be in exclusive range [0, 1]")
    df1 = df[df["description"].isin(["Tenttivastaus palautettu", "Tenttiin vastaaminen aloitettu"])]
    earlier_activity = np.empty(shape=0)
    later_activity = np.empty(shape=0)
    for course_id in file_ids:
        activity = df1[df1["file_id"] == course_id]
        neljannes = ((activity["ts"].max()-activity["ts"].min()))*first_portion
        early = activity[activity["ts"]-activity["ts"].min() <= neljannes]
        later = activity[activity["ts"]-activity["ts"].min() > neljannes]
        user_ids = activity["user_id"].unique()
        for i in user_ids:
            early_activity = early[early["user_id"] == i].sort_values(by=["ts"]).to_numpy()
            late_activity = later[later["user_id"] == i].sort_values(by=["ts"]).to_numpy()
            counter = 0
            start_time = None
            for l in early_activity:
                if l[7] == "Tenttiin vastaaminen aloitettu":#Kuvaus
                    if counter == 0:
                        start_time = dt.datetime(l[2])
                    counter += 1
                else:
                    counter -= 1
                    if counter == 0:
                        earlier_activity = np.append(earlier_activity, (dt.datetime(l[2])-start_time).total_seconds()/3600)
                        start_time = None
            for l in late_activity:
                if l[7] == "Tenttiin vastaaminen aloitettu":#Kuvaus
                    if counter == 0:
                        start_time = dt.datetime(l[2])
                    counter += 1
                else:
                    counter -= 1
                    if counter == 0:
                        later_activity = np.append(later_activity, (dt.datetime(l[2])-start_time).total_seconds()/3600)
                        start_time = None
    return earlier_activity, later_activity

if __name__ == "__main__":
    print("Hello")