import os
import random
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


class ContractsModel:
    """Model pre podpisovanie zmlúv (jazdci a diely).

    Poznámky:
    - driver_slots_current a driver_slots_next držia stav slotov pre jednotlivé roky.
    - metódy upravené tak, aby dodržali single-responsibility a boli
      čitateľné.
    """

    def __init__(self) -> None:
        self.DTcontract: pd.DataFrame = pd.DataFrame()
        self.STcontract: pd.DataFrame = pd.DataFrame()
        self.CScontract: pd.DataFrame = pd.DataFrame()
        self.MScontract: pd.DataFrame = pd.DataFrame()
        self.MTcontract: pd.DataFrame = pd.DataFrame()
        self.reserved_slots: Dict[int, bool] = {}  # teamID → True
        self.driver_slots_current: pd.DataFrame = pd.DataFrame()
        self.driver_slots_next: pd.DataFrame = pd.DataFrame()
        self.rules: pd.DataFrame = pd.DataFrame()
        # mapa seriesID -> reputation (naplnene pri sign_driver_contracts)
        self.series_reputation: Dict[int, float] = {}

    # === Persistence ===
    def load(self, folder: str) -> bool:
        try:
            self.DTcontract = pd.read_csv(os.path.join(folder, "DTcontract.csv"))
            self.STcontract = pd.read_csv(os.path.join(folder, "STcontract.csv"))
            self.CScontract = pd.read_csv(os.path.join(folder, "CScontract.csv"))
            self.MScontract = pd.read_csv(os.path.join(folder, "MScontract.csv"))
            self.MTcontract = pd.read_csv(os.path.join(folder, "MTcontract.csv"))
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
        except Exception as e:  # pragma: no cover - top-level I/O
            print("Contract load failed:", e)
            return False

    def save(self, folder: str) -> None:
        self.DTcontract.to_csv(os.path.join(folder, "DTcontract.csv"), index=False)
        self.STcontract.to_csv(os.path.join(folder, "STcontract.csv"), index=False)
        self.CScontract.to_csv(os.path.join(folder, "CScontract.csv"), index=False)
        self.MScontract.to_csv(os.path.join(folder, "MScontract.csv"), index=False)
        self.MTcontract.to_csv(os.path.join(folder, "MTcontract.csv"), index=False)

    def _ensure_columns(self, df: pd.DataFrame, required: Dict[str, object]) -> None:
        for col, default in required.items():
            if col not in df.columns:
                df[col] = default

    # === Driver Slots ===
    def init_driver_slots_for_year(self, year: int, rules: pd.DataFrame) -> pd.DataFrame:
        """Vytvorí tabuľku slotov pre všetky tímy v STcontract pre zadaný rok.

        Vracia dataframe so stlpcami: teamID, seriesID, year, max_slots, signed_slots, free_slots
        """
        self.rules = rules
        records: List[Dict[str, int]] = []
        for _, row in self.STcontract.iterrows():
            team_id = int(row["teamID"])
            series_id = int(row["seriesID"])
            max_slots = int(rules.loc[rules["seriesID"] == series_id, "max_cars"].iloc[0])
            signed = (
                self.DTcontract[
                    (self.DTcontract["teamID"] == team_id)
                    & (self.DTcontract["startYear"] <= year)
                    & (self.DTcontract["endYear"] >= year)
                    & (self.DTcontract["active"])
                    ]
                .shape[0]
            )
            records.append(
                {
                    "teamID": team_id,
                    "seriesID": series_id,
                    "year": year,
                    "max_slots": max_slots,
                    "signed_slots": signed,
                    "free_slots": max_slots - signed,
                }
            )

        return pd.DataFrame(records)

    def rollover_driver_slots(self) -> None:
        """Presunie next -> current a vygeneruje new next pre nasledujuci rok.

        Očaká sa, že driver_slots_next už obsahuje jeden rok (napr. 2026) pred volaním.
        """
        if self.driver_slots_next.empty:
            # ak nie je next, inicializujeme current cez init pre nasledujuci rok ak možno
            self.driver_slots_current = self.init_driver_slots_for_year(datetime.now().year, self.rules)
            next_year = self.driver_slots_current[
                            "year"].max() + 1 if not self.driver_slots_current.empty else datetime.now().year + 1
            self.driver_slots_next = self.init_driver_slots_for_year(next_year, self.rules)
            print("rollover (empty next) => initialized")
            return

        self.driver_slots_current = self.driver_slots_next.copy(deep=True)
        next_year = int(self.driver_slots_current["year"].max()) + 1
        self.driver_slots_next = self.init_driver_slots_for_year(next_year, self.rules)

    def update_driver_slot(self, team_id: int, year: int) -> None:
        """Zvyší signed_slots a zmení free_slots pre zodpovedajúci rok.

        Upravi sa buď driver_slots_current, alebo driver_slots_next, podľa toho, ktorý rok zodpovedá.
        """
        updated = False
        for df in (self.driver_slots_current, self.driver_slots_next):
            if df.empty:
                continue
            mask = (df["teamID"] == team_id) & (df["year"] == year)
            if mask.any():
                # zabezpečime, že nedojde k negativnym free_slots
                df.loc[mask, "signed_slots"] = df.loc[mask, "signed_slots"] + 1
                df.loc[mask, "free_slots"] = (df.loc[mask, "max_slots"] - df.loc[mask, "signed_slots"]).clip(lower=0)
                updated = True
        if not updated:
            # nie je tam záznam -> vytvoríme novy (fallback)
            # ziskame series pre team
            series_row = self.STcontract[self.STcontract["teamID"] == team_id]
            if not series_row.empty:
                series_id = int(series_row.iloc[0]["seriesID"])
                max_slots = int(self.rules.loc[self.rules["seriesID"] == series_id, "max_cars"].iloc[0])
                rec = {
                    "teamID": team_id,
                    "seriesID": series_id,
                    "year": year,
                    "max_slots": max_slots,
                    "signed_slots": 1,
                    "free_slots": max_slots - 1,
                }
                # pridame do next ak year je > current_year, inak do current
                if not self.driver_slots_current.empty and year == int(self.driver_slots_current["year"].iloc[0]):
                    self.driver_slots_current = pd.concat([self.driver_slots_current, pd.DataFrame([rec])],
                                                          ignore_index=True)
                else:
                    self.driver_slots_next = pd.concat([self.driver_slots_next, pd.DataFrame([rec])], ignore_index=True)

    # === Driver Contracts ===
    def disable_driver_contracts(self, driver_ids: List[int]) -> None:
        self._ensure_columns(self.DTcontract, {"active": True})
        self.DTcontract.loc[self.DTcontract["driverID"].isin(driver_ids), "active"] = False

    def get_MScontract(self) -> pd.DataFrame:
        return self.MScontract

    @staticmethod
    def _is_leap(year: int) -> bool:
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    def _should_sign_today(self, date: datetime) -> bool:
        day_of_year = date.timetuple().tm_yday
        total_days = 366 if self._is_leap(date.year) else 365
        probability = day_of_year / total_days
        return random.random() < probability

    def _choose_team_by_reputation(self, teams_df: pd.DataFrame) -> Optional[int]:
        if teams_df.empty:
            return None
        sorted_teams = teams_df.sort_values("reputation", ascending=False).reset_index(drop=True)
        n = len(sorted_teams)
        # dynamicky vygenerujeme exponencialne klesajuce vahy s fallback pre zostavajuce
        base_weights = [0.5, 0.25, 0.125, 0.0625]
        if n > len(base_weights):
            weights = base_weights + [0.01] * (n - len(base_weights))
        else:
            weights = base_weights[:n]
        chosen_index = random.choices(range(n), weights=weights)[0]
        return int(sorted_teams.iloc[chosen_index]["teamID"])

    def _choose_driver_by_reputation(self, drivers_df: pd.DataFrame) -> Optional[int]:
        if drivers_df.empty:
            return None
        sorted_drivers = drivers_df.sort_values("reputation_race", ascending=False).reset_index(drop=True)
        n = len(sorted_drivers)
        base_weights = [0.5, 0.25, 0.125, 0.0625]
        if n > len(base_weights):
            weights = base_weights + [0.01] * (n - len(base_weights))
        else:
            weights = base_weights[:n]
        chosen_index = random.choices(range(n), weights=weights)[0]
        return int(sorted_drivers.iloc[chosen_index]["driverID"])

    def _reserve_slot_for_human_team(self, team_id: int) -> None:
        self.reserved_slots[team_id] = True

    def _estimate_salary(self, drivers_df: pd.DataFrame, driver_id: int) -> int:
        base = 25000
        rep = int(drivers_df.loc[drivers_df["driverID"] == driver_id, "reputation_race"].iloc[0])
        return int(base + rep * 100)

    def _deactivate_lower_series_contract(self, driver_id: int, year: int, new_team_id: int) -> None:
        """
        Ukončí len tie aktívne kontrakty jazdca, ktoré by inak kolidovali
        s novou zmluvou. Staré historické kontrakty necháva nedotknuté.
        """
        mask = (
                (self.DTcontract["driverID"] == driver_id)
                & (self.DTcontract["teamID"] != new_team_id)
                & (self.DTcontract["active"])
                & (self.DTcontract["endYear"] >= year)
        )

        for idx, row in self.DTcontract[mask].iterrows():
            self.DTcontract.at[idx, "endYear"] = year - 1
            self.DTcontract.at[idx, "active"] = False

    def _create_driver_contract(self, driver_id: int, team_id: int, salary: int, start_year: int, length: int) -> None:
        self.DTcontract.loc[len(self.DTcontract)] = {
            "driverID": int(driver_id),
            "teamID": int(team_id),
            "salary": int(salary),
            "wanted_reputation": 0,
            "startYear": int(start_year),
            "endYear": int(start_year + length),
            "active": True,
        }

        # aktualizujeme slots pre prislusny rok
        self.update_driver_slot(team_id, start_year)
        # upravime stare kontrakty ak treba
        self._deactivate_lower_series_contract(driver_id, start_year, team_id)
        # ak bola rezervacia pre team, vyradime ju
        if team_id in self.reserved_slots:
            del self.reserved_slots[team_id]

    def _get_available_drivers(
            self, active_drivers: pd.DataFrame, year: int, series_id: int, team_id: int, rules: pd.DataFrame
    ) -> pd.DataFrame:
        """Vracia DataFrame jazdcov, ktorí spľaňajú podmienky veku pre dánu sériu a nemajú zmluvu v rovnakej/vyššej sérii.

        Zároveň vypočíta maximálnu povolenú dĺžku zmluvy (max_contract_len) pre každého jazdca tak, aby
        neprekročil max_age v žiadnom roku kontraktu.
        """
        able = active_drivers.copy()
        if "reputation_race" not in able.columns:
            able["reputation_race"] = 0
        able["reputation_race"] = able["reputation_race"].fillna(0)
        # predpoklad: stlpec "year" v active_drivers je rok narodenia
        if "year" not in able.columns:
            able["year"] = 0
        able["age"] = year - able["year"]

        min_age = int(rules.loc[rules["seriesID"] == series_id, "min_age"].iloc[0])
        max_age = int(rules.loc[rules["seriesID"] == series_id, "max_age"].iloc[0])

        team_series_row = self.STcontract[self.STcontract["teamID"] == team_id]
        team_series_id = int(team_series_row.iloc[0]["seriesID"]) if not team_series_row.empty else None

        active_contracts = self.DTcontract[
            (self.DTcontract["startYear"] <= year) & (self.DTcontract["endYear"] >= year) & (self.DTcontract["active"])
            ]

        unavailable_ids: List[int] = []
        for _, row in active_contracts.iterrows():
            driver_id = int(row["driverID"])
            team_id_contract = int(row["teamID"])
            series_row = self.STcontract[self.STcontract["teamID"] == team_id_contract]
            if series_row.empty:
                continue
            series_id_contract = int(series_row.iloc[0]["seriesID"])
            # ak ma jazdec zmluvu v serii, ktora je rovnaká alebo "vyššia" (podľa porovávania id),
            # zväčša to znamena, že nie je dostupný pre nižšiu seriu
            if team_series_id is not None and series_id_contract <= team_series_id:
                unavailable_ids.append(driver_id)

        # teraz odfiltrujeme jednorazovo
        able = able[~able["driverID"].isin(unavailable_ids)]
        able = able[(able["age"] >= min_age) & (able["age"] <= max_age)]

        # vypocitaj maximum rokoch kontraktu, aby jazdec neprekrocil max_age
        able["max_contract_len"] = able["age"].apply(lambda a: max_age - a)
        # ponechame len jazdcov, ktori mozu podpisat aspon jednoročnu zmluvu
        able = able[able["max_contract_len"] >= 1]
        # max_contract_len je integer
        able["max_contract_len"] = able["max_contract_len"].astype(int)

        return able

    def _get_active_team_contracts(self, team_id: int, year: int) -> pd.DataFrame:
        return self.DTcontract[
            (self.DTcontract["teamID"] == team_id)
            & (self.DTcontract["startYear"] <= year)
            & (self.DTcontract["endYear"] >= year)
            & (self.DTcontract["active"])
            ]

    def _get_teams_without_driver(self, teams_df: pd.DataFrame, year: int) -> List[int]:
        active_contracts = self.DTcontract[
            (self.DTcontract["active"]) & (self.DTcontract["startYear"] <= year) & (self.DTcontract["endYear"] >= year)]
        contracted_team_ids = active_contracts["teamID"].unique()
        all_team_ids = teams_df["teamID"].unique()
        return [int(tid) for tid in all_team_ids if int(tid) not in contracted_team_ids]

    def sign_driver_contracts(
            self,
            active_series: pd.DataFrame,
            teams_model,
            current_date: datetime,
            active_drivers: pd.DataFrame,
            rules: pd.DataFrame,
            temp,
            teams: pd.DataFrame,
            team_inputs: Dict[int, tuple],
    ) -> None:
        """Hlavná metóda na podpisovanie jazdeckých zmlúv.

        - Najprv doplníme zmluvy pre sučasny rok (ak su volne miesta).
        - Potom pravdepodobnostne generujeme podpisy pre buduci rok (podla _should_sign_today).
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

        # naplnime mapping seriesID -> reputation (podla specifikacie: active_series obsahuje reputation)
        self.series_reputation = {}
        if "seriesID" in active_series.columns and "reputation" in active_series.columns:
            for _, r in active_series.iterrows():
                self.series_reputation[int(r["seriesID"])] = float(r["reputation"])

        # 1) Doplnime pre aktualny rok
        for series_id in active_series["seriesID"]:
            max_cars = int(rules.loc[rules["seriesID"] == series_id, "max_cars"].iloc[0])
            teams_in_series = self.STcontract[self.STcontract["seriesID"] == series_id]["teamID"]

            for team_id in teams_in_series:
                team_id = int(team_id)
                current_contracts = self._get_active_team_contracts(team_id, current_date.year)
                signed_count = len(current_contracts)
                missing_slots = max_cars - signed_count

                for _ in range(missing_slots):
                    is_human = not bool(
                        teams_model.teams.loc[teams_model.teams["teamID"] == team_id, "ai"].iloc[0]
                    )
                    if is_human and team_inputs.get(team_id):
                        driver_id, salary, length = team_inputs[team_id]
                        # enforce age constraint for provided length
                        available = self._get_available_drivers(active_drivers, current_date.year, int(series_id),
                                                                team_id, rules)
                        if driver_id not in available["driverID"].values:
                            continue
                        max_len = int(available.loc[available["driverID"] == driver_id, "max_contract_len"].iloc[0])
                        length = min(int(length), max_len)
                    else:
                        available = self._get_available_drivers(
                            active_drivers, current_date.year, int(series_id), team_id, rules
                        )
                        if len(available) == 0:
                            continue
                        driver_id = self._choose_driver_by_reputation(available)
                        if driver_id is None:
                            continue
                        salary = self._estimate_salary(available, driver_id)
                        max_len = int(available.loc[available["driverID"] == driver_id, "max_contract_len"].iloc[0])

                        length = random.randint(1, min(4, max_len))
                    self._create_driver_contract(driver_id, team_id, salary, current_date.year, length)

        # 2) Probabilistic signing for next year
        if not self._should_sign_today(current_date):
            return

        # vyberieme tim podla reputacie
        team_id = self._choose_team_by_reputation(teams)
        if team_id is None:
            return
        is_human = not bool(
            teams_model.teams.loc[teams_model.teams["teamID"] == team_id, "ai"].iloc[0]
        )

        # zistime seriu timu a kontrolujeme miesta pre buduci rok
        team_series = self.STcontract[self.STcontract["teamID"] == team_id]
        if team_series.empty:
            return
        series_id = int(team_series.iloc[0]["seriesID"])

        max_cars = int(rules.loc[rules["seriesID"] == series_id, "max_cars"].iloc[0])
        future_contracts = self._get_active_team_contracts(team_id, current_date.year + 1)
        if len(future_contracts) >= max_cars:
            return

        # ak clovek rezervoval slot predtym, nechceme rezervovat znova
        if is_human:
            if self.reserved_slots.get(team_id):
                # slot uz rezervovany, skoncime
                return
            self._reserve_slot_for_human_team(team_id)

        # Ziskame dostupnych jazdcov pre buduci rok v danej serii
        available = self._get_available_drivers(active_drivers, current_date.year + 1, series_id, team_id, rules)
        if available.empty:
            # ak nie su dostupni jazdci, zrusime rezervaciu (ak bola)
            if team_id in self.reserved_slots:
                del self.reserved_slots[team_id]
            return

        if is_human:
            if team_id in team_inputs:
                driver_id, salary, length = team_inputs[team_id]
                if driver_id not in available["driverID"].values:
                    # invalid selection, zrusime rezervaciu
                    if team_id in self.reserved_slots:
                        del self.reserved_slots[team_id]
                    return
                max_len = int(available.loc[available["driverID"] == driver_id, "max_contract_len"].iloc[0])
                length = min(int(length), max_len)
                self._create_driver_contract(driver_id, team_id, salary, current_date.year + 1, length)
            else:
                # nebol zadany input z UI, nechame rezervaciu pre neskor
                return
        else:
            driver_id = self._choose_driver_by_reputation(available)
            if driver_id is None:
                if team_id in self.reserved_slots:
                    del self.reserved_slots[team_id]
                return
            salary = self._estimate_salary(available, driver_id)
            max_len = int(available.loc[available["driverID"] == driver_id, "max_contract_len"].iloc[0])
            length = random.randint(1, min(4, max_len))
            self._create_driver_contract(driver_id, team_id, salary, current_date.year + 1, length)

    # === Car Part Contracts ===
    def _deduct_existing_contract_costs(self, human_teams: pd.DataFrame, active_contracts: pd.DataFrame,
                                        teams: pd.DataFrame) -> None:
        pay_by_team = (
            active_contracts[active_contracts["teamID"].isin(human_teams["teamID"])].groupby("teamID")["cost"].sum()
        )
        for team_id, total_cost in pay_by_team.items():
            teams.loc[teams["teamID"] == team_id, "money"] -= total_cost

    def _generate_part_contracts(
            self,
            part_type: str,
            series_parts: pd.DataFrame,
            manufacturers: pd.DataFrame,
            teams_in_series: pd.Series,
            active_contracts: pd.DataFrame,
            human_teams: pd.DataFrame,
            team_inputs: Dict[int, Dict[str, tuple]],
            year: int,
            teams: pd.DataFrame,
    ) -> List[Dict[str, object]]:
        contracts: List[Dict[str, object]] = []
        parts_of_type = series_parts[series_parts["partType"] == part_type].copy()
        if parts_of_type.empty:
            return contracts

        parts_of_type["manufacturerID"] = parts_of_type["manufacturerID"].astype(int)
        manufacturers["manufacturerID"] = manufacturers["manufacturerID"].astype(int)
        parts_of_type = parts_of_type.merge(manufacturers, on="manufacturerID", how="left")
        parts_of_type["cost"] = parts_of_type["cost"].astype(int)

        for team_id in teams_in_series:
            team_id = int(team_id)
            current_contract = active_contracts[
                (active_contracts["teamID"] == team_id) & (active_contracts["partType"] == part_type)]
            if not current_contract.empty:
                continue

            is_human = team_id in human_teams["teamID"].values
            if is_human and team_inputs.get(team_id, {}).get(part_type):
                manufacturerID, contract_len = team_inputs[team_id][part_type]
                cost = parts_of_type.loc[parts_of_type["manufacturerID"] == manufacturerID, "cost"].iloc[0]
            else:
                sampled = parts_of_type.sample(1).iloc[0]
                manufacturerID = int(sampled["manufacturerID"])
                cost = int(sampled["cost"])
                contract_len = random.randint(1, 4)

            contracts.append(
                {
                    "seriesID": int(series_parts["seriesID"].iloc[0]),
                    "teamID": team_id,
                    "manufacturerID": manufacturerID,
                    "partType": part_type,
                    "startYear": year,
                    "endYear": year + contract_len,
                    "cost": int(cost),
                }
            )
            teams.loc[teams["teamID"] == team_id, "money"] -= cost

        return contracts

    def sign_car_part_contracts(self, active_series: pd.DataFrame, current_date: datetime, car_parts: pd.DataFrame,
                                teams_model, manufacturers: pd.DataFrame,
                                team_inputs: Dict[int, Dict[str, tuple]]) -> None:
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

        car_parts["seriesID"] = car_parts["seriesID"].astype(int)
        car_parts["year"] = car_parts["year"].astype(int)
        manufacturers["manufacturerID"] = manufacturers["manufacturerID"].astype(int)

        teams = teams_model.teams.sort_values(by="reputation")
        human_teams = teams[
            (~teams["ai"]) & (teams["found"] <= current_date.year) & (teams["folded"] >= current_date.year)]

        active_contracts = self.MTcontract[
            (self.MTcontract["startYear"] <= current_date.year) & (self.MTcontract["endYear"] >= current_date.year)]
        self._deduct_existing_contract_costs(human_teams, active_contracts, teams)

        new_contracts: List[Dict[str, object]] = []
        for si in active_series["seriesID"]:
            series_parts = car_parts[(car_parts["seriesID"] == si) & (car_parts["year"] == current_date.year)]
            teams_in_series = self.STcontract[self.STcontract["seriesID"] == si]["teamID"]

            for part_type in ["engine", "chassi", "pneu"]:
                contracts = self._generate_part_contracts(
                    part_type,
                    series_parts,
                    manufacturers,
                    teams_in_series,
                    active_contracts,
                    human_teams,
                    team_inputs,
                    current_date.year,
                    teams,
                )
                new_contracts.extend(contracts)

        if new_contracts:
            self.MTcontract = pd.concat([self.MTcontract, pd.DataFrame(new_contracts)], ignore_index=True)
