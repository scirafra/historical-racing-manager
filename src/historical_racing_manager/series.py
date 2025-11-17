import os

import pandas as pd

from historical_racing_manager.consts import (
    SERIES_FILE,
    POINT_RULES_FILE,
    COL_SERIES_ID,
    COL_SERIES_NAME,
    COL_SERIES_START,
    COL_SERIES_END,
    COL_RULE_SERIES_ID,
    COL_RULE_START,
    COL_RULE_END,
)


class SeriesModel:
    def __init__(self):
        self.series = pd.DataFrame()
        self.point_rules = pd.DataFrame()

    def load(self, folder: str) -> bool:
        series_path = os.path.join(folder, SERIES_FILE)
        points_path = os.path.join(folder, POINT_RULES_FILE)

        if not os.path.exists(series_path) or not os.path.exists(points_path):
            self.series = pd.DataFrame(columns=[
                COL_SERIES_ID, COL_SERIES_NAME, COL_SERIES_START, COL_SERIES_END
            ])

            self.point_rules = pd.DataFrame()
            return False

        self.series = pd.read_csv(series_path)
        self.point_rules = pd.read_csv(points_path)
        return True

    def save(self, folder: str):
        self.series.to_csv(os.path.join(folder, SERIES_FILE), index=False)
        self.point_rules.to_csv(os.path.join(folder, POINT_RULES_FILE), index=False)

    def get_series(self) -> pd.DataFrame:
        return (
            self.series[[COL_SERIES_ID, COL_SERIES_NAME]].copy()
            if not self.series.empty
            else pd.DataFrame(columns=[COL_SERIES_ID, COL_SERIES_NAME])
        )

    def get_series_id(self, series_name: str) -> int | None:
        result = self.series.query(f"{COL_SERIES_NAME} == @series_name")
        return result[COL_SERIES_ID].iat[0] if not result.empty else None

    def _active_series_mask(self, year: int) -> pd.Series:
        return (self.series[COL_SERIES_START] <= year) & (self.series[COL_SERIES_END] >= year)

    def get_active_series(self, year: int) -> pd.DataFrame:
        return self.series.loc[self._active_series_mask(year)].copy()

    def get_point_rules_for_series(self, series_id: int, year: int) -> pd.DataFrame:
        mask = (
                (self.point_rules[COL_RULE_SERIES_ID] == series_id)
                & (self.point_rules[COL_RULE_START] <= year)
                & (self.point_rules[COL_RULE_END] >= year)
        )
        return self.point_rules.loc[mask].reset_index(drop=True)
