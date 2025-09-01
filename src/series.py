import os

import pandas as pd

series = pd.DataFrame()
point_rules = pd.DataFrame()


def load(name):
    global series
    global point_rules

    series = pd.DataFrame(columns=series.columns)
    point_rules = pd.DataFrame(columns=point_rules.columns)
    if not os.path.exists(name + "series.csv"):
        return False
    if not os.path.exists(name + "point_rules.csv"):
        return False
    series = pd.read_csv(name + "series.csv")
    point_rules = pd.read_csv(name + "point_rules.csv")

    return True


def save(name):
    if len(name) > 0:
        series.to_csv(name + "series.csv", index=False)
        point_rules.to_csv(name + "point_rules.csv", index=False)


def get_series():
    df = series[["seriesID", "name"]].copy()

    return df.reset_index(drop=True)


def get_series_id(series_name):
    result = series[series["name"] == series_name]
    if not result.empty:

        return int(result["seriesID"].values[0])
    else:
        return None
