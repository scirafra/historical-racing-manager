import os

import numpy as np
import pandas as pd


class ManufacturerModel:
    def __init__(self):
        self.car_parts = pd.DataFrame()
        self.car_part_models = pd.DataFrame()
        self.cars = pd.DataFrame()
        self.manufacturers = pd.DataFrame()
        self.rules = pd.DataFrame()

    # --- Persistence ---
    def load(self, folder: str) -> bool:
        """Load manufacturer-related data from CSV files if they exist."""
        required_files = [
            "car_parts.csv",
            "cars.csv",
            "manufacturers.csv",
            "car_part_models.csv",
            "rules.csv",
        ]
        for file in required_files:
            if not os.path.exists(os.path.join(folder, file)):
                return False

        self.car_parts = pd.read_csv(os.path.join(folder, "car_parts.csv"))
        self.cars = pd.read_csv(os.path.join(folder, "cars.csv"))
        self.manufacturers = pd.read_csv(os.path.join(folder, "manufacturers.csv"))
        self.car_part_models = pd.read_csv(os.path.join(folder, "car_part_models.csv"))
        self.rules = pd.read_csv(os.path.join(folder, "rules.csv"))
        print(self.car_parts)
        return True

    def save(self, folder: str):
        """Save manufacturer-related data to CSV files."""
        if folder:
            self.car_parts.to_csv(os.path.join(folder, "car_parts.csv"), index=False)
            self.cars.to_csv(os.path.join(folder, "cars.csv"), index=False)
            self.manufacturers.to_csv(os.path.join(folder, "manufacturers.csv"), index=False)
            self.car_part_models.to_csv(os.path.join(folder, "car_part_models.csv"), index=False)
            self.rules.to_csv(os.path.join(folder, "rules.csv"), index=False)

    # --- Business logic ---
    def develop_part(self, date, contracts: pd.DataFrame):
        """
        Develop new car parts for the given year based on contracts and rules.
        Randomly adjusts power, reliability, and safety within defined limits.
        """
        # Merge contracts with rules
        merged = pd.merge(
            contracts,
            self.rules,
            on=["seriesID", "partType"],
            how="left",
        )

        # Filter by active years
        merged = merged[
            (merged["startYear"] <= date.year)
            & (merged["startSeason"] <= date.year)
            & (merged["endYear"] >= date.year)
            & (merged["endSeason"] >= date.year)
        ]

        # Get last year's parts
        filtered_parts = self.car_parts[self.car_parts["year"] == date.year - 1]

        # Merge with last year's parts
        final_merged = pd.merge(
            merged,
            filtered_parts,
            how="left",
            on=["rulesID", "manufacturerID", "partType", "seriesID"],
        )

        # Fill missing values
        final_merged["power"] = final_merged["power"].fillna(final_merged["minA"])
        final_merged["reliability"] = final_merged["reliability"].fillna(1)
        final_merged["safety"] = final_merged["safety"].fillna(1)

        # Random improvements
        random_power = np.random.randint(0, 9, size=len(final_merged))
        random_reliability = np.random.randint(0, 10, size=len(final_merged))
        random_safety = np.random.randint(0, 10, size=len(final_merged))

        final_merged["rand_power"] = random_power
        final_merged["power"] += random_power
        final_merged["reliability"] += random_power - random_reliability
        final_merged["safety"] += random_power - random_safety
        final_merged["year"] = date.year

        # Clamp values to min/max
        final_merged["power"] = final_merged[["power", "minA"]].max(axis=1)
        final_merged["power"] = final_merged[["power", "maxA"]].min(axis=1)
        final_merged["reliability"] = final_merged["reliability"].apply(lambda x: max(1, x))
        final_merged["safety"] = final_merged["safety"].apply(lambda x: max(1, x))

        # Set cost
        final_merged["cost"] = 250000

        # Prepare final DataFrame
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

        # Assign new part IDs
        max_part_id = self.car_parts["partID"].max()
        max_part_id = max(0, max_part_id)
        done.loc[:, "partID"] = range(max_part_id + 1, max_part_id + 1 + len(done))

        # Append to car_parts
        self.car_parts = pd.concat([self.car_parts, done], ignore_index=True)
