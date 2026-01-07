from datetime import datetime

import pandas as pd
import pytest

from historical_racing_manager.drivers import DriversModel


@pytest.fixture
def model_with_mixed_drivers():
    m = DriversModel()

    # Main driver table
    m.drivers = pd.DataFrame({
        "driver_id": [1, 2, 3, 4],
        "forename": ["Lewis", "Max", "Sebastian", "Mick"],
        "surname": ["Hamilton", "Verstappen", "Vettel", "Schumacher"],
        "year": [1985, 1997, 1987, 2008],  # ages depend on current year
        "alive": [True, True, True, True],
        "ability": [95, 92, 90, 70],
        "ability_original": [95, 92, 90, 70],
        "ability_best": [95, 92, 90, 70],
        "reputation_race": [10, 20, 15, 5],
        "reputation_season": [5, 10, 7, 2],
        "retire": [37, 40, 40, 45],
        "nationality": ["UK", "NL", "DE", "DE"],
    })

    # Active drivers start empty (model logic will populate them)
    m.active_drivers = pd.DataFrame(columns=m.drivers.columns)

    # Retiring drivers start empty
    m.retiring_drivers = pd.DataFrame(columns=m.drivers.columns)

    m.ability_change = [5, 4, 3, 2, 1, 0]  # predictable adjustments

    return m


