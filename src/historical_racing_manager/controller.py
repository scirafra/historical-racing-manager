import pathlib
import time
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from dateutil.relativedelta import relativedelta

from historical_racing_manager.consts import (
    FILE_CONTROLLER_DATA, FILE_CONTROLLER_GENERATED_RACES, CONTROLLER_REQUIRED_FILES,
    DEFAULT_BEGIN_YEAR, DEFAULT_END_YEAR, DEFAULT_DRIVERS_PER_YEAR, DEFAULT_SIM_YEARS_STEP,
    SEASON_START_DAY, SEASON_START_MONTH, FIRST_REAL_SEASON_YEAR, FIRST_RACE_PLANNING_YEAR
)
# TODO: you could do: import historical_racing_manager.consts as consts and then use consts.DEFAULT_BEGIN_YEAR etc.
from historical_racing_manager.contracts import ContractsModel
from historical_racing_manager.drivers import DriversModel
from historical_racing_manager.graphics import Graphics
from historical_racing_manager.load import LoadManager
from historical_racing_manager.manufacturer import ManufacturerModel
from historical_racing_manager.race import RaceModel
from historical_racing_manager.series import SeriesModel
from historical_racing_manager.teams import TeamsModel

PACKAGE_DIR = pathlib.Path(__file__).parent
# TODO: Alternatively could use: USER_DIR = pathlib.Path.home() / ".hrm" instead of working dir
USER_DIR = pathlib.Path.cwd()


