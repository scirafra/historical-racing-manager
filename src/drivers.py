import os
import sys
from datetime import date
from typing import List

import numpy as np
import pandas as pd


class DriversModel:
    def __init__(self, ability_min: int = 36, ability_max: int = 69):
        self.drivers = pd.DataFrame()
        self.active_drivers = pd.DataFrame()
        self.retiring_drivers = pd.DataFrame()
        self.old_active_drivers = pd.DataFrame()
        self.dead_drivers: List[List] = []
        self.ability_min = ability_min
        self.ability_max = ability_max

        self.ability_change = [
            4,
            4,
            3,
            3,
            3,
            2,
            2,
            2,
            2,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            -1,
            -1,
            -1,
            -1,
            -1,
            -2,
            -2,
            -2,
            -2,
            -3,
            -3,
            -3,
            -4,
            -4,
            -5,
            -6,
            -7,
            -8,
            -9,
            -10,
            -11,
            -12,
            -13,
            -14,
            -15,
            -16,
            -17,
            -18,
            -19,
            -20,
        ]

    # ====== DATA I/O ======

    def load(self, folder: str) -> bool:
        path = os.path.join(folder, "drivers.csv")
        if not os.path.exists(path):
            return False

        self.drivers = pd.read_csv(path)
        self.ability_min = min(self.ability_min, self.drivers["ability_original"].min())
        self.active_drivers = pd.DataFrame(columns=self.drivers.columns)
        return True

    def save(self, folder: str) -> None:
        if not folder:
            return

        self.sort_active_drivers()
        self._sync_active_to_main()
        self.drivers.to_csv(os.path.join(folder, "drivers.csv"), index=False)
        self.old_active_drivers = self.active_drivers.copy()
        self.active_drivers.drop(self.active_drivers.index, inplace=True)

    def get_driver_id(self, driver_forename: str, driver_surname: str) -> int | None:
        result = self.drivers.query("forename == @driver_forename and surname == @driver_surname")
        return result["driverID"].iat[0] if not result.empty else None

    def get_drivers(self) -> pd.DataFrame:
        return (
            self.drivers[["driverID", "forename", "surname"]].copy()
            if not self.drivers.empty
            else pd.DataFrame(columns=["driverID", "forename", "surname"])
        )

    def _sync_active_to_main(self) -> None:
        self.drivers.set_index("driverID", inplace=True)
        self.active_drivers.set_index("driverID", inplace=True)
        self.drivers.update(self.active_drivers)
        self.drivers.reset_index(inplace=True)
        self.active_drivers.reset_index(inplace=True)

    # ====== ACTIVE DRIVER SELECTION ======

    def choose_active_drivers(self, current_date: date) -> pd.Series:
        if self.active_drivers.empty:
            self._initialize_active_drivers(current_date)
        else:
            self._update_active_driver_list(current_date)

        self.sort_active_drivers()
        self._check_duplicates()
        return self.active_drivers["driverID"]

    def _initialize_active_drivers(self, current_date: date) -> None:
        self._update_ages(self.drivers, current_date.year)
        self.active_drivers = self.drivers[
            (self.drivers["age"] >= 15)
            & (self.drivers["age"] <= self.drivers["retire"])
            & (self.drivers["alive"])
            ].copy()

    def _update_active_driver_list(self, current_date: date) -> pd.DataFrame:
        self._update_ages(self.drivers, current_date.year)
        self._update_ages(self.active_drivers, current_date.year)

        new_drivers = self.drivers[self.drivers["age"] == 15]

        if not self.retiring_drivers.empty:
            self.active_drivers = self.active_drivers[
                ~self.active_drivers["driverID"].isin(self.retiring_drivers["driverID"])
            ]

        self.retiring_drivers = self.active_drivers[
            (self.active_drivers["age"] > self.active_drivers["retire"])
            | (self.active_drivers["age"] < 15)
            ]

        if not new_drivers.empty:
            self.active_drivers = pd.concat([self.active_drivers, new_drivers], ignore_index=True)

        self.drivers.update(self.retiring_drivers.set_index("driverID"))
        return self.retiring_drivers

    def _update_ages(self, df: pd.DataFrame, year: int) -> None:
        df["age"] = year - df["year"]

    def sort_active_drivers(self) -> None:
        self.active_drivers = self.active_drivers.sort_values(
            by=["reputation_race", "year"], ascending=[False, True]
        ).reset_index(drop=True)

    def _check_duplicates(self) -> None:
        if self.active_drivers["driverID"].duplicated().any():
            sys.exit("Program terminated due to duplicate driverID.")

    def get_retiring_drivers(self) -> List[int]:
        return self.retiring_drivers["driverID"].tolist() if not self.retiring_drivers.empty else []

    # ====== DRIVER STATUS UPDATES ======

    def mark_drivers_dead(self, driver_ids: List[int], event_date: str) -> None:
        self.active_drivers.loc[self.active_drivers["driverID"].isin(driver_ids), "alive"] = False
        self.drivers.loc[self.drivers["driverID"].isin(driver_ids), "alive"] = False
        self.active_drivers = self.active_drivers[~self.active_drivers["driverID"].isin(driver_ids)]
        self.dead_drivers.append([event_date, driver_ids])

    def race_reputations(self, reputation: int, results: List[int]) -> None:
        for idx, driver_id in enumerate(results, start=1):
            self.active_drivers.loc[
                self.active_drivers["driverID"] == driver_id, "reputation_race"
            ] += (reputation // idx)

    def update_reputations(self) -> None:
        self.sort_active_drivers()
        self.active_drivers["reputation_race"] //= 2

    # ====== POSITION & ABILITY ======

    @staticmethod
    def reassign_positions(group: pd.DataFrame) -> pd.DataFrame:
        group = group.sort_values(by="position").reset_index(drop=True)
        group["position"] = range(1, len(group) + 1)
        return group

    def calculate_adjustment(self, row: pd.Series, position: str, target_year: int) -> int:
        index = target_year - row["year"]
        if index < 0 or index >= len(self.ability_change):
            return 0

        adjustment = self.ability_change[index]
        return (
            adjustment if position == "first" else adjustment - ["second", "third"].index(position)
        )

    def update_drivers(self, current_date: date) -> None:
        for offset in range(13):
            filtered = self._filter_adjustable_drivers(current_date.year, offset)
            if filtered.empty:
                continue

            filtered = self._assign_positions(filtered)
            filtered = self._apply_adjustments(filtered, current_date.year - 16)
            self._update_driver_abilities(filtered)

    def _filter_adjustable_drivers(self, year: int, offset: int) -> pd.DataFrame:
        age = year - self.active_drivers["year"]
        return (
            self.active_drivers[
                (age > (15 + 3 * offset))
                & (age < (19 + 3 * offset))
                & (self.active_drivers["ability"] > 35)
                ]
            .sort_values(by="reputation_race", ascending=False)
            .reset_index(drop=True)
        )

    def _assign_positions(self, df: pd.DataFrame) -> pd.DataFrame:
        n = len(df)
        a = n // 3
        remainder = n % 3
        a1 = 1 if remainder == 2 else 0
        a2 = 1 if remainder == 1 else 0
        positions = ["first"] * (a + a1) + ["second"] * (a + a2) + ["third"] * (n - 2 * a - a1 - a2)
        df["position"] = positions
        return df

    def _apply_adjustments(self, df: pd.DataFrame, target_year: int) -> pd.DataFrame:
        for i in range(len(df)):
            pos = df.loc[i, "position"]
            adj = self.calculate_adjustment(df.loc[i], pos, target_year)
            df.at[i, "ability"] += adj
        df["ability_best"] = df.apply(lambda row: max(row["ability"], row["ability_best"]), axis=1)
        return df.drop(columns=["position"])[["driverID", "ability", "ability_best"]]

    def _update_driver_abilities(self, updated: pd.DataFrame) -> None:
        self.active_drivers.set_index("driverID", inplace=True)
        updated.set_index("driverID", inplace=True)
        self.active_drivers.update(updated)
        self.active_drivers.reset_index(inplace=True)

    # ====== DRIVER CREATION ======
    @staticmethod
    def ability_distribution() -> list[int]:
        """
        Create a weighted list of abilities:
        69 once, 68 twice, 67 three times, ... down to 36.
        """
        distribution = []
        for ability in range(69, 35, -1):
            count = 70 - ability
            distribution.extend([ability] * count)
        return distribution

    @classmethod
    def generate_new_drivers(
            cls, year: int, count: int, df: pd.DataFrame, nationality_weights: pd.Series, id_offset: int
    ) -> pd.DataFrame:
        """Generate new drivers using weighted ability distribution."""
        new_drivers = []
        dist = cls.ability_distribution()

        for _ in range(count):
            nationality = np.random.choice(nationality_weights.index, p=nationality_weights.values)
            forename, surname = cls._sample_name_by_nationality(df, nationality)
            new_driver_id, id_offset = cls._generate_driver_id(df, id_offset)

            ability_value = dist.pop(0) if dist else np.random.randint(36, 70)

            new_drivers.append(
                cls._build_driver_dict(
                    new_driver_id, forename, surname, nationality, year, ability_value
                )
            )

        return pd.DataFrame(new_drivers)

    @staticmethod
    def _sample_name_by_nationality(df: pd.DataFrame, nationality: str) -> tuple[str, str]:
        names = df[df["nationality"] == nationality]
        return (names["forename"].sample(1).iat[0], names["surname"].sample(1).iat[0])

    @staticmethod
    def _generate_driver_id(df: pd.DataFrame, id_offset: int) -> tuple[int, int]:
        max_id = df["driverId"].max() if not df.empty else 0
        new_id = max_id + 1 + id_offset
        return new_id, id_offset + 1

    @staticmethod
    def _build_driver_dict(
            driver_id: int, forename: str, surname: str, nationality: str, year: int, ability: int
    ) -> dict:
        return {
            "driverID": driver_id,
            "forename": forename,
            "surname": surname,
            "year": year,
            "dob": f"{year}-01-01",
            "nationality": nationality,
            "alive": True,
            "ability": ability,
            "ability_original": ability,
            "ability_best": ability,
            "reputation_race": 0,
            "reputation_season": 0,
            "retire": np.random.randint(30, 59),
        }