def test_get_driver_id(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    assert m.get_driver_id("Lewis", "Hamilton") == 1
    assert m.get_driver_id("Max", "Verstappen") == 2
    assert m.get_driver_id("Unknown", "Driver") is None


def test_get_drivers_light(model_with_mixed_drivers):
    m = model_with_mixed_drivers
    df = m.get_drivers_light()

    assert list(df.columns) == ["driver_id", "forename", "surname"]
    assert len(df) == 4
    assert df.iloc[0]["forename"] == "Lewis"


def test_get_driver_full_names(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    active = [3, 1]
    others = [2, 4]

    result = m.get_driver_full_names(active, others)

    # Active drivers sorted alphabetically by full name
    assert result[0] == "Lewis Hamilton"
    assert result[1] == "Sebastian Vettel"

    # Other drivers sorted alphabetically
    assert result[2] == "Mick Schumacher"
    assert result[3] == "Max Verstappen"


def test_get_raced_drivers(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    # Set active drivers
    m.active_drivers = m.drivers[m.drivers["driver_id"].isin([1, 3])]

    # Input IDs in random order
    ids = [3, 2, 1]

    result = m.get_raced_drivers(ids)

    # Active drivers (1, 3) should come first, sorted alphabetically
    assert result[0] == "Lewis Hamilton"  # driver 1
    assert result[1] == "Sebastian Vettel"  # driver 3

    # Remaining drivers follow
    assert result[2] == "Max Verstappen"  # driver 2


def test_initialize_active_drivers(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    # Current year = 2020 → ages: 35, 23, 33, 12
    m._initialize_active_drivers(datetime(year=2020, month=1, day=1))

    # Mick (17) is too young → excluded
    assert len(m.active_drivers) == 3
    assert set(m.active_drivers["driver_id"]) == {1, 2, 3}


def test_update_active_driver_list(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    # Initialize first
    m._initialize_active_drivers(datetime(year=2022, month=1, day=1))

    # Make driver 1 retire
    m.drivers.loc[m.drivers["driver_id"] == 1, "retire"] = 39

    # Make driver 4 exactly DRIVER_MIN_AGE (15)
    m.drivers.loc[m.drivers["driver_id"] == 4, "year"] = 2008  # 2023 - 2008 = 15

    # Driver 4 should not be in active drivers
    assert 4 not in m.active_drivers["driver_id"].values

    retiring = m._update_active_driver_list(datetime(year=2023, month=1, day=1))

    # Driver 1 should retire
    assert 1 in retiring["driver_id"].values

    # Driver 4 should be added as new driver
    assert 4 in m.active_drivers["driver_id"].values


def test_choose_active_drivers(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    result = m.choose_active_drivers(datetime(year=2016, month=1, day=1))

    assert isinstance(result, pd.Series)
    assert len(result) == 3  # Mick excluded
    assert set(result) == {1, 2, 3}


def test_sort_active_drivers(model_with_mixed_drivers):
    m = model_with_mixed_drivers
    m._initialize_active_drivers(datetime(year=2020, month=1, day=1))

    m.sort_active_drivers()

    # Expected order by reputation_race: Max (20), Sebastian (15), Lewis (10)
    assert list(m.active_drivers["driver_id"]) == [2, 3, 1]


def test_check_duplicates(model_with_mixed_drivers):
    m = model_with_mixed_drivers
    m._initialize_active_drivers(datetime(year=2020, month=1, day=1))

    # Create duplicate
    m.active_drivers.loc[len(m.active_drivers)] = m.active_drivers.iloc[0]

    with pytest.raises(SystemExit):
        m._check_duplicates()


def test_mark_drivers_dead(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    # Initialize active drivers
    m._initialize_active_drivers(datetime(year=2020, month=1, day=1))

    # Kill driver 2
    m.mark_drivers_dead([2], "2020-05-01")

    # Driver 2 should be removed from active drivers
    assert 2 not in m.active_drivers["driver_id"].values

    # Driver 2 should be marked dead in main table
    assert m.drivers.loc[m.drivers["driver_id"] == 2, "alive"].iat[0] == False

    # Dead log should contain entry
    assert m.dead_drivers[-1] == ["2020-05-01", [2]]


def test_race_reputations(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    # Initialize active drivers
    m._initialize_active_drivers(datetime(year=2020, month=1, day=1))

    # Race results: driver 1 wins, driver 2 second, driver 3 third
    m.race_reputations(30, [1, 2, 3])

    # Expected:
    # driver 1: +30
    # driver 2: +15
    # driver 3: +10

    assert m.active_drivers.loc[m.active_drivers["driver_id"] == 1, "reputation_race"].iat[0] == 10 + 30
    assert m.active_drivers.loc[m.active_drivers["driver_id"] == 2, "reputation_race"].iat[0] == 20 + 15
    assert m.active_drivers.loc[m.active_drivers["driver_id"] == 3, "reputation_race"].iat[0] == 15 + 10


def test_update_reputations(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    # Initialize active drivers
    m._initialize_active_drivers(datetime(year=2020, month=1, day=1))

    # Before update:
    # reputations: 10, 20, 15
    m.update_reputations()

    # After halving:
    # 10 → 5
    # 20 → 10
    # 15 → 7
    assert m.active_drivers.loc[m.active_drivers["driver_id"] == 1, "reputation_race"].iat[0] == 5
    assert m.active_drivers.loc[m.active_drivers["driver_id"] == 2, "reputation_race"].iat[0] == 10
    assert m.active_drivers.loc[m.active_drivers["driver_id"] == 3, "reputation_race"].iat[0] == 7


def test_calculate_adjustment(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    row = pd.Series({"year": 2018})

    # target_year - row["year"] = 2020 - 2018 = 2 → ability_change[2] = 3
    assert m.calculate_adjustment(row, "first", 2020) == 3
    assert m.calculate_adjustment(row, "second", 2020) == 3
    assert m.calculate_adjustment(row, "third", 2020) == 2

    # out of range
    assert m.calculate_adjustment(row, "first", 2030) == 0


def test_filter_adjustable_drivers(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    # Ages in 2020: 35, 23, 33, 12
    m._initialize_active_drivers(datetime(year=2020, month=1, day=1))

    filtered = m._filter_adjustable_drivers(2020, 0)

    # DRIVER_MIN_AGE = 15 → range is 15–19
    # No driver is in that range → empty
    assert filtered.empty


def test_assign_positions(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    df = pd.DataFrame({
        "driver_id": [1, 2, 3, 4, 5]
    })

    result = m._assign_positions(df)

    # For n=5:
    # a = 5//3 = 1
    # remainder = 2 → a1 = 1, a2 = 0
    # positions = ["first"]*(1+1) + ["second"]*(1+0) + ["third"]*(5 - 2 - 1)
    assert list(result["position"]) == ["first", "first", "second", "third", "third"]


def test_apply_adjustments(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    df = pd.DataFrame({
        "driver_id": [1, 2],
        "ability": [90, 80],
        "ability_best": [90, 80],
        "year": [2019, 2018],
        "position": ["first", "third"]
    })

    result = m._apply_adjustments(df, target_year=2020)

    # first → +4
    # third → +1
    assert result.loc[result["driver_id"] == 1, "ability"].iat[0] == 94
    assert result.loc[result["driver_id"] == 2, "ability"].iat[0] == 82

    # ability_best updated
    assert result.loc[result["driver_id"] == 1, "ability_best"].iat[0] == 94
    assert result.loc[result["driver_id"] == 2, "ability_best"].iat[0] == 82

    # position removed
    assert "position" not in result.columns


def test_update_driver_abilities(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    m._initialize_active_drivers(datetime(year=2020, month=1, day=1))

    updated = pd.DataFrame({
        "driver_id": [1],
        "ability": [99],
        "ability_best": [99]
    })

    m._update_driver_abilities(updated)

    assert m.active_drivers.loc[m.active_drivers["driver_id"] == 1, "ability"].iat[0] == 99
    assert m.active_drivers.loc[m.active_drivers["driver_id"] == 1, "ability_best"].iat[0] == 99


def test_update_drivers(model_with_mixed_drivers):
    m = model_with_mixed_drivers
    m.ability_change = [
        4, 4, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0,
        -1, -1, -1, -1, -1, -2, -2, -2, -2, -3, -3, -3,
        -4, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13,
        -14, -15, -16, -17, -18, -19, -20
    ]
    m._initialize_active_drivers(datetime(year=2020, month=1, day=1))

    # Before update
    ability_before = m.active_drivers.set_index("driver_id")["ability"].to_dict()

    m.update_drivers(datetime(year=2020, month=1, day=1))

    # After update, driver 1 and 3 should have lowered ability
    ability_after = m.active_drivers.set_index("driver_id")["ability"].to_dict()

    assert ability_after[1] < ability_before[1]
    assert ability_after[3] < ability_before[3]

    # Driver 2 should increase ability
    assert ability_after[2] > ability_before[2]


def test_ability_distribution(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    dist = m.ability_distribution()

    # Distribution starts at DRIVER_ABILITY_DISTRIBUTION_START (69)
    # and ends at DRIVER_ABILITY_DISTRIBUTION_END (36)
    assert dist[0] == 69
    assert dist[-1] == 36

    # 69 appears once, 68 twice, 67 three times...
    assert dist.count(69) == 1
    assert dist.count(68) == 2
    assert dist.count(67) == 3


def test_sample_name_by_nationality(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    forename, surname = m._sample_name_by_nationality(m.drivers, "DE")

    # Only Sebastian and Mick are DE
    assert surname in ["Vettel", "Schumacher"]
    assert forename in ["Sebastian", "Mick"]


def test_generate_driver_id(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    new_id, new_offset = m._generate_driver_id(m.drivers, id_offset=0)

    assert new_id == 5  # max driver_id is 4 → 4 + 1 + 0
    assert new_offset == 1


def test_build_driver_dict(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    d = m._build_driver_dict(
        driver_id=10,
        forename="John",
        surname="Doe",
        nationality="USA",
        year=2000,
        ability=50
    )

    assert d["driver_id"] == 10
    assert d["forename"] == "John"
    assert d["surname"] == "Doe"
    assert d["nationality"] == "USA"
    assert d["year"] == 2000
    assert d["ability"] == 50
    assert d["ability_original"] == 50
    assert d["ability_best"] == 50
    assert d["alive"] is True


def test_generate_new_drivers(model_with_mixed_drivers):
    m = model_with_mixed_drivers

    nationality_weights = pd.Series({
        "UK": 1.0
    })

    df = m.generate_new_drivers(
        year=2025,
        count=2,
        df=m.drivers,
        nationality_weights=nationality_weights,
        id_offset=0
    )

    assert len(df) == 2

    # All drivers must be UK nationality
    assert set(df["nationality"]) == {"UK"}

    # IDs must be > max existing (4)
    assert df["driver_id"].min() >= 5

    # Ability fields must be consistent
    for _, row in df.iterrows():
        assert row["ability"] == row["ability_original"]
        assert row["ability"] == row["ability_best"]
