import os
import random
from datetime import datetime

import pandas as pd


class ContractsModel:
    def __init__(self):
        self.DTcontract = pd.DataFrame()
        self.STcontract = pd.DataFrame()
        self.CScontract = pd.DataFrame()
        self.MScontract = pd.DataFrame()
        self.MTcontract = pd.DataFrame()
        self.reserved_slots = {}  # teamID → True

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
        # print("tu")
        self._ensure_columns(self.DTcontract, {
            "driverID": None, "teamID": None, "salary": 0,
            "wanted_reputation": 0, "startYear": 0, "endYear": 0, "active": True
        })

        if not self._should_sign_today(current_date):
            return
        print("tu 2")
        available = active_drivers.copy()
        available["reputation"] = available["reputation"].fillna(0)
        available = available[~available["driverID"].isin(self.DTcontract["driverID"])]

        team_id = self._choose_team_by_reputation(teams)
        is_human = not teams_model.teams.loc[teams_model.teams["teamID"] == team_id, "ai"].iloc[0]

        if is_human:
            self._reserve_slot_for_human_team(team_id)
            if team_id in team_inputs:
                driver_id, salary, length = team_inputs[team_id]
                self._create_driver_contract(driver_id, team_id, salary, current_date.year, length)
        else:
            driver_id = self._choose_driver_by_reputation(available)
            salary = self._estimate_salary(available, driver_id)
            length = random.randint(1, 4)
            self._create_driver_contract(driver_id, team_id, salary, current_date.year, length)

    def _should_sign_today(self, date: datetime) -> bool:
        day_of_year = date.timetuple().tm_yday
        total_days = 366 if date.year % 4 == 0 else 365
        probability = day_of_year / total_days
        return random.random() < probability

    def _choose_team_by_reputation(self, teams_df: pd.DataFrame) -> int:
        sorted_teams = teams_df.sort_values("reputation", ascending=False).reset_index(drop=True)
        weights = [0.5, 0.25, 0.125, 0.0625] + [0.01] * max(0, len(sorted_teams) - 4)
        chosen_index = random.choices(range(len(sorted_teams)), weights[:len(sorted_teams)])[0]
        return sorted_teams.iloc[chosen_index]["teamID"]

    def _choose_driver_by_reputation(self, drivers_df: pd.DataFrame) -> int:
        sorted_drivers = drivers_df.sort_values("reputation", ascending=False).reset_index(drop=True)
        weights = [0.5, 0.25, 0.125, 0.0625] + [0.01] * max(0, len(sorted_drivers) - 4)
        chosen_index = random.choices(range(len(sorted_drivers)), weights[:len(sorted_drivers)])[0]
        return sorted_drivers.iloc[chosen_index]["driverID"]

    def _reserve_slot_for_human_team(self, team_id: int):
        self.reserved_slots[team_id] = True

    def _estimate_salary(self, drivers_df: pd.DataFrame, driver_id: int) -> int:
        base = 25000
        rep = drivers_df.loc[drivers_df["driverID"] == driver_id, "reputation"].iloc[0]
        return int(base + rep * 100)

    def _create_driver_contract(self, driver_id: int, team_id: int, salary: int, start_year: int, length: int):
        self.DTcontract.loc[len(self.DTcontract)] = {
            "driverID": driver_id,
            "teamID": team_id,
            "salary": salary,
            "wanted_reputation": 0,
            "startYear": start_year,
            "endYear": start_year + length,
            "active": True
        }
        print(self.DTcontract)

    def terminate_driver_contract(self, team_id: int, driver_id: int, current_year: int):
        contract = self.DTcontract[
            (self.DTcontract["teamID"] == team_id) &
            (self.DTcontract["driverID"] == driver_id) &
            (self.DTcontract["active"])
            ]
        if contract.empty:
            return

        end_year = contract.iloc[0]["endYear"]
        salary = contract.iloc[0]["salary"]
        remaining_years = max(0, end_year - current_year)
        payout = remaining_years * salary

        self.DTcontract = self.DTcontract[
            ~((self.DTcontract["teamID"] == team_id) & (self.DTcontract["driverID"] == driver_id))
        ]

    # === Car Part Contracts ===
    def sign_car_part_contracts(
            self, active_series, current_date, car_parts, teams_model, manufacturers, team_inputs
    ):
        # print("here")
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
                contract_len = random.randint(1, 4)

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
