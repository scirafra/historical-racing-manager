import os
import time
from datetime import datetime, timedelta

import pandas as pd

import contracts as ct
import load as ld
import manufacturer as mf
import race as rc
import series as se
import teams as tm
from drivers import DriversModel
from graphics import Graphics


class Controller:
    def __init__(self):
        # Simulation configuration
        self.begin_year = 1843
        self.end_year = 3000
        self.drivers_per_year = 4
        self.sim_years_step = 36

        # Time state
        self.begin_date = datetime.strptime(f"01-01-{self.begin_year}", "%d-%m-%Y")
        self.current_date = self.begin_date
        self.new_game = True
        self.ss = time.time()

        # Core game models
        self.drivers = DriversModel()

        # View layer
        self.view = Graphics(self)

    # ====== PUBLIC API FOR VIEW ======

    def start_new_season(self):
        """Start a new season by loading game state and simulating years."""
        self.load_game("my_data")
        self.current_date = self.sim_year(self.current_date, self.sim_years_step)

    def save_game(self, name: str):
        """Persist current simulation state."""
        if not os.path.isdir(name):
            os.makedirs(name, exist_ok=True)
        meta = pd.DataFrame(
            {"date": [self.current_date], "begin": [self.begin_date], "new_game": [self.new_game]}
        )
        meta.to_csv(f"{name}/data.csv", index=False)

        self.drivers.save(name)  # save drivers model
        ld.save(name)

    def load_game(self, name: str):
        """Load game state from disk."""
        if not os.path.exists(f"{name}/data.csv"):
            return False

        meta = pd.read_csv(f"{name}/data.csv")
        self.current_date = datetime.strptime(meta.loc[0, "date"], "%Y-%m-%d")
        self.begin_date = datetime.strptime(meta.loc[0, "begin"], "%Y-%m-%d")
        self.begin_year = self.begin_date.year
        self.new_game = bool(meta.loc[0, "new_game"])

        if self.new_game:
            # Here you could generate initial drivers if needed
            self.new_game = False

        ld.load_all(name)
        self.drivers.load(name)
        self.drivers.choose_active_drivers(self.current_date)

        # Fast-forward to first season start
        while self.current_date.year < 1894:
            self.current_date = self.sim_day(self.current_date, 1)
        return True

    def get_date(self) -> str:
        """Return current simulation date as string."""
        return self.current_date.strftime("%Y-%m-%d %A")

    def get_series_names(self):
        """List available series names."""
        return se.get_series()["name"].tolist()

    def update_seasons(self, series_name: str):
        """Update list of seasons for given series."""
        self.seasons = rc.get_seasons_for_series(se.get_series_id(series_name))

    def get_season_list(self):
        """Return seasons as list of strings."""
        return [str(y) for y in self.seasons]

    def simulate_days(self, days: int):
        """Simulate given number of days."""
        self.current_date = self.sim_day(self.current_date, days)

    def get_results(self, series_name: str, season_str: str) -> pd.DataFrame:
        """Return processed race results for display."""
        sid = se.get_series_id(series_name)
        season = int(season_str)
        df = rc.pivot_results_by_race(sid, season)

        # Map manufacturer IDs to names
        mf_map = mf.manufacturers.set_index("manufacturerID")["name"].to_dict()
        for col_key, col_name in [("engine", "Engine"), ("chassi", "Chassi"), ("pneu", "Tyres")]:
            if col_key in df.columns:
                df[col_name] = (
                    df[col_key].fillna(0).astype(int).map(mf_map).fillna(df[col_key].astype(str))
                )
                df.drop(columns=[col_key], inplace=True)

        # Merge driver info
        df = df.merge(
            self.drivers.drivers[["driverID", "forename", "surname", "year"]],
            on="driverID",
            how="left",
        )
        df["Age"] = season - df["year"]
        df.drop(columns=["year", "driverID"], inplace=True)

        # Merge team info
        df = df.merge(tm.teams[["teamID", "teamName"]], on="teamID", how="left")
        df.drop(columns=["teamID"], inplace=True)

        # Rename for display
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

        # Format results columns
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

    # ====== SIMULATION ======

    def sim_day(self, dat: datetime, days: int) -> datetime:
        """Simulate a given number of days in the season."""
        for _ in range(days):
            dat += timedelta(days=1)

            # Season start
            if 2999 > dat.year and dat.day == 1 and dat.month == 1:
                if dat.year > 1896:
                    rc.plan_races(dat)

                ct.disable_contracts(self.drivers.get_retiring_drivers())
                self.drivers.update_drivers(dat)
                self.drivers.update_reputations()
                tm.update_reputations()

                retire = self.drivers.choose_active_drivers(dat)

                active_series = se.series[
                    (se.series["startYear"] <= dat.year) & (se.series["endYear"] >= dat.year)
                    ]

                # all_time_best now takes drivers_model
                rc.all_time_best(self.drivers, 1)

                if dat.year >= 1894:
                    mf.develop_part(dat)
                    ct.sign_car_part_contracts(active_series, dat, mf.car_parts, self.view.root)
                    ct.sign_driver_contracts(
                        active_series,
                        dat,
                        ct.DTcontract,
                        self.drivers.active_drivers,
                        se.point_rules,
                        ct.STcontract,
                        False,
                        self.view.root,
                    )

                tm.invest_fin_all(dat, self.view.root)

            # Races on this day
            races_today = rc.races[rc.races["race_date"] == dat].copy()
            if not races_today.empty:
                died = []
                for i in range(len(races_today)):
                    # prepare_race now takes drivers_model
                    died += rc.prepare_race(self.drivers, races_today, i, dat)
                if died:
                    self.drivers.mark_drivers_dead(died, dat)
                    ct.disable_contracts(died)
                    active_series = se.series[
                        (se.series["startYear"] <= dat.year) & (se.series["endYear"] >= dat.year)
                        ]
                    if dat.year >= 1894:
                        ct.sign_driver_contracts(
                            active_series,
                            dat,
                            ct.DTcontract,
                            self.drivers.active_drivers,
                            se.point_rules,
                            ct.STcontract,
                            True,
                            self.view.root,
                        )
        return dat

    def sim_year(self, start_date: datetime, years: int) -> datetime:
        """Simulate given number of years."""
        for _ in range(years * 365):
            start_date = self.sim_day(start_date, 1)
        return start_date

    def run(self):
        """Run the main loop (delegated to view)."""
        self.view.run()
