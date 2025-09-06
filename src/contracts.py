import os
import random

import numpy as np
import pandas as pd


class ContractsModel:
    def __init__(self):
        self.DTcontract = pd.DataFrame()
        self.STcontract = pd.DataFrame()
        self.CScontract = pd.DataFrame()
        self.MScontract = pd.DataFrame()
        self.MTcontract = pd.DataFrame()

    # --- Persistence ---
    def load(self, folder: str) -> bool:
        """Load all contract-related CSVs."""
        try:
            self.DTcontract = pd.read_csv(os.path.join(folder, "DTcontract.csv"))
            self.STcontract = pd.read_csv(os.path.join(folder, "STcontract.csv"))
            self.CScontract = pd.read_csv(os.path.join(folder, "CScontract.csv"))
            self.MScontract = pd.read_csv(os.path.join(folder, "MScontract.csv"))
            self.MTcontract = pd.read_csv(os.path.join(folder, "MTcontract.csv"))

            # Ensure required columns exist
            self._ensure_columns(
                self.DTcontract,
                {
                    "driverID": None,
                    "teamID": None,
                    "salary": 0,
                    "wanted_reputation": 0,
                    "startYear": 0,
                    "endYear": 0,
                    "active": True,
                },
            )

            return True
        except Exception as e:
            print("Contract load failed:", e)
            return False

    def save(self, folder: str):
        """Save all contract-related CSVs."""
        self.DTcontract.to_csv(os.path.join(folder, "DTcontract.csv"), index=False)
        self.STcontract.to_csv(os.path.join(folder, "STcontract.csv"), index=False)
        self.CScontract.to_csv(os.path.join(folder, "CScontract.csv"), index=False)
        self.MScontract.to_csv(os.path.join(folder, "MScontract.csv"), index=False)
        self.MTcontract.to_csv(os.path.join(folder, "MTcontract.csv"), index=False)

    def _ensure_columns(self, df, required: dict):
        """Ensure DataFrame has all required columns."""
        for col, default in required.items():
            if col not in df.columns:
                df[col] = default

    # --- Business logic ---
    def disable_driver_contracts(self, driver_ids):
        """Deactivate contracts for given driver IDs."""
        self._ensure_columns(self.DTcontract, {"active": True})
        for d in driver_ids:
            self.DTcontract.loc[self.DTcontract["driverID"] == d, "active"] = False

    def get_MScontract(self):
        """Return manufacturer-series contracts."""
        return self.MScontract

    def sign_driver_contracts(
        self,
        active_series: pd.DataFrame,
        teams_model,
        date,
        active_drivers: pd.DataFrame,
        rules: pd.DataFrame,
        temp: bool,
        teams: pd.DataFrame,
        team_inputs: dict,  # {teamID: (driverID, salary, contract_length)} or None
    ):
        """
        Sign driver contracts for active series and teams.

        Args:
            active_series: DataFrame of active series.
            teams_model: TeamsModel instance.
            date: Current simulation date.
            active_drivers: DataFrame of available drivers.
            rules: Point rules for current year.
            temp: If True, contracts are temporary (maxLen = 1).
            teams: Full teams DataFrame.
            team_inputs: Dict of user inputs per teamID or None for AI selection.
        """
        self._ensure_columns(
            self.DTcontract,
            {
                "driverID": None,
                "teamID": None,
                "salary": 0,
                "wanted_reputation": 0,
                "startYear": 0,
                "endYear": 0,
                "active": True,
            },
        )

        active_series = active_series.sort_values(by="reputation", ascending=True).reset_index(
            drop=True
        )
        teams = teams.sort_values(by="reputation", ascending=True)

        for si in active_series["seriesID"]:
            series_rep = active_series.loc[active_series["seriesID"] == si, "reputation"].values[0]
            rule = rules[rules["seriesID"] == si]
            if rule.empty:
                continue

            max_age = rule["maxAge"].iloc[0]
            min_age = rule["minAge"].iloc[0]
            max_cars = rule["maxCars"].iloc[0]

            available_drivers = active_drivers[
                (active_drivers["year"] >= date.year - max_age)
                & (active_drivers["year"] <= date.year - min_age)
            ].copy()
            available_drivers["age"] = date.year - available_drivers["year"]
            available_drivers["maxLen"] = (
                1 if temp else np.minimum(4, max_age - available_drivers["age"])
            )

            contracted = self.DTcontract[
                (self.DTcontract["active"] == True)
                & (self.DTcontract["startYear"] <= date.year)
                & (self.DTcontract["endYear"] >= date.year)
                & (self.DTcontract["wanted_reputation"] <= series_rep)
            ]["driverID"]

            non_contracted = available_drivers[
                ~available_drivers["driverID"].isin(contracted)
            ].reset_index(drop=True)
            teams_in_series = self.STcontract[self.STcontract["seriesID"] == si]["teamID"]
            active_contracts = self.DTcontract[
                (self.DTcontract["active"] == True)
                & (self.DTcontract["startYear"] <= date.year)
                & (self.DTcontract["endYear"] >= date.year)
                & (self.DTcontract["teamID"].isin(teams_in_series))
            ]

            contract_counts = (
                active_contracts.groupby("teamID").size().reset_index(name="activeContracts")
            )
            team_df = pd.DataFrame(teams_in_series).rename(columns={0: "teamID"})
            team_df = team_df.merge(contract_counts, on="teamID", how="left").fillna(0)
            team_df["activeContracts"] = team_df["activeContracts"].astype(int)
            team_df = team_df.merge(teams, on="teamID")

            for i in range(max_cars):
                for _, team_row in team_df.iterrows():
                    if team_row["activeContracts"] == i and len(non_contracted) > 0:
                        team_id = team_row["teamID"]
                        is_human = not team_row["ai"]
                        driver_row = non_contracted.iloc[0]

                        if is_human and team_id in team_inputs and team_inputs[team_id]:
                            driverID, salary, length = team_inputs[team_id]
                        else:
                            # AI fallback
                            driverID = driver_row["driverID"]
                            salary = 25000
                            length = random.randint(0, min(4, driver_row["maxLen"]))

                        # Deactivate previous contract
                        self.DTcontract.loc[self.DTcontract["driverID"] == driverID, "active"] = (
                            False
                        )

                        # Add new contract
                        self.DTcontract.loc[len(self.DTcontract)] = [
                            driverID,
                            team_id,
                            salary,
                            series_rep,
                            date.year,
                            date.year + length,
                            True,
                        ]

                        # Update team money
                        teams.loc[teams["teamID"] == team_id, "money"] -= salary

                        # Remove driver from pool
                        non_contracted = non_contracted[
                            non_contracted["driverID"] != driverID
                        ].reset_index(drop=True)
                        team_df.loc[team_df["teamID"] == team_id, "activeContracts"] += 1

    def sign_car_part_contracts(
        self,
        active_series: pd.DataFrame,
        date,
        car_parts: pd.DataFrame,
        teams_model,
        manufacturers: pd.DataFrame,
        team_inputs: dict,  # {teamID: {partType: (manufacturerID, contract_length)}} or None
    ):
        """
        Sign car part contracts for teams in active series.

        Args:
            active_series: DataFrame of active series.
            date: Current simulation date.
            car_parts: DataFrame of available car parts.
            teams_model: TeamsModel instance.
            manufacturers: DataFrame of manufacturers.
            team_inputs: Dict of user inputs per teamID and partType or None for AI selection.
        """
        with pd.option_context("display.max_columns", None, "display.max_rows", None):

            print("cp", car_parts)
        car_parts["seriesID"] = car_parts["seriesID"].astype(int)
        car_parts["year"] = car_parts["year"].astype(int)
        self._ensure_columns(
            self.MTcontract,
            {
                "seriesID": None,
                "teamID": None,
                "manufacturerID": None,
                "partType": "",
                "startYear": 0,
                "endYear": 0,
                "cost": 0,
            },
        )

        active_series = active_series.sort_values(by="reputation", ascending=True).reset_index(
            drop=True
        )
        teams = teams_model.teams.sort_values(by="reputation", ascending=True)
        human_teams = teams[
            (teams["ai"] == False) & (teams["found"] <= date.year) & (teams["folded"] >= date.year)
        ]

        active_contracts = self.MTcontract[
            (self.MTcontract["startYear"] <= date.year) & (self.MTcontract["endYear"] >= date.year)
        ]
        will_pay = active_contracts[active_contracts["teamID"].isin(human_teams["teamID"])]
        pay_by_team = will_pay.groupby("teamID")["cost"].sum()

        for team_id, total_cost in pay_by_team.items():
            teams.loc[teams["teamID"] == team_id, "money"] -= total_cost

        new_contracts = []

        for si in active_series["seriesID"]:
            print(si, date.year)
            print(car_parts.dtypes)
            series_parts = car_parts[
                (car_parts["seriesID"] == si) & (car_parts["year"] == date.year)
            ]
            print("sp", series_parts)
            teams_in_series = self.STcontract[self.STcontract["seriesID"] == si]["teamID"]
            print(manufacturers.dtypes)

            manufacturers["manufacturerID"] = manufacturers["manufacturerID"].astype(int)

            for part_type in ["engine", "chassi", "pneu"]:
                parts_of_type = series_parts[series_parts["partType"] == part_type].copy()
                parts_of_type["manufacturerID"] = parts_of_type["manufacturerID"].astype(int)
                parts_of_type = parts_of_type.merge(manufacturers, on="manufacturerID", how="left")
                parts_of_type["cost"] = parts_of_type["cost"].astype(int)
                print(part_type, parts_of_type)
                for team_id in teams_in_series:
                    current_contract = active_contracts[
                        (active_contracts["seriesID"] == si)
                        & (active_contracts["teamID"] == team_id)
                        & (active_contracts["partType"] == part_type)
                    ]
                    if not current_contract.empty:
                        continue

                    is_human = team_id in human_teams["teamID"].values
                    if is_human and team_inputs.get(team_id, {}).get(part_type):
                        manufacturerID, contract_len = team_inputs[team_id][part_type]
                        cost = parts_of_type.loc[
                            parts_of_type["manufacturerID"] == manufacturerID, "cost"
                        ].iloc[0]
                    else:
                        print(parts_of_type)
                        sampled = parts_of_type.sample(1).iloc[0]
                        manufacturerID = sampled["manufacturerID"]
                        cost = sampled["cost"]
                        contract_len = random.randint(0, 4)

                    new_contracts.append(
                        {
                            "seriesID": si,
                            "teamID": team_id,
                            "manufacturerID": manufacturerID,
                            "partType": part_type,
                            "startYear": date.year,
                            "endYear": date.year + contract_len,
                            "cost": cost,
                        }
                    )
                    teams.loc[teams["teamID"] == team_id, "money"] -= cost

        self.MTcontract = pd.concat(
            [self.MTcontract, pd.DataFrame(new_contracts)], ignore_index=True
        )
