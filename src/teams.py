import os

import pandas as pd


class TeamsModel:
    def __init__(self):
        self.teams = pd.DataFrame()

    # --- Persistence ---
    def load(self, folder: str) -> bool:
        path = os.path.join(folder, "teams.csv")
        if not os.path.exists(path):
            self.teams = pd.DataFrame()
            return False
        self.teams = pd.read_csv(path)
        return True

    def save(self, base_name: str):
        if base_name:
            self.teams.to_csv(f"{base_name}teams.csv", index=False)

    # --- Business Logic ---
    @staticmethod
    def max_affordable_finance(money: int) -> int:
        return money // 250

    def mark_all_as_ai(self):
        self.teams["ai"] = True

    def get_human_team_mask(self, year: int) -> pd.Series:
        return (
                (self.teams["ai"] == False)
                & (self.teams["found"] <= year)
                & (self.teams["folded"] >= year)
        )

    def get_human_teams(self, date) -> pd.DataFrame:
        if self.teams.empty:
            return self.teams.copy()
        return self.teams.loc[self.get_human_team_mask(date.year)].copy()

    def invest_finance(self, year: int, investments: dict):
        human_mask = self.get_human_team_mask(year)
        human_teams = self.teams.loc[human_mask].copy()

        for team_id, fin_count in investments.items():
            if team_id not in human_teams["teamID"].values:
                continue

            team_row = human_teams.loc[human_teams["teamID"] == team_id]
            money = team_row["money"].iloc[0]
            max_fin = money // 2500

            if 0 <= fin_count <= max_fin:
                idx = team_row.index[0]
                human_teams.at[idx, "money"] -= fin_count * 2500
                human_teams.at[idx, "finance_employees"] = fin_count
            else:
                self.mark_all_as_ai()

        self._update_teams(human_teams)

    def _update_teams(self, updated_df: pd.DataFrame):
        self.teams.set_index("teamID", inplace=True)
        updated_df.set_index("teamID", inplace=True)
        self.teams.update(updated_df)
        self.teams.reset_index(inplace=True)

    def update_money(self):
        self.teams = self.teams.apply(self._calculate_financial_update, axis=1)

    @staticmethod
    def _calculate_financial_update(row: pd.Series) -> pd.Series:
        earn_coef = [12000, 11000, 10000, 9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000, 1000, 0]
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

    def halve_reputations(self):
        self.teams["reputation"] = self.teams["reputation"] // 2

    def update_reputations(self):
        self.update_money()
        self.halve_reputations()

    def add_race_reputation(self, base_reputation: int, results: list[int]):
        for i, team_id in enumerate(results):
            if team_id in self.teams["teamID"].values:
                self.teams.loc[
                    self.teams["teamID"] == team_id, "reputation"
                ] += base_reputation // (i + 1)
