import os
import random as rd
from datetime import timedelta

import numpy as np
import pandas as pd


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
    def load(self, base_path: str) -> bool:
        required = [
            "stands.csv",
            "races.csv",
            "pointSystem.csv",
            "results.csv",
            "circuits.csv",
            "circuit_layouts.csv",
        ]
        missing = [f for f in required if not os.path.exists(base_path + f)]
        if missing:
            return False

        self.standings = pd.read_csv(base_path + "stands.csv")
        self.races = pd.read_csv(base_path + "races.csv")
        if not self.races.empty and "race_date" in self.races.columns:
            self.races["race_date"] = pd.to_datetime(self.races["race_date"], errors="coerce")

        self.point_system = pd.read_csv(base_path + "pointSystem.csv")
        self.results = pd.read_csv(base_path + "results.csv")
        self.circuits = pd.read_csv(base_path + "circuits.csv")
        self.circuit_layouts = pd.read_csv(base_path + "circuit_layouts.csv")
        return True

    def save(self, base_path: str) -> None:
        if not base_path:
            return
        self.races.to_csv(base_path + "races.csv", index=False)
        self.standings.to_csv(base_path + "stands.csv", index=False)
        self.point_system.to_csv(base_path + "pointSystem.csv", index=False)
        self.results.to_csv(base_path + "results.csv", index=False)
        self.circuits.to_csv(base_path + "circuits.csv", index=False)
        self.circuit_layouts.to_csv(base_path + "circuit_layouts.csv", index=False)

    # ===== Queries =====
    def extract_champions(self, series_id: str, series: pd.DataFrame, manufacturers: pd.DataFrame,
                          teams: pd.DataFrame, drivers: pd.DataFrame) -> pd.DataFrame:
        # Filtrovanie podľa seriesID a pozície 1
        filtered = self.standings[
            (self.standings['seriesID'] == series_id) &
            (self.standings['position'] == 1)
            ]

        # Pivotovanie dát: každý typ bude vlastný stĺpec
        pivot = filtered.pivot_table(
            index='year',
            columns='typ',
            values='subjectID',
            aggfunc='first'  # predpokladáme, že je len jeden víťaz pre typ a rok
        ).reset_index()

        # Pridáme späť seriesID ako stĺpec
        pivot.insert(0, 'seriesID', series_id)

        # Získaj názov série
        series_name = series.loc[series["seriesID"] == series_id, "name"].values
        series_label = series_name[0] if len(series_name) > 0 else None
        pivot.insert(1, 'series', series_label)

        # Doplníme meno jazdca, ak existuje stĺpec 'driver'
        if 'driver' in pivot.columns:
            pivot = pivot.merge(
                drivers[["driverID", "forename", "surname"]],
                left_on="driver",
                right_on="driverID",
                how="left"
            )
            pivot["driver_name"] = pivot["forename"] + " " + pivot["surname"]
            pivot.drop(columns=["driverID", "forename", "surname", "driver"], inplace=True)

        # Doplníme názov tímu, ak existuje stĺpec 'team'
        if 'team' in pivot.columns:
            pivot = pivot.merge(
                teams[["teamID", "team_name"]],
                left_on="team",
                right_on="teamID",
                how="left"
            )
            pivot.drop(columns=["teamID", "team"], inplace=True)

        # Doplníme názvy výrobcov pre engine, chassi, pneu
        mf_map = manufacturers.set_index("manufacturerID")["name"].to_dict()
        for part in ["engine", "chassi", "pneu"]:
            if part in pivot.columns:
                pivot[part] = pivot[part].map(mf_map)

        # Zoradenie stĺpcov: year, forename, surname, team_name, engine, chassi, pneu, ostatné
        desired_order = ['year', 'driver_name', 'team_name', 'engine', 'chassi', 'pneu']
        other_columns = sorted([
            col for col in pivot.columns
            if col not in desired_order and col not in ('series')
        ])
        final_order = ['series'] + desired_order + other_columns
        pivot = pivot[[col for col in final_order if col in pivot.columns]]

        # Odstráň seriesID
        pivot.drop(columns=["seriesID"], inplace=True)

        return pivot

    def get_upcoming_races_for_series(self, series_ids: list[int], series: pd.DataFrame,
                                      current_date: str) -> pd.DataFrame:
        """
        Vráti najbližších 5 pretekov pre dané série po aktuálnom dátume.
        """
        try:
            if not series_ids or self.races.empty:
                return pd.DataFrame(columns=["Date", "Race Name", "Series", "Country"])

            # Vyfiltruj relevantné preteky
            races = self.races[
                (self.races["seriesID"].isin(series_ids)) &
                (self.races["race_date"] >= current_date)
                ].copy()

            # Premenuj názov pretekov, aby sa nebil s názvom série
            races.rename(columns={"name": "Race Name"}, inplace=True)

            # Spoj s názvami sérií
            races = races.merge(series[["seriesID", "name"]], on="seriesID", how="left")

            # Premenuj názov série
            races.rename(columns={"name": "Series", "race_date": "Date"}, inplace=True)

            # Voliteľne: ak máš stĺpec "country" v self.races, pridaj ho
            if "country" in races.columns:
                races.rename(columns={"country": "Country"}, inplace=True)
                races = races[["Date", "Race Name", "Series", "Country"]]
            else:
                races = races[["Date", "Race Name", "Series"]]
            # Preveď dátum na formát yyyy-mm-dd bez času
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
        Returns the seasonal statistics of a driver/team based on standings and results.
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

            # Získaj názov série
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
        # Vytvor mapovanie ID → názov výrobcu
        manu_map = manufacturers.set_index("manufacturerID")["name"].to_dict()

        if df.empty:
            return pd.DataFrame()

        df["round"] = df["round"].fillna(0).astype(int)
        df["position"] = df["position"].replace({999: "Crash", 998: "Death"})

        zero_rids = sorted(df.loc[df["round"] == 0, "raceID"].unique())
        zero_map = {rid: f"NC{i + 1}" for i, rid in enumerate(zero_rids)}
        df["col_label"] = df.apply(
            lambda r: zero_map[r["raceID"]] if r["round"] == 0 else str(r["round"]), axis=1
        )
        # Nahraď ID za názvy
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

    # ===== Simulation =====
    def prepare_race(
            self,
            drivers_model,
            series_model,
            manufacturer_model,
            contracts_model,
            races_today: pd.DataFrame,
            idx: int,
            current_date,
    ) -> list[int]:
        series_id = int(races_today.iloc[idx]["seriesID"])
        layout_id = int(races_today.iloc[idx]["layoutID"])
        layout_row = self.circuit_layouts[self.circuit_layouts["layoutID"] == layout_id].iloc[0]

        active_dt = contracts_model.DTcontract[
            (contracts_model.DTcontract["active"])
            & (contracts_model.DTcontract["startYear"] <= current_date.year)
            & (contracts_model.DTcontract["endYear"] >= current_date.year)
            ]
        active_dt = active_dt[active_dt["driverID"].isin(drivers_model.active_drivers["driverID"])]

        teams_in_series = contracts_model.STcontract[
            contracts_model.STcontract["seriesID"] == series_id
            ]["teamID"]
        grid_dt = active_dt[active_dt["teamID"].isin(teams_in_series)]

        selected = pd.merge(
            grid_dt,
            drivers_model.active_drivers[["driverID", "ability"]],
            on="driverID",
            how="left",
        )

        for col in ("power", "reliability", "safety", "engine", "chassi", "pneu"):
            selected[col] = selected.get(col, 0)

        active_mt = contracts_model.MTcontract[
            (contracts_model.MTcontract["startYear"] <= current_date.year)
            & (contracts_model.MTcontract["endYear"] >= current_date.year)
            & (contracts_model.MTcontract["seriesID"] == series_id)
            ].copy()

        parts = manufacturer_model.car_parts[
            (manufacturer_model.car_parts["seriesID"] == series_id)
            & (manufacturer_model.car_parts["year"] == current_date.year)
            ].copy()
        merge_keys = ["seriesID", "manufacturerID"]
        for key in merge_keys:
            parts[key] = parts[key].astype(int)
            active_mt[key] = active_mt[key].astype(int)

        parts["partType"] = parts["partType"].astype(str)
        active_mt["partType"] = active_mt["partType"].astype(str)

        merged = pd.merge(
            active_mt,
            parts,
            on=["seriesID", "manufacturerID", "partType"],
            how="left",
        )

        for _, part in merged.iterrows():
            team_id = part["teamID"]
            mask = selected["teamID"] == team_id
            selected.loc[mask, part["partType"]] = (
                int(part["manufacturerID"]) if pd.notna(part["manufacturerID"]) else 0
            )
            selected.loc[mask, "power"] += int(part.get("power", 0))
            selected.loc[mask, "reliability"] += int(part.get("reliability", 0))
            selected.loc[mask, "safety"] += int(part.get("safety", 0))

        corners = int(layout_row.get("corners", 1) or 1)
        wet_val = max(float(races_today.iloc[idx].get("wet", 1) or 1), 1.0)
        track_factor = max(int(corners / wet_val), 1)

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

        race_data = race_data.sort_values(by="totalAbility", ascending=False).reset_index(drop=True)

        rules = series_model.point_rules[
            (series_model.point_rules["seriesID"] == series_id)
            & (series_model.point_rules["startSeason"] <= current_date.year)
            & (series_model.point_rules["endSeason"] >= current_date.year)
            ].reset_index(drop=True)

        ps = self.point_system[self.point_system["psID"] == rules.loc[0, "psID"]].reset_index(
            drop=True
        )

        return self.simulate_race(drivers_model, races_today.iloc[idx], race_data, rules, ps)

    def simulate_race(
            self,
            drivers_model,
            race_row: pd.Series,
            race_data: pd.DataFrame,
            current_point_rules: pd.DataFrame,
            ps: pd.DataFrame,
    ) -> list[int]:
        died: list[int] = []
        if race_data.empty:
            return died

        track_safety = float(race_row.get("trackSafety", 1) or 1)
        wet_val = float(race_row.get("wet", 1) or 1)
        race_data["carReliability"] = (race_data["carReliability"] * track_safety * wet_val).astype(
            int
        )
        race_data["finished"] = race_data.apply(self._simulate_outcome, axis=1)

        if int(race_row["seriesID"]) == 1 and int(race_row["season"]) > 1949:
            self.crashes += int((race_data["finished"] == "Crash").sum())
            self.deaths += int((race_data["finished"] == "Death").sum())
            self.f1_races += 1

        finish = race_data[race_data["finished"] == "Good"].reset_index(drop=True)
        crash = race_data[race_data["finished"] == "Crash"].reset_index(drop=True)
        death = race_data[race_data["finished"] == "Death"].reset_index(drop=True)

        idx_pool = list(range(len(finish)))
        ranking: list[tuple[int, bool]] = []
        rep_drivers: list[int] = []

        dmax = len(finish)
        for _ in range(dmax):
            chosen = dmax
            while chosen == dmax:
                for j in range(len(idx_pool)):
                    if rd.randint(0, 9) < 3:
                        chosen = idx_pool[j]
                        break
            ranking.append((chosen, True))
            rep_drivers.append(int(finish.loc[chosen, "driverID"]))
            idx_pool.remove(chosen)

        if hasattr(drivers_model, "race_reputations"):
            drivers_model.race_reputations(int(race_row.get("reputation", 0) or 0), rep_drivers)

        round_no = 0
        if bool(race_row.get("championship", False)):
            pre = self.standings[
                (self.standings["seriesID"] == race_row["seriesID"])
                & (self.standings["year"] == race_row["season"])
                ]
            round_no = 1 if pre.empty else int(pre["round"].max()) + 1

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

        for _, row in crash.iterrows():
            self.results.loc[len(self.results)] = [
                int(race_row["raceID"]),
                int(row["driverID"]),
                int(row["teamID"]),
                int(row["carID"]),
                999,
                int(race_row["season"]),
                int(race_row["seriesID"]),
                int(round_no),
                int(row["engineID"]),
                int(row["chassiID"]),
                int(row["pneuID"]),
            ]

        for _, row in death.iterrows():
            self.results.loc[len(self.results)] = [
                int(race_row["raceID"]),
                int(row["driverID"]),
                int(row["teamID"]),
                int(row["carID"]),
                998,
                int(race_row["season"]),
                int(race_row["seriesID"]),
                int(round_no),
                int(row["engineID"]),
                int(row["chassiID"]),
                int(row["pneuID"]),
            ]
            died.append(int(row["driverID"]))

        if bool(race_row.get("championship", False)):
            self._update_standings(
                race_row, race_data, ranking, finish, crash, death, current_point_rules, ps
            )

        return died

    def _simulate_outcome(self, row: pd.Series) -> str:
        speed_limit = max(int(row.get("carSpeedAbility", 0)), 0)
        reliability = max(int(row.get("carReliability", 0)), 0)
        safety = max(int(row.get("carSafety", 0)), 0)

        if speed_limit <= 0:
            return "Crash"

        rnd1 = np.random.randint(0, speed_limit * 1000)
        if rnd1 < reliability:
            rnd2 = np.random.randint(0, speed_limit + 1)
            return "Death" if rnd2 < safety else "Crash"
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
        pre = self.standings[
            (self.standings["seriesID"] == race_row["seriesID"])
            & (self.standings["year"] == race_row["season"])
            ]
        final_blocks = []
        not_finish = pd.concat([crash, death], ignore_index=True)

        for typ in ("driver", "team", "engine", "chassi", "pneu"):
            subj_col = f"{typ}ID"
            subjects = race_data[[subj_col]].drop_duplicates().copy()
            subjects["cars"] = (
                1 if typ == "driver" else int(current_point_rules.iloc[0].get(f"{typ}Cts", 1))
            )
            subjects["points"] = 0

            prev_for_typ = pre[pre["typ"] == typ]
            this_round = prev_for_typ["round"].max() if not prev_for_typ.empty else 0
            last_round_block = (
                prev_for_typ[prev_for_typ["round"] == this_round].copy()
                if this_round
                else pd.DataFrame(columns=["subjectID", "points"])
            )

            for pos, (fin_idx, _) in enumerate(ranking, start=1):
                if fin_idx not in finish.index:
                    continue
                current_subject = int(finish.loc[fin_idx, subj_col])
                pts = int(ps.iloc[0].get(str(pos), 0))
                mask = (subjects[subj_col] == current_subject) & (subjects["cars"] > 0)
                subjects.loc[mask, ["cars", "points"]] += [-1, pts]

            for _, row in not_finish.iterrows():
                current_subject = int(row[subj_col])
                mask = (subjects[subj_col] == current_subject) & (subjects["cars"] > 0)
                subjects.loc[mask, ["cars", "points"]] += [-1, 0]

            subjects["raceID"] = int(race_row["raceID"])
            subjects["year"] = int(race_row["season"])
            subjects["round"] = 1 if last_round_block.empty else int(this_round) + 1
            subjects["position"] = 0
            subjects["seriesID"] = int(race_row["seriesID"])
            subjects["typ"] = typ

            if not last_round_block.empty:
                prev_pts = last_round_block.set_index("subjectID")["points"]
                subjects["points"] = subjects[subj_col].map(prev_pts).fillna(0).astype(
                    int
                ) + subjects["points"].astype(int)

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

            subjects = subjects.rename(columns={subj_col: "subjectID"})
            subjects["points"] = subjects["points"].astype(int)
            subjects = subjects.sort_values(
                by=["points", "subjectID"], ascending=[False, True]
            ).reset_index(drop=True)
            subjects["position"] = range(1, len(subjects) + 1)

            for col in ["subjectID", "seriesID", "year", "round"]:
                subjects[col] = subjects[col].astype(int)

            final_blocks.append(subjects)

        if final_blocks:
            self.standings = pd.concat([self.standings, *final_blocks], ignore_index=True)

    def plan_races(self, series_model, current_date) -> None:
        week_counter = 0
        date = pd.Timestamp(current_date)

        for _ in range(364):
            if date.strftime("%a") == "Sun":
                week_counter += 1
                if week_counter % 5 == 0:
                    active_series = series_model.series[
                        (series_model.series["startYear"] <= date.year)
                        & (series_model.series["endYear"] >= date.year)
                        ]
                    for si, srow in active_series.iterrows():
                        new_race_id = 0 if self.races.empty else int(self.races["raceID"].max()) + 1
                        championship = not (si == active_series.index[-1] and week_counter % 6 == 0)

                        if self.circuits.empty or self.circuit_layouts.empty:
                            continue
                        track_id = int(rd.choice(self.circuits["circuitID"].tolist()))
                        matching = self.circuit_layouts[
                            self.circuit_layouts["circuitID"] == track_id
                            ]
                        if matching.empty:
                            continue
                        layout_id = int(rd.choice(matching["layoutID"].tolist()))
                        safety = float(
                            self.circuit_layouts.loc[
                                self.circuit_layouts["layoutID"] == layout_id, "safety"
                            ].iloc[0]
                        )

                        wet_roll = rd.randint(1, 8)
                        wet = rd.randint(1, 50) / 100 + 1 if wet_roll == 8 else 1

                        self.races.loc[len(self.races)] = {
                            "raceID": new_race_id,
                            "seriesID": int(srow["seriesID"]),
                            "season": int(date.year),
                            "trackID": track_id,
                            "layoutID": layout_id,
                            "trackSafety": safety,
                            "race_date": date,
                            "name": f"Preteky {srow['name']}",
                            "championship": championship,
                            "reputation": (
                                1000 // int(srow["reputation"]) if int(srow["reputation"]) else 0
                            ),
                            "reward": (
                                1000000 // int(srow["reputation"]) if int(srow["reputation"]) else 0
                            ),
                            "wet": wet,
                        }
            date += timedelta(days=1)
