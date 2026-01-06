import pathlib

import numpy as np
import pandas as pd

from historical_racing_manager.consts import (
    MANUFACTURER_REQUIRED_FILES,
    MERGE_KEYS,
    DEFAULT_PART_COST,
    UPGRADE_POWER_MIN,
    UPGRADE_POWER_MAX,
    UPGRADE_RELIABILITY_MIN,
    UPGRADE_RELIABILITY_MAX,
    UPGRADE_SAFETY_MIN,
    UPGRADE_SAFETY_MAX,
)


class ManufacturerModel:
    """Model handling manufacturers, car parts, part models, and related rules."""

    def __init__(self):
        self.car_parts = pd.DataFrame()
        self.car_part_models = pd.DataFrame()
        self.cars = pd.DataFrame()
        self.manufacturers = pd.DataFrame()
        self.rules = pd.DataFrame()

    # --- Persistence ---
    def load(self, folder: pathlib.Path) -> bool:
        """Load manufacturer-related dataframes from CSV files in the given folder."""
        required_files = MANUFACTURER_REQUIRED_FILES

        missing = [f for f in required_files if not (folder / f).exists()]
        if missing:
            self._initialize_empty()
            return False

        # TODO: Why not constants??
        self.car_parts = pd.read_csv(folder / "car_parts.csv")
        self.cars = pd.read_csv(folder / "cars.csv")
        self.manufacturers = pd.read_csv(folder / "manufacturers.csv")
        self.car_part_models = pd.read_csv(folder / "car_part_models.csv")
        self.rules = pd.read_csv(folder / "rules.csv")
        return True

    def save(self, folder: pathlib.Path):
        """Save manufacturer-related dataframes to CSV files in the given folder."""
        self.car_parts.to_csv(folder / "car_parts.csv", index=False)
        self.cars.to_csv(folder / "cars.csv", index=False)
        self.manufacturers.to_csv(folder / "manufacturers.csv", index=False)
        self.car_part_models.to_csv(folder / "car_part_models.csv", index=False)
        self.rules.to_csv(folder / "rules.csv", index=False)

    def _initialize_empty(self):
        """Initialize all internal tables to empty DataFrames."""
        self.car_parts = pd.DataFrame()
        self.cars = pd.DataFrame()
        self.manufacturers = pd.DataFrame()
        self.car_part_models = pd.DataFrame()
        self.rules = pd.DataFrame()

    # --- Business logic ---
    def develop_part(self, date, contracts: pd.DataFrame):
        """Develop parts for the given year based on active contracts and rules, then append to car_parts."""
        merged = self._merge_contracts_with_rules(contracts, date.year)

        last_year_parts = self.car_parts[self.car_parts["year"] == date.year - 1].copy()

        # Unify key column types before merging
        merge_keys = MERGE_KEYS
        for key in merge_keys:
            if key in merged.columns:
                merged[key] = merged[key].astype(str)
            if key in last_year_parts.columns:
                last_year_parts[key] = last_year_parts[key].astype(str)

        final = pd.merge(
            merged,
            last_year_parts,
            how="left",
            on=merge_keys,
        )

        final = self._fill_missing_values(final)
        final = self._apply_car_part_improvements(final, date.year)
        final = self._clamp_values(final)
        final["cost"] = DEFAULT_PART_COST

        new_parts = final[
            [
                "part_id",
                "part_type",
                "manufacture_id",
                "rules_id",
                "series_id",
                "power",
                "reliability",
                "safety",
                "year",
                "cost",
            ]
        ].copy()
        new_parts.loc[:, "part_id"] = self._generate_new_part_ids(len(new_parts))

        self.car_parts = pd.concat([self.car_parts, new_parts], ignore_index=True)

    def get_manufacturers(self) -> pd.DataFrame:
        """Return manufacturer IDs and names, or an empty DataFrame if unavailable."""
        return (
            self.manufacturers[["manufacture_id", "name"]].copy()
            if not self.manufacturers.empty
            else pd.DataFrame(columns=["manufacture_id", "name"])
        )

    def get_manufacturers_id(self, manufacturer_name: str) -> int | None:
        """Return the manufacture_id for a given name, or None if not found."""
        result = self.manufacturers.query("name == @manufacturer_name")
        return result["manufacture_id"].iat[0] if not result.empty else None

    def _merge_contracts_with_rules(self, contracts: pd.DataFrame, year: int) -> pd.DataFrame:
        """Merge contracts with rules and filter to those active in the given year."""
        merged = pd.merge(contracts, self.rules, on=["series_id", "part_type"], how="left")
        mask = (
                (merged["start_year"] <= year)
                & (merged["start_season"] <= year)
                & (merged["end_year"] >= year)
                & (merged["end_season"] >= year)
        )
        return merged.loc[mask].copy()

    def _fill_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill missing part attributes with safe defaults."""
        df["power"] = df["power"].fillna(df["min_ability"])
        df["reliability"] = df["reliability"].fillna(1)
        df["safety"] = df["safety"].fillna(1)
        return df

    def _apply_car_part_improvements(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Apply random improvements to part attributes and set the target year."""
        rand_power = np.random.randint(UPGRADE_POWER_MIN, UPGRADE_POWER_MAX + 1, size=len(df))
        rand_reliability = np.random.randint(UPGRADE_RELIABILITY_MIN, UPGRADE_RELIABILITY_MAX + 1, size=len(df))
        rand_safety = np.random.randint(UPGRADE_SAFETY_MIN, UPGRADE_SAFETY_MAX + 1, size=len(df))

        df["power"] += rand_power
        df["reliability"] += rand_power - rand_reliability
        df["safety"] += rand_power - rand_safety
        df["year"] = year
        return df

    def _clamp_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clamp attributes within rule bounds and minimum thresholds."""
        df["power"] = df[["power", "min_ability"]].max(axis=1)
        df["power"] = df[["power", "max_ability"]].min(axis=1)
        df["reliability"] = df["reliability"].apply(lambda x: max(1, x))
        df["safety"] = df["safety"].apply(lambda x: max(1, x))
        return df

    def _generate_new_part_ids(self, count: int) -> range:
        """Generate a sequence of new part IDs continuing from the current maximum."""
        if self.car_parts.empty or self.car_parts["part_id"].isnull().all():
            start = 0
        else:
            try:
                max_id = pd.to_numeric(self.car_parts["part_id"], errors="coerce").max()
                start = int(max_id) + 1 if pd.notna(max_id) else 0
            except Exception:
                start = 0
        return range(start, start + count)

    def map_manufacturer_ids_to_names(self, manu_dict: dict[int, list[str]]) -> dict[str, list[str]]:
        """
        Convert {manufacture_id: [parts]} to {manufacturer_name: [parts]}.
        If manufacture_id does not exist, the key becomes "" (empty string).
        """
        df = self.manufacturers

        if df is None or df.empty:
            # Every ID becomes empty string
            return {"": parts for _, parts in manu_dict.items()}

        # Build lookup: "0" -> "Ferrari"
        lookup = (
            df.assign(mid_norm=df["manufacture_id"].astype(str))
            .set_index("mid_norm")["name"]
            .to_dict()
        )

        result = {}
        for mid, parts in manu_dict.items():
            name = lookup.get(str(mid), "")
            result[name] = parts

        return result
