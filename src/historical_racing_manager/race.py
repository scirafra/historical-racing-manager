import pathlib
import random as rd
from datetime import timedelta

import numpy as np
import pandas as pd

from historical_racing_manager.consts import (
    RACE_REQUIRED_FILES,
    DAYS_PER_SEASON,
    RACE_WEEKDAY,
    RAIN_TRIGGER_MIN,
    RAIN_TRIGGER_MAX,
    RAIN_STRENGTH_MIN,
    RAIN_STRENGTH_MAX,
    RNG_PICK_MAX,
    RNG_PICK_THRESHOLD,
    SPEED_MULTIPLIER,
    CRASH_CODE,
    DEATH_CODE,
)


class RaceModel:
    def __init__(self):
        self.results = pd.DataFrame()
        self.races = pd.DataFrame()
        self.standings = pd.DataFrame()
        self.point_system = pd.DataFrame()
        self.circuits = pd.DataFrame()
        self.circuit_layouts = pd.DataFrame()

        self.crashes = 0
        self.deaths = 0
        self.f1_races = 0

    # ===== Persistence =====
    def load(self, folder: pathlib.Path) -> bool:
        """
        Load required race-related CSV files from folder into the model.
        Returns True if all required files exist and were loaded, False otherwise.
        """
        required = RACE_REQUIRED_FILES

        missing = [f for f in required if not (folder / f).exists()]
        if missing:
            return False

        self.standings = pd.read_csv(folder / "stands.csv")
        self.races = pd.read_csv(folder / "races.csv")
        if not self.races.empty and "race_date" in self.races.columns:
            # Parse race_date column into pandas datetime
            self.races["race_date"] = pd.to_datetime(self.races["race_date"], errors="coerce")

        self.point_system = pd.read_csv(folder / "pointSystem.csv")
        self.results = pd.read_csv(folder / "results.csv")
        self.circuits = pd.read_csv(folder / "circuits.csv")
        self.circuit_layouts = pd.read_csv(folder / "circuit_layouts.csv")
        return True

    def save(self, folder: pathlib.Path) -> None:
        """
        Save model DataFrames to CSV files under folder.
        If folder is falsy, do nothing.
        """
        if not folder:
            return
        self.races.to_csv(folder / "races.csv", index=False)
        self.standings.to_csv(folder / "stands.csv", index=False)
        self.point_system.to_csv(folder / "pointSystem.csv", index=False)
        self.results.to_csv(folder / "results.csv", index=False)
        self.circuits.to_csv(folder / "circuits.csv", index=False)
        self.circuit_layouts.to_csv(folder / "circuit_layouts.csv", index=False)

    # ===== Queries =====
    def get_raced_series(self) -> list[int]:

        """
        Vráti unikátne seriesID z self.results ako list int v poradí prvého výskytu.
        Predpoklad: self.results je pandas.DataFrame.
        """
        # overenie typu
        if not isinstance(self.results, pd.DataFrame):
            # ak nie je DataFrame, vrátime prázdny zoznam
            return []

        # overenie existencie stĺpca
        if "seriesID" not in self.results.columns:
            return []

        # vybrať stĺpec, odstrániť NA, konvertovať na int ak je to možné,
        # zachovať poradie prvého výskytu pomocou drop_duplicates
        series = self.results["seriesID"].dropna()

        try:
            series_int = series.astype(int)
        except Exception:
            # ak konverzia zlyhá (napr. textové ID), vrátime unikátne hodnoty ako stringy
            return series.astype(str).drop_duplicates(keep="first").tolist()

        return series_int.drop_duplicates(keep="first").tolist()

    def get_raced_teams(self) -> list[int]:

        """
        Vráti unikátne seriesID z self.results ako list int v poradí prvého výskytu.
        Predpoklad: self.results je pandas.DataFrame.
        """
        # overenie typu
        if not isinstance(self.results, pd.DataFrame):
            # ak nie je DataFrame, vrátime prázdny zoznam
            return []

        # overenie existencie stĺpca
        if "teamID" not in self.results.columns:
            return []

        # vybrať stĺpec, odstrániť NA, konvertovať na int ak je to možné,
        # zachovať poradie prvého výskytu pomocou drop_duplicates
        series = self.results["teamID"].dropna()

        try:
            series_int = series.astype(int)
        except Exception:
            # ak konverzia zlyhá (napr. textové ID), vrátime unikátne hodnoty ako stringy
            return series.astype(str).drop_duplicates(keep="first").tolist()

        return series_int.drop_duplicates(keep="first").tolist()

    def get_raced_drivers(self) -> list[int]:

        """
        Vráti unikátne seriesID z self.results ako list int v poradí prvého výskytu.
        Predpoklad: self.results je pandas.DataFrame.
        """
        # overenie typu
        if not isinstance(self.results, pd.DataFrame):
            # ak nie je DataFrame, vrátime prázdny zoznam
            return []

        # overenie existencie stĺpca
        if "driverID" not in self.results.columns:
            return []

        # vybrať stĺpec, odstrániť NA, konvertovať na int ak je to možné,
        # zachovať poradie prvého výskytu pomocou drop_duplicates
        series = self.results["driverID"].dropna()

        try:
            series_int = series.astype(int)
        except Exception:
            # ak konverzia zlyhá (napr. textové ID), vrátime unikátne hodnoty ako stringy
            return series.astype(str).drop_duplicates(keep="first").tolist()

        return series_int.drop_duplicates(keep="first").tolist()

    def get_raced_manufacturers(self) -> dict[int, list[str]]:
        """
        Returns a dict mapping manufacturerID -> list of used part types.
        Example:
        {
            5: ["engine", "pneu"],
            12: ["chassi"],
        }
        """

        if not isinstance(self.results, pd.DataFrame):
            return {}

        # required columns
        columns = {
            "engineID": "engine",
            "chassiID": "chassi",
            "pneuID": "pneu"
        }

        for col in columns:
            if col not in self.results.columns:
                return {}

        manufacturer_map: dict[int, set[str]] = {}

        # iterate each part column
        for col, part_name in columns.items():
            series = self.results[col].dropna()

            # convert to int safely
            try:
                ids = series.astype(int).tolist()
            except Exception:
                ids = series.astype(str).tolist()

            # add to dictionary
            for manufacturer_id in ids:
                manufacturer_map.setdefault(manufacturer_id, set()).add(part_name)

        # convert sets to sorted lists
        return {mid: sorted(list(parts)) for mid, parts in manufacturer_map.items()}

    def extract_champions(self, series_id: int, series: pd.DataFrame, manufacturers: pd.DataFrame,
                          teams: pd.DataFrame, drivers: pd.DataFrame) -> pd.DataFrame:
        """
        Extract champions for a given series.

        Returns a DataFrame with one row per year containing the winners for each
        subject type (driver, team, engine, chassi, pneu) for the specified series.
        The function enriches the pivot with human-readable names for drivers, teams,
        and manufacturers when those columns are present.
        """
        # keep only rows for the requested series
        s = self.standings[self.standings['seriesID'] == series_id].copy()

        # compute max round per year and typ (if you want final per typ separately).
        # If final should be per year regardless of typ, group only by 'year' instead of ['year','typ'].
        s['max_round'] = s.groupby(['year', 'typ'])['round'].transform('max')

        # keep only rows that correspond to the final round for that year/typ
        final_round_rows = s[s['round'] == s['max_round']].copy()

        # now pick champions (position == 1) from those final-round rows
        champions = final_round_rows[final_round_rows['position'] == 1].copy()

        # pivot so each typ becomes a column with the subjectID of the champion
        pivot = champions.pivot_table(
            index='year',
            columns='typ',
            values='subjectID',
            aggfunc='first'  # one winner per type/year
        ).reset_index()

        # Insert seriesID column back into the pivot
        pivot.insert(0, 'seriesID', series_id)

        # Get series name label
        series_name = series.loc[series["seriesID"] == series_id, "name"].values
        series_label = series_name[0] if len(series_name) > 0 else None
        pivot.insert(1, 'series', series_label)

        # If driver column exists, merge driver names and create a driver_name column
        if 'driver' in pivot.columns:
            pivot = pivot.merge(
                drivers[["driverID", "forename", "surname"]],
                left_on="driver",
                right_on="driverID",
                how="left"
            )
            pivot["driver_name"] = pivot["forename"] + " " + pivot["surname"]
            pivot.drop(columns=["driverID", "forename", "surname", "driver"], inplace=True)

        # If team column exists, merge team names
        if 'team' in pivot.columns:
            pivot = pivot.merge(
                teams[["teamID", "team_name"]],
                left_on="team",
                right_on="teamID",
                how="left"
            )
            pivot.drop(columns=["teamID", "team"], inplace=True)

        # Map manufacturer IDs to names for engine, chassi, and pneu columns
        mf_map = manufacturers.set_index("manufacturerID")["name"].to_dict()
        for part in ["engine", "chassi", "pneu"]:
            if part in pivot.columns:
                pivot[part] = pivot[part].map(mf_map)

        # Reorder columns: series, year, driver_name, team_name, engine, chassi, pneu, then any others
        desired_order = ['year', 'driver_name', 'team_name', 'engine', 'chassi', 'pneu']
        other_columns = sorted([
            col for col in pivot.columns
            if col not in desired_order and col not in ('series')
        ])
        final_order = ['series'] + desired_order + other_columns
        pivot = pivot[[col for col in final_order if col in pivot.columns]]

        # Remove seriesID column from final output
        pivot.drop(columns=["seriesID"], inplace=True)

        return pivot

    def get_upcoming_races_for_series(self, series_ids: list[int], series: pd.DataFrame,
                                      current_date: str) -> pd.DataFrame:
        """
        Return the next 5 upcoming races for the given series after the current date.
        """
        try:
            if not series_ids or self.races.empty:
                return pd.DataFrame(columns=["Date", "Race Name", "Series", "Country"])

            # Filter relevant races
            races = self.races[
                (self.races["seriesID"].isin(series_ids)) &
                (self.races["race_date"] >= current_date)
                ].copy()

            # Rename race name column so it does not conflict with series name
            races.rename(columns={"name": "Race Name"}, inplace=True)

            # Join with series names
            races = races.merge(series[["seriesID", "name"]], on="seriesID", how="left")

            # Rename series column and race_date to Date
            races.rename(columns={"name": "Series", "race_date": "Date"}, inplace=True)

            # Optionally include country column if present in self.races
            if "country" in races.columns:
                races.rename(columns={"country": "Country"}, inplace=True)
                races = races[["Date", "Race Name", "Series", "Country"]]
            else:
                races = races[["Date", "Race Name", "Series"]]

            # Convert date to yyyy-mm-dd format (date only, no time)
            races["Date"] = pd.to_datetime(races["Date"]).dt.strftime("%Y-%m-%d")

            races.sort_values("Date", inplace=True)
            return races.head(5).reset_index(drop=True)

        except Exception as e:
            print(f"get_upcoming_races_for_series error: {e}")
            return pd.DataFrame(columns=["Date", "Race Name", "Series", "Country"])

    def get_results_for_series_and_season(self, series_id: int, season: int) -> pd.DataFrame:
        df = self.results[
            (self.results["seriesID"] == series_id) & (self.results["season"] == season)
            ][
            ["driverID", "teamID", "engineID", "chassiID", "pneuID", "raceID", "position", "round"]
        ].copy()
        return df.reset_index(drop=True)

    def get_subject_season_stands(self, subject_id: int, subject_type: str, series: pd.DataFrame) -> pd.DataFrame:
        """
        Return seasonal statistics for a subject (driver/team) based on standings and results.
        """
        subject_stands = self.standings[
            (self.standings["subjectID"] == subject_id) &
            (self.standings["typ"] == subject_type)
            ].copy()

        if subject_stands.empty:
            return pd.DataFrame()

        grouped = subject_stands.groupby(["year", "seriesID"])
        records = []

        for (year, series_id), group in grouped:
            group = group.copy()
            group["round"] = pd.to_numeric(group["round"], errors="coerce")
            max_round_idx = group["round"].idxmax()
            max_round_row = group.loc[max_round_idx]

            total_points = max_round_row["points"]
            championship_position = max_round_row["position"]
            races = group["raceID"].nunique()

            race_results = self.results[
                (self.results[subject_type + "ID"] == subject_id) &
                (self.results["season"] == year) &
                (self.results["seriesID"] == series_id)
                ]

            wins = (race_results["position"] == 1).sum()
            podiums = (race_results["position"] <= 3).sum()
            best_position = race_results["position"].min()

            # Get series name
            series_name = series.loc[series["seriesID"] == series_id, "name"].values
            series_label = series_name[0] if len(series_name) > 0 else None

            records.append({
                "season": year,
                "series": series_label,
                "races": races,
                "wins": wins,
                "podiums": podiums,
                "points": total_points,
                "championship": championship_position,
                "best_result": best_position
            })

        return pd.DataFrame(records)

    def get_seasons_for_series(self, series_id: int) -> list[int]:
        if self.results.empty:
            return []
        seasons = self.results.loc[self.results["seriesID"] == series_id, "season"].unique()
        return sorted(seasons.tolist())

    def all_time_best(self, drivers_model, series_id: int) -> pd.DataFrame:
        filtered = self.standings[
            (self.standings["seriesID"] == series_id) & (self.standings["typ"] == "driver")
            ]
        if filtered.empty:
            return pd.DataFrame()

        max_rounds = filtered.groupby("year")["round"].max().reset_index()
        result = pd.merge(filtered, max_rounds, on=["year", "round"])
        result = result.rename(columns={"subjectID": "driverID"})

        position_counts = result.pivot_table(
            index="driverID", columns="position", aggfunc="size", fill_value=0
        )
        sorted_df = position_counts.sort_values(
            by=position_counts.columns.tolist(), ascending=[False] * len(position_counts.columns)
        ).reset_index()

        names = drivers_model.drivers[["driverID", "forename", "surname"]]
        return pd.merge(sorted_df, names, on="driverID", how="left")

    def pivot_results_by_race(self, series_id: int, season: int, manufacturers: pd.DataFrame,
                              fill_value=None) -> pd.DataFrame:
        df = self.get_results_for_series_and_season(series_id, season)
        # Create mapping from manufacturer ID to manufacturer name
        manu_map = manufacturers.set_index("manufacturerID")["name"].to_dict()

        if df.empty:
            return pd.DataFrame()

        df["round"] = df["round"].fillna(0).astype(int)
        df["position"] = df["position"].replace({CRASH_CODE: "Crash", DEATH_CODE: "Death"})

        # Label non-championship races (round == 0) as NC1, NC2, ...
        zero_rids = sorted(df.loc[df["round"] == 0, "raceID"].unique())
        zero_map = {rid: f"NC{i + 1}" for i, rid in enumerate(zero_rids)}
        df["col_label"] = df.apply(
            lambda r: zero_map[r["raceID"]] if r["round"] == 0 else str(r["round"]), axis=1
        )

        # Replace manufacturer IDs with names for engine, chassi and tyre
        df["engineID"] = df["engineID"].map(manu_map)
        df["chassiID"] = df["chassiID"].map(manu_map)
        df["pneuID"] = df["pneuID"].map(manu_map)

        pivot = df.pivot(
            index=["driverID", "teamID", "engineID", "chassiID", "pneuID"],
            columns="col_label",
            values="position",
        )

        order = df[["col_label", "raceID"]].drop_duplicates().sort_values("raceID")
        labels = order["col_label"].tolist()
        pivot = pivot[labels]
        pivot = pivot.fillna("" if fill_value is None else fill_value)
        pivot.reset_index(inplace=True)
        pivot.columns.name = None

        # If championship rounds exist, attach final position and points for drivers
        if "1" in labels:
            st2 = self.standings.loc[
                (self.standings["seriesID"] == series_id)
                & (self.standings["year"] == season)
                & (self.standings["typ"] == "driver"),
                ["subjectID", "round", "points", "position"],
            ].copy()
            if not st2.empty:
                st2["round"] = pd.to_numeric(st2["round"], errors="coerce").dropna().astype(int)
                last_idx = st2.groupby("subjectID")["round"].idxmax()
                final = st2.loc[last_idx].rename(
                    columns={
                        "subjectID": "driverID",
                        "position": "final_position",
                        "points": "final_points",
                    }
                )[["driverID", "final_position", "final_points"]]
                pivot = pivot.merge(final, on="driverID", how="left")

        return pivot

    """
    Race simulation helpers: prepare race entry data and run race simulation.

    This file contains methods to prepare race grids from contracts, manufacturers,
    and driver data, and to simulate a race producing results, crashes, and deaths.
    All comments and docstrings are in English. Code logic is unchanged.
    """

    # ===== Simulation =====
    def prepare_race(
            self,
            drivers_model,
            teams_model,
            series_model,
            manufacturer_model,
            contracts_model,
            races_today: pd.DataFrame,
            idx: int,
            current_date,
    ) -> list[int]:
        """
        Prepare race data for a single scheduled race and invoke the race simulator.

        This method builds the race grid by selecting active driver-team contracts for
        the series, merging driver abilities, applying manufacturer parts (power,
        reliability, safety), computing track/wet modifiers, and assembling a
        race_data DataFrame sorted by total ability. It then looks up the point rules
        and point system for the series/season and calls simulate_race.

        Parameters
        ----------
        drivers_model : object
            Model containing active driver records (expects active_drivers DataFrame).
        teams_model : object
            Team model (used later by simulate_race for reputation updates).
        series_model : object
            Series model containing point_rules and series metadata.
        manufacturer_model : object
            Manufacturer model containing car_parts DataFrame.
        contracts_model : object
            Contracts model containing DTcontract, MTcontract, STcontract DataFrames.
        races_today : pd.DataFrame
            DataFrame of races scheduled for the current date.
        idx : int
            Index of the race in races_today to prepare.
        current_date : date-like
            Current date used to filter active contracts and parts.

        Returns
        -------
        list[int]
            List of driver IDs who died during the simulated race (returned by simulate_race).
        """
        series_id = int(races_today.iloc[idx]["seriesID"])
        layout_id = int(races_today.iloc[idx]["layoutID"])
        layout_row = self.circuit_layouts[self.circuit_layouts["layoutID"] == layout_id].iloc[0]

        # Select active driver-team contracts valid for the current year
        active_dt = contracts_model.DTcontract[
            (contracts_model.DTcontract["active"])
            & (contracts_model.DTcontract["startYear"] <= current_date.year)
            & (contracts_model.DTcontract["endYear"] >= current_date.year)
            ]
        # Keep only drivers that are currently active in drivers_model
        active_dt = active_dt[active_dt["driverID"].isin(drivers_model.active_drivers["driverID"])]

        # Teams that participate in this series
        teams_in_series = contracts_model.STcontract[
            contracts_model.STcontract["seriesID"] == series_id
            ]["teamID"]
        # Grid entries limited to teams in the series
        grid_dt = active_dt[active_dt["teamID"].isin(teams_in_series)]

        # Merge driver ability into the grid
        selected = pd.merge(
            grid_dt,
            drivers_model.active_drivers[["driverID", "ability"]],
            on="driverID",
            how="left",
        )

        # Ensure part-related columns exist with default 0
        for col in ("power", "reliability", "safety", "engine", "chassi", "pneu"):
            selected[col] = selected.get(col, 0)

        # Active manufacturer-team contracts for this series and year
        active_mt = contracts_model.MTcontract[
            (contracts_model.MTcontract["startYear"] <= current_date.year)
            & (contracts_model.MTcontract["endYear"] >= current_date.year)
            & (contracts_model.MTcontract["seriesID"] == series_id)
            ].copy()

        # Manufacturer parts available for this series and year
        parts = manufacturer_model.car_parts[
            (manufacturer_model.car_parts["seriesID"] == series_id)
            & (manufacturer_model.car_parts["year"] == current_date.year)
            ].copy()

        # Normalize merge keys to integer type for a reliable merge
        merge_keys = ["seriesID", "manufacturerID"]
        for key in merge_keys:
            parts[key] = parts[key].astype(int)
            active_mt[key] = active_mt[key].astype(int)

        # Ensure partType is string for merging
        parts["partType"] = parts["partType"].astype(str)
        active_mt["partType"] = active_mt["partType"].astype(str)

        # Merge active manufacturer contracts with available parts
        merged = pd.merge(
            active_mt,
            parts,
            on=["seriesID", "manufacturerID", "partType"],
            how="left",
        )

        # Apply parts to selected grid entries: set part IDs and accumulate stats
        for _, part in merged.iterrows():
            team_id = part["teamID"]
            mask = selected["teamID"] == team_id
            selected.loc[mask, part["partType"]] = (
                int(part["manufacturerID"]) if pd.notna(part["manufacturerID"]) else 0
            )
            selected.loc[mask, "power"] += int(part.get("power", 0))
            selected.loc[mask, "reliability"] += int(part.get("reliability", 0))
            selected.loc[mask, "safety"] += int(part.get("safety", 0))

        # Track characteristics and wetness modifiers
        corners = int(layout_row.get("corners", 1) or 1)
        wet_val = max(float(races_today.iloc[idx].get("wet", 1) or 1), 1.0)
        track_factor = max(int(corners / wet_val), 1)

        # Build the race_data DataFrame with required columns
        race_data = pd.DataFrame(
            columns=[
                "driverID",
                "ability",
                "carID",
                "carSpeedAbility",
                "carReliability",
                "carSafety",
                "totalAbility",
                "teamID",
                "engineID",
                "chassiID",
                "pneuID",
            ]
        )

        # Populate race_data rows from selected drivers and applied parts
        for j, row in selected.iterrows():
            power = int(row.get("power", 0))
            rel = int(row.get("reliability", 0))
            saf = int(row.get("safety", 0))
            ability = int(row.get("ability", 0))

            race_data.loc[len(race_data)] = [
                int(row["driverID"]),
                ability,
                j,
                power,
                int(rel * wet_val),
                int(saf * wet_val),
                int(power * track_factor + ability * 100),
                int(row["teamID"]),
                int(row.get("engine", 0)),
                int(row.get("chassi", 0)),
                int(row.get("pneu", 0)),
            ]

        # Sort grid by computed total ability (descending)
        race_data = race_data.sort_values(by="totalAbility", ascending=False).reset_index(drop=True)

        # Lookup point rules for the series and season
        rules = series_model.point_rules[
            (series_model.point_rules["seriesID"] == series_id)
            & (series_model.point_rules["startSeason"] <= current_date.year)
            & (series_model.point_rules["endSeason"] >= current_date.year)
            ].reset_index(drop=True)

        # Resolve point system by psID referenced in rules
        ps = self.point_system[self.point_system["psID"] == rules.loc[0, "psID"]].reset_index(
            drop=True
        )

        # Run the race simulation and return list of deceased driver IDs
        return self.simulate_race(drivers_model, teams_model, races_today.iloc[idx], race_data, rules, ps)

    def simulate_race(
            self,
            drivers_model,
            teams_model,
            race_row: pd.Series,
            race_data: pd.DataFrame,
            current_point_rules: pd.DataFrame,
            ps: pd.DataFrame,
    ) -> list[int]:
        """
        Simulate a race given prepared race_data and record results.

        This function applies track modifiers to reliability, simulates each car's
        outcome using _simulate_outcome, tallies crashes/deaths for statistics,
        determines finishing order via a randomized selection process, updates
        driver and team reputations if supported, records results (including crash
        and death codes), updates championship standings when applicable, and
        returns a list of driver IDs who died in the event.

        Parameters
        ----------
        drivers_model : object
            Drivers model; may implement race_reputations(reputation, driver_list).
        teams_model : object
            Teams model; may implement add_race_reputation(reputation, team_list).
        race_row : pd.Series
            Race metadata (raceID, seriesID, season, trackSafety, wet, reputation, championship).
        race_data : pd.DataFrame
            Prepared race grid with car and driver attributes.
        current_point_rules : pd.DataFrame
            Point rules for the current series/season.
        ps : pd.DataFrame
            Point system mapping finishing positions to points.

        Returns
        -------
        list[int]
            List of driver IDs who died during the race.
        """
        died: list[int] = []
        if race_data.empty:
            return []

        # Apply track safety and wetness to car reliability
        track_safety = float(race_row.get("trackSafety", 1) or 1)
        wet_val = float(race_row.get("wet", 1) or 1)
        race_data["carReliability"] = (race_data["carReliability"] * track_safety * wet_val).astype(
            int
        )

        # Simulate outcome for each car: "Good", "Crash", or "Death"
        race_data["finished"] = race_data.apply(self._simulate_outcome, axis=1)

        # Update global counters for Formula 1 era races (seriesID == 1 and season > 1949)
        if int(race_row["seriesID"]) == 1 and int(race_row["season"]) > 1949:
            self.crashes += int((race_data["finished"] == "Crash").sum())
            self.deaths += int((race_data["finished"] == "Death").sum())
            self.f1_races += 1

        # Partition results by outcome
        finish = race_data[race_data["finished"] == "Good"].reset_index(drop=True)
        crash = race_data[race_data["finished"] == "Crash"].reset_index(drop=True)
        death = race_data[race_data["finished"] == "Death"].reset_index(drop=True)

        # Build a randomized finishing ranking from the finishers
        idx_pool = list(range(len(finish)))
        ranking: list[tuple[int, bool]] = []
        rep_drivers: list[int] = []

        dmax = len(finish)
        for _ in range(dmax):
            chosen = dmax
            # Continue selecting until a valid index from idx_pool is chosen
            while chosen == dmax:
                for j in range(len(idx_pool)):
                    if rd.randint(0, RNG_PICK_MAX) < RNG_PICK_THRESHOLD:
                        chosen = idx_pool[j]
                        break
            ranking.append((chosen, True))
            rep_drivers.append(int(finish.loc[chosen, "driverID"]))
            idx_pool.remove(chosen)

        # Update driver reputations if the drivers_model supports it
        if hasattr(drivers_model, "race_reputations"):
            drivers_model.race_reputations(int(race_row.get("reputation", 0) or 0), rep_drivers)

        # Update team reputations if the teams_model supports it
        if hasattr(teams_model, "add_race_reputation"):
            team_results = []
            for driver_id in rep_drivers:
                team_id = finish.loc[finish["driverID"] == driver_id, "teamID"].iloc[0]
                team_results.append(int(team_id))

            teams_model.add_race_reputation(int(race_row.get("reputation", 0) or 0), team_results)

        # Determine championship round number if this race counts toward the championship
        round_no = 0
        if bool(race_row.get("championship", False)):
            pre = self.standings[
                (self.standings["seriesID"] == race_row["seriesID"])
                & (self.standings["year"] == race_row["season"])
                ]
            round_no = 1 if pre.empty else int(pre["round"].max()) + 1

        # Record finishing results with positions
        for pos, (fin_idx, _) in enumerate(ranking, start=1):
            self.results.loc[len(self.results)] = [
                int(race_row["raceID"]),
                int(finish.loc[fin_idx, "driverID"]),
                int(finish.loc[fin_idx, "teamID"]),
                int(finish.loc[fin_idx, "carID"]),
                int(pos),
                int(race_row["season"]),
                int(race_row["seriesID"]),
                int(round_no),
                int(finish.loc[fin_idx, "engineID"]),
                int(finish.loc[fin_idx, "chassiID"]),
                int(finish.loc[fin_idx, "pneuID"]),
            ]

        # Record crash results using CRASH_CODE
        for _, row in crash.iterrows():
            self.results.loc[len(self.results)] = [
                int(race_row["raceID"]),
                int(row["driverID"]),
                int(row["teamID"]),
                int(row["carID"]),
                CRASH_CODE,
                int(race_row["season"]),
                int(race_row["seriesID"]),
                int(round_no),
                int(row["engineID"]),
                int(row["chassiID"]),
                int(row["pneuID"]),
            ]

        # Record death results using DEATH_CODE and collect deceased driver IDs
        for _, row in death.iterrows():
            self.results.loc[len(self.results)] = [
                int(race_row["raceID"]),
                int(row["driverID"]),
                int(row["teamID"]),
                int(row["carID"]),
                DEATH_CODE,
                int(race_row["season"]),
                int(race_row["seriesID"]),
                int(round_no),
                int(row["engineID"]),
                int(row["chassiID"]),
                int(row["pneuID"]),
            ]
            died.append(int(row["driverID"]))

        # Update championship standings if this race is part of the championship
        if bool(race_row.get("championship", False)):
            self._update_standings(
                race_row, race_data, ranking, finish, crash, death, current_point_rules, ps
            )

        return died

    """
    Race simulation and scheduling helpers.

    This module contains methods used to simulate race outcomes, update championship standings,
    and plan races across a season. Comments and docstrings are written in English for clarity.
    """

    def _simulate_outcome(self, row: pd.Series) -> str:
        """
        Simulate the outcome for a single car/entry based on its attributes.

        Parameters
        ----------
        row : pd.Series
            A row containing car attributes. Expected keys:
            - "carSpeedAbility": integer-like, the car's speed capability.
            - "carReliability": integer-like, the car's reliability rating.
            - "carSafety": integer-like, the car's safety rating.

        Returns
        -------
        str
            One of "Good", "Crash", or "Death" representing the simulated result.
        """
        # Ensure numeric, non-negative values for the attributes
        speed_limit = max(int(row.get("carSpeedAbility", 0)), 0)
        reliability = max(int(row.get("carReliability", 0)), 0)
        safety = max(int(row.get("carSafety", 0)), 0)

        # If the car has no speed capability, treat it as an immediate crash
        if speed_limit <= 0:
            return "Crash"

        # Random roll influenced by speed capability and a multiplier constant
        rnd1 = np.random.randint(0, speed_limit * SPEED_MULTIPLIER)

        # If the first roll is below reliability, the car fails; second roll decides severity
        if rnd1 < reliability:
            rnd2 = np.random.randint(0, speed_limit + 1)
            # If the second roll is below safety, it's fatal; otherwise it's a crash
            return "Death" if rnd2 < safety else "Crash"
        # Otherwise the car finishes the race in good condition
        return "Good"

    def _update_standings(
            self,
            race_row: pd.Series,
            race_data: pd.DataFrame,
            ranking: list,
            finish: pd.DataFrame,
            crash: pd.DataFrame,
            death: pd.DataFrame,
            current_point_rules: pd.DataFrame,
            ps: pd.DataFrame,
    ) -> None:
        """
        Update championship standings after a race.

        This method computes points for different subject types (driver, team, engine, chassi, pneu)
        based on the race results and previous standings, then appends the new standings blocks
        to self.standings.

        Parameters
        ----------
        race_row : pd.Series
            Row describing the race (seriesID, season, raceID, etc.).
        race_data : pd.DataFrame
            DataFrame with entries for the race; must include subject ID columns like "driverID".
        ranking : list
            Ordered list of finishing entries (tuples of index and something else).
        finish : pd.DataFrame
            DataFrame of finishing entries indexed by their finish index.
        crash : pd.DataFrame
            DataFrame of entries that crashed.
        death : pd.DataFrame
            DataFrame of entries that resulted in death.
        current_point_rules : pd.DataFrame
            DataFrame containing point rules and counts for subjects (e.g., driverCts, teamCts).
        ps : pd.DataFrame
            DataFrame mapping finishing positions to points (stringified position keys).
        """
        # Filter previous standings for the same series and year
        pre = self.standings[
            (self.standings["seriesID"] == race_row["seriesID"])
            & (self.standings["year"] == race_row["season"])
            ]
        final_blocks = []
        # Combine crash and death into a single "not finished" frame
        not_finish = pd.concat([crash, death], ignore_index=True)

        # Iterate over each subject type to compute points and positions
        for typ in ("driver", "team", "engine", "chassi", "pneu"):
            subj_col = f"{typ}ID"
            # Start with unique subjects present in race_data
            subjects = race_data[[subj_col]].drop_duplicates().copy()
            # Number of cars that count for this subject; drivers count as 1, others use rules
            subjects["cars"] = (
                1 if typ == "driver" else int(current_point_rules.iloc[0].get(f"{typ}Cts", 1))
            )
            subjects["points"] = 0

            # Get previous standings block for this subject type
            prev_for_typ = pre[pre["typ"] == typ]
            this_round = prev_for_typ["round"].max() if not prev_for_typ.empty else 0
            last_round_block = (
                prev_for_typ[prev_for_typ["round"] == this_round].copy()
                if this_round
                else pd.DataFrame(columns=["subjectID", "points"])
            )

            # Award points for finishers according to ranking and points schedule (ps)
            for pos, (fin_idx, _) in enumerate(ranking, start=1):
                if fin_idx not in finish.index:
                    continue
                current_subject = int(finish.loc[fin_idx, subj_col])
                pts = int(ps.iloc[0].get(str(pos), 0))
                mask = (subjects[subj_col] == current_subject) & (subjects["cars"] > 0)
                # Decrement available car count and add points
                subjects.loc[mask, ["cars", "points"]] += [-1, pts]

            # Handle non-finishers: decrement car count but award zero points
            for _, row in not_finish.iterrows():
                current_subject = int(row[subj_col])
                mask = (subjects[subj_col] == current_subject) & (subjects["cars"] > 0)
                subjects.loc[mask, ["cars", "points"]] += [-1, 0]

            # Add race metadata to the subjects block
            subjects["raceID"] = int(race_row["raceID"])
            subjects["year"] = int(race_row["season"])
            subjects["round"] = 1 if last_round_block.empty else int(this_round) + 1
            subjects["position"] = 0
            subjects["seriesID"] = int(race_row["seriesID"])
            subjects["typ"] = typ

            # If previous round exists, add previous points to current points
            if not last_round_block.empty:
                prev_pts = last_round_block.set_index("subjectID")["points"]
                subjects["points"] = subjects[subj_col].map(prev_pts).fillna(0).astype(
                    int
                ) + subjects["points"].astype(int)

                # Include any subjects that were present in previous standings but not in this race
                missing = last_round_block[
                    ~last_round_block["subjectID"].isin(subjects[subj_col])
                ].copy()
                if not missing.empty:
                    missing["round"] = int(subjects["round"].iloc[0])
                    missing["raceID"] = int(race_row["raceID"])
                    missing = missing.rename(columns={"subjectID": subj_col})
                    subjects = pd.concat(
                        [
                            subjects,
                            missing[
                                [
                                    subj_col,
                                    "points",
                                    "raceID",
                                    "year",
                                    "round",
                                    "position",
                                    "seriesID",
                                ]
                            ].assign(typ=typ),
                        ],
                        ignore_index=True,
                    )

            # Normalize column name to subjectID for the standings table
            subjects = subjects.rename(columns={subj_col: "subjectID"})
            subjects["points"] = subjects["points"].astype(int)
            # Sort by points descending, then by subjectID ascending for deterministic ordering
            subjects = subjects.sort_values(
                by=["points", "subjectID"], ascending=[False, True]
            ).reset_index(drop=True)
            # Assign positions based on sorted order
            subjects["position"] = range(1, len(subjects) + 1)

            # Ensure integer types for key columns
            for col in ["subjectID", "seriesID", "year", "round"]:
                subjects[col] = subjects[col].astype(int)

            final_blocks.append(subjects)

        # Append all computed blocks to the main standings DataFrame
        if final_blocks:
            self.standings = pd.concat([self.standings, *final_blocks], ignore_index=True)

    def plan_races(self, series_model, current_date, champ_per_series: int, nonchamp_per_series: int) -> None:
        """
        Plan races for a season starting from the given date.

        This version picks all candidate race dates (Sundays) inside the season window,
        then for each active series selects (champ_per_series + nonchamp_per_series)
        dates roughly evenly distributed across those Sundays. If there are fewer
        candidate Sundays than required races, the remaining races are assigned
        by round-robin reusing available Sundays so the requested counts always fit.

        Parameters
        ----------
        series_model : object
            Model or container that holds series definitions in series_model.series DataFrame.
            Expected columns: "startYear", "endYear", "seriesID", "name", "reputation".
        current_date : date-like
            Starting date for planning (converted to pandas.Timestamp).
        champ_per_series : int
            Number of races per series per season that should count to the championship.
        nonchamp_per_series : int
            Number of races per series per season that should NOT count to the championship.
        """
        date = pd.Timestamp(current_date)

        # build list of candidate race dates (all Sundays within DAYS_PER_SEASON)
        candidate_dates = []
        d = date
        for _ in range(DAYS_PER_SEASON):
            if d.strftime("%a") == RACE_WEEKDAY:
                candidate_dates.append(pd.Timestamp(d))
            d += timedelta(days=1)

        # helper: choose k indices from n positions roughly evenly distributed
        def pick_even_indices(n: int, k: int):
            if k <= 0:
                return []
            if n <= 0:
                # no candidate dates; return k zeros (will be handled by round-robin later)
                return [0] * k
            if k == 1:
                return [n // 2]
            # distribute using linear spacing and round to nearest index
            indices = []
            for i in range(k):
                # avoid division by zero when k==1 handled above
                pos = i * (n - 1) / (k - 1)
                indices.append(int(round(pos)))
            return indices

        # iterate active series per year and schedule required number of races
        active_series_all = series_model.series  # DataFrame
        # For each day we will still pick a random circuit/layout per race as before.
        for si, srow in active_series_all.iterrows():
            # determine seasons where this series is active within the planning window
            # we will schedule per-season; current_date may span only one season so use candidate_dates' years
            # collect unique seasons present in candidate_dates
            seasons = sorted({int(d.year) for d in candidate_dates}) if candidate_dates else [
                int(pd.Timestamp(current_date).year)]
            for season in seasons:
                # skip series not active this season
                if not (int(srow["startYear"]) <= season <= int(srow["endYear"])):
                    continue

                total_required = int(champ_per_series) + int(nonchamp_per_series)
                # pick indices of candidate_dates to use for this series-season
                n = len(candidate_dates)
                chosen_indices = pick_even_indices(n, total_required)

                # if there were fewer candidate dates than required, fill remaining by round-robin over available indices
                if n < total_required and n > 0:
                    # extend chosen_indices by cycling through 0..n-1 until length == total_required
                    extra_needed = total_required - n
                    for i in range(extra_needed):
                        chosen_indices.append(i % n)
                elif n == 0:
                    # no candidate dates at all: fallback to schedule all races on the season start date
                    chosen_indices = [0] * total_required
                    candidate_dates = [pd.Timestamp(current_date)]

                # decide which of the chosen slots are championship races: pick champ_per_series indices evenly among chosen_indices
                champ_indices_in_chosen = set()
                if champ_per_series > 0:
                    # choose positions among 0..total_required-1
                    pos_indices = pick_even_indices(total_required, champ_per_series)
                    champ_indices_in_chosen = set(pos_indices)

                # now create races for each chosen slot
                for pos, ci in enumerate(chosen_indices):
                    race_date = candidate_dates[ci]
                    is_championship = (pos in champ_indices_in_chosen) and (race_date.year >= 1897)

                    # Skip if no circuits or layouts are available
                    if self.circuits.empty or self.circuit_layouts.empty:
                        continue

                    # Choose a random circuit and a matching layout
                    track_id = int(rd.choice(self.circuits["circuitID"].tolist()))
                    matching = self.circuit_layouts[self.circuit_layouts["circuitID"] == track_id]
                    if matching.empty:
                        continue
                    layout_id = int(rd.choice(matching["layoutID"].tolist()))
                    # Read layout safety rating
                    safety = float(
                        self.circuit_layouts.loc[
                            self.circuit_layouts["layoutID"] == layout_id, "safety"
                        ].iloc[0]
                    )

                    # Determine wetness: a trigger roll and a strength roll if triggered
                    wet_roll = rd.randint(RAIN_TRIGGER_MIN, RAIN_TRIGGER_MAX)
                    wet = rd.randint(RAIN_STRENGTH_MIN,
                                     RAIN_STRENGTH_MAX) / 100 + 1 if wet_roll == RAIN_TRIGGER_MAX else 1

                    # Determine new race ID (incremental)
                    new_race_id = 0 if self.races.empty else int(self.races["raceID"].max()) + 1

                    # Append the new race entry to the races DataFrame
                    self.races.loc[len(self.races)] = {
                        "raceID": new_race_id,
                        "seriesID": int(srow["seriesID"]),
                        "season": int(season),
                        "trackID": track_id,
                        "layoutID": layout_id,
                        "trackSafety": safety,
                        "race_date": race_date,
                        "name": f"Preteky {srow['name']}",
                        "championship": bool(is_championship),
                        "reputation": (
                            1000 // int(srow["reputation"]) if int(srow["reputation"]) else 0
                        ),
                        "reward": (
                            1000000 // int(srow["reputation"]) if int(srow["reputation"]) else 0
                        ),
                        "wet": wet,
                    }
