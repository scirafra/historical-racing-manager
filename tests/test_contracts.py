from datetime import datetime

import pandas as pd
import pytest

from historical_racing_manager.contracts import ContractsModel


# --------------------------------------------------
# FIXTURES
# --------------------------------------------------

@pytest.fixture
def contracts_model():
    return ContractsModel()


@pytest.fixture
def rules_df():
    return pd.DataFrame({
        "series_id": [1],
        "max_cars": [2],
        "min_age": [18],
        "max_age": [40],
    })


@pytest.fixture
def series_df():
    return pd.DataFrame({
        "series_id": [1],
        "name": ["Formula Test"],
        "reputation": [50],
    })


@pytest.fixture
def st_contract_df():
    return pd.DataFrame({
        "team_id": [100],
        "series_id": [1],
    })


@pytest.fixture
def active_drivers_df():
    return pd.DataFrame({
        "driver_id": [10, 11, 12],
        "forename": ["Lewis", "Max", "Seb"],
        "surname": ["Hamilton", "Verstappen", "Vettel"],
        "nationality": ["UK", "NL", "DE"],
        "year": [1985, 1997, 1987],
        "reputation_race": [90, 80, 70],
    })


@pytest.fixture
def dt_contract_df():
    return pd.DataFrame({
        "driver_id": [10],
        "team_id": [100],
        "salary": [1000],
        "wanted_reputation": [40],
        "start_year": [2019],
        "end_year": [2025],
        "active": [True],
    })


@pytest.fixture
def empty_dt_contract_df():
    # empty df with all required columns
    return pd.DataFrame(columns=[
        "driver_id",
        "team_id",
        "salary",
        "wanted_reputation",
        "start_year",
        "end_year",
        "active",
    ])


# --------------------------------------------------
# BASIC HELPERS
# --------------------------------------------------

def test_ensure_columns_adds_missing():
    df = pd.DataFrame({"a": [1]})
    model = ContractsModel()

    model._ensure_columns(df, {"a": None, "b": 0})

    assert "b" in df.columns
    assert df.loc[0, "b"] == 0


# --------------------------------------------------
# DRIVER SLOTS
# --------------------------------------------------

def test_init_driver_slots_for_year_basic(
        contracts_model, rules_df, st_contract_df, dt_contract_df
):
    m = contracts_model
    m.st_contract = st_contract_df
    m.dt_contract = dt_contract_df.copy()

    slots = m.init_driver_slots_for_year(2020, rules_df)

    assert len(slots) == 1
    row = slots.iloc[0]

    assert row["team_id"] == 100
    assert row["series_id"] == 1
    assert row["max_slots"] == 2
    assert row["signed_slots"] == 1
    assert row["free_slots"] == 1


def test_rollover_driver_slots_initializes(
        contracts_model, rules_df, st_contract_df, empty_dt_contract_df
):
    m = contracts_model
    m.st_contract = st_contract_df
    m.rules = rules_df

    m.dt_contract = empty_dt_contract_df.copy()
    m._ensure_columns(m.dt_contract, {
        "driver_id": None,
        "team_id": None,
        "start_year": 0,
        "end_year": 0,
        "active": True
    })

    m.rollover_driver_slots()

    assert not m.driver_slots_current.empty
    assert not m.driver_slots_next.empty


# --------------------------------------------------
# TEAM / SERIES
# --------------------------------------------------

def test_get_team_series_basic(contracts_model, st_contract_df):
    m = contracts_model
    m.st_contract = st_contract_df

    result = m.get_team_series(100)

    assert result == [1]


def test_get_team_series_missing_team(contracts_model, st_contract_df):
    m = contracts_model
    m.st_contract = st_contract_df

    assert m.get_team_series(999) == []


# --------------------------------------------------
# CONTRACTS
# --------------------------------------------------

def test_get_contracts_for_year_basic(contracts_model):
    m = contracts_model

    m.dt_contract = pd.DataFrame([{
        "driver_id": 10,
        "team_id": 100,
        "salary": 1000,
        "wanted_reputation": 40,
        "start_year": 2019,
        "end_year": 2025,
        "active": True
    }])

    year = 2019
    print(m.dt_contract)
    df = m.get_contracts_for_year(year)
    print(df)

    assert not df.empty, "DataFrame is empty, contract not found"
    assert df.iloc[0]["driver_id"] == 10
    assert df.iloc[0]["team_id"] == 100


def test_disable_driver_contracts(contracts_model, dt_contract_df):
    m = contracts_model
    m.dt_contract = dt_contract_df.copy()

    m.disable_driver_contracts([10])

    # pandas uses np.bool_, not Python bool
    assert not m.dt_contract.loc[0, "active"]


# --------------------------------------------------
# UTILS
# --------------------------------------------------

def test_is_leap_year():
    m = ContractsModel()

    assert m._is_leap(2020) is True
    assert m._is_leap(1900) is False
    assert m._is_leap(2000) is True


