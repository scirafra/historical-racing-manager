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
        self.reserved_slots: Dict[int, int] = {}  # teamID → Avaiable seats
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

    def find_active_driver_contracts(self, team_id: int, start_range: int, series: pd.DataFrame,
                                     active_drivers: pd.DataFrame,
                                     race_model=None) -> pd.DataFrame:
        years = (start_range, start_range - 1, start_range - 2)
        """
        Nájde všetky zmluvy, ktoré platili pre daný team_id počas zadaného rozsahu rokov.

        Args:
            df (pd.DataFrame): DataFrame so zmluvami.
            team_id (int): ID tímu.
            start_range (int): Začiatok sledovaného obdobia.
            end_range (int): Koniec sledovaného obdobia.

        Returns:
            pd.DataFrame: Podmnožina zmlúv, ktoré v daných rokoch platili.
        """
        mask = (
                (self.DTcontract["teamID"] == team_id) &
                (self.DTcontract["active"]) &  # voliteľné – ak chceš iba aktívne zmluvy

                ((self.DTcontract["endYear"] >= start_range) |

                 (self.DTcontract["startYear"] >= start_range))
        )
        contracts = self.DTcontract[mask].copy()
        # print("find active contracts", contracts)
        if not active_drivers.empty:
            custom_drivers = active_drivers[["driverID", "forename", "surname", "nationality", "age"]]
            contracts = custom_drivers.merge(contracts, on="driverID", how="right")

            """
            Pridá k zmluvám jazdcov ich výsledky (pozíciu, body, sériu) za zadané roky.
            """
            merged = contracts.copy()

            for yr in years:
                # Vyfiltruj výsledky pre daný rok
                year_standings = race_model.standings[race_model.standings["year"] == yr]

                # Zredukuj na posledný známy výsledok (napr. posledné kolo)
                # alebo môžeš agregovať podľa priemeru či súčtu bodov
                last_round = year_standings.sort_values("round").groupby("subjectID").last().reset_index()

                # Spoj s názvami sérií
                last_round = last_round.merge(series[["seriesID", "name"]], on="seriesID", how="left")

                # Premenuj stĺpce, aby mali názvy s rokom
                year_standings = last_round.rename(
                    columns={
                        "name": f"{yr}",
                        "position": f"Position_{yr}",
                        "points": f"Points_{yr}",
                    }
                )[
                    ["subjectID", f"{yr}", f"Position_{yr}", f"Points_{yr}"]
                ]

                # Spoj s hlavnou tabuľkou
                merged = merged.merge(year_standings, left_on="driverID", right_on="subjectID", how="left")
                merged = merged.drop(columns=["subjectID"], errors="ignore")

            # Voliteľne — zoradiť stĺpce podľa vzoru
            base_cols = ["forename", "surname", "nationality", "age", "salary", "startYear", "endYear"]
            other_cols = [c for c in merged.columns if c not in base_cols and c != "driverID"]
            merged = merged[base_cols + other_cols]
            merged = merged.drop(columns=["teamID", "wanted_reputation", "active", "driverID"], errors="ignore")
            return merged

        contracts = contracts.drop(columns=["teamID", "wanted_reputation", "active", "driverID"], errors="ignore")
        return contracts

    def get_contracts_for_year(self, year: int) -> pd.DataFrame:
        """Vráti všetky zmluvy aktívne v danom roku."""
        return self.DTcontract[
            (self.DTcontract["startYear"] <= year) &
            (self.DTcontract["endYear"] >= year) &
            (self.DTcontract["active"] == True)
            ].copy()

    """
    def find_active_driver_contracts(self, team_id: int, start_range: int, driver_model=None,
                                     race_model=None) -> pd.DataFrame:
        years = (start_range, start_range - 1, start_range - 2)
        """"""
        Nájde všetky zmluvy, ktoré platili pre daný team_id počas zadaného rozsahu rokov.

        Args:
            df (pd.DataFrame): DataFrame so zmluvami.
            team_id (int): ID tímu.
            start_range (int): Začiatok sledovaného obdobia.
            end_range (int): Koniec sledovaného obdobia.

        Returns:
            pd.DataFrame: Podmnožina zmlúv, ktoré v daných rokoch platili.
        """"""
        mask = (
                (self.DTcontract["teamID"] == team_id) &
                (((self.DTcontract["active"]) &  # voliteľné – ak chceš iba aktívne zmluvy

                  (self.DTcontract["endYear"] >= start_range)) |

                 (self.DTcontract["startYear"] >= start_range))
        )
        contracts = self.DTcontract[mask].copy()

        if driver_model is not None:
            custom_drivers = driver_model.drivers[["driverID", "forename", "surname", "nationality", "age"]]
            contracts = custom_drivers.merge(contracts, on="driverID", how="right")

            
            #Pridá k zmluvám jazdcov ich výsledky (pozíciu, body, sériu) za zadané roky.
            
            merged = contracts.copy()

            for yr in years:
                # Vyfiltruj výsledky pre daný rok
                year_standings = race_model.standings[race_model.standings["year"] == yr]

                # Zredukuj na posledný známy výsledok (napr. posledné kolo)
                # alebo môžeš agregovať podľa priemeru či súčtu bodov
                last_round = year_standings.sort_values("round").groupby("subjectID").last().reset_index()

                # Premenuj stĺpce, aby mali názvy s rokom
                year_standings = last_round.rename(
                    columns={
                        "seriesID": f"{yr}",
                        "position": f"Position_{yr}",
                        "points": f"Points_{yr}",
                    }
                )[
                    ["subjectID", f"{yr}", f"Position_{yr}", f"Points_{yr}"]
                ]

                # Spoj s hlavnou tabuľkou
                merged = merged.merge(year_standings, left_on="driverID", right_on="subjectID", how="left")
                merged = merged.drop(columns=["subjectID"], errors="ignore")

            # Voliteľne — zoradiť stĺpce podľa vzoru
            base_cols = ["forename", "surname", "nationality", "age", "salary", "startYear", "endYear"]
            other_cols = [c for c in merged.columns if c not in base_cols and c != "driverID"]
            merged = merged[base_cols + other_cols]
            merged = merged.drop(columns=["teamID", "wanted_reputation", "active", "driverID"], errors="ignore")
            return merged

        contracts = contracts.drop(columns=["teamID", "wanted_reputation", "active", "driverID"], errors="ignore")
        return contracts
    """

    def get_team_series(self, team_id: int) -> list[int]:
        """
        Vráti zoznam ID sérií, v ktorých má tím kontrakt.
        """
        try:
            team_contracts = self.STcontract[self.STcontract["teamID"] == team_id]
            if team_contracts.empty:
                return []
            return team_contracts["seriesID"].astype(int).unique().tolist()
        except Exception as e:
            print(f" get_team_series error: {e}")
            return []

    def find_active_manufacturer_contracts(
            self,
            team_id: int,
            start_range: int,
            series: pd.DataFrame,
            manufacturer_model=None,
            race_model=None
    ) -> pd.DataFrame:
        """
        Nájde všetky zmluvy výrobcov (MTcontract), ktoré sú aktívne pre daný team_id
        počas daného obdobia. Doplní informácie o výrobcoch a ich výsledkoch
        (pozícia, body, séria) z posledných 3 rokov podľa typu partu (engine, chassi, pneu),
        pričom sa berú len výsledky z tej istej série, v ktorej platí kontrakt.
        """

        years = (start_range, start_range - 1, start_range - 2)

        # 🔍 Vyber všetky kontrakty pre daný tím
        mask = (
                (self.MTcontract["teamID"] == team_id)
                & (
                        (self.MTcontract["endYear"] >= start_range)
                        | (self.MTcontract["startYear"] >= start_range)
                )
        )
        contracts = self.MTcontract[mask].copy()

        if contracts.empty:
            return pd.DataFrame(columns=[
                "name", "partType", "cost", "startYear", "endYear",
                "seriesID", "Position", "Points"
            ])

        # 🔧 Spoj s tabuľkou výrobcov (ak existuje)
        if manufacturer_model is not None and hasattr(manufacturer_model, "manufacturers"):
            manu_df = manufacturer_model.manufacturers[
                ["manufacturerID", "name", "owner", "money", "engine", "chassi", "pneu", "emp"]
            ]
            contracts = contracts.merge(manu_df, on="manufacturerID", how="left")

        merged = contracts.copy()

        # 📈 Pridaj dáta zo standings (výsledky podľa partType a seriesID)
        if race_model is not None and hasattr(race_model, "standings"):
            for yr in years:
                year_standings = race_model.standings[
                    race_model.standings["year"] == yr
                    ].copy()

                year_data = []

                for _, row in contracts.iterrows():
                    part_type = row["partType"]
                    series_id = row["seriesID"]
                    manu_id = row["manufacturerID"]

                    filt = (
                            (year_standings["typ"] == part_type)
                            & (year_standings["seriesID"] == series_id)
                            & (year_standings["subjectID"] == manu_id)
                    )
                    tmp = year_standings[filt]

                    if not tmp.empty:
                        last = tmp.sort_values("round").iloc[-1]
                        # Získaj názov série
                        series_name = series.loc[series["seriesID"] == last["seriesID"], "name"].values
                        series_label = series_name[0] if len(series_name) > 0 else None

                        year_data.append({
                            "manufacturerID": manu_id,
                            "partType": part_type,
                            f"{yr}": series_label,
                            f"Position_{yr}": last["position"],
                            f"Points_{yr}": last["points"]
                        })

                if year_data:
                    df_year = pd.DataFrame(year_data)
                    merged = merged.merge(df_year, on=["manufacturerID", "partType"], how="left")

        # 🧾 Zoradenie stĺpcov: základné + roky v poradí rok → pozícia → body
        base_cols = ["name", "partType", "cost", "startYear", "endYear"]
        year_blocks = {}

        for col in merged.columns:
            if col.isdigit():
                year_blocks.setdefault(col, []).append(col)
            elif col.startswith("Position_") or col.startswith("Points_"):
                year = col.split("_")[1]
                year_blocks.setdefault(year, []).append(col)

        sorted_years = sorted(year_blocks.keys(), reverse=True)

        ordered_year_cols = []
        for y in sorted_years:
            cols = year_blocks[y]
            # zoradi: rok, pozícia, body
            cols_sorted = sorted(cols, key=lambda x: (0 if x == y else 1 if "Position" in x else 2))
            ordered_year_cols.extend(cols_sorted)

        final_cols = [c for c in base_cols if c in merged.columns] + ordered_year_cols
        final = merged[final_cols].copy()
        return final

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
        # self.DTcontract.loc[self.DTcontract["driverID"].isin(driver_ids), "en"] = False

    def disable_driver_contract(self, driver_id: int, current: bool, current_year: int) -> None:
        """
        Deaktivuje zmluvu jazdca podľa toho, či je aktuálna alebo budúca.
        """
        self._ensure_columns(self.DTcontract, {"active": True})

        if current:
            mask = (
                    (self.DTcontract["driverID"] == driver_id) &
                    (self.DTcontract["startYear"] <= current_year) &
                    (self.DTcontract["endYear"] >= current_year) &
                    (self.DTcontract["active"] == True)
            )
        else:
            mask = (
                    (self.DTcontract["driverID"] == driver_id) &
                    (self.DTcontract["startYear"] > current_year) &
                    (self.DTcontract["active"] == True)
            )

        affected = self.DTcontract.loc[mask]
        self.DTcontract.loc[mask, "active"] = False

        print(f"[ContractsModel] Deaktivovaná {'aktuálna' if current else 'budúca'} zmluva pre jazdca {driver_id}.")
        print(affected)

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

    def _generate_index(self, n: int):
        if n < 10:
            weights = [2 ** (n - i - 1) for i in range(n)]
            return random.choices(range(n), weights=weights, k=1)[0]
        while True:
            for i in range(n):
                if random.random() < 0.5:
                    return i

    def _drop_until_free_slot(self, df: pd.DataFrame) -> pd.DataFrame:
        for i, row in df.iterrows():
            if row["free_slots"] != 0:
                return df.iloc[i:]
        return df.iloc[0:0]  # ak žiadny riadok nemá voľné miesto

    def _choose_team_by_reputation(self, teams_df: pd.DataFrame) -> Optional[int]:
        if teams_df.empty:
            return None

        sorted_teams = teams_df.sort_values("reputation", ascending=False).reset_index(drop=True)
        filtered_teams = self._drop_until_free_slot(sorted_teams)
        n = len(filtered_teams)

        if n == 0:
            return None

        chosen_index = self._generate_index(n)
        # print("filtered count:", n, chosen_index)
        # Posúvaj sa smerom nahor, kým nenájdeš tím s voľným miestom
        while chosen_index >= 0 and filtered_teams.iloc[chosen_index]["free_slots"] == 0:
            chosen_index -= 1

        if chosen_index < 0:
            return None  # žiadny tím s voľným miestom

        team_id = int(filtered_teams.iloc[chosen_index]["teamID"])
        # print("team chosen_index", chosen_index, team_id)

        # with pd.option_context('display.max_columns', None, 'display.expand_frame_repr', False):
        # print(filtered_teams.head(5))

        return team_id

    def _choose_driver_by_reputation(self, drivers_df: pd.DataFrame) -> Optional[int]:
        if drivers_df.empty:
            return None
        sorted_drivers = drivers_df.sort_values("reputation_race", ascending=False).reset_index(drop=True)
        n = len(sorted_drivers)

        chosen_index = self._generate_index(n)

        # print("driver chosen_index", chosen_index, int(sorted_drivers.iloc[chosen_index]["driverID"]))
        # with pd.option_context('display.max_columns', None, 'display.expand_frame_repr', False):
        # print(sorted_drivers.head(5))

        return int(sorted_drivers.iloc[chosen_index]["driverID"])

    def _reserve_slot_for_human_team(self, team_id: int, max_cars: int) -> None:
        """Zvýši počet rezervovaných miest pre daný tím, ak ešte nedosiahol maximum."""
        current = self.reserved_slots.get(team_id, 0)
        if current < max_cars:
            self.reserved_slots[team_id] = current + 1
        print(f"Rezervované sloty: {self.reserved_slots}")

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

    def _create_driver_contract(
            self, driver_id: int, team_id: int, series_reputation: int, salary: int, start_year: int, length: int
    ) -> None:
        """Vytvorí novú jazdeckú zmluvu a aktualizuje stav systému."""
        self.DTcontract.loc[len(self.DTcontract)] = {
            "driverID": int(driver_id),
            "teamID": int(team_id),
            "salary": int(salary),
            "wanted_reputation": series_reputation,
            "startYear": int(start_year),
            "endYear": int(start_year + length),
            "active": True,
        }

        self.update_driver_slot(team_id, start_year)
        self._deactivate_lower_series_contract(driver_id, start_year, team_id)
        self._decrement_reserved_slot(team_id)

    def _get_available_drivers(
            self, active_drivers: pd.DataFrame, series: pd.DataFrame, year: int, series_id: int, team_id: int,
            rules: pd.DataFrame
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
        if "age" not in able.columns:
            if "year" not in able.columns:
                able["year"] = 0
            able["age"] = year - able["year"]

        min_age = int(rules.loc[rules["seriesID"] == series_id, "min_age"].iloc[0])
        max_age = int(rules.loc[rules["seriesID"] == series_id, "max_age"].iloc[0])

        team_series_row = self.STcontract[self.STcontract["teamID"] == team_id]
        team_series_id = int(team_series_row.iloc[0]["seriesID"]) if not team_series_row.empty else None

        # Získaj reputáciu série tímu
        series_row = series[series["seriesID"] == team_series_id]
        series_reputation = int(series_row.iloc[0]["reputation"]) if not series_row.empty else None

        # Získaj aktívne zmluvy
        active_contracts = self.DTcontract[
            (self.DTcontract["startYear"] <= year) &
            (self.DTcontract["endYear"] >= year) &
            (self.DTcontract["active"])
            ]

        unavailable_ids: List[int] = []
        for _, row in active_contracts.iterrows():
            driver_id = int(row["driverID"])
            wanted_rep = int(row.get("wanted_reputation", 0))

            # Jazdec je nedostupný, ak jeho wanted_reputation je ≤ reputácia série
            if series_reputation is not None and wanted_rep <= series_reputation:
                unavailable_ids.append(driver_id)
        # print()
        # print(able)
        # print(len(able), len(unavailable_ids))
        # teraz odfiltrujeme jednorazovo
        able = able[~able["driverID"].isin(unavailable_ids)]
        # print(len(able), len(unavailable_ids))
        able = able[(able["age"] >= min_age) & (able["age"] <= max_age)]
        # print(len(able), len(unavailable_ids), min_age, max_age, year)

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
            series: pd.DataFrame,
            temp,
            teams: pd.DataFrame,
            team_inputs: Dict[int, tuple],
    ) -> None:
        """Hlavná metóda na podpisovanie jazdeckých zmlúv."""
        self._ensure_columns(self.DTcontract, {
            "driverID": None,
            "teamID": None,
            "salary": 0,
            "wanted_reputation": 0,
            "startYear": 0,
            "endYear": 0,
            "active": True,
        })

        self._prepare_series_reputation(active_series)

        for series_id in active_series["seriesID"]:
            self._sign_current_year_contracts(series_id, teams_model, current_date, active_drivers, series, rules,
                                              team_inputs)

        if self._should_sign_today(current_date):
            self._sign_next_year_contract_if_needed(teams_model, current_date, active_drivers, series, rules, teams,
                                                    team_inputs)

    def _prepare_series_reputation(self, active_series: pd.DataFrame) -> None:
        self.series_reputation = {
            int(row["seriesID"]): float(row["reputation"])
            for _, row in active_series.iterrows()
            if "seriesID" in row and "reputation" in row
        }

    def _sign_current_year_contracts(
            self, series_id: int, teams_model, current_date: datetime,
            active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame, team_inputs: Dict[int, tuple]
    ) -> None:
        max_cars = int(rules.loc[rules["seriesID"] == series_id, "max_cars"].iloc[0])
        team_ids = self.STcontract[self.STcontract["seriesID"] == series_id]["teamID"].astype(int)

        for team_id in team_ids:
            signed = len(self._get_active_team_contracts(team_id, current_date.year))
            missing = max_cars - signed
            is_human = teams_model.teams.loc[teams_model.teams["teamID"] == team_id, "owner_id"].iloc[0] > 0

            for _ in range(missing):
                if is_human and team_inputs.get(team_id):
                    print("R")
                    self._handle_human_contract(team_id, series_id, current_date.year, active_drivers, series, rules,
                                                team_inputs)
                else:
                    if not is_human:
                        # print("M")
                        self._handle_ai_contract(team_id, series_id, current_date.year, active_drivers, series, rules)

    def _annotate_teams_with_free_slots(
            self,
            series: pd.DataFrame,
            teams: pd.DataFrame,
            rules: pd.DataFrame,
            current_year: int
    ) -> pd.DataFrame:
        teams = teams.copy()
        free_slots = []

        for _, row in teams.iterrows():
            team_id = row["teamID"]

            # Získaj seriesID z STcontract
            team_series = self.STcontract[self.STcontract["teamID"] == team_id]
            if team_series.empty:
                free_slots.append(0)
                continue

            series_id = int(team_series.iloc[0]["seriesID"])
            max_cars = int(rules.loc[rules["seriesID"] == series_id, "max_cars"].iloc[0])
            reserved = self.reserved_slots.get(team_id, 0)
            active = len(self._get_active_team_contracts(team_id, current_year + 1))

            free = max(0, max_cars - reserved - active)
            free_slots.append(free)

        teams["free_slots"] = free_slots
        return teams

    def _sign_next_year_contract_if_needed(
            self, teams_model, current_date: datetime,
            active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame,
            teams: pd.DataFrame, team_inputs: Dict[int, tuple]
    ) -> None:
        teams_updated = self._annotate_teams_with_free_slots(series, teams, rules, current_date.year)
        team_id = self._choose_team_by_reputation(teams_updated)
        if team_id is None:
            return

        is_human = teams_model.teams.loc[teams_model.teams["teamID"] == team_id, "owner_id"].iloc[0] > 0
        team_series = self.STcontract[self.STcontract["teamID"] == team_id]
        if team_series.empty:
            return

        series_id = int(team_series.iloc[0]["seriesID"])
        max_cars = int(rules.loc[rules["seriesID"] == series_id, "max_cars"].iloc[0])
        future_contracts = self._get_active_team_contracts(team_id, current_date.year + 1)
        if len(future_contracts) >= max_cars:
            return

        if is_human:
            if self.reserved_slots.get(team_id, 0) >= max_cars:
                return
            self._increment_reserved_slot(team_id, max_cars)

        available = self._get_available_drivers(active_drivers, series, current_date.year + 1, series_id, team_id,
                                                rules)
        if available.empty:
            self._decrement_reserved_slot(team_id)
            return

        if is_human:
            if team_id in team_inputs:
                print("T")
                self._handle_human_contract(team_id, series_id, current_date.year + 1, active_drivers, series, rules,
                                            team_inputs)
            return
        else:

            self._handle_ai_contract(team_id, series_id, current_date.year + 1, active_drivers, series, rules)

    def _get_reputation_by_series_id(self, df: pd.DataFrame, series_id: int) -> int | None:
        row = df.loc[df['seriesID'] == series_id]
        if not row.empty:
            return int(row.iloc[0]['reputation'])
        return None

    def _handle_human_contract(
            self, team_id: int, series_id: int, year: int,
            active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame,
            team_inputs: Dict[int, tuple]
    ) -> None:
        print("Human team:", team_id)
        driver_id, salary, length = team_inputs[team_id]
        available = self._get_available_drivers(active_drivers, series, year, series_id, team_id, rules)

        if driver_id not in available["driverID"].values:
            self._decrement_reserved_slot(team_id)
            return

        max_len = int(available.loc[available["driverID"] == driver_id, "max_contract_len"].iloc[0])
        length = min(length, max_len)
        series_reputation = self._get_reputation_by_series_id(series, series_id)
        self._create_driver_contract(driver_id, team_id, series_reputation, salary, year, length)

    def _handle_ai_contract(
            self, team_id: int, series_id: int, year: int,
            active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame
    ) -> None:
        # print("AI team:", team_id)
        available = self._get_available_drivers(active_drivers, series, year, series_id, team_id, rules)
        if available.empty:
            return

        driver_id = self._choose_driver_by_reputation(available)
        if driver_id is None:
            self._decrement_reserved_slot(team_id)
            return

        salary = self._estimate_salary(available, driver_id)
        max_len = int(available.loc[available["driverID"] == driver_id, "max_contract_len"].iloc[0])
        # Realistické rozdelenie dĺžok zmlúv v F1
        lengths = [1, 2, 3, 4]
        weights = [40, 30, 20, 10]

        # Ak je max_len menší ako 4, obmedz zoznamy
        max_len = max_len if max_len >= 1 else 1  # istota, že nebude 0 alebo menej
        lengths = lengths[:max_len]
        weights = weights[:max_len]

        # Normalizuj váhy, aby sedeli percentuálne
        total = sum(weights)
        weights = [w / total for w in weights]

        # Vyber dĺžku podľa rozdelenia
        length = random.choices(lengths, weights, k=1)[0]
        series_reputation = self._get_reputation_by_series_id(series, series_id)
        self._create_driver_contract(driver_id, team_id, series_reputation, salary, year, length)

    def _increment_reserved_slot(self, team_id: int, max_cars: int) -> None:
        """Zvýši počet rezervovaných miest pre tím, ak ešte nedosiahol maximum."""
        current = self.reserved_slots.get(team_id, 0)
        if current < max_cars:
            self.reserved_slots[team_id] = current + 1
        # print(self.reserved_slots)

    def _decrement_reserved_slot(self, team_id: int) -> None:
        """Zníži počet rezervovaných miest pre tím, ak existuje."""
        if team_id in self.reserved_slots:
            self.reserved_slots[team_id] = max(0, self.reserved_slots[team_id] - 1)

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

    def get_available_series_parts(self, team_id: int, year: int, car_parts: pd.DataFrame) -> pd.DataFrame:
        """
        Vráti súčiastky dostupné pre tím v jeho sérii v danom roku.
        """
        if not hasattr(self, "STcontract"):
            print("[ContractsModel] ⚠️ STcontract nie je inicializovaný.")
            return pd.DataFrame()

        # Zisti, v akej sérii tím pôsobí
        match = self.STcontract[self.STcontract["teamID"] == team_id]
        if match.empty:
            return pd.DataFrame()

        series_id = int(match.iloc[0]["seriesID"])
        print("C", series_id)
        # Filtrovanie podľa série a roku
        available_parts = car_parts[
            (car_parts["seriesID"] == series_id) &
            (car_parts["year"] == year)
            ].copy()

        return available_parts

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
            (teams["owner_id"] > 0) & (teams["found"] <= current_date.year) & (teams["folded"] >= current_date.year)]

        active_contracts = self.MTcontract[
            (self.MTcontract["startYear"] <= current_date.year) & (self.MTcontract["endYear"] >= current_date.year)]
        self._deduct_existing_contract_costs(human_teams, active_contracts, teams)

        new_contracts: List[Dict[str, object]] = []
        for si in active_series["seriesID"]:
            series_parts = car_parts[
                (car_parts["seriesID"] == si) & (car_parts["year"] == current_date.year)
                ]
            all_teams_in_series = self.STcontract[self.STcontract["seriesID"] == si]["teamID"].astype(int)

            # Odstráň ľudské tímy
            human_ids = set(teams_model.get_human_teams(current_date)["teamID"].astype(int).values)
            ai_teams_in_series = all_teams_in_series[~all_teams_in_series.isin(human_ids)]

            for part_type in ["engine", "chassi", "pneu"]:
                contracts = self._generate_part_contracts(
                    part_type,
                    series_parts,
                    manufacturers,
                    ai_teams_in_series,
                    active_contracts,
                    team_inputs,
                    current_date.year,
                    teams,
                )
                new_contracts.extend(contracts)

        if new_contracts:
            self.MTcontract = pd.concat([self.MTcontract, pd.DataFrame(new_contracts)], ignore_index=True)
        # === Spracovanie ľudských ponúk ===
        if hasattr(self, "pending_part_offers"):
            for offer in self.pending_part_offers:
                self.MTcontract = pd.concat([
                    self.MTcontract,
                    pd.DataFrame([{
                        "seriesID": self._get_series_for_team(offer["team_id"]),
                        "teamID": offer["team_id"],
                        "manufacturerID": self._get_manufacturer_for_part(offer["part_id"]),
                        "partType": self._get_part_type(offer["part_id"]),
                        "startYear": offer["year"],
                        "endYear": offer["year"] + offer["length"],
                        "cost": offer["price"],
                    }])
                ], ignore_index=True)

                teams_model.teams.loc[teams_model.teams["teamID"] == offer["team_id"], "money"] -= offer["price"]

            self.pending_part_offers.clear()

    def _get_series_for_team(self, team_id: int) -> int:
        match = self.STcontract[self.STcontract["teamID"] == team_id]
        return int(match["seriesID"].iloc[0]) if not match.empty else -1

    def _get_manufacturer_for_part(self, part_id: int) -> int:
        match = self.car_parts[self.car_parts["partID"] == part_id]
        return int(match["manufacturerID"].iloc[0]) if not match.empty else -1

    def _get_part_type(self, part_id: int) -> str:
        match = self.car_parts[self.car_parts["partID"] == part_id]
        return str(match["partType"].iloc[0]) if not match.empty else ""

    def offer_car_part_contract(self, manufacturer_id: int, team_id: int, length: int, price: int, year: int,
                                part_type: str) -> bool:
        """
        Pokúsi sa vytvoriť zmluvu na súčiastku. Ak tím už má zmluvu na daný typ v danom období, nič sa nevytvorí.
        """
        self._ensure_columns(self.MTcontract, {
            "seriesID": None,
            "teamID": None,
            "manufacturerID": None,
            "partType": "",
            "startYear": 0,
            "endYear": 0,
            "cost": 0,
        })

        # Skontroluj, či už existuje zmluva pre daný partType v danom období
        overlap_mask = (
                (self.MTcontract["teamID"] == team_id) &
                (self.MTcontract["partType"] == part_type) &
                (self.MTcontract["startYear"] <= year + length - 1) &
                (self.MTcontract["endYear"] >= year)
        )

        if overlap_mask.any():
            print(f"[ContractsModel] Tím {team_id} už má zmluvu na {part_type} v období {year}–{year + length - 1}.")
            return False  # nič sa nevytvorí

        # Zisti sériu tímu
        match = self.STcontract[self.STcontract["teamID"] == team_id]
        if match.empty:
            print(f"[ContractsModel]  Tím {team_id} nemá sériu, zmluva sa nevytvorí.")
            return False

        series_id = int(match.iloc[0]["seriesID"])

        # Vytvor novú zmluvu
        new_contract = {
            "seriesID": series_id,
            "teamID": team_id,
            "manufacturerID": manufacturer_id,
            "partType": part_type,
            "startYear": year,
            "endYear": year + length - 1,
            "cost": price,
        }

        self.MTcontract = pd.concat([self.MTcontract, pd.DataFrame([new_contract])], ignore_index=True)
        print(
            f"[ContractsModel] ✅ Nová zmluva na {part_type} od výrobcu {manufacturer_id} pre tím {team_id} vytvorená.")
        return True

    def get_available_drivers_for_offer(
            self, team_id: int, year: int, active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Vráti zoznam jazdcov, ktorých môže tím (hráč) podpísať pre daný rok.
        """
        team_row = self.STcontract[self.STcontract["teamID"] == team_id]
        if team_row.empty:
            print("teamrow empty")
            return pd.DataFrame()
        series_id = int(team_row.iloc[0]["seriesID"])
        print(len(active_drivers), year, series_id, team_id,
              len(self._get_available_drivers(active_drivers, series, year, series_id, team_id, rules)))
        return self._get_available_drivers(active_drivers, series, year, series_id, team_id, rules)

    def offer_driver_contract(
            self, driver_id: int, team_id: int, salary: int, length: int, year: int
    ) -> None:
        """
        Vytvorí ponuku zmluvy (pending) – jazdec sa rozhodne nasledujúci deň.
        """
        if not hasattr(self, "pending_offers"):
            self.pending_offers: List[Dict[str, int]] = []
        team_series = self.STcontract[self.STcontract["teamID"] == team_id]
        if team_series.empty:
            print(f" Tím {team_id} nemá sériu – nie je možné ponúknuť kontrakt.")
            return

        offer = {
            "driver_id": int(driver_id),
            "team_id": int(team_id),
            "salary": int(salary),
            "length": int(length),
            "year": int(year),
            "days_pending": 1,  # jazdec sa rozhodne do jedného dňa
        }
        self.pending_offers.append(offer)
        print(f"[ContractsModel] Ponuka pre jazdca {driver_id} vytvorená (rok {year}).")

    def process_driver_offers(self, current_date: datetime, active_drivers: pd.DataFrame) -> List[Dict]:

        """
        Spracuje čakajúce ponuky – jazdec sa rozhodne, či prijme kontrakt.
        Volá sa typicky pri posune dňa.
        """

        if not hasattr(self, "pending_offers") or not self.pending_offers:
            return []
        signed_contracts = []

        remaining_offers = []
        print("pocet zmluv v pending", self.pending_offers)

        for offer in self.pending_offers:
            driver_id = offer["driver_id"]
            team_id = offer["team_id"]
            salary = offer["salary"]
            length = offer["length"]
            year = offer["year"]

            # Získaj pozíciu jazdca podľa reputácie
            drivers_sorted = active_drivers.sort_values("reputation_race", ascending=False).reset_index(drop=True)
            driver_pos = drivers_sorted[drivers_sorted["driverID"] == driver_id].index
            if driver_pos.empty:
                print(f" Jazdec {driver_id} nie je medzi aktívnymi.")
                continue

            position = driver_pos[0] + 1
            min_salary = 4000000 // position

            # Získaj info o tíme a sérii
            team_series = self.STcontract[self.STcontract["teamID"] == team_id]
            if team_series.empty:
                print(f" Tím {team_id} nemá sériu.")
                continue

            series_id = int(team_series.iloc[0]["seriesID"])
            max_cars = int(self.rules.loc[self.rules["seriesID"] == series_id, "max_cars"].iloc[0])
            reserved = self.reserved_slots.get(team_id, 0)
            active_contracts = self._get_active_team_contracts(team_id, year)
            active = len(active_contracts)

            # === Rozhodovanie podľa roku ===
            if year == current_date.year:
                # Zmluva na tento rok → kontroluj aktívne miesta
                if salary >= min_salary and active < max_cars:
                    print(f" Jazdec {driver_id} prijal ponuku s tímom {team_id} (tento rok).")
                    self._create_driver_contract(driver_id, team_id, 0, salary, year, length - 1)
                    signed_contracts.append({
                        "driver_id": driver_id,
                        "team_id": team_id,
                        "salary": salary,
                        "year": year
                    })

                else:
                    print(
                        f" Jazdec {driver_id} odmietol ponuku (tento rok) – plat {salary} < {min_salary} alebo tím plný.")
            elif year == current_date.year + 1:
                # Zmluva na budúci rok → kontroluj rezervácie
                if reserved > 0 and salary >= min_salary and (reserved + active) <= max_cars:
                    print(f" Jazdec {driver_id} prijal ponuku s tímom {team_id} (budúci rok).")
                    self._create_driver_contract(driver_id, team_id, 0, salary, year, length - 1)
                    self._decrement_reserved_slot(team_id)
                else:
                    print(
                        f" Jazdec {driver_id} odmietol ponuku (budúci rok) – plat {salary} < {min_salary} alebo tím nemá rezerváciu.")
            else:
                print(f" Neznámy rok {year} – ponuka ignorovaná.")

        self.pending_offers = remaining_offers
        print("premazavam pending", self.pending_offers, current_date, "reserved", self.reserved_slots)
        return signed_contracts

    def reset_reserved_slot(self) -> None:
        """Resetuje hodnoty rezervovaných slotov na 0, ponechá existujúce teamID."""
        for team_id in self.reserved_slots:
            self.reserved_slots[team_id] = 0

    def cancel_driver_offer(self, driver_id: int, team_id: int) -> None:
        """Zruší čakajúcu ponuku na zmluvu (ak existuje)."""
        if not hasattr(self, "pending_offers"):
            return
        self.pending_offers = [
            o for o in self.pending_offers if not (o["driver_id"] == driver_id and o["team_id"] == team_id)
        ]
        self._decrement_reserved_slot(team_id)
        print(f"[ContractsModel] Ponuka pre jazdca {driver_id} zrušená.")

    def get_terminable_contracts(self, team_id: int, current_year: int) -> pd.DataFrame:
        """
        Vráti zmluvy, ktoré sú aktívne od aktuálneho roku ďalej, spolu s nákladmi na ukončenie
        a indikátorom, či sú aktuálne platné.
        """
        contracts = self.DTcontract[
            (self.DTcontract["teamID"] == team_id) &
            (self.DTcontract["active"] == True) &
            (self.DTcontract["endYear"] >= current_year)
            ].copy()

        if contracts.empty:
            return contracts

        contracts["termination_cost"] = contracts.apply(
            lambda row: max(0, row["endYear"] - current_year) * row["salary"],
            axis=1
        )

        contracts["current"] = contracts["startYear"] <= current_year

        return contracts

    def terminate_driver_contract(self, driver_id: int, team_id: int, current_year: int) -> int:
        """
        Ukončí zmluvu jazdca a vráti náklady na ukončenie.
        """
        mask = (
                (self.DTcontract["driverID"] == driver_id) &
                (self.DTcontract["teamID"] == team_id) &
                (self.DTcontract["endYear"] >= current_year)
        )
        contract = self.DTcontract[mask]

        if contract.empty:
            return 0

        salary = int(contract.iloc[0]["salary"])
        end_year = int(contract.iloc[0]["endYear"])
        cost = max(0, end_year - current_year) * salary

        # Odstráň zmluvu
        self.DTcontract = self.DTcontract.drop(contract.index)
        print(f"[ContractsModel] Zmluva jazdca {driver_id} ukončená. Náklady: {cost}")
        return cost

    def get_active_part_contracts_for_year(self, year: int) -> pd.DataFrame:
        """
        Vráti všetky zmluvy na súčiastky (MTcontract), ktoré sú aktívne v danom roku.
        """
        self._ensure_columns(self.MTcontract, {
            "seriesID": None,
            "teamID": None,
            "manufacturerID": None,
            "partType": "",
            "startYear": 0,
            "endYear": 0,
            "cost": 0,
        })

        active = self.MTcontract[
            (self.MTcontract["startYear"] <= year) &
            (self.MTcontract["endYear"] >= year)
            ].copy()

        return active
