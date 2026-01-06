from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from historical_racing_manager.consts import (
    DEFAULT_PART_COST,
    UPGRADE_POWER_MIN,
    UPGRADE_POWER_MAX,
)
from historical_racing_manager.manufacturer import ManufacturerModel


# === Fixtures ===
@pytest.fixture
def model():
    m = ManufacturerModel()

    m.rules = pd.DataFrame({
        "rules_id": [0, 1, 2, 3, 4, 5, 6, 7, 8],
        "series_id": [1, 1, 1, 5, 5, 5, 6, 6, 6],
        "name": [
            "F1 Engine", "F1 Chassi", "F1 Pneu",
            "F2 Engine", "F2 Chassi", "F2 Pneu",
            "F3 Engine", "F3 Chassi", "F3 Pneu"
        ],
        "start_season": [1894] * 9,
        "end_season": [3000] * 9,
        "part_type": [
            "engine", "chassi", "pneu",
            "engine", "chassi", "pneu",
            "engine", "chassi", "pneu"
        ],
        "min_ability": [80, 70, 60, 50, 40, 30, 20, 10, 1],
        "max_ability": [300, 300, 200, 200, 200, 200, 100, 100, 200],
    })

    m.manufacturers = pd.DataFrame({
        "manufacture_id": [0, 1, 2, 3, 4, 5, 6],
        "owner": ["", "", "", "", "", "", ""],
        "name": ["Ferrari", "Ford", "Dallara", "Lola", "Dunlop", "Michelin", "Mercedes"],
        "found": [1800] * 7,
        "folded": [9999] * 7,
        "money": [10000000] * 7,
        "engine": [True, True, False, False, False, False, True],
        "chassi": [True, False, True, True, False, False, False],
        "pneu": [False, False, False, False, True, True, False],
        "emp": [0] * 7,
        "ai": [True] * 7,
    })

    m.car_parts = pd.DataFrame({
        "part_id": [0],
        "part_type": ["engine"],
        "manufacture_id": [10],
        "rules_id": [1],
        "series_id": [1],
        "power": [80],
        "reliability": [10],
        "safety": [10],
        "year": [2024],
        "cost": [DEFAULT_PART_COST],
    })

    return m


# === Tests: load() ===

def test_load_missing_files(tmp_path):
    model = ManufacturerModel()
    assert model.load(tmp_path) is False
    assert model.car_parts.empty
    assert model.rules.empty


def test_load_existing_files(tmp_path):
    # Prepare CSVs
    (tmp_path / "car_parts.csv").write_text("a,b\n1,2")
    (tmp_path / "cars.csv").write_text("a,b\n1,2")
    (tmp_path / "manufacturers.csv").write_text("a,b\n1,2")
    (tmp_path / "car_part_models.csv").write_text("a,b\n1,2")
    (tmp_path / "rules.csv").write_text("a,b\n1,2")

    model = ManufacturerModel()
    assert model.load(tmp_path) is True
    assert not model.car_parts.empty


# === Tests: save() ===

def test_save(tmp_path, model):
    model.save(tmp_path)
    assert (tmp_path / "car_parts.csv").exists()
    assert (tmp_path / "rules.csv").exists()


# === Tests: get_manufacturers() ===

def test_get_manufacturers(model):
    df = model.get_manufacturers()
    assert list(df.columns) == ["manufacture_id", "name"]
    assert len(df) == 7


def test_get_manufacturers_empty():
    m = ManufacturerModel()
    df = m.get_manufacturers()
    assert df.empty
    assert list(df.columns) == ["manufacture_id", "name"]


# === Tests: get_manufacturers_id() ===

def test_get_manufacturers_id(model):
    assert model.get_manufacturers_id("Ford") == 1
    assert model.get_manufacturers_id("Unknown") is None


# === Tests: map_manufacturer_ids_to_names() ===

def test_map_manufacturer_ids_to_names(model):
    result = model.map_manufacturer_ids_to_names({0: ["engine"], 999: ["gearbox"]})
    assert result["Ferrari"] == ["engine"]
    assert result[""] == ["gearbox"]


def test_map_manufacturer_ids_to_names_empty():
    m = ManufacturerModel()
    result = m.map_manufacturer_ids_to_names({10: ["engine"]})
    assert result == {"": ["engine"]}


# === Tests: _fill_missing_values() ===

def test_fill_missing_values(model):
    df = pd.DataFrame({
        "power": [None],
        "reliability": [None],
        "safety": [None],
        "min_ability": [55],
    })

    out = model._fill_missing_values(df)
    assert out["power"].iloc[0] == 55
    assert out["reliability"].iloc[0] == 1
    assert out["safety"].iloc[0] == 1


# === Tests: _apply_car_part_improvements() ===

def test_apply_car_part_improvements(model):
    np.random.seed(0)  # deterministic
    df = pd.DataFrame({
        "power": [80],
        "reliability": [10],
        "safety": [10],
    })

    out = model._apply_car_part_improvements(df, 2025)
    assert out["year"].iloc[0] == 2025
    assert out["power"].iloc[0] >= 80 + UPGRADE_POWER_MIN
    assert out["power"].iloc[0] <= 80 + UPGRADE_POWER_MAX


# === Tests: _clamp_values() ===

def test_clamp_values(model):
    df = pd.DataFrame({
        "power": [200],  # too high
        "min_ability": [50],
        "max_ability": [100],
        "reliability": [-5],
        "safety": [-10],
    })

    out = model._clamp_values(df)
    assert out["power"].iloc[0] == 100
    assert out["reliability"].iloc[0] == 1
    assert out["safety"].iloc[0] == 1


# === Tests: _generate_new_part_ids() ===

def test_generate_new_part_ids(model):
    ids = list(model._generate_new_part_ids(3))
    assert ids == [1, 2, 3]  # existing max part_id = 0


def test_generate_new_part_ids_empty():
    m = ManufacturerModel()
    ids = list(m._generate_new_part_ids(2))
    assert ids == [0, 1]


# === Tests: develop_part() ===

def test_develop_part(model):
    np.random.seed(0)

    # Contracts exactly like in your real CSV
    contracts = pd.DataFrame({
        "series_id": [
            1, 1, 1, 1, 1,
            5, 5, 5, 5, 5,
            6, 6, 6, 6, 6, 6
        ],
        "manufacture_id": [
            0, 1, 0, 1, 4,
            0, 1, 0, 2, 5,
            1, 0, 2, 3, 5, 4
        ],
        "part_type": [
            "engine", "engine", "chassi", "chassi", "pneu",
            "engine", "engine", "chassi", "chassi", "pneu",
            "engine", "chassi", "chassi", "chassi", "pneu", "pneu"
        ],
        "start_year": [1894] * 16,
        "end_year": [3000] * 16,
    })

    # Develop parts for 1895 (same as your real data)
    model.develop_part(datetime(year=1895, month=1, day=1), contracts)
    assert len(model.car_parts) == 1 + 16  # model fixture starts with 1 part

    new_parts = model.car_parts.tail(16)

    # All new parts must be from 1895
    assert (new_parts["year"] == 1895).all()

    # All new parts must have default cost
    assert (new_parts["cost"] == DEFAULT_PART_COST).all()

    # Check F1 engine rules (min 80, max 300)
    f1_engine = new_parts[
        (new_parts["series_id"] == 1) & (new_parts["part_type"] == "engine")
        ]
    assert (f1_engine["power"] >= 80).all()
    assert (f1_engine["power"] <= 300).all()
