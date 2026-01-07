import pathlib
from collections.abc import Iterable

import pandas as pd

from historical_racing_manager.consts import (
    TEAMS_FILE, TEAMS_FINANCE_FILE,
    COL_TEAM_ID, COL_FOUND, COL_FOLDED,
    FINANCE_EMPLOYEE_SALARY, KICK_EMPLOYEE_PRICE,
    DEFAULT_FOUND_YEAR, DEFAULT_FOLDED_YEAR,
    FINANCE_EARN_COEF,
)


class TeamsModel:
    """Model for managing teams, their staff and basic finances."""

    finance_employee_salary = FINANCE_EMPLOYEE_SALARY
    kick_employee_price = KICK_EMPLOYEE_PRICE

    def __init__(self):
        self.teams = pd.DataFrame()
        self.team_finances = pd.DataFrame()

    # --- Persistence ---
    def load(self, folder: pathlib.Path) -> bool:
        """
        Load teams from a CSV file into a DataFrame.
        If required columns are missing, add them with sensible defaults so GUI and logic work.
        """
        path = folder / TEAMS_FILE
        path_finance = folder / TEAMS_FINANCE_FILE
        if not path.exists():
            self.teams = pd.DataFrame()
            return False
        if not path_finance.exists():
            self.team_finances = pd.DataFrame()
            return False
        self.teams = pd.read_csv(path)
        self.team_finances = pd.read_csv(path_finance)
        # Ensure required columns exist so GUI and business logic don't fail
        required_cols = [
            "team_id",
            "team_name",
            "owner_id",
            "money",
            "finance_employees",
            "reputation",
            "found",
            "folded",
        ]
        for col in required_cols:
            if col not in self.teams.columns:
                # Provide default values based on expected type
                if col in ("money", "finance_employees", "reputation", "owner_id"):
                    self.teams[col] = 0
                elif col == COL_FOUND:
                    self.teams[col] = DEFAULT_FOUND_YEAR
                elif col == COL_FOLDED:
                    self.teams[col] = DEFAULT_FOLDED_YEAR

        return True

    def save(self, folder: pathlib.Path):
        """Save manufacturer-related dataframes to CSV files in the given folder."""
        self.teams.to_csv(folder / TEAMS_FILE, index=False)
        self.team_finances.to_csv(folder / TEAMS_FINANCE_FILE, index=False)

    def get_finance_employee_salary(self) -> int:
        """Return configured salary for a finance employee."""
        return self.finance_employee_salary

    def get_kick_employee_price(self) -> int:
        """Return configured cost for firing/kicking an employee."""
        return self.kick_employee_price

    # --- Business Logic ---
    @staticmethod
    def max_affordable_finance(money: int) -> int:
        """Return how many finance employees can be afforded with the given money."""
        return money // TeamsModel.finance_employee_salary

    def mark_all_as_ai(self):
        """Mark all teams as AI-controlled (owner_id = 0)."""
        self.teams["owner_id"] = 0

    def _get_teams_light(self) -> pd.DataFrame:
        """
        Return a lightweight DataFrame with team_id and team_name.
        Always returns a DataFrame with those columns even if self.teams is empty.
        """
        if getattr(self, "teams", None) is None or self.teams.empty:
            return pd.DataFrame(columns=[COL_TEAM_ID, "team_name"])
        # Ensure team_id column exists
        if COL_TEAM_ID not in self.teams.columns:
            return pd.DataFrame(columns=[COL_TEAM_ID, "team_name"])
        # Ensure team_name exists
        if "team_name" not in self.teams.columns:
            self.teams["team_name"] = ""
        return self.teams[[COL_TEAM_ID, "team_name"]].copy()

    def get_team_names(self, team_ids: Iterable[int]) -> list[str]:
        """
        Return list of team names for the provided team_ids in the same order.
        If an ID is not found, returns an empty string for that position.
        """
        df = self._get_teams_light()
        if df is None or df.empty:
            return ["" for _ in team_ids]

        lookup = df.copy()
        lookup["tid_norm"] = lookup[COL_TEAM_ID].astype(str)
        name_map = lookup.set_index("tid_norm")["team_name"].to_dict()

        result: list[str] = []
        for tid in team_ids:
            key = str(tid)
            result.append(name_map.get(key, ""))
        return result

    def get_teams(self) -> pd.DataFrame:
        """
        Return a DataFrame with team_id, team_name and owner_id for all teams.

        Ensures the returned DataFrame always contains these columns even if the main table is empty.
        """
        if self.teams.empty:
            return pd.DataFrame(columns=["team_id", "team_name", "owner_id"])

        if "owner_id" not in self.teams.columns:
            self.teams["owner_id"] = 0

        return self.teams[["team_id", "team_name", "owner_id"]].copy()

    def get_teams_id(self, search_team_name: str) -> int | None:
        """Return the team_id for a given team name, or None if not found."""
        result = self.teams.query("team_name == @search_team_name")
        return result["team_id"].iat[0] if not result.empty else None

    def get_human_team_mask(self, year: int) -> pd.Series:
        """
        Return a boolean mask selecting teams that are human-controlled and active in the given year.
        A team is considered active if found <= year <= folded.
        """
        return (
                (self.teams["owner_id"] != 0)
                & (self.teams["found"] <= year)
                & (self.teams["folded"] >= year)
        )

    def get_human_teams(self, date) -> pd.DataFrame:
        """Return DataFrame of human-controlled teams active at the given date."""
        if self.teams.empty:
            return pd.DataFrame(columns=self.teams.columns)
        return self.teams.loc[self.get_human_team_mask(date.year)].copy()

    def get_team_staff_counts(self, team_id: int) -> pd.DataFrame:
        """
        Return a DataFrame with counts of finance and design employees for the given team_id.
        Columns: team_id, finance_employees, design_employees.
        """
        result = self.teams.loc[self.teams["team_id"] == team_id, ["team_id", "finance_employees", "design_employees"]]
        return result.reset_index(drop=True)

    def invest_finance(self, year: int, investments: dict):
        """
        Apply finance investments for human teams for a given year.

        investments: dict mapping team_id -> desired number of finance employees.
        The method deducts the corresponding salary cost from the team's money and updates staff counts.
        If an invalid investment is detected, fallback behavior marks all teams as AI.
        """
        human_mask = self.get_human_team_mask(year)
        human_teams = self.teams.loc[human_mask].copy()

        for team_id, fin_count in investments.items():
            if team_id not in human_teams["team_id"].values:
                continue

            team_row = human_teams.loc[human_teams["team_id"] == team_id]
            money = team_row["money"].iloc[0]
            max_fin = money // self.finance_employee_salary

            if 0 <= fin_count <= max_fin:
                idx = team_row.index[0]
                human_teams.at[idx, "money"] -= fin_count * self.finance_employee_salary
                human_teams.at[idx, "finance_employees"] = fin_count
            else:
                # If invalid input is encountered, mark all teams as AI to avoid inconsistent state
                self.mark_all_as_ai()

        self._update_teams(human_teams)

    def _update_teams(self, updated_df: pd.DataFrame):
        """Update the main teams table with values from updated_df (indexed by team_id)."""
        self.teams.set_index("team_id", inplace=True)
        updated_df.set_index("team_id", inplace=True)
        self.teams.update(updated_df)
        self.teams.reset_index(inplace=True)

    def update_money(self, year: int):
        """Apply periodic financial updates to all teams (e.g., revenue from finance employees)."""
        self.teams = self.teams.apply(lambda row: self._calculate_financial_update(row, year), axis=1)

    def _calculate_financial_update(self, row: pd.Series, year: int) -> pd.Series:
        """
        Compute money changes based on finance employees and log the update
        into self.team_finances.
        """
        earn_coef = FINANCE_EARN_COEF

        team_id = row["team_id"]
        money = row["money"]
        old_finance_employees = int(row["finance_employees"])

        new_money = 0
        remaining = old_finance_employees

        for coef in earn_coef:
            if remaining <= 0:
                break
            used = min(remaining, 100)
            new_money += coef * used
            remaining -= used

        # Update row values
        row["money"] = int(money + new_money)
        row["finance_employees"] = int(remaining)

        # --- LOG TO team_finances ---
        if old_finance_employees > 0:
            self.team_finances.loc[len(self.team_finances)] = {
                "team_id": team_id,
                "season": year,
                "finance_employees": old_finance_employees,
                "income": int(new_money),
            }

        return row

    def change_finance_employees(self, team_id: int, amount: int) -> None:
        """
        Set the number of finance employees for the given team to `amount`.
        """
        if team_id in self.teams[COL_TEAM_ID].values:
            self.teams.loc[self.teams[COL_TEAM_ID] == team_id, "finance_employees"] = amount
        else:
            print(f"Team {team_id} does not exist — cannot update employees.")

    def deduct_money(self, team_id: int, amount: int) -> None:
        """Deduct money from the team's balance (e.g., for paying contracts)."""
        if team_id in self.teams[COL_TEAM_ID].values:
            self.teams.loc[self.teams[COL_TEAM_ID] == team_id, "money"] -= amount
        else:
            print(f"Team {team_id} does not exist — cannot deduct money.")

    def get_team_finance_info(self, team_id: int) -> dict:
        """
        Return basic financial information for a team: team_id, money, finance_employees.

        Returns an empty dict if the teams table is not initialized or the team is not found.
        """
        if not hasattr(self, "teams"):
            print("[TeamsModel] teams table is not initialized.")
            return {}

        match = self.teams[self.teams[COL_TEAM_ID] == team_id]
        if match.empty:
            print(f"[TeamsModel] Team with ID {team_id} does not exist.")
            return {}

        row = match.iloc[0]
        return {
            "team_id": int(row["team_id"]),
            "money": int(row["money"]),
            "finance_employees": int(row["finance_employees"]),
        }

    def halve_reputations(self):
        """Halve all teams' reputation values (integer division)."""
        self.teams["reputation"] = self.teams["reputation"] // 2

    def update_reputations_and_money(self, year: int):
        """Update money and then halve reputations as part of end-of-period maintenance."""
        self.update_money(year)
        self.halve_reputations()

    def add_race_reputation(self, base_reputation: int, results: list[int]):
        """
        Increase team reputations based on race results.

        `results` is an ordered list of team IDs (first element = winner).
        Reputation gain is base_reputation divided by finishing position (integer division).
        """
        for i, team_id in enumerate(results):
            if team_id in self.teams[COL_TEAM_ID].values:
                self.teams.loc[self.teams[COL_TEAM_ID] == team_id, "reputation"] += base_reputation // (i + 1)

    def auto_invest_ai_finance(self) -> None:
        """
        For every AI-controlled team (owner_id == 0) choose the number of finance employees
        as min(max_affordable_with_current_money, 1000), deduct the total salary cost from
        the team's money and set the team's finance_employees to that chosen number.

        This operates in-place on self.teams and uses the configured finance_employee_salary.
        """
        if self.teams.empty:
            return

        # Ensure required columns exist to avoid KeyError
        if "owner_id" not in self.teams.columns:
            self.teams["owner_id"] = 0
        if "money" not in self.teams.columns:
            self.teams["money"] = 0
        if "finance_employees" not in self.teams.columns:
            self.teams["finance_employees"] = 0

        # Mask for AI-controlled teams
        ai_mask = self.teams["owner_id"] == 0

        # Iterate over AI teams and apply investment logic
        for idx, row in self.teams.loc[ai_mask].iterrows():
            money = int(row.get("money", 0))
            # Maximum number of finance employees the team can afford right now
            max_affordable = self.max_affordable_finance(money)
            # Choose the number to hire: cap at 1000
            chosen_fin = min(max_affordable, 1000)
            cost = chosen_fin * self.finance_employee_salary

            # Deduct cost and set finance_employees
            self.teams.at[idx, "money"] = money - cost
            self.teams.at[idx, "finance_employees"] = int(chosen_fin)

    def check_debt(self) -> None:
        """
        Check all teams for negative balance. For any team with money < 0:
        - set owner_id to 0 (make the team AI-controlled)
        - reset the team's money to 10_000_000

        Operates in-place on self.teams and is safe if expected columns are missing.
        """
        if self.teams.empty:
            return

        # Ensure required columns exist to avoid KeyError
        if "owner_id" not in self.teams.columns:
            self.teams["owner_id"] = 0
        if "money" not in self.teams.columns:
            self.teams["money"] = 0

        # Create boolean mask for teams with negative money (treat NaN as 0)
        money_series = pd.to_numeric(self.teams["money"].fillna(0), errors="coerce").fillna(0).astype(int)
        debt_mask = money_series < 0

        if not debt_mask.any():
            return

        # Apply bankruptcy rules: make AI-controlled and give bailout
        self.teams.loc[debt_mask, "owner_id"] = 0
        self.teams.loc[debt_mask, "money"] = 10_000_000

        # Optional logging for visibility
        bankrupt_ids = self.teams.loc[debt_mask, "team_id"].tolist() if "team_id" in self.teams.columns else []
        print(f"[TeamsModel] Applied bankruptcy reset to {len(bankrupt_ids)} teams: {bankrupt_ids}")
