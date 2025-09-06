import os
import time
from datetime import datetime, timedelta

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

        self.drivers_model = DriversModel()
        self.teams_model = TeamsModel()
        self.series_model = SeriesModel()
        self.manufacturer_model = ManufacturerModel()
        self.contracts_model = ContractsModel()
        self.race_model = RaceModel()

        self.view = Graphics(self)

    def start_new_season(self):
        self.load_game("my_data")
        self.current_date = self.sim_year(self.current_date, self.sim_years_step)

    def save_game(self, name: str):
        if not os.path.isdir(name):
            os.makedirs(name, exist_ok=True)

        meta = pd.DataFrame(
            {"date": [self.current_date], "begin": [self.begin_date], "new_game": [self.new_game]}
        )
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

        while self.current_date.year < 1894:
            self.current_date = self.sim_day(self.current_date, 1)

        self.new_game = False
        return True

    def get_date(self) -> str:
        return self.current_date.strftime("%Y-%m-%d %A")

    def get_series_names(self):
        return self.series_model.get_series()["name"].tolist()

    def update_seasons(self, series_name: str):
        sid = self.series_model.get_series_id(series_name)
        self.seasons = self.race_model.get_seasons_for_series(sid)

    def get_season_list(self):
        return [str(y) for y in self.seasons]

    def simulate_days(self, days: int):
        self.current_date = self.sim_day(self.current_date, days)

    def get_results(self, series_name: str, season_str: str) -> pd.DataFrame:
        sid = self.series_model.get_series_id(series_name)
        season = int(season_str)
        df = self.race_model.pivot_results_by_race(sid, season)

        mf_map = self.manufacturer_model.manufacturers.set_index("manufacturerID")["name"].to_dict()
        for col_key, col_name in [("engine", "Engine"), ("chassi", "Chassi"), ("pneu", "Tyres")]:
            if col_key in df.columns:
                df[col_name] = (
                    df[col_key].fillna(0).astype(int).map(mf_map).fillna(df[col_key].astype(str))
                )
                df.drop(columns=[col_key], inplace=True)

        df = df.merge(
            self.drivers_model.drivers[["driverID", "forename", "surname", "year"]],
            on="driverID",
            how="left",
        )
        df["Age"] = season - df["year"]
        df.drop(columns=["year", "driverID"], inplace=True)

        df = df.merge(self.teams_model.teams[["teamID", "teamName"]], on="teamID", how="left")
        df.drop(columns=["teamID"], inplace=True)

        df.rename(
            columns={
                "forename": "Forename",
                "surname": "Surname",
                "teamName": "Team Name",
                "final_position": "Position",
                "final_points": "Points",
            },
            inplace=True,
        )

        if "Position" in df.columns:
            df.sort_values("Position", inplace=True)

        base_cols = ["Forename", "Surname", "Age", "Team Name"]
        for extra in ("Engine", "Chassi", "Tyres", "Position", "Points"):
            if extra in df.columns:
                base_cols.append(extra)
        others = [c for c in df.columns if c not in base_cols]
        df = df[base_cols + others]

        def fmt(x):
            if x in ("Crash", "Death"):
                return x
            try:
                return str(int(float(x)))
            except:
                return ""

        for col in df.columns:
            if col not in base_cols:
                df[col] = df[col].apply(fmt)

        return df

    def sim_day(self, date: datetime, days: int) -> datetime:
        for _ in range(days):
            date += timedelta(days=1)

            if self._is_season_start(date):
                self._handle_season_start(date)

            self._handle_races(date)

        return date

    def sim_year(self, start_date: datetime, years: int) -> datetime:
        for _ in range(years * 365):
            start_date = self.sim_day(start_date, 1)
        return start_date

    def run(self):
        self.view.run()

    def _is_season_start(self, date: datetime) -> bool:
        return 2999 > date.year and date.day == 1 and date.month == 1

    def _handle_season_start(self, date: datetime):
        if date.year > 1896:
            self.race_model.plan_races(self.series_model, date)
        print(date, self.drivers_model.get_retiring_drivers())
        self.contracts_model.disable_driver_contracts(self.drivers_model.get_retiring_drivers())
        self.drivers_model.update_drivers(date)
        self.drivers_model.update_reputations()
        self.teams_model.update_reputations()
        self.drivers_model.choose_active_drivers(date)
        self.race_model.all_time_best(self.drivers_model, 1)

        if date.year >= 1894:
            self.manufacturer_model.develop_part(date, self.contracts_model.get_MScontract())

            car_part_inputs = self.view.ask_car_part_contracts(
                self.teams_model.get_human_teams(date), self.manufacturer_model.car_parts, date.year
            )
            print("uuuuj", self.manufacturer_model.car_parts)
            self.contracts_model.sign_car_part_contracts(
                active_series=self.series_model.get_active_series(date.year),
                date=date,
                car_parts=self.manufacturer_model.car_parts,
                teams_model=self.teams_model,
                manufacturers=self.manufacturer_model.manufacturers,
                team_inputs=car_part_inputs,
            )

            driver_inputs = self.view.ask_driver_contracts(
                self.teams_model.get_human_teams(date), self.drivers_model.active_drivers, date.year
            )
            self.contracts_model.sign_driver_contracts(
                active_series=self.series_model.get_active_series(date.year),
                teams_model=self.teams_model,
                date=date,
                active_drivers=self.drivers_model.active_drivers,
                rules=self.series_model.point_rules,
                temp=False,
                teams=self.teams_model.teams,
                team_inputs=driver_inputs,
            )

        investments = self.view.ask_finance_investments(self.teams_model.get_human_teams(date))
        self.teams_model.invest_finance(date.year, investments)

    def _handle_races(self, date: datetime):
        races_today = self.race_model.races[self.race_model.races["race_date"] == date].copy()
        if races_today.empty:
            return

        died = []
        for i in range(len(races_today)):
            died += self.race_model.prepare_race(
                self.drivers_model,
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
                    date=date,
                    active_drivers=self.drivers_model.active_drivers,
                    rules=self.series_model.point_rules,
                    temp=True,
                    teams=self.teams_model.teams,
                    team_inputs={},  # AI fallback only
                )