def test_drop_until_free_slot():
    m = ContractsModel()
    df = pd.DataFrame({
        "team_id": [1, 2, 3],
        "free_slots": [0, 0, 1],
    })

    result = m._drop_until_free_slot(df)

    assert len(result) == 1
    assert result.iloc[0]["team_id"] == 3


def test_choose_team_by_reputation(monkeypatch):
    m = ContractsModel()

    df = pd.DataFrame({
        "team_id": [1, 2],
        "reputation": [100, 50],
        "free_slots": [1, 1],
    })

    monkeypatch.setattr(m, "_generate_index", lambda n: 0)

    team = m._choose_team_by_reputation(df)

    assert team == 1


def test_estimate_salary(contracts_model, active_drivers_df):
    m = contracts_model

    salary = m._estimate_salary(active_drivers_df, 10)

    assert salary > 0


# --------------------------------------------------
# AVAILABLE DRIVERS
# --------------------------------------------------

def test_get_available_drivers_basic(
        contracts_model, active_drivers_df, rules_df, series_df, st_contract_df, empty_dt_contract_df
):
    m = contracts_model
    m.st_contract = st_contract_df
    m.dt_contract = empty_dt_contract_df.copy()

    m._ensure_columns(m.dt_contract, {
        "driver_id": None,
        "team_id": None,
        "start_year": 0,
        "end_year": 0,
        "active": True,
        "wanted_reputation": 0
    })

    df = m._get_available_drivers(
        active_drivers=active_drivers_df,
        series=series_df,
        year=2020,
        series_id=1,
        team_id=100,
        rules=rules_df,
    )

    assert not df.empty
    assert "max_contract_len" in df.columns


def test_annotate_teams_with_free_slots_basic(contracts_model):
    cm = contracts_model

    cm.st_contract = pd.DataFrame([
        {"team_id": 1, "series_id": 1},
        {"team_id": 2, "series_id": 1}
    ])
    cm.reserved_slots = {1: 1, 2: 0}

    teams = pd.DataFrame([{"team_id": 1}, {"team_id": 2}])
    rules = pd.DataFrame([{"series_id": 1, "max_cars": 2}])

    # Assuming no active contracts
    cm.dt_contract = pd.DataFrame(
        columns=["driver_id", "team_id", "salary", "wanted_reputation", "start_year", "end_year", "active"])

    df = cm._annotate_teams_with_free_slots(teams, rules, 2026)
    assert df.loc[df["team_id"] == 1, "free_slots"].iloc[0] == 1  # 2 - reserved(1) - active(0)
    assert df.loc[df["team_id"] == 2, "free_slots"].iloc[0] == 2  # 2 - reserved(0) - active(0)


def test_generate_part_contracts_basic(contracts_model):
    cm = contracts_model
    cm.mt_contract = pd.DataFrame(
        columns=["series_id", "team_id", "manufacture_id", "part_type", "start_year", "end_year", "cost"])

    series_parts = pd.DataFrame([
        {"series_id": 1, "part_type": "engine", "manufacture_id": 10, "cost": 5000, "year": 2026}
    ])
    manufacturers = pd.DataFrame([{"manufacture_id": 10, "name": "MotorCo"}])
    teams_in_series = pd.Series([100])
    active_contracts = pd.DataFrame(columns=cm.mt_contract.columns)
    teams = pd.DataFrame([{"team_id": 100, "money": 20000}])

    contracts = cm._generate_part_contracts("engine", series_parts, manufacturers, teams_in_series, active_contracts,
                                            2026, teams)

    assert len(contracts) == 1
    assert contracts[0]["team_id"] == 100
    assert teams.loc[teams["team_id"] == 100, "money"].iloc[0] < 20000  # money reduced by cost


def test_offer_and_process_driver_contract(contracts_model):
    cm = contracts_model

    # Setting up existing teams and contracts
    cm.st_contract = pd.DataFrame([{"team_id": 100, "series_id": 1}])
    cm.dt_contract = pd.DataFrame(
        columns=["driver_id", "team_id", "salary", "wanted_reputation", "start_year", "end_year", "active"]
    )

    # Active drivers
    active_drivers = pd.DataFrame([
        {
            "driver_id": 1,
            "reputation_race": 100,
            "max_contract_len": 3,
            "age": 25,  # added to satisfy min_age
            "series_id": 1  # added to know which series the driver belongs to
        }
    ])

    cm.rules = pd.DataFrame([
        {"series_id": 1, "max_cars": 2, "min_age": 18}
    ])
    cm.offer_driver_contract(driver_id=1, team_id=100, salary=500000, length=2, year=2026)

    signed = cm.process_driver_offers(current_date=datetime(2026, 1, 1), active_drivers=active_drivers)

    assert len(signed) == 0

    cm.offer_driver_contract(driver_id=1, team_id=100, salary=5000000, length=2, year=2026)

    signed = cm.process_driver_offers(current_date=datetime(2026, 1, 1), active_drivers=active_drivers)

    assert len(signed) == 1
    assert cm.dt_contract.iloc[0]["driver_id"] == 1
    assert cm.dt_contract.iloc[0]["team_id"] == 100
