import pandas as pd
import pytest

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
from historical_racing_manager.series import SeriesModel


# === Fixtures ===
@pytest.fixture
def model():
    m = SeriesModel()
    m.series = pd.DataFrame({
        COL_SERIES_ID: [1, 2, 3],
        COL_SERIES_NAME: ["F1", "F2", "F3"],
        COL_SERIES_START: [1950, 1960, 1970],
        COL_SERIES_END: [2100, 2020, 1980],
    })

    m.point_rules = pd.DataFrame({
        COL_RULE_SERIES_ID: [1, 1, 2],
        COL_RULE_START: [2000, 2010, 1990],
        COL_RULE_END: [2009, 2025, 2020],
        "points": [10, 25, 15],
    })

    return m


# === Tests: load() ===

def test_load_missing_files(tmp_path):
    model = SeriesModel()
    assert model.load(tmp_path) is False
    assert list(model.series.columns) == [
        COL_SERIES_ID, COL_SERIES_NAME, COL_SERIES_START, COL_SERIES_END
    ]
    assert model.point_rules.empty


def test_load_existing_files(tmp_path):
    # Prepare CSVs
    series_df = pd.DataFrame({
        COL_SERIES_ID: [1],
        COL_SERIES_NAME: ["F1"],
        COL_SERIES_START: [1950],
        COL_SERIES_END: [2100],
    })
    rules_df = pd.DataFrame({
        COL_RULE_SERIES_ID: [1],
        COL_RULE_START: [2000],
        COL_RULE_END: [2020],
    })

    (tmp_path / SERIES_FILE).write_text(series_df.to_csv(index=False))
    (tmp_path / POINT_RULES_FILE).write_text(rules_df.to_csv(index=False))

    model = SeriesModel()
    assert model.load(tmp_path) is True
    assert len(model.series) == 1
    assert len(model.point_rules) == 1


# === Tests: save() ===

def test_save(tmp_path, model):
    model.save(tmp_path)

    assert (tmp_path / SERIES_FILE).exists()
    assert (tmp_path / POINT_RULES_FILE).exists()

    saved_series = pd.read_csv(tmp_path / SERIES_FILE)
    assert list(saved_series.columns) == list(model.series.columns)


# === Tests: get_series() ===

def test_get_series(model):
    df = model.get_series()
    assert list(df.columns) == [COL_SERIES_ID, COL_SERIES_NAME]
    assert len(df) == 3


def test_get_series_empty():
    model = SeriesModel()
    df = model.get_series()
    assert df.empty
    assert list(df.columns) == [COL_SERIES_ID, COL_SERIES_NAME]


# === Tests: get_series_by_id() ===

def test_get_series_by_id(model):
    names = model.get_series_by_id([1, 3, 999])
    assert names == ["F1", "F3", ""]


def test_get_series_by_id_empty_model():
    model = SeriesModel()
    names = model.get_series_by_id([1, 2])
    assert names == ["", ""]


# === Tests: get_series_id() ===

def test_get_series_id(model):
    assert model.get_series_id("F2") == 2
    assert model.get_series_id("Unknown") is None


# === Tests: _active_series_mask() ===

def test_active_series_mask(model):
    mask = model._active_series_mask(1980)
    # F1 active, F2 active, F3 ends 1980 → active
    assert mask.tolist() == [True, True, True]

    mask2 = model._active_series_mask(2050)
    # F1 active, F2 ended 2020, F3 ended 1980
    assert mask2.tolist() == [True, False, False]


# === Tests: get_active_series() ===

def test_get_active_series(model):
    df = model.get_active_series(1980)
    assert set(df[COL_SERIES_ID]) == {1, 2, 3}

    df2 = model.get_active_series(2050)
    assert set(df2[COL_SERIES_ID]) == {1}


# === Tests: get_point_rules_for_series() ===

def test_get_point_rules_for_series(model):
    rules = model.get_point_rules_for_series(1, 2005)
    # Only the first rule applies (2000–2009)
    assert len(rules) == 1
    assert rules.iloc[0]["points"] == 10


def test_get_point_rules_for_series_no_match(model):
    rules = model.get_point_rules_for_series(3, 2000)
    assert rules.empty
