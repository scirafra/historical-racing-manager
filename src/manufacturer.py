import os

import numpy as np
import pandas as pd

import contracts as co

car_parts = pd.DataFrame()
car_part_models = pd.DataFrame()
cars = pd.DataFrame()
manufacturers = pd.DataFrame()
rules = pd.DataFrame()


def load(name):
    global car_parts
    global cars
    global manufacturers
    global car_part_models
    global rules

    car_parts = pd.DataFrame(columns=car_parts.columns)
    cars = pd.DataFrame(columns=cars.columns)
    manufacturers = pd.DataFrame(columns=manufacturers.columns)
    car_part_models = pd.DataFrame(columns=car_part_models.columns)
    rules = pd.DataFrame(columns=rules.columns)
    if not os.path.exists(name + "car_parts.csv"):
        return False
    if not os.path.exists(name + "cars.csv"):
        return False
    if not os.path.exists(name + "manufacturers.csv"):
        return False
    if not os.path.exists(name + "car_part_models.csv"):
        return False
    if not os.path.exists(name + "rules.csv"):
        return False
    car_parts = pd.read_csv(name + "car_parts.csv")
    cars = pd.read_csv(name + "cars.csv")
    manufacturers = pd.read_csv(name + "manufacturers.csv")
    car_part_models = pd.read_csv(name + "car_part_models.csv")
    rules = pd.read_csv(name + "rules.csv")
    return True


def save(name):
    if len(name) > 0:
        car_parts.to_csv(name + "car_parts.csv", index=False)
        cars.to_csv(name + "cars.csv", index=False)
        manufacturers.to_csv(name + "manufacturers.csv", index=False)
        car_part_models.to_csv(name + "car_part_models.csv", index=False)
        rules.to_csv(name + "rules.csv", index=False)


def develop_part(dat):
    global car_parts

    merged = pd.merge(
        co.MScontract,
        rules,
        left_on=["seriesID", "partType"],
        right_on=["seriesID", "partType"],
        how="left",
    )
    merged = merged[
        (merged["startYear"] <= dat.year)
        & (merged["startSeason"] <= dat.year)
        & (merged["endYear"] >= dat.year)
        & (merged["endSeason"] >= dat.year)
    ]

    filtered_parts = car_parts[car_parts["year"] == dat.year - 1]

    final_merged = pd.merge(
        merged, filtered_parts, how="left", on=["rulesID", "manufacturerID", "partType", "seriesID"]
    )
    final_merged["power"] = final_merged["power"].fillna(final_merged["minA"])
    final_merged["reliability"] = final_merged["reliability"].fillna(1)
    final_merged["safety"] = final_merged["safety"].fillna(1)
    random_power = np.random.randint(0, 9, size=len(final_merged))
    random_reliability = np.random.randint(0, 10, size=len(final_merged))
    random_safety = np.random.randint(0, 10, size=len(final_merged))

    final_merged["rand_power"] = random_power
    final_merged["power"] += random_power
    final_merged["reliability"] += random_power - random_reliability
    final_merged["safety"] += random_power - random_safety
    final_merged["year"] = dat.year

    final_merged["power"] = final_merged[["power", "minA"]].max(axis=1)

    final_merged["power"] = final_merged[["power", "maxA"]].min(axis=1)
    final_merged["reliability"] = final_merged["reliability"].apply(lambda x: 1 if x < 1 else x)
    final_merged["safety"] = final_merged["safety"].apply(lambda x: 1 if x < 1 else x)
    final_merged["cost"] = 250000
    done = final_merged[
        [
            "partID",
            "partType",
            "manufacturerID",
            "rulesID",
            "seriesID",
            "power",
            "reliability",
            "safety",
            "year",
            "cost",
        ]
    ]
    max_part_id = car_parts["partID"].max()

    max_part_id = max(0, max_part_id)

    done.loc[:, "partID"] = range(max_part_id + 1, max_part_id + 1 + len(done))

    car_parts = pd.concat([car_parts, done], ignore_index=True)
