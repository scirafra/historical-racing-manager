import os

import pandas as pd

from historical_racing_manager.consts import (
    TEAMS_FILE,
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

    # --- Persistence ---
    def load(self, folder: str) -> bool:
        """
        Load teams from a CSV file into a DataFrame.
        If required columns are missing, add them with sensible defaults so GUI and logic work.
        """
        path = os.path.join(folder, TEAMS_FILE)

        if not os.path.exists(path):
            self.teams = pd.DataFrame()
            return False

        self.teams = pd.read_csv(path)

        # Ensure required columns exist so GUI and business logic don't fail
        required_cols = [
            "teamID",
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

    def save(self, base_name: str):
        """Save teams DataFrame to CSV if a base name is provided."""
        if base_name:
            self.teams.to_csv(f"{base_name}{TEAMS_FILE}", index=False)

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

    def get_teams(self) -> pd.DataFrame:
        """
        Return a DataFrame with teamID, team_name and owner_id for all teams.

        Ensures the returned DataFrame always contains these columns even if the main table is empty.
        """
        if self.teams.empty:
            return pd.DataFrame(columns=["teamID", "team_name", "owner_id"])

        if "owner_id" not in self.teams.columns:
            self.teams["owner_id"] = 0

        return self.teams[["teamID", "team_name", "owner_id"]].copy()

    def get_teams_id(self, search_team_name: str) -> int | None:
        """Return the teamID for a given team name, or None if not found."""
        result = self.teams.query("team_name == @search_team_name")
        return result["teamID"].iat[0] if not result.empty else None

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
        Columns: teamID, finance_employees, design_employees.
        """
        result = self.teams.loc[self.teams["teamID"] == team_id, ["teamID", "finance_employees", "design_employees"]]
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
            if team_id not in human_teams["teamID"].values:
                continue

            team_row = human_teams.loc[human_teams["teamID"] == team_id]
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
        """Update the main teams table with values from updated_df (indexed by teamID)."""
        self.teams.set_index("teamID", inplace=True)
        updated_df.set_index("teamID", inplace=True)
        self.teams.update(updated_df)
        self.teams.reset_index(inplace=True)

    def update_money(self):
        """Apply periodic financial updates to all teams (e.g., revenue from finance employees)."""
        self.teams = self.teams.apply(self._calculate_financial_update, axis=1)

    @staticmethod
    def _calculate_financial_update(row: pd.Series) -> pd.Series:
        """
        Internal helper to compute money changes based on finance employees.

        Uses FINANCE_EARN_COEF as a tiered earning coefficient list.
        """
        earn_coef = FINANCE_EARN_COEF

        money, finance_employees = row["money"], row["finance_employees"]

        for coef in earn_coef:
            if finance_employees <= 0:
                break
            used = min(finance_employees, 100)
            money += coef * used
            finance_employees -= used

        row["money"] = int(money)
        row["finance_employees"] = int(finance_employees)
        return row

    def change_finance_employees(self, team_id: int, amount: int) -> None:
        """
        Set the number of finance employees for the given team to `amount`.
        """
        if team_id in self.teams[COL_TEAM_ID].values:
            self.teams.loc[self.teams[COL_TEAM_ID] == team_id, "finance_employees"] = amount
            print(f"Team {team_id} now has {amount} finance employees.")
        else:
            print(f"Team {team_id} does not exist — cannot update employees.")

    def deduct_money(self, team_id: int, amount: int) -> None:
        """Deduct money from the team's balance (e.g., for paying contracts)."""
        if team_id in self.teams[COL_TEAM_ID].values:
            self.teams.loc[self.teams[COL_TEAM_ID] == team_id, "money"] -= amount
            print(f"Team {team_id} paid {amount}.")
        else:
            print(f"Team {team_id} does not exist — cannot deduct money.")

    def get_team_finance_info(self, team_id: int) -> dict:
        """
        Return basic financial information for a team: teamID, money, finance_employees.

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
            "teamID": int(row["teamID"]),
            "money": int(row["money"]),
            "finance_employees": int(row["finance_employees"]),
        }

    def halve_reputations(self):
        """Halve all teams' reputation values (integer division)."""
        self.teams["reputation"] = self.teams["reputation"] // 2

    def update_reputations(self):
        """Update money and then halve reputations as part of end-of-period maintenance."""
        self.update_money()
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
