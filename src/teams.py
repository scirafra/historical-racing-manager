import os

import pandas as pd


class TeamsModel:
    def __init__(self):
        self.teams = pd.DataFrame()

    # --- Persistence ---
    def load(self, folder: str) -> bool:
        """Load teams from CSV if it exists."""
        file_path = os.path.join(folder, "teams.csv")
        if not os.path.exists(file_path):
            self.teams = pd.DataFrame()
            return False
        self.teams = pd.read_csv(file_path)
        return True

    def save(self, base_name: str):
        """Save teams to CSV."""
        if base_name:
            self.teams.to_csv(f"{base_name}teams.csv", index=False)

    # --- Business logic ---
    @staticmethod
    def max_affordable_finance(money: int) -> int:
        """Return the maximum number of finance employees affordable with the given budget."""
        return money // 250

    def mark_all_as_ai(self):
        """Mark all teams as AI-controlled."""
        self.teams["ai"] = True

    def invest_finance(self, year: int, investments: dict):
        """
        Update finances of human-controlled teams based on investments.
        investments = {teamID: number_of_finance_employees}
        """
        mask = (
                (self.teams["ai"] == False)
                & (self.teams["found"] <= year)
                & (self.teams["folded"] >= year)
        )
        human_teams = self.teams.loc[mask].copy()

        for team_id, fin_count in investments.items():
            if team_id in human_teams["teamID"].values:
                max_fin = human_teams.loc[human_teams["teamID"] == team_id, "money"].iloc[0] // 2500
                if 0 <= fin_count <= max_fin:
                    idx = human_teams.index[human_teams["teamID"] == team_id][0]
                    human_teams.at[idx, "money"] -= fin_count * 2500
                    human_teams.at[idx, "fin"] = fin_count
                else:
                    self.mark_all_as_ai()

        self.teams.set_index("teamID", inplace=True)
        human_teams.set_index("teamID", inplace=True)
        self.teams.update(human_teams)
        self.teams.reset_index(inplace=True)

    @staticmethod
    def _update_money_for_team(row):
        """Calculate profit based on the number of finance employees."""
        earn_coef = [12000, 11000, 10000, 9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000, 1000, 0]
        money, fin = row["money"], row["fin"]

        for coef in earn_coef:
            if fin <= 0:
                break
            used = min(fin, 100)
            money += coef * used
            fin -= used

        row["money"] = int(money)
        row["fin"] = int(fin)
        return row

    def update_money(self):
        """Update finances for all teams."""
        self.teams = self.teams.apply(self._update_money_for_team, axis=1)

    def update_reputations(self):
        """Halve the reputation of all teams after updating finances."""
        self.update_money()

        self.teams["reputation"] = self.teams["reputation"] // 2

    def get_human_teams(self, date):
        """
        Return a DataFrame of human-controlled teams that exist in the given year.
        """
        if self.teams.empty:
            return self.teams  # empty DataFrame

        mask = (
                (self.teams["ai"] == False)
                & (self.teams["found"] <= date.year)
                & (self.teams["folded"] >= date.year)
        )
        return self.teams.loc[mask].copy()

    def add_race_reputation(self, base_reputation: int, results: list):
        """Increase reputation based on race results."""
        for i, team_id in enumerate(results):
            self.teams.loc[self.teams["teamID"] == team_id, "reputation"] += base_reputation // (
                    i + 1
            )
