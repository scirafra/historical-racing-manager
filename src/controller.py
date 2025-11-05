import os
import time
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

import load as ld
from contracts import ContractsModel
from drivers import DriversModel
from graphics import Graphics
from manufacturer import ManufacturerModel
from race import RaceModel
from series import SeriesModel
from teams import TeamsModel


class Controller:
    def __init__(self):
        self.begin_year = 1843
        self.end_year = 3000
        self.drivers_per_year = 4
        self.sim_years_step = 36

        self.begin_date = datetime.strptime(f"01-01-{self.begin_year}", "%d-%m-%Y")
        self.current_date = self.begin_date
        self.new_game = True
        self.ss = time.time()

        self._initialize_models()
        self.view = Graphics(self)

    def _initialize_models(self):
        self.drivers_model = DriversModel()
        self.teams_model = TeamsModel()
        self.series_model = SeriesModel()
        self.manufacturer_model = ManufacturerModel()
        self.contracts_model = ContractsModel()
        self.race_model = RaceModel()

    def run(self):
        self.view.run()

    def get_team_list(self) -> list[dict]:
        """
        Vráti zoznam názvov tímov, ktoré už majú majiteľa (owner_id > 0).
        """
        teams_df = self.teams_model.get_teams()

        if teams_df.empty:
            return []

        owned_teams = teams_df.query("owner_id > 0")

        if owned_teams.empty:
            return []

        return [
            {"team_name": row.team_name, "owner_id": row.owner_id}
            for row in owned_teams.itertuples()
        ]

    def on_team_selected(self, value: str):
        """
        Callback volaný z GUI pri zmene tímu v ComboBoxe.
        """
        try:
            if not value or "(" not in value:
                return

            team_name = value.split("(")[0].strip()
            self.set_active_team(team_name)

        except Exception as e:
            print(f"[Controller] Chyba pri výbere tímu: {e}")

    def set_active_team(self, team_name: str):
        """
        Nastaví aktívny tím podľa mena a aktualizuje My Team tab.
        """
        try:
            teams_df = self.teams_model.get_teams()
            match = teams_df[teams_df["team_name"] == team_name]

            if match.empty:
                print(f"[Controller]  Tím '{team_name}' sa nenašiel.")
                return

            self.active_team = team_name
            self.active_team_id = int(match.iloc[0]["teamID"])
            print(f"[Controller]  Aktívny tím nastavený na {team_name} (ID {self.active_team_id})")

            #  automatická aktualizácia My Team tabu
            self.refresh_myteam()

        except Exception as e:
            print(f"[Controller]  Chyba pri nastavovaní aktívneho tímu: {e}")

    def get_active_team(self) -> str:
        """
        Vráti názov aktuálneho aktívneho tímu, ak je nastavený.
        """
        return getattr(self, "active_team", None)

    def get_active_team_id(self) -> int | None:
        """
        Vráti ID aktuálneho aktívneho tímu, ak je nastavený.
        """
        return getattr(self, "active_team_id", None)

    def get_owners_team_driver_data(self):
        return self.contracts_model.find_active_driver_contracts(self.active_team_id, self.get_year(),
                                                                 self.series_model.get_series(),
                                                                 self.drivers_model.get_active_drivers(),
                                                                 self.race_model
                                                                 )

    def get_active_team_info(self) -> dict:
        """Vracia všetky dáta o aktívnom tíme."""
        team_id = self.get_active_team_id()
        team_name = self.get_active_team()
        money = int(self.teams_model.teams.loc[self.teams_model.teams["teamID"] == team_id, "money"].iloc[0])

        return {
            "name": team_name,
            "budget": money,
            "drivers": self.get_owners_team_driver_data(),
            "parts": self.get_owners_team_parts_data(),
            "staff": self.get_team_staff(team_id),
            "races": self.get_upcoming_races(team_id),
        }

    def get_team_selector_values(self) -> list[str]:
        teams_df = self.teams_model.get_teams()
        if teams_df.empty:
            return []

        values = []
        for _, row in teams_df.iterrows():
            owner = row["owner_id"]
            if owner > 0:
                owner_text = f"Owner {owner}"
                values.append(f"{row['team_name']} ({owner_text})")
        return values

    def get_myteam_tab_data(self) -> dict:
        """
        Vracia všetky dáta potrebné pre My Team tabuľku:
        - názov tímu
        - rozpočet
        - DataFrame s jazdcami
        - DataFrame s komponentmi
        - DataFrame so staff
        - DataFrame s nadchádzajúcimi pretekmi
        """
        try:
            team_info = self.get_active_team_info()

            return {
                "team_name": team_info["name"],
                "budget": team_info["budget"],
                "drivers": team_info["drivers"],
                "components": team_info["parts"],
                "staff": team_info["staff"],
                "races": team_info["races"],
            }

        except Exception as e:
            print(f" get_myteam_tab_data error: {e}")
            # fallback – prázdne tabuľky, aby GUI nezlyhalo
            empty = pd.DataFrame()
            return {
                "team_name": "No Team Selected",
                "budget": 0,
                "drivers": empty,
                "components": empty,
                "staff": empty,
                "races": empty,
            }

    def get_team_staff(self, team_id: int) -> pd.DataFrame:
        """
        Vracia informácie o zamestnancoch daného tímu podľa tabuľky teams.
        Obsahuje stĺpce: Department, Employees, Next Year.
        """
        try:
            team = self.teams_model.get_team_staff_counts(team_id)
            if team.empty:
                return pd.DataFrame(columns=["Department", "Employees"])

            finance = int(team["finance_employees"].iloc[0])
            design = int(team["design_employees"].iloc[0])

            data = [
                {"Department": "Finance", "Employees": finance},
                {"Department": "Design", "Employees": design},
            ]

            return pd.DataFrame(data)

        except Exception as e:
            print(f" get_team_staff error: {e}")
            return pd.DataFrame(columns=["Department", "Employees"])

    def get_upcoming_races(self, team_id: int) -> pd.DataFrame:
        """
        Vracia nadchádzajúce preteky pre série, v ktorých má tím kontrakt.
        """
        try:
            #  Zisti, v akých sériách má tím kontrakt
            series_ids = self.contracts_model.get_team_series(team_id)
            if not series_ids:
                return pd.DataFrame(columns=["Date", "Race Name", "Series"])

            # Získaj nadchádzajúcich 5 pretekov pre tieto série
            upcoming = self.race_model.get_upcoming_races_for_series(series_ids, self.series_model.get_series(),
                                                                     self.current_date)
            return upcoming

        except Exception as e:
            print(f" get_upcoming_races error: {e}")
            return pd.DataFrame(columns=["Date", "Race Name", "Series"])

    def refresh_myteam(self):
        """
        Znovu načíta My Team tab z aktuálnych dát.
        Volá sa po zmene tímu, po simulácii, alebo po zmene tabu.
        """

        try:
            if hasattr(self, "view") and hasattr(self.view, "refresh_myteam_tab"):
                self.view.refresh_myteam_tab()
                print("[Controller]  My Team tab refreshed.")
            else:
                print("[Controller]  View nie je inicializovaný, refresh preskočený.")
        except Exception as e:
            print(f"[Controller]  Chyba pri refreshi My Team tabu: {e}")

    def get_owners_team_parts_data(self):
        return self.contracts_model.find_active_manufacturer_contracts(self.active_team_id, self.get_year(),
                                                                       self.series_model.get_series(),
                                                                       self.manufacturer_model, self.race_model)

    def get_owners_team_future_data(self, team_id):
        return

    def get_date(self) -> str:
        return self.current_date.strftime("%Y-%m-%d %A")

    def get_year(self) -> int:
        return self.current_date.year

    def get_series_names(self):
        return self.series_model.get_series()["name"].tolist()

    def get_names(self, subject_type: str):
        if subject_type == "Seasons":
            return self.series_model.get_series()["name"].tolist()
        if subject_type == "Manufacturers":
            return self.manufacturer_model.get_manufacturers()["name"].tolist()
        if subject_type == "Drivers":
            df = self.drivers_model.get_drivers()
            df["name"] = df["forename"] + " " + df["surname"]

            return df["name"].tolist()
        if subject_type == "Teams":
            return self.teams_model.get_teams()["team_name"].tolist()
        if subject_type == "Series":
            return self.series_model.get_series()["name"].tolist()
        return None

    def update_seasons(self, series_name: str):
        sid = self.series_model.get_series_id(series_name)
        self.seasons = self.race_model.get_seasons_for_series(sid)

    def get_season_list(self):
        return [str(y) for y in self.seasons]

    def simulate_days(self, days: int):
        self.current_date = self.sim_day(self.current_date, days)
        self.refresh_myteam()

    def sim_day(self, date: datetime, days: int) -> datetime:
        for _ in range(days):
            date += timedelta(days=1)
            if self._is_season_start(date):
                print("start of season", self.get_year())
                self._handle_season_start(date)
                with pd.option_context('display.max_columns', None, 'display.expand_frame_repr', False):
                    print(self.teams_model.teams.sort_values(by="reputation", ascending=False))
                #  print(self.drivers_model.active_drivers.sort_values(by="reputation_race", ascending=False).head(50))
            if date.year >= 1894:
                """
                driver_inputs = self.view.ask_driver_contracts(
                    self.teams_model.get_human_teams(date),
                    self.drivers_model.active_drivers,
                    date.year
                )
                """
                driver_inputs = {}
                self.contracts_model.sign_driver_contracts(
                    active_series=self.series_model.get_active_series(date.year),
                    teams_model=self.teams_model,
                    current_date=date,
                    active_drivers=self.drivers_model.active_drivers,
                    rules=self.series_model.point_rules,
                    series=self.series_model.series,
                    temp=False,
                    teams=self.teams_model.teams,
                    team_inputs=driver_inputs,
                )
            self._simulate_race_day(date)
            self.process_driver_offers()
        return date

    def sim_year(self, start_date: datetime, years: int) -> datetime:
        for _ in range(years * 365):
            start_date = self.sim_day(start_date, 1)
        return start_date

    def start_new_season(self):
        self.load_game("my_data")
        self.current_date = self.sim_year(self.current_date, self.sim_years_step)

    def save_game(self, name: str):
        if not os.path.isdir(name):
            os.makedirs(name, exist_ok=True)

        meta = pd.DataFrame({
            "date": [self.current_date.strftime("%Y-%m-%d")],
            "begin": [self.begin_date.strftime("%Y-%m-%d")],
            "new_game": [self.new_game]
        })
        meta.to_csv(f"{name}/data.csv", index=False)

        ld.save(
            name,
            self.teams_model,
            self.series_model,
            self.drivers_model,
            self.manufacturer_model,
            self.contracts_model,
            self.race_model,
        )

    def load_game(self, name: str):
        if not os.path.exists(f"{name}/data.csv"):
            return False

        meta = pd.read_csv(f"{name}/data.csv")
        self.current_date = datetime.strptime(meta.loc[0, "date"], "%Y-%m-%d")
        self.begin_date = datetime.strptime(meta.loc[0, "begin"], "%Y-%m-%d")
        self.begin_year = self.begin_date.year
        self.new_game = bool(meta.loc[0, "new_game"])

        ld.load_all(
            name,
            self.series_model,
            self.teams_model,
            self.drivers_model,
            self.manufacturer_model,
            self.contracts_model,
            self.race_model,
        )

        self.drivers_model.choose_active_drivers(self.current_date)

        # Inicializácia slotov
        self.contracts_model.driver_slots_current = self.contracts_model.init_driver_slots_for_year(
            self.current_date.year, self.series_model.point_rules
        )
        self.contracts_model.driver_slots_next = self.contracts_model.init_driver_slots_for_year(
            self.current_date.year + 1, self.series_model.point_rules
        )

        while self.current_date.year < 1894:
            self.current_date = self.sim_day(self.current_date, 1)

        self.new_game = False

        self.refresh_myteam()
        return True

    def kick_driver(self, team_id: int, driver_id: int):
        self.contracts_model.terminate_driver_contract(team_id, driver_id, self.current_date.year)

    def get_active_driver_contracts(self):
        return self.contracts_model.DTcontract[self.contracts_model.DTcontract["active"]]

    def get_human_teams(self, date: datetime) -> pd.DataFrame:
        """
        Wrapper pre získanie tímov, ktoré sú riadené hráčom pre dané dátumové obdobie.
        Očakáva sa, že TeamsModel poskytuje metódu get_human_teams(date).
        """
        try:
            return self.teams_model.get_human_teams(date)
        except Exception:
            return pd.DataFrame()

    def _is_season_start(self, date: datetime) -> bool:
        return 2999 > date.year and date.day == 1 and date.month == 1

    def _deduct_all_contracts_for_year(self, year: int):
        contracts = self.contracts_model.get_contracts_for_year(year)
        for _, row in contracts.iterrows():
            self.teams_model.deduct_money(row["teamID"], row["salary"])
            print(f"💸 Tím {row['teamID']} zaplatil {row['salary']} za jazdca {row['driverID']} v roku {year}.")

    def _handle_season_start(self, date: datetime):

        if date.year > 1896:
            self.race_model.plan_races(self.series_model, date)

        self._update_entities_for_new_season(date)

        # Prekopírovanie slotov
        self.contracts_model.rollover_driver_slots()
        self.contracts_model.reset_reserved_slot()

        if date.year >= 1894:
            self._handle_contracts(date)
            self._deduct_all_contracts_for_year(date.year)

        # Poznámka: investície sa už nespúšťajú automaticky pri štarte sezóny.
        # Používateľ spúšťa investície cez tlačidlo v GUI.

    def _update_entities_for_new_season(self, date: datetime):
        self.contracts_model.disable_driver_contracts(self.drivers_model.get_retiring_drivers())
        self.drivers_model.update_drivers(date)
        self.drivers_model.update_reputations()
        self.teams_model.update_reputations()
        self.drivers_model.choose_active_drivers(date)
        self.race_model.all_time_best(self.drivers_model, 1)

    def _handle_contracts(self, date: datetime):
        self.manufacturer_model.develop_part(date, self.contracts_model.get_MScontract())

        """car_part_inputs = self.view.ask_car_part_contracts(
            self.teams_model.get_human_teams(date),
            self.manufacturer_model.car_parts,
            date.year
        )"""
        car_part_inputs = {}
        self.contracts_model.sign_car_part_contracts(
            active_series=self.series_model.get_active_series(date.year),
            current_date=date,
            car_parts=self.manufacturer_model.car_parts,
            teams_model=self.teams_model,
            manufacturers=self.manufacturer_model.manufacturers,
            team_inputs=car_part_inputs,
        )

    def _handle_investments(self, date: datetime):
        # interná metóda; ponechaná pre prípady, keď je potrebné spúšťať investície programovo
        investments = self.view.ask_finance_investments(self.teams_model.get_human_teams(date))
        self.teams_model.invest_finance(date.year, investments)

    def apply_investments(self, year: int, investments: Any):
        """
        Verejná metóda, ktorú môže GUI zavolať pre aplikovanie investícií.
        investments môže byť dict {team_id: amount} alebo list of dicts [{'team_id':..,'investment':..}, ...].
        """
        if investments is None:
            return
        if isinstance(investments, dict):
            try:
                self.teams_model.invest_finance(year, investments)
                return
            except Exception:
                # fallback: pokus spracovať položky jednotlivo
                conv = {}
                for k, v in investments.items():
                    try:
                        conv[int(k)] = int(v)
                    except Exception:
                        continue
                if conv:
                    self.teams_model.invest_finance(year, conv)
                return

        if isinstance(investments, list):
            conv = {}
            for item in investments:
                try:
                    tid = int(item.get("team_id"))
                    amt = int(item.get("investment"))
                    conv[tid] = amt
                except Exception:
                    continue
            if conv:
                self.teams_model.invest_finance(year, conv)

    def get_available_drivers_for_offer(self, next_year: bool = False) -> pd.DataFrame:
        """
        Vráti DataFrame s jazdcami, ktorých môže aktívny tím podpísať
        (pre aktuálny alebo budúci rok podľa parametra next_year).
        """
        try:
            team_id = self.get_active_team_id()
            if not team_id:
                print("Žiadny aktívny tím nie je nastavený.")
                return pd.DataFrame()

            year = self.get_year() + (1 if next_year else 0)
            active_drivers = self.drivers_model.get_active_drivers()
            rules = self.series_model.point_rules

            df = self.contracts_model.get_available_drivers_for_offer(
                team_id=team_id,
                year=year,
                active_drivers=active_drivers,
                series=self.series_model.series,
                rules=rules
            )
            print(f"[Controller]  Našiel som {len(df)} dostupných jazdcov pre rok {year}.")
            return df
        except Exception as e:
            print(f"[Controller]  Chyba pri načítaní dostupných jazdcov: {e}")
            return pd.DataFrame()

    def offer_driver_contract(self, driver_id: int, salary: int, length: int, next_year: bool = False):
        """
        Ponúkne zmluvu jazdcovi pre aktuálny alebo budúci rok.
        Jazdec sa rozhodne pri nasledujúcom posune dňa.
        """
        try:
            team_id = self.get_active_team_id()
            if not team_id:
                print("Najprv musíš mať vybraný tím.")
                return False

            year = self.get_year() + (1 if next_year else 0)
            self.contracts_model.offer_driver_contract(driver_id, team_id, salary, length, year)
            print(f"[Controller]  Ponuka zmluvy pre jazdca {driver_id} (rok {year}) vytvorená.")
            return True
        except Exception as e:
            print(f"[Controller]  Chyba pri vytváraní ponuky: {e}")
            return False

    def process_driver_offers(self):
        """
        Spracuje všetky čakajúce ponuky jazdcov (hráčove aj AI),
        či boli prijaté alebo odmietnuté.
        """
        try:
            signed = self.contracts_model.process_driver_offers(
                self.current_date,
                self.drivers_model.get_active_drivers_with_reputation()
            )
            for contract in signed:
                if contract["year"] == self.get_year():
                    self.teams_model.deduct_money(contract["team_id"], contract["salary"])

            # self.refresh_myteam()
            # print("[Controller]  Spracované všetky ponuky jazdcov.")
        except Exception as e:
            print(f"[Controller]  Chyba pri spracovaní ponúk: {e}")

    def _simulate_race_day(self, date: datetime):
        races_today = self.race_model.races[self.race_model.races["race_date"] == date].copy()
        if races_today.empty:
            return

        died = []
        for i in range(len(races_today)):
            died += self.race_model.prepare_race(
                self.drivers_model,
                self.teams_model,
                self.series_model,
                self.manufacturer_model,
                self.contracts_model,
                races_today,
                i,
                date,
            )

        if died:
            self.drivers_model.mark_drivers_dead(died, date.year)
            self.contracts_model.disable_driver_contracts(died)

            if date.year >= 1894:
                self.contracts_model.sign_driver_contracts(
                    active_series=self.series_model.get_active_series(date.year),
                    teams_model=self.teams_model,
                    current_date=date,
                    active_drivers=self.drivers_model.active_drivers,
                    rules=self.series_model.point_rules,
                    series=self.series_model.series,
                    temp=True,
                    teams=self.teams_model.teams,
                    team_inputs={},  # AI fallback only
                )

    # Výstupy / formátovanie výsledkov pre GUI
    def get_results(self, series_name: str, season_str: str) -> pd.DataFrame:
        sid = self.series_model.get_series_id(series_name)
        if not season_str or not season_str.strip().isdigit():
            return pd.DataFrame()

        season = int(season_str)

        df = self.race_model.pivot_results_by_race(sid, season, self.manufacturer_model.get_manufacturers())
        return self._format_results(df, season)

    def get_stats(self, subject_name: str, stats_type: str, manufacturer_type: str) -> pd.DataFrame:

        if stats_type == "Drivers":
            if not subject_name or not stats_type:
                return pd.DataFrame()
            name = subject_name.split()

            sid = self.drivers_model.get_driver_id(name[0], name[-1])

            df = self.race_model.get_subject_season_stands(sid, "driver", self.series_model.get_series())
            return df  # self._format_results(df, season)
        elif stats_type == "Manufacturers":
            if not subject_name or not stats_type or not manufacturer_type:
                return pd.DataFrame()

            mid = self.manufacturer_model.get_manufacturers_id(subject_name)
            df = self.race_model.get_subject_season_stands(mid, manufacturer_type, self.series_model.get_series())
            return df  # self._format_results(df, season)
        elif stats_type == "Teams":
            if not subject_name or not stats_type:
                return pd.DataFrame()

            tid = self.teams_model.get_teams_id(subject_name)

            df = self.race_model.get_subject_season_stands(tid, "team", self.series_model.get_series())
            return df  # self._format_results(df, season)
        elif stats_type == "Series":
            if not subject_name or not stats_type:
                return pd.DataFrame()

            sid = self.series_model.get_series_id(subject_name)

            df = self.race_model.extract_champions(sid, self.series_model.get_series(),
                                                   self.manufacturer_model.get_manufacturers(),
                                                   self.teams_model.get_teams(), self.drivers_model.get_drivers())
            return df  # self._format_results(df, season)
        return None

    def _format_results(self, df: pd.DataFrame, season: int) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        # Mapovanie manufacturerID → názov
        mf_map = self.manufacturer_model.manufacturers.set_index("manufacturerID")["name"].to_dict()

        # Spracovanie stĺpcov engine/chassi/pneu alebo engineID/chassiID/pneuID
        part_columns = {
            "engine": "Engine",
            "engineID": "Engine",
            "chassi": "Chassi",
            "chassiID": "Chassi",
            "pneu": "Tyres",
            "pneuID": "Tyres"
        }

        for raw_col, final_col in part_columns.items():
            if raw_col in df.columns:
                if df[raw_col].dtype in ("int64", "float64"):
                    df[final_col] = (
                        df[raw_col].fillna(0).astype(int).map(mf_map).fillna(df[raw_col].astype(str))
                    )
                else:
                    df[final_col] = df[raw_col]
                df.drop(columns=[raw_col], inplace=True)

        # Pridaj meno a vek jazdca
        df = df.merge(
            self.drivers_model.drivers[["driverID", "forename", "surname", "year"]],
            on="driverID", how="left"
        )
        df["Age"] = season - df["year"]
        df.drop(columns=["year", "driverID"], inplace=True)

        # Pridaj názov tímu
        df = df.merge(
            self.teams_model.teams[["teamID", "team_name"]],
            on="teamID", how="left"
        )
        df.drop(columns=["teamID"], inplace=True)

        # Premenuj stĺpce
        df.rename(columns={
            "forename": "Forename",
            "surname": "Surname",
            "team_name": "Team Name",
            "final_position": "Position",
            "final_points": "Points",
        }, inplace=True)

        # Zoradenie podľa pozície
        if "Position" in df.columns:
            df.sort_values("Position", inplace=True)

        # Zoradenie stĺpcov: základné + ostatné
        base_cols = ["Forename", "Surname", "Age", "Team Name"]
        for extra in ("Engine", "Chassi", "Tyres", "Position", "Points"):
            if extra in df.columns:
                base_cols.append(extra)

        others = [c for c in df.columns if c not in base_cols]
        df = df[base_cols + others]

        # Formátovanie pozícií v jednotlivých kolách
        def fmt(x):
            if x in ("Crash", "Death"):
                return x
            try:
                return str(int(float(x)))
            except Exception:
                return ""

        for col in others:
            df[col] = df[col].apply(fmt)

        return df
