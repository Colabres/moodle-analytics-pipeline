import pandas as pd
import numpy as np
import datetime as dt

def compute_earlier_and_later_submission_activity(df:pd.DataFrame, file_ids, event_names:pd.DataFrame, per_day:bool=False, first_portion:float=1/4):
    """
    Note: the datatype of "timestamp" column in "df" is assumed to be datetime

    Inputs:
       df: pandas Dataframe of all moodle activity
       file_ids: numpy array or list of all course ids to be included
       event_names: Dataframe containing event names and their corresponding ids
       per_day: boolean designating whether or not to average over days, default False
       first_portion: a float in exclusive range [0, 1] designating the portion of overall course duration to be designated for early activity, default 1/4 == 0.25
    
    Outputs:
       earlier_activity: numpy array of earlier submission activity
       later_activity: numpy array of later submission activity
    """
    if first_portion >= 1 or first_portion <= 0:
        raise ValueError("Input 'first portion' must be in exclusive range [0, 1]")
    event_name_ids_df = event_names[event_names["name"].isin(["Tenttivastaus palautettu", "Palautus on lähetetty"])]
    event_name_ids = event_name_ids_df["id"].unique()
    df1 = df[df["event_name_id"].isin(event_name_ids)]
    earlier_activity = np.empty(shape=0)
    later_activity = np.empty(shape=0)
    for course_id in file_ids:
        activity = df1[df1["file_id"] == course_id]
        neljannes = ((activity["timestamp"].max()-activity["timestamp"].min()))*first_portion
        early = activity[activity["timestamp"]-activity["timestamp"].min() <= neljannes]
        later = activity[activity["timestamp"]-activity["timestamp"].min() > neljannes]
        user_ids = activity["user_id"].unique()
        for i in user_ids:
            early_activity = len(early[early["user_id"] == i].index)
            later_activity = len(later[later["user_id"] == i].index)
            if per_day:
                earlier_activity = np.append(earlier_activity, early_activity/neljannes.days)
                later_activity = np.append(later_activity, later_activity/((activity["timestamp"].max()-activity["timestamp"].min()).days-neljannes.days))
            else:
                earlier_activity = np.append(earlier_activity, early_activity)
                later_activity = np.append(later_activity, later_activity)
    return earlier_activity, later_activity


if __name__ == "__main__":
    print("Hello")