class Controller:
    teams = 0

    def __init__(self):
        self.begin_year = DEFAULT_BEGIN_YEAR
        self.end_year = DEFAULT_END_YEAR
        self.drivers_per_year = DEFAULT_DRIVERS_PER_YEAR
        self.sim_years_step = DEFAULT_SIM_YEARS_STEP

        self.begin_date = datetime.strptime(f"01-01-{self.begin_year}", "%d-%m-%Y")
        self.current_date = self.begin_date
        self.new_game = True
        self.ss = time.time()
        self.generated_races = pd.DataFrame()
        self._initialize_models()
        self.teams = 0
        self.view = Graphics(self)

    def _initialize_models(self):
        self.load_model = LoadManager()
        self.drivers_model = DriversModel()
        self.teams_model = TeamsModel()
        self.series_model = SeriesModel()
        self.manufacturer_model = ManufacturerModel()
        self.contracts_model = ContractsModel()
        self.race_model = RaceModel()

    def run(self):
        self.view.run()

    def _set_default_active_team(self):
        """
        Sets the active team to the first team in the list whose owner_id > 0.
        Safely ignores the case where no team is owned.
        """
        try:
            teams = self.get_team_list()  # returns a list of dicts {"team_name", "owner_id"}
            if not teams:
                return False
            first_team_name = teams[0]["team_name"]
            self.set_active_team(first_team_name)
            return True
        except Exception as e:
            print(f"[Controller] set_default_active_team error: {e}")
            return False

    def get_team_list(self) -> list[dict]:
        """
        Returns a list of team names that already have an owner (owner_id > 0).
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
        Callback invoked from the GUI when the team is changed in the ComboBox.
        """
        try:
            if not value or "(" not in value:
                return

            team_name = value.split("(")[0].strip()
            self.set_active_team(team_name)

        except Exception as e:
            print(f"[Controller] Error selecting team: {e}")

    def set_active_team(self, team_name: str):
        """
        Sets the active team by name and refreshes the My Team tab.
        """

        try:
            teams_df = self.teams_model.get_teams()
            match = teams_df[teams_df["team_name"] == team_name]

            if match.empty:
                return

            self.active_team = team_name
            self.active_team_id = int(match.iloc[0]["team_id"])

            # Automatically refresh the My Team tab
            self.refresh_myteam()

        except Exception as e:
            print(f"[Controller] Error setting active team: {e}")

    def get_active_team(self) -> str:
        """
        Returns the name of the current active team, if set.
        """
        return getattr(self, "active_team", None)

    def get_active_team_id(self) -> int | None:
        """
        Returns the ID of the current active team, if set.
        """

        return getattr(self, "active_team_id", None)

    def get_owners_team_driver_data(self):
        return self.contracts_model.find_active_driver_contracts(
            self.active_team_id,
            self.current_date.year,
            self.series_model.get_series(),
            self.drivers_model.get_active_drivers(),
            self.race_model
        )

    def get_team_money_and_finance_employees(self) -> tuple[int, int, int, int]:
        """
        Returns (finance_employees, max_possible_employees, employee_salary, kick_price) for the active team.
        """
        team_id = self.get_active_team_id()
        team = self.teams_model.teams[self.teams_model.teams["team_id"] == team_id]
        if team.empty:
            print(f"[Controller] Team {team_id} does not exist.")
            return 0, 0, 0, 0

        row = team.iloc[0]
        money = int(row["money"])
        max_affordable = TeamsModel.max_affordable_finance(money)

        finance_employees = int(row["finance_employees"])
        employee_salary = self.teams_model.get_finance_employee_salary()
        kick_price = self.teams_model.get_kick_employee_price()

        return finance_employees, finance_employees + max_affordable, employee_salary, kick_price

    def count_active_contracts(self, df: pd.DataFrame, year: int) -> int:
        return df[(df["start_year"] <= year) & (df["end_year"] >= year)].shape[0]

    def get_active_team_info(self) -> dict:
        """Returns all data for the active team."""
        team_id = self.get_active_team_id()
        team_name = self.get_active_team()
        money = int(self.teams_model.teams.loc[self.teams_model.teams["team_id"] == team_id, "money"].iloc[0])

        next_year_free = self.contracts_model.get_team_next_year_free_space(team_id)
        series_id = self.contracts_model.get_team_series_id(team_id)
        series_name = self.series_model.get_series_by_id([series_id])[0]
        drivers = self.get_owners_team_driver_data()

        drivers_this_year = self.count_active_contracts(drivers, self.current_date.year)
        drivers_next_year = self.count_active_contracts(drivers, self.current_date.year + 1)
        parts = self.get_owners_team_parts_data()
        parts_this_year = self.count_active_contracts(parts, self.current_date.year)
        parts_next_year = self.count_active_contracts(parts, self.current_date.year + 1)
        pr = self.series_model.get_point_rules_for_series(series_id, self.current_date.year)
        if len(pr) > 0:
            max_cars = pr["max_cars"].iloc[0]
        else:
            max_cars = 0
        return {
            "name": team_name,
            "budget": money,
            "series": series_name,
            "drivers": self.get_owners_team_driver_data(),
            "parts": self.get_owners_team_parts_data(),
            "staff": self.get_team_staff(team_id),
            "races": self.get_upcoming_races(team_id),
            "finances": self.get_team_finances(team_id),
            "driver_contracts": [drivers_this_year, max_cars, drivers_next_year, drivers_next_year + next_year_free],
            "car_part_contracts": [parts_this_year, 3, parts_next_year, 3]
        }

    def get_team_owners(self) -> pd.DataFrame:
        return self.teams_model.get_team_owners_table()

    def update_team_owners(self, updates: dict[int, int]):
        """
        updates = {team_id: owner_id}
        """
        self.teams_model.set_team_owners(updates)

    def get_team_selector_values(self) -> list[str]:
        teams_df = self.teams_model.get_teams()
        if teams_df.empty:
            self.set_active_team("")
            return []

        values = []
        selected_team = ""
        for _, row in teams_df.iterrows():
            owner = row["owner_id"]
            if owner > 0:
                owner_text = f"Owner {owner}"
                selected_team = row['team_name']
                values.append(f"{row['team_name']} ({owner_text})")
        if len(values) < self.teams:
            self.set_active_team(selected_team)
        self.teams = len(values)
        return values

    def get_myteam_tab_data(self) -> dict:
        """
        Returns all data needed for the My Team table:
        - team name
        - budget
        - drivers DataFrame
        - components DataFrame
        - staff DataFrame
        - upcoming races DataFrame
        """
        try:
            if self.teams == 0:
                empty = pd.DataFrame()
                return {
                    "team_name": "No Team Selected",
                    "series": "",
                    "budget": 0,
                    "drivers": empty,
                    "components": empty,
                    "staff": empty,
                    "races": empty,
                    "finances": empty,
                    "driver_contracts": [0, 0, 0, 0],

                    "car_part_contracts": [0, 0, 0, 0]

                }
            team_info = self.get_active_team_info()

            return {
                "team_name": team_info["name"],
                "series": team_info["series"],
                "budget": team_info["budget"],
                "drivers": team_info["drivers"],
                "components": team_info["parts"],
                "staff": team_info["staff"],
                "finances": team_info["finances"],
                "races": team_info["races"],
                "driver_contracts": team_info["driver_contracts"],
                "car_part_contracts": team_info["car_part_contracts"]
            }

        except Exception as e:
            print(f" get_myteam_tab_data error: {e}")
            # Fallback — empty tables so the GUI does not crash
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
        Returns information about the team's employees based on the teams table.
        Includes columns: Department, Employees.
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

    def get_team_finances(self, team_id: int) -> pd.DataFrame:
        """
        Returns financial history for the given team.
        Includes columns: Season, Employees, Income.
        """
        try:
            if self.teams == 0:
                return pd.DataFrame(columns=["Season", "Employees", "Income"])
            df = self.teams_model.get_team_finance_history(team_id)

            if df.empty:
                return pd.DataFrame(columns=["Season", "Employees", "Income"])

            return df.sort_values("Season", ascending=False).reset_index(drop=True)

        except Exception as e:
            print(f" get_team_finances error: {e}")
            return pd.DataFrame(columns=["Season", "Employees", "Income"])

    def get_upcoming_races(self, team_id: int) -> pd.DataFrame:
        """
        Returns upcoming races for the series in which the team has a contract.
        """
        try:
            # Determine the series in which the team has a contract
            series_ids = self.contracts_model.get_team_series(team_id)
            if not series_ids:
                return pd.DataFrame(columns=["Date", "Race Name", "Series"])

            # Get the next races for these series
            upcoming = self.race_model.get_upcoming_races_for_series(
                series_ids, self.series_model.get_series(), self.current_date
            )
            return upcoming

        except Exception as e:
            print(f" get_upcoming_races error: {e}")
            return pd.DataFrame(columns=["Date", "Race Name", "Series"])

    def refresh_myteam(self):
        """
        Reloads the My Team tab from current data.
        Called after changing the team, after simulation, or when the tab changes.
        """

        try:
            if hasattr(self, "view") and hasattr(self.view, "refresh_myteam_tab"):
                self.view.refresh_myteam_tab()
            else:
                print("[Controller] View is not initialized, refresh skipped.")
        except Exception as e:
            print(f"[Controller] Error refreshing My Team tab: {e}")

    def get_owners_team_parts_data(self):
        return self.contracts_model.find_active_manufacturer_contracts(
            self.active_team_id,
            self.current_date.year,
            self.series_model.get_series(),
            self.manufacturer_model,
            self.race_model
        )

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
            raced = self.race_model.get_raced_series()
            return sorted(self.series_model.get_series_by_id(raced))
        if subject_type == "Manufacturers":
            raced = self.race_model.get_raced_manufacturers()

            return self.manufacturer_model.map_manufacturer_ids_to_names(raced)

        if subject_type == "Drivers":
            raced = self.race_model.get_raced_drivers()
            return self.drivers_model.get_raced_drivers(raced)

        if subject_type == "Teams":
            raced = self.race_model.get_raced_teams()
            return sorted(self.teams_model.get_team_names(raced))

        if subject_type == "Series":
            raced = self.race_model.get_raced_series()
            return sorted(self.series_model.get_series_by_id(raced))
        return None

    def update_seasons(self, series_name: str):
        sid = self.series_model.get_series_id(series_name)
        self.seasons = self.race_model.get_seasons_for_series(sid)

    def get_season_list(self):

        seasons = list(reversed(self.seasons))
        return [str(y) for y in seasons]

    def simulate_days(self, days: int):
        self.current_date = self.sim_day(self.current_date, days)
        self.refresh_myteam()

    def sim_to_next_race(self):
        """
        Simulate day-by-day until the next race date.
        Uses RaceModel.get_next_race_date() to determine the target.
        """

        next_race_date = self.race_model.get_next_race_date(self.current_date)
        if next_race_date is None or next_race_date.year > self.current_date.year:
            target_stop = pd.Timestamp(year=self.current_date.year + 1, month=1, day=1)
        else:
            target_stop = next_race_date
        while self.current_date < target_stop:
            self.current_date = self.sim_day(self.current_date, 1)
        return

    def sim_day(self, date: datetime, days: int) -> datetime:
        for _ in range(days):
            date += timedelta(days=1)
            if self._is_season_start(date):
                self._handle_season_start(date)

            if date.year >= FIRST_REAL_SEASON_YEAR:
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

    def save_game(self, name: str):
        folder = USER_DIR / name
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        meta = pd.DataFrame({
            "date": [self.current_date.strftime("%Y-%m-%d")],
            "begin": [self.begin_date.strftime("%Y-%m-%d")],
            "new_game": [self.new_game]
        })
        meta.to_csv(folder / FILE_CONTROLLER_DATA, index=False)
        self.generated_races.to_csv(folder / FILE_CONTROLLER_GENERATED_RACES, index=False)
        self.load_model.save(
            folder,
            self.teams_model,
            self.series_model,
            self.drivers_model,
            self.manufacturer_model,
            self.contracts_model,
            self.race_model,
        )

    def load_default_game(self):
        return self.load_game("default_data", base_folder=PACKAGE_DIR)

    def load_game(self, name: str, base_folder: pathlib.Path = USER_DIR) -> bool:
        folder = base_folder / name
        missing = [f for f in CONTROLLER_REQUIRED_FILES if not (folder / f).exists()]
        if missing:
            print("Missing controller files:", missing)
            return False
        # Load using constants
        meta = pd.read_csv(folder / FILE_CONTROLLER_DATA)
        self.generated_races = pd.read_csv(folder / FILE_CONTROLLER_GENERATED_RACES)
        self.current_date = datetime.strptime(meta.loc[0, "date"], "%Y-%m-%d")
        self.begin_date = datetime.strptime(meta.loc[0, "begin"], "%Y-%m-%d")
        self.begin_year = self.begin_date.year
        self.new_game = bool(meta.loc[0, "new_game"])

        self.load_model.load_all(
            folder,
            self.series_model,
            self.teams_model,
            self.drivers_model,
            self.manufacturer_model,
            self.contracts_model,
            self.race_model,
        )

        self.drivers_model.choose_active_drivers(self.current_date)

        # Initialize driver slots
        self.contracts_model.driver_slots_current = self.contracts_model.init_driver_slots_for_year(
            self.current_date.year, self.series_model.point_rules
        )
        self.contracts_model.driver_slots_next = self.contracts_model.init_driver_slots_for_year(
            self.current_date.year + 1, self.series_model.point_rules
        )

        while self.current_date < datetime(1893, 12, 31):
            self.current_date = self.sim_day(self.current_date, 1)

        self.new_game = False
        self._set_default_active_team()
        self.refresh_myteam()
        return True

    def kick_driver(self, team_id: int, driver_id: int):
        self.contracts_model.terminate_driver_contract(team_id, driver_id, self.current_date.year)

    def get_active_driver_contracts(self):
        return self.contracts_model.dt_contract[self.contracts_model.dt_contract["active"]]

    def get_human_teams(self, date: datetime) -> pd.DataFrame:
        """
        Wrapper to get teams controlled by the player for the given date range.
        Assumes TeamsModel provides get_human_teams(date).
        """
        try:
            return self.teams_model.get_human_teams(date)
        except Exception:
            return pd.DataFrame()

    def _is_season_start(self, date: datetime) -> bool:
        return date.year < DEFAULT_END_YEAR and date.day == SEASON_START_DAY and date.month == SEASON_START_MONTH

    def _deduct_all_contracts_for_year(self, year: int):
        contracts = self.contracts_model.get_contracts_for_year(year)
        for _, row in contracts.iterrows():
            self.teams_model.deduct_money(row["team_id"], row["salary"])

    def _deduct_all_part_contracts_for_year(self, year: int):
        contracts = self.contracts_model.get_active_part_contracts_for_year(year)
        for _, row in contracts.iterrows():
            self.teams_model.deduct_money(row["team_id"], row["cost"])

    def _handle_season_start(self, date: datetime):
        # If we should plan races this year
        if date.year >= FIRST_RACE_PLANNING_YEAR:
            # plan for the next calendar year (your original behavior)
            target_date = date + relativedelta(years=1)
            target_year = int(target_date.year)

            # get the DataFrame that contains per-year quotas
            df = getattr(self, "generated_races", None)

            # default quotas if no row exists
            champ, nonchamp = 9, 1

            # if DataFrame exists and has rows, try to find the row for target_year
            if df is not None and not df.empty:
                # match by year (ensure numeric comparison)
                row = df[df["year"].astype(int) == target_year]
                if not row.empty:
                    # extract champ and nonchamp as ints
                    champ = int(row.iloc[0]["champ"])
                    nonchamp = int(row.iloc[0]["nonchamp"])

            # call plan_races with the extracted values
            # expected signature: plan_races(series_model, current_date, champ_per_series, nonchamp_per_series)
            self.race_model.plan_races(self.series_model, target_date, champ, nonchamp)

        # continue with the rest of the original season-start logic
        self._update_entities_for_new_season(date)

        # Copy over driver slots
        self.contracts_model.rollover_driver_slots()
        self.contracts_model.reset_reserved_slot()

        if date.year >= FIRST_REAL_SEASON_YEAR:
            self._handle_contracts(date)
            self._deduct_all_contracts_for_year(date.year)
            self._deduct_all_part_contracts_for_year(date.year)

        # Note: investments are no longer triggered automatically at season start.
        # The user triggers investments via a button in the GUI.

    def _update_entities_for_new_season(self, date: datetime):
        self.contracts_model.disable_driver_contracts(self.drivers_model.get_retiring_drivers())
        self.drivers_model.update_drivers(date)
        self.drivers_model.update_reputations()
        self.teams_model.auto_invest_ai_finance()
        self.teams_model.update_reputations_and_money(date.year)
        self.teams_model.check_debt()
        self.drivers_model.choose_active_drivers(date)
        self.race_model.all_time_best(self.drivers_model, 1)

    def _handle_contracts(self, date: datetime):
        self.manufacturer_model.develop_part(date, self.contracts_model.get_ms_contract())

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
        # Internal method; kept for cases where investments need to be triggered programmatically
        investments = self.view.ask_finance_investments(self.teams_model.get_human_teams(date))
        self.teams_model.invest_finance(date.year, investments)

    def apply_investments(self, year: int, investments: Any):
        """
        Public method the GUI can call to apply investments.
        'investments' can be a dict {team_id: amount} or a list of dicts [{'team_id':...,'investment':...}, ...].
        """
        if investments is None:
            return
        if isinstance(investments, dict):
            try:
                self.teams_model.invest_finance(year, investments)
                return
            except Exception:
                # Fallback: attempt to process items individually
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
        Returns a DataFrame of drivers the active team can sign
        (for the current or next year depending on the next_year parameter).
        """
        try:
            team_id = self.get_active_team_id()
            if team_id is None:
                print("No active team selected.")
                return pd.DataFrame()

            year = self.current_date.year + (1 if next_year else 0)
            active_drivers = self.drivers_model.get_active_drivers()
            rules = self.series_model.point_rules

            df = self.contracts_model.get_available_drivers_for_offer(
                team_id=team_id,
                year=year,
                active_drivers=active_drivers,
                series=self.series_model.series,
                rules=rules
            )
            return df
        except Exception as e:
            print(f"[Controller] Error loading available drivers: {e}")
            return pd.DataFrame()

    def offer_driver_contract(self, driver_id: int, salary: int, length: int, next_year: bool = False):
        """
        Offers a contract to a driver for the current or next year.
        The driver decides on the next day advance.
        """
        try:
            team_id = self.get_active_team_id()
            if team_id is None:
                print("You must select a team first.")
                return False

            year = self.current_date.year + (1 if next_year else 0)
            self.contracts_model.offer_driver_contract(driver_id, team_id, salary, length, year)
            return True
        except Exception as e:
            print(f"[Controller] Error creating offer: {e}")
            return False

    def process_driver_offers(self):
        """
        Processes all pending driver offers (player and AI),
        whether they were accepted or rejected.
        """
        try:
            signed = self.contracts_model.process_driver_offers(
                self.current_date,
                self.drivers_model.get_active_drivers_with_reputation()
            )
            for contract in signed:
                if contract["year"] == self.current_date.year:
                    self.teams_model.deduct_money(contract["team_id"], contract["salary"])
        except Exception as e:
            print(f"[Controller] Error processing offers: {e}")

    def get_max_marketing_staff(self, team_id: int) -> int:
        return self.teams_model.get_max_marketing_staff(team_id)

    def get_marketing_hire_cost(self) -> int:
        return self.teams_model.marketing_hire_cost

    def get_marketing_fire_cost(self) -> int:
        return self.teams_model.marketing_fire_cost

    def adjust_marketing_staff(self, new_employees: int, cost: int) -> str:
        """
        Sets a new number of marketing employees and deducts the cost.
        """
        team_id = self.get_active_team_id()
        if team_id is None:
            return "No active team selected."

        # Deduct money
        self.teams_model.deduct_money(team_id, cost)

        # Set new count
        self.teams_model.change_finance_employees(team_id, new_employees)

        return f"Finance employees set on:{new_employees}. Cost: €{cost}"

    def _simulate_race_day(self, date: datetime):
        races_today = self.race_model.races[self.race_model.races["race_date"] == date - timedelta(days=1)].copy()
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

    # Outputs / formatting results for GUI
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
            return df
        elif stats_type == "Manufacturers":
            if not subject_name or not stats_type or not manufacturer_type:
                return pd.DataFrame()

            mid = self.manufacturer_model.get_manufacturers_id(subject_name)
            df = self.race_model.get_subject_season_stands(mid, manufacturer_type, self.series_model.get_series())
            return df
        elif stats_type == "Teams":
            if not subject_name or not stats_type:
                return pd.DataFrame()

            tid = self.teams_model.get_teams_id(subject_name)

            df = self.race_model.get_subject_season_stands(tid, "team", self.series_model.get_series())
            return df
        elif stats_type == "Series":
            if not subject_name or not stats_type:
                return pd.DataFrame()

            sid = self.series_model.get_series_id(subject_name)

            df = self.race_model.extract_champions(
                sid,
                self.series_model.get_series(),
                self.manufacturer_model.get_manufacturers(),
                self.teams_model.get_teams(),
                self.drivers_model.get_drivers()
            )
            return df
        return None

    def _format_results(self, df: pd.DataFrame, season: int) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        # Map manufacture_id → name
        mf_map = self.manufacturer_model.manufacturers.set_index("manufacture_id")["name"].to_dict()

        # Handle columns engine/chassi/pneu or engine_id/chassi_id/pneu_id
        part_columns = {
            "engine": "Engine",
            "engine_id": "Engine",
            "chassi": "Chassi",
            "chassi_id": "Chassi",
            "pneu": "Tyres",
            "pneu_id": "Tyres"
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

        # Add driver name and age

        df["driver_id"] = df["driver_id"].astype(int)
        self.drivers_model.drivers["driver_id"] = self.drivers_model.drivers["driver_id"].astype(int)
        df = df.merge(
            self.drivers_model.drivers[["driver_id", "forename", "surname", "year"]],
            left_on="driver_id",
            right_on="driver_id",
            how="left"
        )

        df["Age"] = season - df["year"]

        df.drop(columns=["year", "driver_id"], inplace=True)

        # Add team name
        df = df.merge(
            self.teams_model.teams[["team_id", "team_name"]],
            on="team_id", how="left"
        )
        df.drop(columns=["team_id"], inplace=True)

        # Rename columns
        df.rename(columns={
            "forename": "Forename",
            "surname": "Surname",
            "team_name": "Team Name",
            "final_position": "Position",
            "final_points": "Points",
        }, inplace=True)

        # Sort by final position, then by secondary_position (descending)
        if "Position" in df.columns and "secondary_position" in df.columns:
            df.sort_values(
                by=["Position", "secondary_position"],
                ascending=[True, False],
                inplace=True
            )
        # Otherwise sort only by secondary_position (descending)
        elif "secondary_position" in df.columns:
            df.sort_values(
                by=["secondary_position"],
                ascending=False,
                inplace=True
            )
        # Remove secondary_position column
        if "secondary_position" in df.columns:
            df.drop(columns=["secondary_position"], inplace=True)
        # Column ordering: base + others
        base_cols = ["Forename", "Surname", "Age", "Team Name"]
        for extra in ("Engine", "Chassi", "Tyres", "Position", "Points"):
            if extra in df.columns:
                base_cols.append(extra)

        others = [c for c in df.columns if c not in base_cols]
        df = df[base_cols + others]

        # Format positions in individual rounds
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

    def terminate_driver_contract(self) -> str:
        team_id = self.get_active_team_id()
        if team_id is None:
            return "No active team selected."

        current_year = self.current_date.year
        contracts = self.contracts_model.get_terminable_contracts(team_id, current_year)

        if contracts.empty:
            return "No terminable contracts found."

        # In production, you should display a driver selection (e.g., via GUI).
        # For testing, we pick the first:
        contract = contracts.iloc[0]
        driver_id = contract["driver_id"]
        cost = self.contracts_model.terminate_driver_contract(driver_id, team_id, current_year)
        self.teams_model.deduct_money(team_id, cost)

        return f"Contract with driver {driver_id} terminated. Cost: {cost}"

    def get_terminable_contracts_for_team(self) -> pd.DataFrame:
        team_id = self.get_active_team_id()
        if team_id is None:
            return pd.DataFrame()

        contracts = self.contracts_model.get_terminable_contracts(team_id, self.current_date.year)
        if contracts.empty:
            return contracts

        drivers = self.drivers_model.get_active_drivers()
        merged = drivers.merge(contracts, on="driver_id", how="right")
        return merged

    def terminate_driver_contract_by_id(self, driver_id: int, cost: int, is_current: bool) -> str:
        team_id = self.get_active_team_id()
        if team_id is None:
            return "No active team selected."

        # Verify the contract exists (optional if UI filters correctly)
        contract = self.contracts_model.dt_contract[
            (self.contracts_model.dt_contract["driver_id"] == driver_id) &
            (self.contracts_model.dt_contract["team_id"] == team_id) &
            (self.contracts_model.dt_contract["active"] is True)
            ]

        if contract.empty:
            return f"No active contract found for driver {driver_id}."

        # Deactivate contract
        self.contracts_model.disable_driver_contract(driver_id, is_current, self.current_date.year)

        # Deduct money
        self.teams_model.deduct_money(team_id, cost)

        # Type of contract
        contract_type = "current" if is_current else "future"
        # TODO: really not nice to return string that is then displayed directly in GUI...
        return f"Contract with driver {driver_id} terminated. Type: {contract_type}. Cost: €{cost:,}"

    def get_available_car_parts(self) -> pd.DataFrame:
        team_id = self.get_active_team_id()
        if team_id is None:
            return pd.DataFrame()

        parts = self.contracts_model.get_available_series_parts(
            team_id,
            self.current_date.year,
            car_parts=self.manufacturer_model.car_parts
        )

        manufacturers = self.manufacturer_model.get_manufacturers()
        manufacturers["manufacture_id"] = manufacturers["manufacture_id"].astype(int)

        parts["manufacture_id"] = parts["manufacture_id"].astype(int)
        parts = parts.merge(manufacturers[["manufacture_id", "name"]], on="manufacture_id", how="left")
        parts.rename(columns={"name": "manufacturer_name"}, inplace=True)

        return parts

    def offer_car_part_contract(self, manufacturer_id: int, length: int, price: int, year: int, part_type: str) -> bool:
        try:
            team_id = self.get_active_team_id()
            if team_id is None:
                return False

            if self.contracts_model.offer_car_part_contract(
                    manufacturer_id, team_id, length, price, year, part_type
            ) and year == self.current_date.year:
                self.teams_model.deduct_money(team_id, price)

            return True
        except Exception as e:
            print(f"[Controller] Error when offering part: {e}")
            return False
