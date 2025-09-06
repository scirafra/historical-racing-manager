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

    # === Persistence ===
    def load(self, folder: str) -> bool:
        try:
            self.DTcontract = pd.read_csv(os.path.join(folder, "DTcontract.csv"))
            self.STcontract = pd.read_csv(os.path.join(folder, "STcontract.csv"))
            self.CScontract = pd.read_csv(os.path.join(folder, "CScontract.csv"))
            self.MScontract = pd.read_csv(os.path.join(folder, "MScontract.csv"))
            self.MTcontract = pd.read_csv(os.path.join(folder, "MTcontract.csv"))

            self._ensure_columns(self.DTcontract, {
                "driverID": None, "teamID": None, "salary": 0,
                "wanted_reputation": 0, "startYear": 0, "endYear": 0, "active": True
            })
            return True
        except Exception as e:
            print("Contract load failed:", e)
            return False

    def save(self, folder: str):
        self.DTcontract.to_csv(os.path.join(folder, "DTcontract.csv"), index=False)
        self.STcontract.to_csv(os.path.join(folder, "STcontract.csv"), index=False)
        self.CScontract.to_csv(os.path.join(folder, "CScontract.csv"), index=False)
        self.MScontract.to_csv(os.path.join(folder, "MScontract.csv"), index=False)
        self.MTcontract.to_csv(os.path.join(folder, "MTcontract.csv"), index=False)

    def _ensure_columns(self, df, required: dict):
        for col, default in required.items():
            if col not in df.columns:
                df[col] = default

    # === Driver Contracts ===
    def disable_driver_contracts(self, driver_ids):
        self._ensure_columns(self.DTcontract, {"active": True})
        self.DTcontract.loc[self.DTcontract["driverID"].isin(driver_ids), "active"] = False

    def get_MScontract(self):
        return self.MScontract

    def sign_driver_contracts(
            self, active_series, teams_model, current_date,
            active_drivers, rules, temp, teams, team_inputs
    ):
        self._ensure_columns(self.DTcontract, {
            "driverID": None, "teamID": None, "salary": 0,
            "wanted_reputation": 0, "startYear": 0, "endYear": 0, "active": True
        })

        active_series = active_series.sort_values(by="reputation")
        teams = teams.sort_values(by="reputation")

        for _, series in active_series.iterrows():
            rule = rules[rules["seriesID"] == series["seriesID"]]
            if rule.empty:
                continue

            max_age, min_age, max_cars = rule.iloc[0][["maxAge", "minAge", "maxCars"]]
            available = self._get_available_drivers(active_drivers, current_date.year, max_age, min_age, temp)
            contracted = self._get_contracted_driver_ids(series["reputation"], current_date.year)
            pool = available[~available["driverID"].isin(contracted)].reset_index(drop=True)

            team_df = self._get_eligible_teams(series["seriesID"], teams, current_date.year)
            for i in range(max_cars):
                for _, team in team_df.iterrows():
                    if team["activeContracts"] == i and not pool.empty:
                        self._assign_driver_to_team(
                            team, pool, team_inputs, series["reputation"], current_date.year, temp
                        )
                        pool = pool[pool["driverID"] != team["assigned_driver"]].reset_index(drop=True)
                        team_df.loc[team_df["teamID"] == team["teamID"], "activeContracts"] += 1

    def _get_available_drivers(self, drivers, year, max_age, min_age, temp):
        df = drivers[(drivers["year"] >= year - max_age) & (drivers["year"] <= year - min_age)].copy()
        df["age"] = year - df["year"]
        df["maxLen"] = 1 if temp else np.minimum(4, max_age - df["age"])
        return df

    def _get_contracted_driver_ids(self, reputation, year):
        return self.DTcontract[
            (self.DTcontract["active"]) &
            (self.DTcontract["startYear"] <= year) &
            (self.DTcontract["endYear"] >= year) &
            (self.DTcontract["wanted_reputation"] <= reputation)
            ]["driverID"]

    def _get_eligible_teams(self, seriesID, teams, year):
        team_ids = self.STcontract[self.STcontract["seriesID"] == seriesID]["teamID"]
        active = self.DTcontract[
            (self.DTcontract["active"]) &
            (self.DTcontract["startYear"] <= year) &
            (self.DTcontract["endYear"] >= year) &
            (self.DTcontract["teamID"].isin(team_ids))
            ]
        counts = active.groupby("teamID").size().reset_index(name="activeContracts")
        df = pd.DataFrame(team_ids).rename(columns={0: "teamID"}).merge(counts, on="teamID", how="left").fillna(0)
        df["activeContracts"] = df["activeContracts"].astype(int)
        return df.merge(teams, on="teamID")

    def _assign_driver_to_team(self, team_row, pool, team_inputs, reputation, year, temp):
        team_id = team_row["teamID"]
        is_human = not team_row["ai"]
        driver_row = pool.iloc[0]

        if is_human and team_inputs.get(team_id):
            driverID, salary, length = team_inputs[team_id]
        else:
            driverID = driver_row["driverID"]
            salary = 25000
            length = random.randint(0, min(4, driver_row["maxLen"]))

        self.DTcontract.loc[self.DTcontract["driverID"] == driverID, "active"] = False
        self.DTcontract.loc[len(self.DTcontract)] = [
            driverID, team_id, salary, reputation, year, year + length, True
        ]
        team_row["assigned_driver"] = driverID

    # === Car Part Contracts ===
    def sign_car_part_contracts(
            self, active_series, current_date, car_parts, teams_model, manufacturers, team_inputs
    ):
        self._ensure_columns(self.MTcontract, {
            "seriesID": None, "teamID": None, "manufacturerID": None,
            "partType": "", "startYear": 0, "endYear": 0, "cost": 0
        })

        car_parts["seriesID"] = car_parts["seriesID"].astype(int)
        car_parts["year"] = car_parts["year"].astype(int)
        manufacturers["manufacturerID"] = manufacturers["manufacturerID"].astype(int)

        teams = teams_model.teams.sort_values(by="reputation")
        human_teams = teams[
            (~teams["ai"]) & (teams["found"] <= current_date.year) & (teams["folded"] >= current_date.year)
            ]

        active_contracts = self.MTcontract[
            (self.MTcontract["startYear"] <= current_date.year) &
            (self.MTcontract["endYear"] >= current_date.year)
            ]
        self._deduct_existing_contract_costs(human_teams, active_contracts, teams)

        new_contracts = []
        for si in active_series["seriesID"]:
            series_parts = car_parts[
                (car_parts["seriesID"] == si) & (car_parts["year"] == current_date.year)
                ]
            teams_in_series = self.STcontract[self.STcontract["seriesID"] == si]["teamID"]

            for part_type in ["engine", "chassi", "pneu"]:
                contracts = self._generate_part_contracts(
                    part_type, series_parts, manufacturers, teams_in_series,
                    active_contracts, human_teams, team_inputs, current_date.year, teams
                )
                new_contracts.extend(contracts)

                if new_contracts:
                    self.MTcontract = pd.concat([self.MTcontract, pd.DataFrame(new_contracts)], ignore_index=True)

    def _deduct_existing_contract_costs(self, human_teams, active_contracts, teams):
        pay_by_team = (
            active_contracts[active_contracts["teamID"].isin(human_teams["teamID"])]
            .groupby("teamID")["cost"]
            .sum()
        )
        for team_id, total_cost in pay_by_team.items():
            teams.loc[teams["teamID"] == team_id, "money"] -= total_cost

    def _generate_part_contracts(
            self, part_type, series_parts, manufacturers, teams_in_series,
            active_contracts, human_teams, team_inputs, year, teams
    ):
        contracts = []
        parts_of_type = series_parts[series_parts["partType"] == part_type].copy()
        if parts_of_type.empty:
            return contracts

        parts_of_type["manufacturerID"] = parts_of_type["manufacturerID"].astype(int)
        manufacturers["manufacturerID"] = manufacturers["manufacturerID"].astype(int)
        parts_of_type = parts_of_type.merge(manufacturers, on="manufacturerID", how="left")
        parts_of_type["cost"] = parts_of_type["cost"].astype(int)

        for team_id in teams_in_series:
            current_contract = active_contracts[
                (active_contracts["teamID"] == team_id) &
                (active_contracts["partType"] == part_type)
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
                sampled = parts_of_type.sample(1).iloc[0]
                manufacturerID = sampled["manufacturerID"]
                cost = sampled["cost"]
                contract_len = random.randint(0, 4)

            contracts.append({
                "seriesID": int(series_parts["seriesID"].iloc[0]),
                "teamID": team_id,
                "manufacturerID": manufacturerID,
                "partType": part_type,
                "startYear": year,
                "endYear": year + contract_len,
                "cost": cost,
            })
            teams.loc[teams["teamID"] == team_id, "money"] -= cost

        return contracts
