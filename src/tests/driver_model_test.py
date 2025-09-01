import os
import tempfile
from datetime import date

import pandas as pd
import pytest

from src.drivers import DriversModel


@pytest.fixture
def populated_model():
    m = DriversModel()
    m.drivers = pd.DataFrame(
        [
            {
                "driverID": 1,
                "year": 2000,
                "retire": 40,
                "ability": 50,
                "ability_best": 50,
                "ability_original": 50,
                "alive": True,
                "reputation_race": 10,
            },
            {
                "driverID": 2,
                "year": 2010,
                "retire": 35,
                "ability": 40,
                "ability_best": 40,
                "ability_original": 40,
                "alive": True,
                "reputation_race": 5,
            },
            {
                "driverID": 3,
                "year": 2005,
                "retire": 45,
                "ability": 38,
                "ability_best": 38,
                "ability_original": 38,
                "alive": False,
                "reputation_race": 8,
            },
        ]
    )
    return m


def test_initialize_and_update_active_drivers(populated_model):
    today = date(2020, 1, 1)
    ids_first = populated_model.choose_active_drivers(today)
    assert all(populated_model.active_drivers["alive"])
    # Simuluj ďalší rok s novými 15-ročnými
    populated_model.drivers.loc[len(populated_model.drivers)] = {
        "driverID": 4,
        "year": 2005,
        "retire": 40,
        "ability": 45,
        "ability_best": 45,
        "ability_original": 45,
        "alive": True,
        "reputation_race": 0,
    }
    ids_second = populated_model.choose_active_drivers(date(2020, 1, 1))
    assert 4 in ids_second.values


def test_check_duplicates_triggers_exit(populated_model):
    populated_model.active_drivers = pd.DataFrame(
        [
            {"driverID": 1, "reputation_race": 5},
            {"driverID": 1, "reputation_race": 6},
        ]
    )
    with pytest.raises(SystemExit):
        populated_model._check_duplicates()


def test_calculate_adjustment_variants(populated_model):
    row = pd.Series({"year": 2000})
    assert populated_model.calculate_adjustment(row, "first", 2010) != 0
    assert populated_model.calculate_adjustment(
        row, "second", 2010
    ) < populated_model.calculate_adjustment(row, "first", 2010)
    assert populated_model.calculate_adjustment(
        row, "third", 2010
    ) <= populated_model.calculate_adjustment(row, "second", 2010)
    assert populated_model.calculate_adjustment(row, "other", 2010) == 0


def test_update_drivers_changes_ability(populated_model):
    populated_model.active_drivers = populated_model.drivers.copy()
    before = populated_model.active_drivers["ability"].sum()
    populated_model.update_drivers(date(2025, 1, 1))
    after = populated_model.active_drivers["ability"].sum()
    # Hodnota sa môže zvýšiť alebo ostať rovnaká, nemala by klesnúť pre pozitívne úpravy
    assert after >= before


def test_reassign_positions_orders_correctly():
    df = pd.DataFrame({"position": [3, 1, 2]})
    result = DriversModel.reassign_positions(df)
    assert list(result["position"]) == [1, 2, 3]


def test_load_and_save_with_tempfile(populated_model):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Ulož CSV
        populated_model.active_drivers = populated_model.drivers.copy()
        populated_model.save(tmpdir)
        path = os.path.join(tmpdir, "drivers.csv")
        assert os.path.exists(path)
        # Nový model vie načítať
        m2 = DriversModel()
        assert m2.load(tmpdir)
        assert not m2.drivers.empty
