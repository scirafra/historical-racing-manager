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
        required_files = [
            "car_parts.csv",
            "cars.csv",
            "manufacturers.csv",
            "car_part_models.csv",
            "rules.csv",
        ]
        missing = [f for f in required_files if not os.path.exists(os.path.join(folder, f))]
        if missing:
            self._initialize_empty()
            return False

        self.car_parts = pd.read_csv(os.path.join(folder, "car_parts.csv"))
        self.cars = pd.read_csv(os.path.join(folder, "cars.csv"))
        self.manufacturers = pd.read_csv(os.path.join(folder, "manufacturers.csv"))
        self.car_part_models = pd.read_csv(os.path.join(folder, "car_part_models.csv"))
        self.rules = pd.read_csv(os.path.join(folder, "rules.csv"))
        return True

    def save(self, folder: str):
        self.car_parts.to_csv(os.path.join(folder, "car_parts.csv"), index=False)
        self.cars.to_csv(os.path.join(folder, "cars.csv"), index=False)
        self.manufacturers.to_csv(os.path.join(folder, "manufacturers.csv"), index=False)
        self.car_part_models.to_csv(os.path.join(folder, "car_part_models.csv"), index=False)
        self.rules.to_csv(os.path.join(folder, "rules.csv"), index=False)

    def _initialize_empty(self):
        self.car_parts = pd.DataFrame()
        self.cars = pd.DataFrame()
        self.manufacturers = pd.DataFrame()
        self.car_part_models = pd.DataFrame()
        self.rules = pd.DataFrame()

    # --- Business logic ---
    def develop_part(self, date, contracts: pd.DataFrame):

        merged = self._merge_contracts_with_rules(contracts, date.year)

        last_year_parts = self.car_parts[self.car_parts["year"] == date.year - 1].copy()

        # Zjednotenie typov kľúčov pred merge
        merge_keys = ["rulesID", "manufacturerID", "partType", "seriesID"]
        for key in merge_keys:
            if key in merged.columns:
                merged[key] = merged[key].astype(str)
            if key in last_year_parts.columns:
                last_year_parts[key] = last_year_parts[key].astype(str)

        final = pd.merge(
            merged,
            last_year_parts,
            how="left",
            on=merge_keys,
        )

        final = self._fill_missing_values(final)
        final = self._apply_random_improvements(final, date.year)
        final = self._clamp_values(final)
        final["cost"] = 250000

        new_parts = final[
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
        ].copy()
        new_parts.loc[:, "partID"] = self._generate_new_part_ids(len(new_parts))

        self.car_parts = pd.concat([self.car_parts, new_parts], ignore_index=True)

    def get_manufacturers(self) -> pd.DataFrame:
        return (
            self.manufacturers[["manufacturerID", "name"]].copy()
            if not self.manufacturers.empty
            else pd.DataFrame(columns=["manufacturerID", "name"])
        )

    def get_manufacturers_id(self, manufacturer_name: str) -> int | None:
        result = self.manufacturers.query("name == @manufacturer_name")
        return result["manufacturerID"].iat[0] if not result.empty else None

    def _merge_contracts_with_rules(self, contracts: pd.DataFrame, year: int) -> pd.DataFrame:

        merged = pd.merge(contracts, self.rules, on=["seriesID", "partType"], how="left")
        mask = (
                (merged["startYear"] <= year)
                & (merged["startSeason"] <= year)
                & (merged["endYear"] >= year)
                & (merged["endSeason"] >= year)
        )
        return merged.loc[mask].copy()

    def _fill_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        df["power"] = df["power"].fillna(df["min_ability"])
        df["reliability"] = df["reliability"].fillna(1)
        df["safety"] = df["safety"].fillna(1)
        return df

    def _apply_random_improvements(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        rand_power = np.random.randint(0, 9, size=len(df))
        rand_reliability = np.random.randint(0, 10, size=len(df))
        rand_safety = np.random.randint(0, 10, size=len(df))

        df["power"] += rand_power
        df["reliability"] += rand_power - rand_reliability
        df["safety"] += rand_power - rand_safety
        df["year"] = year
        return df

    def _clamp_values(self, df: pd.DataFrame) -> pd.DataFrame:
        df["power"] = df[["power", "min_ability"]].max(axis=1)
        df["power"] = df[["power", "max_ability"]].min(axis=1)
        df["reliability"] = df["reliability"].apply(lambda x: max(1, x))
        df["safety"] = df["safety"].apply(lambda x: max(1, x))
        return df

    def _generate_new_part_ids(self, count: int) -> range:
        if self.car_parts.empty or self.car_parts["partID"].isnull().all():
            start = 0
        else:
            try:
                max_id = pd.to_numeric(self.car_parts["partID"], errors="coerce").max()
                start = int(max_id) + 1 if pd.notna(max_id) else 0
            except Exception:
                start = 0
        return range(start, start + count)
