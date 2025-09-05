import os

import pandas as pd


class SeriesModel:
    def __init__(self):
        self.series = pd.DataFrame()
        self.point_rules = pd.DataFrame()

    def load(self, folder: str) -> bool:
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
        self.series.to_csv(os.path.join(folder, "series.csv"), index=False)
        self.point_rules.to_csv(os.path.join(folder, "point_rules.csv"), index=False)

    def get_series(self) -> pd.DataFrame:
        return (
            self.series[["seriesID", "name"]].copy()
            if not self.series.empty
            else pd.DataFrame(columns=["seriesID", "name"])
        )

    def get_series_id(self, series_name: str) -> int | None:
        result = self.series.query("name == @series_name")
        return result["seriesID"].iat[0] if not result.empty else None

    def _active_series_mask(self, year: int) -> pd.Series:
        return (self.series["startYear"] <= year) & (self.series["endYear"] >= year)

    def get_active_series(self, year: int) -> pd.DataFrame:
        return self.series.loc[self._active_series_mask(year)].copy()

    def get_point_rules_for_series(self, series_id: int, year: int) -> pd.DataFrame:
        mask = (
                (self.point_rules["seriesID"] == series_id)
                & (self.point_rules["startSeason"] <= year)
                & (self.point_rules["endSeason"] >= year)
        )
        return self.point_rules.loc[mask].reset_index(drop=True)

        mask = (
                (self.point_rules["seriesID"] == series_id)
                & (self.point_rules["startSeason"] <= year)
                & (self.point_rules["endSeason"] >= year)
        )
        return self.point_rules.loc[mask].reset_index(drop=True)
