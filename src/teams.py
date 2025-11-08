import os

import pandas as pd


class TeamsModel:
    finance_employee_salary = 2500
    kick_employee_price = 1000

    def __init__(self):
        self.teams = pd.DataFrame()

    # --- Persistence ---
    def load(self, folder: str) -> bool:
        """
        Načíta tímy z CSV súboru do DataFrame.
        Ak chýbajú povinné stĺpce, doplní ich.
        """
        path = os.path.join(folder, "teams.csv")
        if not os.path.exists(path):
            self.teams = pd.DataFrame()
            return False

        self.teams = pd.read_csv(path)

        # ✅ doplnenie chýbajúcich stĺpcov, aby GUI aj logika fungovali
        required_cols = ["teamID", "team_name", "owner_id", "money", "finance_employees", "reputation", "found",
                         "folded"]
        for col in required_cols:
            if col not in self.teams.columns:
                # podľa typu dáme default hodnotu
                if col in ("money", "finance_employees", "reputation", "owner_id"):
                    self.teams[col] = 0
                elif col in ("found",):
                    self.teams[col] = 1800
                elif col in ("folded",):
                    self.teams[col] = 3000

        return True

    def save(self, base_name: str):
        if base_name:
            self.teams.to_csv(f"{base_name}teams.csv", index=False)

    def get_finance_employee_salary(self) -> int:
        return self.finance_employee_salary

    def get_kick_employee_price(self) -> int:
        return self.kick_employee_price

    # --- Business Logic ---
    @staticmethod
    def max_affordable_finance(money: int) -> int:
        return money // TeamsModel.finance_employee_salary

    def mark_all_as_ai(self):
        self.teams["owner_id"] = 0

    def get_teams(self) -> pd.DataFrame:
        """
        Vracia DataFrame s ID, menom a vlastníkom tímu.
        """
        if self.teams.empty:
            return pd.DataFrame(columns=["teamID", "team_name", "owner_id"])

        if "owner_id" not in self.teams.columns:
            self.teams["owner_id"] = 0

        return self.teams[["teamID", "team_name", "owner_id"]].copy()

    def get_teams_id(self, search_team_name: str) -> int | None:
        result = self.teams.query("team_name == @search_team_name")
        return result["teamID"].iat[0] if not result.empty else None

    def get_human_team_mask(self, year: int) -> pd.Series:
        return (
                (self.teams["owner_id"] != 0)
                & (self.teams["found"] <= year)
                & (self.teams["folded"] >= year)
        )

    def get_human_teams(self, date) -> pd.DataFrame:
        if self.teams.empty:
            return pd.DataFrame(columns=self.teams.columns)
        return self.teams.loc[self.get_human_team_mask(date.year)].copy()

    def get_team_staff_counts(self, team_id: int) -> pd.DataFrame:
        """
        Vráti DataFrame s počtom finančných a dizajnérskych zamestnancov pre daný team_id.
        Obsahuje stĺpce: teamID, finance_employees, design_employees.
        """
        result = self.teams.loc[self.teams['teamID'] == team_id, ['teamID', 'finance_employees', 'design_employees']]
        return result.reset_index(drop=True)

    def invest_finance(self, year: int, investments: dict):

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

    def change_finance_employees(self, team_id: int, amount: int) -> None:
        """
        Nastaví počet finančných zamestnancov pre daný tím na hodnotu `amount`.
        """
        if team_id in self.teams["teamID"].values:
            self.teams.loc[self.teams["teamID"] == team_id, "finance_employees"] = amount
            print(f"👥 Tím {team_id} má teraz {amount} finančných zamestnancov.")
        else:
            print(f"⚠️ Tím {team_id} neexistuje – nemôžem upraviť zamestnancov.")

    def deduct_money(self, team_id: int, amount: int) -> None:
        """Odpočíta peniaze tímu za kontrakt."""
        if team_id in self.teams["teamID"].values:
            self.teams.loc[self.teams["teamID"] == team_id, "money"] -= amount
            print(f"💸 Tím {team_id} zaplatil {amount}.")
        else:
            print(f"⚠️ Tím {team_id} neexistuje – nemôžem odpočítať peniaze.")

    def get_team_finance_info(self, team_id: int) -> dict:
        """
        Vráti základné finančné údaje tímu: teamID, money, finance_employees.
        """
        if not hasattr(self, "teams"):
            print("[TeamsModel] ⚠️ teams tabuľka nie je inicializovaná.")
            return {}

        match = self.teams[self.teams["teamID"] == team_id]
        if match.empty:
            print(f"[TeamsModel] ⚠️ Tím s ID {team_id} neexistuje.")
            return {}

        row = match.iloc[0]
        return {
            "teamID": int(row["teamID"]),
            "money": int(row["money"]),
            "finance_employees": int(row["finance_employees"])
        }

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
