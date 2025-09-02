import os

import pandas as pd


class SeriesModel:
    def __init__(self):
        self.series = pd.DataFrame()
        self.point_rules = pd.DataFrame()

    # --- Persistence ---
    def load(self, folder: str) -> bool:
        """Load series and point rules from CSV files if they exist."""
        series_path = os.path.join(folder, "series.csv")
        points_path = os.path.join(folder, "point_rules.csv")

        if not os.path.exists(series_path) or not os.path.exists(points_path):
            self.series = pd.DataFrame(columns=["seriesID", "name", "startYear", "endYear"])
            self.point_rules = pd.DataFrame()
            return False

        self.series = pd.read_csv(series_path)
        self.point_rules = pd.read_csv(points_path)

        return True

    def save(self, folder: str):
        """Save series and point rules to CSV files."""
        if folder:
            self.series.to_csv(os.path.join(folder, "series.csv"), index=False)
            self.point_rules.to_csv(os.path.join(folder, "point_rules.csv"), index=False)

    # --- Business logic ---
    def get_series(self) -> pd.DataFrame:
        """Return a DataFrame with seriesID and name columns."""
        if self.series.empty:
            return pd.DataFrame(columns=["seriesID", "name"])
        return self.series[["seriesID", "name"]].reset_index(drop=True)

    def get_series_id(self, series_name: str):
        """Return the seriesID for the given series name, or None if not found."""
        result = self.series[self.series["name"] == series_name]
        if not result.empty:
            return int(result["seriesID"].values[0])
        return None

    def get_active_series(self, date: int) -> pd.DataFrame:
        """
        Return a DataFrame of series active in the given year.
        A series is active if startYear <= year <= endYear.
        """

        if self.series.empty:
            return pd.DataFrame(columns=self.series.columns)

        mask = (self.series["startYear"] <= date) & (self.series["endYear"] >= date)

        return self.series.loc[mask].copy()

    def get_point_rules_for_series(self, series_id: int, year: int) -> pd.DataFrame:
        """
        Return point rules for a given series and year.

        Args:
            series_id (int): ID of the series.
            year (int): Year to filter rules by.

        Returns:
            pd.DataFrame: Filtered point rules DataFrame.
        """
        if self.point_rules.empty:
            return pd.DataFrame(columns=self.point_rules.columns)

        mask = (
            (self.point_rules["seriesID"] == series_id)
            & (self.point_rules["startSeason"] <= year)
            & (self.point_rules["endSeason"] >= year)
        )
        return self.point_rules.loc[mask].reset_index(drop=True)
