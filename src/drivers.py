import os
import sys
from datetime import date
from typing import List

import numpy as np
import pandas as pd


class DriversModel:
    """
    Manages driver-related data using pandas DataFrames.
    Encapsulates loading, saving, updating, and selecting drivers.
    """

    def __init__(self, ability_min: int = 36, ability_max: int = 69):
        self.drivers = pd.DataFrame()
        self.active_drivers = pd.DataFrame()
        self.old_active_drivers = pd.DataFrame()
        self.dead_drivers: list = []
        self.ability_min = ability_min
        self.ability_max = ability_max

        # Ability change table (index = years since start)
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
        ]

    # ====== DATA I/O ======

    def load(self, folder: str) -> bool:
        """Load drivers from CSV and set minimum ability."""
        file_path = os.path.join(folder, "drivers.csv")
        if not os.path.exists(file_path):
            return False

        self.drivers = pd.read_csv(file_path)
        self.ability_min = min(self.ability_min, self.drivers["ability_original"].min())
        self.active_drivers = pd.DataFrame(columns=self.drivers.columns)
        return True

    def save(self, folder: str):
        """Save current drivers to CSV."""
        if not folder:
            return

        self.sort_active_drivers()

        # Update main drivers table from active drivers
        self.drivers = self.drivers.set_index("driverID")
        self.active_drivers = self.active_drivers.set_index("driverID")
        self.drivers.update(self.active_drivers)

        # Reset indexes for saving
        self.drivers.reset_index(inplace=True)
        self.active_drivers.reset_index(inplace=True)
        self.drivers.to_csv(os.path.join(folder, "drivers.csv"), index=False)

        # Store current state as old
        self.old_active_drivers = self.active_drivers.copy()
        self.active_drivers.drop(self.active_drivers.index, inplace=True)

    # ====== ACTIVE DRIVER SELECTION ======

    def choose_active_drivers(self, current_date: date) -> pd.Series:
        """Select active drivers for the current season."""
        if self.active_drivers.empty:
            self._initialize_active_drivers(current_date)
        else:
            self._update_active_driver_list(current_date)

        self.sort_active_drivers()
        self._check_duplicates()
        return self.active_drivers["driverID"]

    def _initialize_active_drivers(self, current_date: date):
        """First-time active driver selection."""
        print("Init ", current_date.year)
        self.drivers["age"] = current_date.year - self.drivers["year"]

        self.active_drivers = self.drivers[
            (self.drivers["age"] >= 15)
            # & (self.drivers["ability"] >= self.ability_min)
            & (self.drivers["age"] <= self.drivers["retire"])
            & (self.drivers["alive"])
            ].copy()

        print("Init self.active_drivers", self.active_drivers)

    def _update_active_driver_list(self, current_date: date):
        """Add rookies and remove retirees."""
        print("Update ", current_date.year)
        self.drivers["age"] = current_date.year - self.drivers["year"]
        self.active_drivers["age"] = current_date.year - self.active_drivers["year"]

        # Noví jazdci
        new_drivers = self.drivers[self.drivers["age"] == 15]
        print("Update new_drivers", new_drivers)

        # Odchod do dôchodku alebo neplatní jazdci
        retired_drivers = self.active_drivers[
            (self.active_drivers["age"] > self.active_drivers["retire"])
            | (self.active_drivers["age"] < 15)
            # | (self.active_drivers["ability"] < self.ability_min)
            # | (~self.active_drivers["alive"])
            ]
        print("Update retired_drivers", retired_drivers, self.ability_min)

        # Odstrániť dôchodcov
        self.active_drivers = self.active_drivers[
            ~self.active_drivers["driverID"].isin(retired_drivers["driverID"])
        ]

        # Pridať nových
        if not new_drivers.empty:
            self.active_drivers = pd.concat([self.active_drivers, new_drivers], ignore_index=True)

        # Update v hlavnom DF
        self.drivers.update(retired_drivers.set_index("driverID"))

        return retired_drivers

    def sort_active_drivers(self):
        """Sort active drivers by race reputation and year."""
        self.active_drivers = self.active_drivers.sort_values(
            by=["reputation_race", "year"], ascending=[False, True]
        ).reset_index(drop=True)

    def _check_duplicates(self):
        """Ensure there are no duplicate driver IDs."""
        if self.active_drivers["driverID"].duplicated().any():
            sys.exit("Program terminated due to duplicate driverID.")

    # ====== DRIVER STATUS UPDATES ======

    def mark_drivers_dead(self, driver_ids: List[int], event_date: str):
        """Mark drivers as deceased and remove them from active list."""
        self.active_drivers.loc[self.active_drivers["driverID"].isin(driver_ids), "alive"] = False
        self.drivers.loc[self.drivers["driverID"].isin(driver_ids), "alive"] = False
        self.active_drivers = self.active_drivers[~self.active_drivers["driverID"].isin(driver_ids)]
        self.dead_drivers.append([event_date, driver_ids])

    def race_reputations(self, reputation: int, results: List[int]):
        """Update race reputation for drivers after a race."""
        for idx, driver_id in enumerate(results, start=1):
            self.active_drivers.loc[
                self.active_drivers["driverID"] == driver_id, "reputation_race"
            ] += (reputation // idx)

    def update_reputations(self):
        """Halve the race reputation for all active drivers."""
        self.sort_active_drivers()
        self.active_drivers["reputation_race"] //= 2

    # ====== POSITION & ABILITY ======

    @staticmethod
    def reassign_positions(group: pd.DataFrame) -> pd.DataFrame:
        """Renumber driver positions from 1 to N within group."""
        group = group.sort_values(by="position").reset_index(drop=True)
        group["position"] = range(1, len(group) + 1)
        return group

    def calculate_adjustment(self, row: pd.Series, position: str, target_year: int) -> int:
        """Calculate ability adjustment based on driver age and position."""
        index = target_year - row["year"]
        if index < 0 or index >= len(self.ability_change):
            return 0

        adjustment = self.ability_change[index]
        if position == "first":
            return adjustment
        elif position == "second":
            return adjustment - 1
        elif position == "third":
            return adjustment - 2
        return 0

    def update_drivers(self, current_date: date):
        """Apply yearly ability adjustments for active drivers."""
        for offset in range(13):
            filtered = self.active_drivers[
                (current_date.year - self.active_drivers["year"] > (15 + 3 * offset))
                & (current_date.year - self.active_drivers["year"] < (19 + 3 * offset))
                & (self.active_drivers["ability"] > 35)
                ]
            if filtered.empty:
                continue

            filtered = filtered.sort_values(by="reputation_race", ascending=False).reset_index(
                drop=True
            )

            n = len(filtered)
            a = n // 3
            remainder = n % 3

            a1 = 1 if remainder == 2 else 0
            a2 = 1 if remainder == 1 else 0

            positions = (
                    ["first"] * (a + a1) + ["second"] * (a + a2) + ["third"] * (n - 2 * a - a1 - a2)
            )
            filtered["position"] = positions

            for i in range(len(filtered)):
                pos = filtered.loc[i, "position"]
                adj = self.calculate_adjustment(filtered.loc[i], pos, current_date.year - 16)
                filtered.at[i, "ability"] += adj
                filtered["ability_best"] = filtered.apply(
                    lambda row: max(row["ability"], row["ability_best"]), axis=1
                )

            filtered.drop(columns=["position"], inplace=True)
            filtered = filtered[["driverID", "ability", "ability_best"]]
            self.active_drivers.set_index("driverID", inplace=True)
            filtered.set_index("driverID", inplace=True)
            self.active_drivers.update(filtered)
            self.active_drivers.reset_index(inplace=True)
            print(current_date.year)
            with pd.option_context("display.max_rows", None, "display.max_columns", None):
                print(self.active_drivers)

    # ====== DRIVER CREATION ======

    @staticmethod
    def ability_distribution() -> list[int]:
        """
        Create a weighted list of abilities:
        69 once, 68 twice, 67 three times, ... down to 36.
        """
        distribution = []
        for ability in range(69, 35, -1):  # from 69 down to 36 inclusive
            count = 70 - ability  # e.g. 69->1, 68->2, ...
            distribution.extend([ability] * count)
        return distribution

    @classmethod
    def generate_new_drivers(
            cls, year: int, count: int, df: pd.DataFrame, nationality_weights: pd.Series, id_offset: int
    ) -> pd.DataFrame:
        """
        Generate new drivers using the fixed ability distribution.
        """
        new_drivers = []
        dist = cls.ability_distribution()

        for _ in range(count):
            nationality = np.random.choice(nationality_weights.index, p=nationality_weights.values)
            forename = df[df["nationality"] == nationality]["forename"].sample(1).iat[0]
            surname = df[df["nationality"] == nationality]["surname"].sample(1).iat[0]

            new_driver_id = (df["driverId"].max() + 1 + id_offset) if not df.empty else 1
            id_offset += 1

            # Pick ability from pre-made weighted list
            ability_value = dist.pop(0) if dist else np.random.choice(range(36, 70))

            new_drivers.append(
                {
                    "driverID": new_driver_id,
                    "forename": forename,
                    "surname": surname,
                    "year": year,
                    "dob": f"{year}-01-01",
                    "nationality": nationality,
                    "alive": True,
                    "ability": ability_value,
                    "ability_original": ability_value,
                    "ability_best": ability_value,
                    "reputation_race": 0,
                    "reputation_season": 0,
                    "retire": np.random.randint(34, 42),
                }
            )

        return pd.DataFrame(new_drivers)
