import pandas as pd
import matplotlib.pyplot as plt

def add_time_columns(df):
   
    df = df.copy()

    df["päivä"] = df["ts"].dt.date
    df["tunti"] = df["ts"].dt.hour
    df["viikko"] = df["ts"].dt.isocalendar().week

    return df


def plot_hourly_activity(df):
    hourly_activity = df.groupby("tunti").size()

    plt.figure(figsize=(10,5))
    hourly_activity.plot(kind="bar")
    plt.title("Moodle-aktiviteetit tunneittain")
    plt.xlabel("Tunti")
    plt.ylabel("Tapahtumien määrä")
    plt.tight_layout()
    plt.show()

    return hourly_activity


def plot_weekly_activity(df):
    weekly_activity = df.groupby("viikko").size()

    plt.figure(figsize=(10,5))
    weekly_activity.plot()
    plt.title("Moodle-aktiviteetit viikoittain")
    plt.xlabel("Viikko")
    plt.ylabel("Tapahtumien määrä")

    plt.xticks(range(int(weekly_activity.index.min()),
                     int(weekly_activity.index.max()) + 1,5))

    plt.tight_layout()
    plt.show()

    return weekly_activity


def plot_component_distribution(df):
    component_percent = (
        df["component"]
        .value_counts(normalize=True)
        .mul(100)
        .round(1)
        .sort_values()
    )

    plt.figure(figsize=(10,6))
    component_percent.plot(kind="barh")
    plt.xlabel("Osuus kaikista tapahtumista (%)")
    plt.title("Tapahtumien jakauma komponenteittain")
    plt.tight_layout()
    plt.show()

    return component_percent


def plot_top_events(df, top_n=10):
    top_events = (
        df["event_name"]
        .value_counts()
        .head(top_n)
        .sort_values()
    )

    plt.figure(figsize=(10,6))
    top_events.plot(kind="barh")
    plt.xlabel("Tapahtumien määrä")
    plt.title(f"{top_n} yleisintä tapahtumatyyppiä")
    plt.tight_layout()
    plt.show()

    return top_events


