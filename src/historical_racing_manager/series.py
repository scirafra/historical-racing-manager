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

"""
SeriesModel

Handles loading, saving and querying series metadata and point rules.
The model keeps two tables in memory:
- self.series: information about available series (id, name, start/end years)
- self.point_rules: point allocation rules per series and season range
"""


class SeriesModel:
    """Model for series metadata and point rules."""

    def __init__(self):
        # DataFrames holding series definitions and point rules
        self.series = pd.DataFrame()
        self.point_rules = pd.DataFrame()

    def load(self, folder: str) -> bool:
        """
        Load series and point rules CSV files from the given folder.

        Args:
            folder (str): Path to the folder containing SERIES_FILE and POINT_RULES_FILE.

        Returns:
            bool: True if both files were loaded successfully, False otherwise.
        """
        series_path = os.path.join(folder, SERIES_FILE)
        points_path = os.path.join(folder, POINT_RULES_FILE)

        # If either file is missing, initialize empty structures and return False
        if not os.path.exists(series_path) or not os.path.exists(points_path):
            self.series = pd.DataFrame(columns=[
                COL_SERIES_ID, COL_SERIES_NAME, COL_SERIES_START, COL_SERIES_END
            ])
            self.point_rules = pd.DataFrame()
            return False

        # Read CSV files into DataFrames
        self.series = pd.read_csv(series_path)
        self.point_rules = pd.read_csv(points_path)
        return True

    def save(self, folder: str):
        """
        Save series and point rules DataFrames to CSV files in the given folder.

        Args:
            folder (str): Destination folder for the CSV files.
        """
        self.series.to_csv(os.path.join(folder, SERIES_FILE), index=False)
        self.point_rules.to_csv(os.path.join(folder, POINT_RULES_FILE), index=False)

    def get_series(self) -> pd.DataFrame:
        """
        Return a lightweight DataFrame with series ID and name.

        Returns:
            pd.DataFrame: DataFrame with columns [COL_SERIES_ID, COL_SERIES_NAME].
                          If no series are loaded, returns an empty DataFrame with those columns.
        """
        return (
            self.series[[COL_SERIES_ID, COL_SERIES_NAME]].copy()
            if not self.series.empty
            else pd.DataFrame(columns=[COL_SERIES_ID, COL_SERIES_NAME])
        )

    def get_series_id(self, series_name: str) -> int | None:
        """
        Look up a series ID by its name.

        Args:
            series_name (str): Human-readable series name.

        Returns:
            int | None: The series ID if found, otherwise None.
        """
        result = self.series.query(f"{COL_SERIES_NAME} == @series_name")
        return result[COL_SERIES_ID].iat[0] if not result.empty else None

    def _active_series_mask(self, year: int) -> pd.Series:
        """
        Internal helper that returns a boolean mask for series active in the given year.

        Args:
            year (int): Year to test.

        Returns:
            pd.Series: Boolean mask where True indicates the series is active in the year.
        """
        return (self.series[COL_SERIES_START] <= year) & (self.series[COL_SERIES_END] >= year)

    def get_active_series(self, year: int) -> pd.DataFrame:
        """
        Return all series that are active in the specified year.

        Args:
            year (int): Year to filter active series.

        Returns:
            pd.DataFrame: Subset of self.series active in the given year.
        """
        return self.series.loc[self._active_series_mask(year)].copy()

    def get_point_rules_for_series(self, series_id: int, year: int) -> pd.DataFrame:
        """
        Return point rules that apply to a given series in a specific year.

        Args:
            series_id (int): Series identifier.
            year (int): Year for which rules should be returned.

        Returns:
            pd.DataFrame: Point rules rows matching the series and covering the year.
        """
        mask = (
                (self.point_rules[COL_RULE_SERIES_ID] == series_id)
                & (self.point_rules[COL_RULE_START] <= year)
                & (self.point_rules[COL_RULE_END] >= year)
        )
        return self.point_rules.loc[mask].reset_index(drop=True)
