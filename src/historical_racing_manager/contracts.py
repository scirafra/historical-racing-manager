import pathlib
import random
from datetime import datetime

import pandas as pd


class ContractsModel:
    """Model for managing contracts (drivers and parts).

    Notes:
    - ``driver_slots_current`` and ``driver_slots_next`` track slot states for each year.
    - Methods are structured to follow the single-responsibility principle and remain readable.
    """

    def __init__(self) -> None:
        # TODO: better would be snake_case naming such as dt_contract
        self.dt_contract: pd.DataFrame = pd.DataFrame()
        self.st_contract: pd.DataFrame = pd.DataFrame()
        self.cs_contract: pd.DataFrame = pd.DataFrame()
        self.ms_contract: pd.DataFrame = pd.DataFrame()
        self.mt_contract: pd.DataFrame = pd.DataFrame()
        self.reserved_slots: dict[int, int] = {}  # team_id → available seats
        self.driver_slots_current: pd.DataFrame = pd.DataFrame()
        self.driver_slots_next: pd.DataFrame = pd.DataFrame()
        self.rules: pd.DataFrame = pd.DataFrame()
        # Mapping: series_id -> reputation (filled during sign_driver_contracts)
        self.series_reputation: dict[int, float] = {}

    # === Persistence ===
    def load(self, folder: pathlib.Path) -> bool:
        """Loads all contract-related CSV files from the given folder.

        Ensures required columns exist in ``dt_contract``.

         folder (Path): Path to the folder containing contract CSV files.

        Returns ``True`` on success, ``False`` on failure.
        """
        try:
            # TODO: why no constants for those file names??
            self.dt_contract = pd.read_csv(folder / "dt_contract.csv")
            self.st_contract = pd.read_csv(folder / "st_contract.csv")
            self.cs_contract = pd.read_csv(folder / "cs_contract.csv")
            self.ms_contract = pd.read_csv(folder / "ms_contract.csv")
            self.mt_contract = pd.read_csv(folder / "mt_contract.csv")
            # TODO: why inconsistent column names and not in some enum/constants?
            self._ensure_columns(
                self.dt_contract,
                {
                    "driver_id": None,
                    "team_id": None,
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

    def save(self, folder: pathlib.Path) -> None:
        """Saves all contract-related DataFrames into CSV files in the given folder."""
        self.dt_contract.to_csv(folder / "dt_contract.csv", index=False)
        self.st_contract.to_csv(folder / "st_contract.csv", index=False)
        self.cs_contract.to_csv(folder / "cs_contract.csv", index=False)
        self.ms_contract.to_csv(folder / "ms_contract.csv", index=False)
        self.mt_contract.to_csv(folder / "mt_contract.csv", index=False)

    def _ensure_columns(self, df: pd.DataFrame, required: dict[str, object]) -> None:
        """Ensures the DataFrame ``df`` contains required columns.

        Missing columns are added with the provided default values.
        """
        for col, default in required.items():
            if col not in df.columns:
                df[col] = default

    # === Driver Slots ===
    def init_driver_slots_for_year(self, year: int, rules: pd.DataFrame) -> pd.DataFrame:
        """Creates a slot table for all teams in ``st_contract`` for the specified year.

        Returns:
            DataFrame with columns: ``team_id``, ``series_id``, ``year``, ``max_slots``, ``signed_slots``, ``free_slots``.
        """
        self.rules = rules
        records: list[dict[str, int]] = []
        for _, row in self.st_contract.iterrows():
            team_id = int(row["team_id"])
            series_id = int(row["series_id"])
            max_slots = int(rules.loc[rules["series_id"] == series_id, "max_cars"].iloc[0])
            signed = (
                self.dt_contract[
                    (self.dt_contract["team_id"] == team_id)
                    & (self.dt_contract["startYear"] <= year)
                    & (self.dt_contract["endYear"] >= year)
                    & (self.dt_contract["active"])
                    ].shape[0]
            )
            records.append(
                {
                    "team_id": team_id,
                    "series_id": series_id,
                    "year": year,
                    "max_slots": max_slots,
                    "signed_slots": signed,
                    "free_slots": max_slots - signed,
                }
            )

        return pd.DataFrame(records)

    def rollover_driver_slots(self) -> None:
        """Moves ``driver_slots_next`` to ``driver_slots_current`` and generates a new ``driver_slots_next``.

        Assumes ``driver_slots_next`` already contains one future year before calling.
        If ``driver_slots_next`` is empty, initializes both ``current`` and ``next``.
        """
        if self.driver_slots_next.empty:
            self.driver_slots_current = self.init_driver_slots_for_year(datetime.now().year, self.rules)
            next_year = (
                self.driver_slots_current["year"].max() + 1
                if not self.driver_slots_current.empty
                else datetime.now().year + 1
            )
            self.driver_slots_next = self.init_driver_slots_for_year(next_year, self.rules)
            print("rollover (empty next) => initialized")
            return

        self.driver_slots_current = self.driver_slots_next.copy(deep=True)
        next_year = int(self.driver_slots_current["year"].max()) + 1
        self.driver_slots_next = self.init_driver_slots_for_year(next_year, self.rules)

    def find_active_driver_contracts(self, team_id: int, start_range: int, series: pd.DataFrame,
                                     active_drivers: pd.DataFrame,
                                     race_model=None) -> pd.DataFrame:
        """Finds all contracts valid for the given ``team_id`` during a sliding 3‑year window.

        The window includes: ``start_range``, ``start_range - 1``, ``start_range - 2``.

        If ``active_drivers`` is provided, merges driver metadata and previous results
        from the race model.
        """
        years = (start_range, start_range - 1, start_range - 2)

        mask = (
                (self.dt_contract["team_id"] == team_id)
                & (self.dt_contract["active"])
                & (
                        (self.dt_contract["endYear"] >= start_range)
                        | (self.dt_contract["startYear"] >= start_range)
                )
        )
        contracts = self.dt_contract[mask].copy()

        if not active_drivers.empty:
            custom_drivers = active_drivers[["driver_id", "forename", "surname", "nationality", "age"]]
            contracts = custom_drivers.merge(contracts, on="driver_id", how="right")

            merged = contracts.copy()

            for yr in years:
                # Filter standings for that year
                year_standings = race_model.standings[race_model.standings["year"] == yr]

                # Reduce to last known round (or last entry)
                last_round = year_standings.sort_values("round").groupby("subjectID").last().reset_index()

                last_round = last_round.merge(series[["series_id", "name"]], on="series_id", how="left")

                year_standings = last_round.rename(
                    columns={
                        "name": f"{yr}",
                        "position": f"Position_{yr}",
                        "points": f"Points_{yr}",
                    }
                )[["subjectID", f"{yr}", f"Position_{yr}", f"Points_{yr}"]]

                merged = merged.merge(year_standings, left_on="driver_id", right_on="subjectID", how="left")
                merged = merged.drop(columns=["subjectID"], errors="ignore")

            base_cols = ["forename", "surname", "nationality", "age", "salary", "startYear", "endYear"]
            other_cols = [c for c in merged.columns if c not in base_cols and c != "driver_id"]
            merged = merged[base_cols + other_cols]
            merged = merged.drop(columns=["team_id", "wanted_reputation", "active", "driver_id"], errors="ignore")
            return merged

        contracts = contracts.drop(columns=["team_id", "wanted_reputation", "active", "driver_id"], errors="ignore")
        return contracts

    def get_contracts_for_year(self, year: int) -> pd.DataFrame:
        """Returns all active contracts for the given year."""
        return self.dt_contract[
            (self.dt_contract["startYear"] <= year)
            & (self.dt_contract["endYear"] >= year)
            & (self.dt_contract["active"] is True)
            ].copy()

    def get_team_series(self, team_id: int) -> list[int]:
        """
        Return a list of series IDs in which the team has a contract.
        """
        try:
            team_contracts = self.st_contract[self.st_contract["team_id"] == team_id]
            if team_contracts.empty:
                return []
            return team_contracts["series_id"].astype(int).unique().tolist()
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
        Find all manufacturer contracts (mt_contract) that are active for the given team_id
        during the specified period. Add information about manufacturers and their results
        (position, points, series) from the last 3 years by part type (engine, chassis, tyres),
        considering only results from the same series in which the contract is valid.
        """

        years = (start_range, start_range - 1, start_range - 2)

        # TODO: emojis in comments are a bit weird... look like AI generated?
        # 🔍 Select all contracts for the given team
        mask = (
                (self.mt_contract["team_id"] == team_id)
                & (
                        (self.mt_contract["endYear"] >= start_range)
                        | (self.mt_contract["startYear"] >= start_range)
                )
        )
        contracts = self.mt_contract[mask].copy()

        if contracts.empty:
            return pd.DataFrame(columns=[
                "name", "part_type", "cost", "startYear", "endYear",
                "series_id", "Position", "Points"
            ])

        # 🔧 Merge with manufacturer table (if available)
        if manufacturer_model is not None and hasattr(manufacturer_model, "manufacturers"):
            manu_df = manufacturer_model.manufacturers[
                ["manufacture_id", "name", "owner", "money", "engine", "chassi", "pneu", "emp"]
            ]
            contracts = contracts.merge(manu_df, on="manufacture_id", how="left")

        merged = contracts.copy()

        # 📈 Add data from standings (results by part_type and series_id)
        if race_model is not None and hasattr(race_model, "standings"):
            for yr in years:
                year_standings = race_model.standings[
                    race_model.standings["year"] == yr
                    ].copy()

                year_data = []

                for _, row in contracts.iterrows():
                    part_type = row["part_type"]
                    series_id = row["series_id"]
                    manu_id = row["manufacture_id"]

                    filt = (
                            (year_standings["typ"] == part_type)
                            & (year_standings["series_id"] == series_id)
                            & (year_standings["subjectID"] == manu_id)
                    )
                    tmp = year_standings[filt]

                    if not tmp.empty:
                        last = tmp.sort_values("round").iloc[-1]
                        # Get series name
                        series_name = series.loc[series["series_id"] == last["series_id"], "name"].values
                        series_label = series_name[0] if len(series_name) > 0 else None

                        year_data.append({
                            "manufacture_id": manu_id,
                            "part_type": part_type,
                            f"{yr}": series_label,
                            f"Position_{yr}": last["position"],
                            f"Points_{yr}": last["points"]
                        })

                if year_data:
                    df_year = pd.DataFrame(year_data)
                    merged = merged.merge(df_year, on=["manufacture_id", "part_type"], how="left")

        # 🧾 Order columns: base + years in order year → position → points
        base_cols = ["name", "part_type", "cost", "startYear", "endYear"]
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
            # order: year, position, points
            cols_sorted = sorted(cols, key=lambda x: (0 if x == y else 1 if "Position" in x else 2))
            ordered_year_cols.extend(cols_sorted)

        final_cols = [c for c in base_cols if c in merged.columns] + ordered_year_cols
        final = merged[final_cols].copy()
        return final

    def update_driver_slot(self, team_id: int, year: int) -> None:
        """
        Increase signed_slots and update free_slots for the corresponding year.

        Updates either driver_slots_current or driver_slots_next depending on which year matches.
        """
        updated = False
        for df in (self.driver_slots_current, self.driver_slots_next):
            if df.empty:
                continue
            mask = (df["team_id"] == team_id) & (df["year"] == year)
            if mask.any():
                # Ensure free_slots does not go negative
                df.loc[mask, "signed_slots"] = df.loc[mask, "signed_slots"] + 1
                df.loc[mask, "free_slots"] = (df.loc[mask, "max_slots"] - df.loc[mask, "signed_slots"]).clip(lower=0)
                updated = True
        if not updated:
            # No record found -> create new (fallback)
            # Get series for team
            series_row = self.st_contract[self.st_contract["team_id"] == team_id]
            if not series_row.empty:
                series_id = int(series_row.iloc[0]["series_id"])
                max_slots = int(self.rules.loc[self.rules["series_id"] == series_id, "max_cars"].iloc[0])
                rec = {
                    "team_id": team_id,
                    "series_id": series_id,
                    "year": year,
                    "max_slots": max_slots,
                    "signed_slots": 1,
                    "free_slots": max_slots - 1,
                }
                # Add to next if year > current_year, otherwise to current
                if not self.driver_slots_current.empty and year == int(self.driver_slots_current["year"].iloc[0]):
                    self.driver_slots_current = pd.concat([self.driver_slots_current, pd.DataFrame([rec])],
                                                          ignore_index=True)
                else:
                    self.driver_slots_next = pd.concat([self.driver_slots_next, pd.DataFrame([rec])], ignore_index=True)

    # === Driver Contracts ===
    def disable_driver_contracts(self, driver_ids: list[int]) -> None:
        """Disable contracts for the given driver IDs."""
        self._ensure_columns(self.dt_contract, {"active": True})
        self.dt_contract.loc[self.dt_contract["driver_id"].isin(driver_ids), "active"] = False

    def disable_driver_contract(self, driver_id: int, current: bool, current_year: int) -> None:
        """
        Disable a driver's contract depending on whether it is current or future.
        """
        self._ensure_columns(self.dt_contract, {"active": True})

        if current:
            mask = (
                    (self.dt_contract["driver_id"] == driver_id) &
                    (self.dt_contract["startYear"] <= current_year) &
                    (self.dt_contract["endYear"] >= current_year) &
                    (self.dt_contract["active"] is True)
            )
        else:
            mask = (
                    (self.dt_contract["driver_id"] == driver_id) &
                    (self.dt_contract["startYear"] > current_year) &
                    (self.dt_contract["active"] is True)
            )

        affected = self.dt_contract.loc[mask]
        self.dt_contract.loc[mask, "active"] = False

        print(f"[ContractsModel] Disabled {'current' if current else 'future'} contract for driver {driver_id}.")
        print(affected)

    def get_ms_contract(self) -> pd.DataFrame:
        """Return the ms_contract DataFrame."""
        return self.ms_contract

    @staticmethod
    def _is_leap(year: int) -> bool:
        """Return True if the given year is a leap year, otherwise False."""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    def _should_sign_today(self, date: datetime) -> bool:
        """
        Determine whether contracts should be signed today based on probability.
        Probability increases as the year progresses.
        """
        day_of_year = date.timetuple().tm_yday
        total_days = 366 if self._is_leap(date.year) else 365
        probability = day_of_year / total_days
        return random.random() < probability

    def _generate_index(self, n: int):
        """
        Generate an index based on weighted probability.
        For small n (<10), use exponential weights. For larger n, use random checks.
        """
        if n < 10:
            weights = [2 ** (n - i - 1) for i in range(n)]
            return random.choices(range(n), weights=weights, k=1)[0]
        while True:
            for i in range(n):
                if random.random() < 0.5:
                    return i

    def _drop_until_free_slot(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Drop rows until a team with free slots is found.
        Returns an empty DataFrame if no team has free slots.
        """
        for i, row in df.iterrows():
            if row["free_slots"] != 0:
                return df.iloc[i:]
        return df.iloc[0:0]  # if no row has a free slot

    def _choose_team_by_reputation(self, teams_df: pd.DataFrame) -> int | None:
        """
        Choose a team based on reputation, ensuring it has free slots available.
        Returns the team_id or None if no suitable team is found.
        """
        if teams_df.empty:
            return None

        sorted_teams = teams_df.sort_values("reputation", ascending=False).reset_index(drop=True)
        filtered_teams = self._drop_until_free_slot(sorted_teams)
        n = len(filtered_teams)

        if n == 0:
            return None

        chosen_index = self._generate_index(n)
        # Move upward until a team with free slots is found
        while chosen_index >= 0 and filtered_teams.iloc[chosen_index]["free_slots"] == 0:
            chosen_index -= 1

        if chosen_index < 0:
            return None  # no team with free slots

        team_id = int(filtered_teams.iloc[chosen_index]["team_id"])
        return team_id

    def _choose_driver_by_reputation(self, drivers_df: pd.DataFrame) -> int | None:
        """
        Choose a driver based on race reputation.
        Returns the driver_id or None if no drivers are available.
        """
        if drivers_df.empty:
            return None
        sorted_drivers = drivers_df.sort_values("reputation_race", ascending=False).reset_index(drop=True)
        n = len(sorted_drivers)

        chosen_index = self._generate_index(n)
        return int(sorted_drivers.iloc[chosen_index]["driver_id"])

    def _reserve_slot_for_human_team(self, team_id: int, max_cars: int) -> None:
        """Increase the number of reserved slots for a human team if it has not reached the maximum."""
        current = self.reserved_slots.get(team_id, 0)
        if current < max_cars:
            self.reserved_slots[team_id] = current + 1
        print(f"Reserved slots: {self.reserved_slots}")

    def _estimate_salary(self, drivers_df: pd.DataFrame, driver_id: int) -> int:
        """Estimate salary for a driver based on base salary and race reputation."""
        base = 25000
        rep = int(drivers_df.loc[drivers_df["driver_id"] == driver_id, "reputation_race"].iloc[0])
        return int(base + rep * 100)

    def _deactivate_lower_series_contract(self, driver_id: int, year: int, new_team_id: int) -> None:
        """
        Deactivate only those active contracts of a driver that would otherwise
        conflict with a new contract. Historical contracts remain untouched.
        """
        mask = (
                (self.dt_contract["driver_id"] == driver_id)
                & (self.dt_contract["team_id"] != new_team_id)
                & (self.dt_contract["active"])
                & (self.dt_contract["endYear"] >= year)
        )

        for idx, row in self.dt_contract[mask].iterrows():
            # print(new_team_id, year, self.dt_contract.at[idx, "endYear"], row)
            self.dt_contract.at[idx, "endYear"] = year - 1
            # print(self.dt_contract.at[idx, "endYear"], row)
            # self.dt_contract.at[idx, "active"] = False

    def _create_driver_contract(
            self, driver_id: int, team_id: int, series_reputation: int, salary: int, start_year: int, length: int
    ) -> None:
        """Create a new driver contract and update the system state."""
        self.dt_contract.loc[len(self.dt_contract)] = {
            "driver_id": int(driver_id),
            "team_id": int(team_id),
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
        """
        Return a DataFrame of drivers who meet the age requirements for the given series
        and do not already have a contract in the same or higher series.

        Also calculates the maximum allowed contract length (max_contract_len) for each driver
        so they do not exceed the maximum age during the contract period.
        """
        able = active_drivers.copy()
        if "reputation_race" not in able.columns:
            able["reputation_race"] = 0
        able["reputation_race"] = able["reputation_race"].fillna(0)

        # Assume "year" column in active_drivers is year of birth
        if "age" not in able.columns:
            if "year" not in able.columns:
                able["year"] = 0
            able["age"] = year - able["year"]

        min_age = int(rules.loc[rules["series_id"] == series_id, "min_age"].iloc[0])
        max_age = int(rules.loc[rules["series_id"] == series_id, "max_age"].iloc[0])

        team_series_row = self.st_contract[self.st_contract["team_id"] == team_id]
        team_series_id = int(team_series_row.iloc[0]["series_id"]) if not team_series_row.empty else None

        # Get series reputation for the team
        series_row = series[series["series_id"] == team_series_id]
        series_reputation = int(series_row.iloc[0]["reputation"]) if not series_row.empty else None

        # Get active contracts
        active_contracts = self.dt_contract[
            (self.dt_contract["startYear"] <= year) &
            (self.dt_contract["endYear"] >= year) &
            (self.dt_contract["active"])
            ]

        unavailable_ids: list[int] = []
        for _, row in active_contracts.iterrows():
            driver_id = int(row["driver_id"])
            wanted_rep = int(row.get("wanted_reputation", 0))

            # Driver is unavailable if their wanted_reputation is ≤ series reputation
            if series_reputation is not None and wanted_rep <= series_reputation:
                unavailable_ids.append(driver_id)

        # Filter out unavailable drivers
        able = able[~able["driver_id"].isin(unavailable_ids)]
        able = able[(able["age"] >= min_age) & (able["age"] <= max_age)]

        # Calculate maximum contract length so driver does not exceed max_age
        able["max_contract_len"] = able["age"].apply(lambda a: max_age - a)
        able = able[able["max_contract_len"] >= 1]
        able["max_contract_len"] = able["max_contract_len"].astype(int)

        return able

    def _get_active_team_contracts(self, team_id: int, year: int) -> pd.DataFrame:
        """Return all active driver contracts for a given team in a specific year."""
        return self.dt_contract[
            (self.dt_contract["team_id"] == team_id)
            & (self.dt_contract["startYear"] <= year)
            & (self.dt_contract["endYear"] >= year)
            & (self.dt_contract["active"])
            ]

    def _get_teams_without_driver(self, teams_df: pd.DataFrame, year: int) -> list[int]:
        """Return a list of team IDs that do not have an active driver contract in the given year."""
        active_contracts = self.dt_contract[
            (self.dt_contract["active"]) & (self.dt_contract["startYear"] <= year) & (
                    self.dt_contract["endYear"] >= year)]
        contracted_team_ids = active_contracts["team_id"].unique()
        all_team_ids = teams_df["team_id"].unique()
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
            team_inputs: dict[int, tuple],
    ) -> None:
        """Main method for signing driver contracts."""
        self._ensure_columns(self.dt_contract, {
            "driver_id": None,
            "team_id": None,
            "salary": 0,
            "wanted_reputation": 0,
            "startYear": 0,
            "endYear": 0,
            "active": True,
        })

        self._prepare_series_reputation(active_series)

        for series_id in active_series["series_id"]:
            self._sign_current_year_contracts(series_id, teams_model, current_date, active_drivers, series, rules,
                                              team_inputs)

        if self._should_sign_today(current_date):
            self._sign_next_year_contract_if_needed(teams_model, current_date, active_drivers, series, rules, teams,
                                                    team_inputs)

    def _prepare_series_reputation(self, active_series: pd.DataFrame) -> None:
        """Prepare a mapping of series_id to reputation values for active series."""
        self.series_reputation = {
            int(row["series_id"]): float(row["reputation"])
            for _, row in active_series.iterrows()
            if "series_id" in row and "reputation" in row
        }

    def _sign_current_year_contracts(
            self, series_id: int, teams_model, current_date: datetime,
            active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame, team_inputs: dict[int, tuple]
    ) -> None:
        """Sign contracts for the current year for all teams in a given series."""
        max_cars = int(rules.loc[rules["series_id"] == series_id, "max_cars"].iloc[0])
        team_ids = self.st_contract[self.st_contract["series_id"] == series_id]["team_id"].astype(int)

        for team_id in team_ids:
            signed = len(self._get_active_team_contracts(team_id, current_date.year))
            missing = max_cars - signed
            is_human = teams_model.teams.loc[teams_model.teams["team_id"] == team_id, "owner_id"].iloc[0] > 0

            for _ in range(missing):
                if is_human and team_inputs.get(team_id):
                    print("R")
                    self._handle_human_contract(team_id, series_id, current_date.year, active_drivers, series, rules,
                                                team_inputs)
                else:
                    if not is_human:
                        # AI team contract signing
                        self._handle_ai_contract(team_id, series_id, current_date.year, 0, active_drivers, series,
                                                 rules)

    def _annotate_teams_with_free_slots(
            self,
            teams: pd.DataFrame,
            rules: pd.DataFrame,
            current_year: int
    ) -> pd.DataFrame:
        """Annotate teams with the number of free slots available for the next year."""
        teams = teams.copy()
        free_slots = []

        for _, row in teams.iterrows():
            team_id = row["team_id"]

            # Get series_id from st_contract
            team_series = self.st_contract[self.st_contract["team_id"] == team_id]
            if team_series.empty:
                free_slots.append(0)
                continue

            series_id = int(team_series.iloc[0]["series_id"])
            max_cars = int(rules.loc[rules["series_id"] == series_id, "max_cars"].iloc[0])
            reserved = self.reserved_slots.get(team_id, 0)
            active = len(self._get_active_team_contracts(team_id, current_year + 1))

            free = max(0, max_cars - reserved - active)
            free_slots.append(free)

        teams["free_slots"] = free_slots
        return teams

    def _sign_next_year_contract_if_needed(
            self, teams_model, current_date: datetime,
            active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame,
            teams: pd.DataFrame, team_inputs: dict[int, tuple]
    ) -> None:
        """Attempt to sign contracts for the next year if conditions are met."""
        teams_updated = self._annotate_teams_with_free_slots(teams, rules, current_date.year)
        team_id = self._choose_team_by_reputation(teams_updated)
        if team_id is None:
            return

        is_human = teams_model.teams.loc[teams_model.teams["team_id"] == team_id, "owner_id"].iloc[0] > 0
        team_series = self.st_contract[self.st_contract["team_id"] == team_id]
        if team_series.empty:
            return

        series_id = int(team_series.iloc[0]["series_id"])
        max_cars = int(rules.loc[rules["series_id"] == series_id, "max_cars"].iloc[0])
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
            self._handle_ai_contract(team_id, series_id, current_date.year, 1, active_drivers, series, rules)

    def _get_reputation_by_series_id(self, df: pd.DataFrame, series_id: int) -> int | None:
        """Return the reputation value for a given series ID, or None if not found."""
        row = df.loc[df['series_id'] == series_id]
        if not row.empty:
            return int(row.iloc[0]['reputation'])
        return None

    def _handle_human_contract(
            self, team_id: int, series_id: int, year: int,
            active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame,
            team_inputs: dict[int, tuple]
    ) -> None:
        """Handle contract signing for a human-controlled team."""
        print("Human team:", team_id)
        driver_id, salary, length = team_inputs[team_id]
        available = self._get_available_drivers(active_drivers, series, year, series_id, team_id, rules)

        if driver_id not in available["driver_id"].values:
            self._decrement_reserved_slot(team_id)
            return

        max_len = int(available.loc[available["driver_id"] == driver_id, "max_contract_len"].iloc[0])
        length = min(length, max_len)
        series_reputation = self._get_reputation_by_series_id(series, series_id)
        self._create_driver_contract(driver_id, team_id, series_reputation, salary, year, length)

    def _handle_ai_contract(
            self, team_id: int, series_id: int, year: int, future_years: int,
            active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame
    ) -> None:
        # print("AI team:", team_id)
        available = self._get_available_drivers(active_drivers, series, year + future_years, series_id, team_id, rules)
        if available.empty:
            return

        driver_id = self._choose_driver_by_reputation(available)
        if driver_id is None:
            self._decrement_reserved_slot(team_id)
            return

        salary = self._estimate_salary(available, driver_id)
        length = 1
        if future_years > 0:
            max_len = int(available.loc[available["driver_id"] == driver_id, "max_contract_len"].iloc[0])
            # Realistic distribution of contract lengths in F1
            lengths = [1, 2, 3, 4]
            weights = [40, 30, 20, 10]

            # If max_len is less than 4, restrict the lists
            max_len = max_len if max_len >= 1 else 1  # ensure it is not 0 or less
            lengths = lengths[:max_len]
            weights = weights[:max_len]

            # Normalize weights to percentages
            total = sum(weights)
            weights = [w / total for w in weights]

            # Choose contract length based on distribution
            length = random.choices(lengths, weights, k=1)[0]

        series_reputation = self._get_reputation_by_series_id(series, series_id)
        self._create_driver_contract(driver_id, team_id, series_reputation, salary, year + future_years, length - 1)

    def _increment_reserved_slot(self, team_id: int, max_cars: int) -> None:
        """Increase the number of reserved slots for a team if it has not reached the maximum."""
        current = self.reserved_slots.get(team_id, 0)
        if current < max_cars:
            self.reserved_slots[team_id] = current + 1
        # print(self.reserved_slots)

    def _decrement_reserved_slot(self, team_id: int) -> None:
        """Decrease the number of reserved slots for a team if it exists."""
        if team_id in self.reserved_slots:
            self.reserved_slots[team_id] = max(0, self.reserved_slots[team_id] - 1)

    # === Car Part Contracts ===
    def _deduct_existing_contract_costs(self, human_teams: pd.DataFrame, active_contracts: pd.DataFrame,
                                        teams: pd.DataFrame) -> None:
        """Deduct costs of existing contracts from human teams' budgets."""
        pay_by_team = (
            active_contracts[active_contracts["team_id"].isin(human_teams["team_id"])].groupby("team_id")["cost"].sum()
        )
        for team_id, total_cost in pay_by_team.items():
            teams.loc[teams["team_id"] == team_id, "money"] -= total_cost

    def _generate_part_contracts(
            self,
            part_type: str,
            series_parts: pd.DataFrame,
            manufacturers: pd.DataFrame,
            teams_in_series: pd.Series,
            active_contracts: pd.DataFrame,
            year: int,
            teams: pd.DataFrame,
    ) -> list[dict[str, object]]:
        """Generate contracts for AI teams for a given part type if no active contract exists."""
        contracts: list[dict[str, object]] = []
        parts_of_type = series_parts[series_parts["part_type"] == part_type].copy()
        if parts_of_type.empty:
            return contracts

        parts_of_type["manufacture_id"] = parts_of_type["manufacture_id"].astype(int)
        manufacturers["manufacture_id"] = manufacturers["manufacture_id"].astype(int)
        parts_of_type = parts_of_type.merge(manufacturers, on="manufacture_id", how="left")
        parts_of_type["cost"] = parts_of_type["cost"].astype(int)

        for team_id in teams_in_series:
            team_id = int(team_id)
            current_contract = active_contracts[
                (active_contracts["team_id"] == team_id) & (active_contracts["part_type"] == part_type)]
            if not current_contract.empty:
                continue

            sampled = parts_of_type.sample(1).iloc[0]
            manufacture_id = int(sampled["manufacture_id"])
            cost = int(sampled["cost"])
            contract_len = random.randint(1, 4)

            contracts.append(
                {
                    "series_id": int(series_parts["series_id"].iloc[0]),
                    "team_id": team_id,
                    "manufacture_id": manufacture_id,
                    "part_type": part_type,
                    "startYear": year,
                    "endYear": year + contract_len,
                    "cost": int(cost),
                }
            )
            teams.loc[teams["team_id"] == team_id, "money"] -= cost

        return contracts

    def get_available_series_parts(self, team_id: int, year: int, car_parts: pd.DataFrame) -> pd.DataFrame:
        """
        Return car parts available for a team in its series for the given year.
        """
        if not hasattr(self, "st_contract"):
            print("[ContractsModel] ⚠️ st_contract is not initialized.")
            return pd.DataFrame()

        # Determine which series the team belongs to
        match = self.st_contract[self.st_contract["team_id"] == team_id]
        if match.empty:
            return pd.DataFrame()

        series_id = int(match.iloc[0]["series_id"])
        print("C", series_id)
        # Filter by series and year
        available_parts = car_parts[
            (car_parts["series_id"] == series_id) &
            (car_parts["year"] == year)
            ].copy()

        return available_parts

    def sign_car_part_contracts(self, active_series: pd.DataFrame, current_date: datetime, car_parts: pd.DataFrame,
                                teams_model, manufacturers: pd.DataFrame,
                                team_inputs: dict[int, dict[str, tuple]]) -> None:
        """
        Sign car part contracts for AI teams and process pending offers for human teams.
        """
        self._ensure_columns(
            self.mt_contract,
            {
                "series_id": None,
                "team_id": None,
                "manufacture_id": None,
                "part_type": "",
                "startYear": 0,
                "endYear": 0,
                "cost": 0,
            },
        )

        car_parts["series_id"] = car_parts["series_id"].astype(int)
        car_parts["year"] = car_parts["year"].astype(int)
        manufacturers["manufacture_id"] = manufacturers["manufacture_id"].astype(int)

        teams = teams_model.teams.sort_values(by="reputation")
        human_teams = teams[
            (teams["owner_id"] > 0) & (teams["found"] <= current_date.year) & (teams["folded"] >= current_date.year)]

        active_contracts = self.mt_contract[
            (self.mt_contract["startYear"] <= current_date.year) & (self.mt_contract["endYear"] >= current_date.year)]
        self._deduct_existing_contract_costs(human_teams, active_contracts, teams)

        new_contracts: list[dict[str, object]] = []
        for si in active_series["series_id"]:
            series_parts = car_parts[
                (car_parts["series_id"] == si) & (car_parts["year"] == current_date.year)
                ]
            all_teams_in_series = self.st_contract[self.st_contract["series_id"] == si]["team_id"].astype(int)

            # Remove human teams
            human_ids = set(teams_model.get_human_teams(current_date)["team_id"].astype(int).values)
            ai_teams_in_series = all_teams_in_series[~all_teams_in_series.isin(human_ids)]

            for part_type in ["engine", "chassi", "pneu"]:
                contracts = self._generate_part_contracts(
                    part_type,
                    series_parts,
                    manufacturers,
                    ai_teams_in_series,
                    active_contracts,
                    current_date.year,
                    teams,
                )
                new_contracts.extend(contracts)

        if new_contracts:
            self.mt_contract = pd.concat([self.mt_contract, pd.DataFrame(new_contracts)], ignore_index=True)

        # === Process human offers ===
        if hasattr(self, "pending_part_offers"):
            for offer in self.pending_part_offers:
                self.mt_contract = pd.concat([
                    self.mt_contract,
                    pd.DataFrame([{
                        "series_id": self._get_series_for_team(offer["team_id"]),
                        "team_id": offer["team_id"],
                        "manufacture_id": self._get_manufacturer_for_part(offer["part_id"]),
                        "part_type": self._get_part_type(offer["part_id"]),
                        "startYear": offer["year"],
                        "endYear": offer["year"] + offer["length"],
                        "cost": offer["price"],
                    }])
                ], ignore_index=True)

                teams_model.teams.loc[teams_model.teams["team_id"] == offer["team_id"], "money"] -= offer["price"]

            self.pending_part_offers.clear()

    def _get_series_for_team(self, team_id: int) -> int:
        match = self.st_contract[self.st_contract["team_id"] == team_id]
        return int(match["series_id"].iloc[0]) if not match.empty else -1

    def _get_manufacturer_for_part(self, part_id: int) -> int:
        match = self.car_parts[self.car_parts["partID"] == part_id]
        return int(match["manufacture_id"].iloc[0]) if not match.empty else -1

    def _get_part_type(self, part_id: int) -> str:
        match = self.car_parts[self.car_parts["partID"] == part_id]
        return str(match["part_type"].iloc[0]) if not match.empty else ""

    def offer_car_part_contract(self, manufacturer_id: int, team_id: int, length: int, price: int, year: int,
                                part_type: str) -> bool:
        """
        Attempts to create a car part contract. If the team already has a contract for the given part type
        during the specified period, no new contract is created.
        """
        self._ensure_columns(self.mt_contract, {
            "series_id": None,
            "team_id": None,
            "manufacture_id": None,
            "part_type": "",
            "startYear": 0,
            "endYear": 0,
            "cost": 0,
        })

        # Check if a contract for this part type already exists during the given period
        overlap_mask = (
                (self.mt_contract["team_id"] == team_id) &
                (self.mt_contract["part_type"] == part_type) &
                (self.mt_contract["startYear"] <= year + length - 1) &
                (self.mt_contract["endYear"] >= year)
        )

        if overlap_mask.any():
            print(
                f"[ContractsModel] Team {team_id} already has a contract for {part_type} in {year}–{year + length - 1}.")
            return False

        # Determine the series for the team
        match = self.st_contract[self.st_contract["team_id"] == team_id]
        if match.empty:
            print(f"[ContractsModel] Team {team_id} has no series, contract not created.")
            return False

        series_id = int(match.iloc[0]["series_id"])

        # Create the new contract
        new_contract = {
            "series_id": series_id,
            "team_id": team_id,
            "manufacture_id": manufacturer_id,
            "part_type": part_type,
            "startYear": year,
            "endYear": year + length - 1,
            "cost": price,
        }

        self.mt_contract = pd.concat([self.mt_contract, pd.DataFrame([new_contract])], ignore_index=True)
        print(
            f"[ContractsModel] ✅ New contract for {part_type} from manufacturer {manufacturer_id} for team {team_id} created.")
        return True

    def get_available_drivers_for_offer(
            self, team_id: int, year: int, active_drivers: pd.DataFrame, series: pd.DataFrame, rules: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Returns a list of drivers that the team (player) can sign for the given year.
        """
        team_row = self.st_contract[self.st_contract["team_id"] == team_id]
        if team_row.empty:
            print("teamrow empty")
            return pd.DataFrame()
        series_id = int(team_row.iloc[0]["series_id"])
        print(len(active_drivers), year, series_id, team_id,
              len(self._get_available_drivers(active_drivers, series, year, series_id, team_id, rules)))
        return self._get_available_drivers(active_drivers, series, year, series_id, team_id, rules)

    def offer_driver_contract(
            self, driver_id: int, team_id: int, salary: int, length: int, year: int
    ) -> None:
        """
        Creates a pending contract offer – the driver will decide the next day.
        """
        if not hasattr(self, "pending_offers"):
            self.pending_offers: list[dict[str, int]] = []
        team_series = self.st_contract[self.st_contract["team_id"] == team_id]
        if team_series.empty:
            print(f"Team {team_id} has no series – cannot offer contract.")
            return

        offer = {
            "driver_id": int(driver_id),
            "team_id": int(team_id),
            "salary": int(salary),
            "length": int(length),
            "year": int(year),
            "days_pending": 1,  # driver will decide within one day
        }
        self.pending_offers.append(offer)
        print(f"[ContractsModel] Offer for driver {driver_id} created (year {year}).")

    def process_driver_offers(self, current_date: datetime, active_drivers: pd.DataFrame) -> list[dict]:
        """
        Processes pending offers – drivers decide whether to accept the contract.
        Typically called during daily progression.
        """
        if not hasattr(self, "pending_offers") or not self.pending_offers:
            return []
        signed_contracts = []

        remaining_offers = []
        print("number of pending offers", self.pending_offers)

        for offer in self.pending_offers:
            driver_id = offer["driver_id"]
            team_id = offer["team_id"]
            salary = offer["salary"]
            length = offer["length"]
            year = offer["year"]

            # Get driver's position based on reputation
            drivers_sorted = active_drivers.sort_values("reputation_race", ascending=False).reset_index(drop=True)
            driver_pos = drivers_sorted[drivers_sorted["driver_id"] == driver_id].index
            if driver_pos.empty:
                print(f"Driver {driver_id} is not among active drivers.")
                continue

            position = driver_pos[0] + 1
            min_salary = 4000000 // position

            # Get team and series info
            team_series = self.st_contract[self.st_contract["team_id"] == team_id]
            if team_series.empty:
                print(f"Team {team_id} has no series.")
                continue

            series_id = int(team_series.iloc[0]["series_id"])
            max_cars = int(self.rules.loc[self.rules["series_id"] == series_id, "max_cars"].iloc[0])
            reserved = self.reserved_slots.get(team_id, 0)
            active_contracts = self._get_active_team_contracts(team_id, year)
            active = len(active_contracts)

            # === Decision logic based on year ===
            if year == current_date.year:
                # Contract for current year → check active slots
                if salary >= min_salary and active < max_cars:
                    print(f"Driver {driver_id} accepted offer from team {team_id} (current year).")
                    self._create_driver_contract(driver_id, team_id, 0, salary, year, length - 1)
                    signed_contracts.append({
                        "driver_id": driver_id,
                        "team_id": team_id,
                        "salary": salary,
                        "year": year
                    })
                else:
                    print(
                        f"Driver {driver_id} rejected offer (current year) – salary {salary} < {min_salary} or team full.")
            elif year == current_date.year + 1:
                # Contract for next year → check reservations
                if reserved > 0 and salary >= min_salary and (reserved + active) <= max_cars:
                    print(f"Driver {driver_id} accepted offer from team {team_id} (next year).")
                    self._create_driver_contract(driver_id, team_id, 0, salary, year, length - 1)
                    self._decrement_reserved_slot(team_id)
                else:
                    print(
                        f"Driver {driver_id} rejected offer (next year) – salary {salary} < {min_salary} or no reservation.")
            else:
                print(f"Unknown year {year} – offer ignored.")

        self.pending_offers = remaining_offers
        print("clearing pending", self.pending_offers, current_date, "reserved", self.reserved_slots)
        return signed_contracts

    def reset_reserved_slot(self) -> None:
        """Resets the reserved slot counts to 0 while preserving existing team_ids."""
        for team_id in self.reserved_slots:
            self.reserved_slots[team_id] = 0

    def cancel_driver_offer(self, driver_id: int, team_id: int) -> None:
        """Cancels a pending contract offer for a driver from a specific team, if it exists."""
        if not hasattr(self, "pending_offers"):
            return
        self.pending_offers = [
            o for o in self.pending_offers if not (o["driver_id"] == driver_id and o["team_id"] == team_id)
        ]
        self._decrement_reserved_slot(team_id)
        print(f"[ContractsModel] Offer for driver {driver_id} from team {team_id} cancelled.")

    def get_terminable_contracts(self, team_id: int, current_year: int) -> pd.DataFrame:
        """
        Returns all active contracts for a team that extend beyond the current year,
        including termination cost and a flag indicating whether the contract is currently active.
        """
        contracts = self.dt_contract[
            (self.dt_contract["team_id"] == team_id) &
            (self.dt_contract["active"] is True) &
            (self.dt_contract["endYear"] >= current_year)
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
        Terminates a driver's contract and returns the termination cost.

        Args:
            driver_id (int): ID of the driver.
            team_id (int): ID of the team.
            current_year (int): The year in which the termination occurs.

        Returns:
            int: The cost of terminating the contract.
        """
        mask = (
                (self.dt_contract["driver_id"] == driver_id) &
                (self.dt_contract["team_id"] == team_id) &
                (self.dt_contract["endYear"] >= current_year)
        )
        contract = self.dt_contract[mask]

        if contract.empty:
            return 0

        salary = int(contract.iloc[0]["salary"])
        end_year = int(contract.iloc[0]["endYear"])
        cost = max(0, end_year - current_year) * salary

        # Remove the contract
        self.dt_contract = self.dt_contract.drop(contract.index)
        print(f"[ContractsModel] Driver {driver_id}'s contract terminated. Cost: {cost}")
        return cost

    def get_active_part_contracts_for_year(self, year: int) -> pd.DataFrame:
        """
        Returns all active part contracts (mt_contract) for the specified year.

        Args:
            year (int): The year to filter contracts by.

        Returns:
            pd.DataFrame: DataFrame containing active part contracts.
        """
        self._ensure_columns(self.mt_contract, {
            "series_id": None,
            "team_id": None,
            "manufacture_id": None,
            "part_type": "",
            "startYear": 0,
            "endYear": 0,
            "cost": 0,
        })

        active = self.mt_contract[
            (self.mt_contract["startYear"] <= year) &
            (self.mt_contract["endYear"] >= year)
            ].copy()

        return active
