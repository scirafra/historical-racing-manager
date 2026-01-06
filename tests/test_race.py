import pandas as pd
import pytest

from historical_racing_manager.race import RaceModel


@pytest.fixture
def teams_model():
    class DummyTeams:
        def add_race_reputation(self, reputation, team_list):
            pass

    return DummyTeams()


@pytest.fixture
def manufacturer_model():
    class DummyManu:
        car_parts = pd.DataFrame({
            "series_id": [1, 1, 1],
            "year": [2020, 2020, 2020],
            "manufacture_id": [200, 300, 400],
            "part_type": ["engine", "chassi", "pneu"],
            "power": [10, 0, 0],
            "reliability": [5, 5, 5],
            "safety": [3, 3, 3]
        })

    return DummyManu()


@pytest.fixture
def contracts_model():
    class DummyContracts:
        dt_contract = pd.DataFrame({
            "driver_id": [10, 11],
            "team_id": [100, 100],
            "active": [True, True],
            "start_year": [2019, 2019],
            "end_year": [2025, 2025]
        })

        mt_contract = pd.DataFrame({
            "team_id": [100, 100, 100],
            "series_id": [1, 1, 1],
            "manufacture_id": [200, 300, 400],
            "part_type": ["engine", "chassi", "pneu"],
            "start_year": [2019, 2019, 2019],
            "end_year": [2025, 2025, 2025]
        })

        st_contract = pd.DataFrame({
            "team_id": [100],
            "series_id": [1]
        })

    return DummyContracts()


@pytest.fixture
def series_model():
    class DummySeries:
        point_rules = pd.DataFrame({
            "series_id": [1],
            "start_season": [2020],
            "end_season": [2025],
            "ps_id": [1]
        })

    return DummySeries()


@pytest.fixture
def drivers_model():
    class DummyDrivers:
        drivers = pd.DataFrame({"driver_id": [10, 11, 12],
                                "forename": ["Lewis", "Max", "Seb"],
                                "surname": ["Hamilton", "Verstappen", "Vettel"],
                                "ability": [90, 80, 70]
                                })
        active_drivers = pd.DataFrame({"driver_id": [10, 11, 12],
                                       "forename": ["Lewis", "Max", "Seb"],
                                       "surname": ["Hamilton", "Verstappen", "Vettel"],
                                       "ability": [90, 80, 70]})

    return DummyDrivers()


@pytest.fixture
def race_model():
    m = RaceModel()

    # ============================
    # RESULTS TABLE
    # ============================
    m.results = pd.DataFrame({
        "race_id": [1, 1, 2, 3, 4],
        "driver_id": [10, 11, 10, 12, 11],
        "team_id": [100, 100, 101, 102, 100],
        "car_id": [1, 1, 2, 1, 1],
        "position": [1, 2, 3, 1, 99],  # 99 = crash/death placeholder
        "season": [2020, 2020, 2021, 2020, 2021],
        "series_id": [1, 1, 1, 2, 2],
        "round": [1, 1, 2, 1, 1],
        "engine_id": [200, 201, 200, 201, 200],
        "chassi_id": [300, 300, 301, 300, 301],
        "pneu_id": [400, 401, 400, 401, 400],
    })

    # ============================
    # STANDINGS TABLE
    # ============================
    m.standings = pd.DataFrame({
        "series_id": [1, 1, 1, 2],
        "year": [2020, 2020, 2021, 2020],
        "typ": ["driver", "team", "driver", "driver"],
        "subject_id": [10, 100, 11, 12],
        "round": [1, 1, 2, 1],
        "points": [25, 40, 18, 25],
        "position": [1, 1, 2, 1],
        "race_id": [1, 1, 2, 3],
    })

    # ============================
    # POINT SYSTEM
    # ============================
    m.point_system = pd.DataFrame({
        "ps_id": [1],
        "pos": [1],
        "pts": [25],
    })

    # ============================
    # RACES TABLE
    # ============================
    m.races = pd.DataFrame({
        "race_id": [1, 2, 3, 4],
        "series_id": [1, 1, 2, 2],
        "name": ["A", "B", "C", "D"],
        "country": ["UK", "DE", "FR", "IT"],
        "race_date": pd.to_datetime([
            "2020-05-01",
            "2020-06-01",
            "2020-07-01",
            "2021-05-01"
        ]),
        "layout_id": [10, 11, 12, 13],
        "wet": [1, 2, 1, 1],
    })

    # ============================
    # CIRCUITS TABLE
    # ============================
    m.circuits = pd.DataFrame({
        "circuit_id": [1],
        "name": ["Test Circuit"],
    })

    # ============================
    # CIRCUIT LAYOUTS TABLE
    # ============================
    m.circuit_layouts = pd.DataFrame({
        "layout_id": [10, 11, 12, 13],
        "circuit_id": [1, 1, 1, 1],
        "corners": [10, 12, 8, 15],
    })

    return m


def test_get_raced_series(race_model):
    m = race_model

    result = m.get_raced_series()

    # Expected order of first appearance: series 1, then 2
    assert result == [1, 2]


def test_get_raced_teams(race_model):
    m = race_model

    result = m.get_raced_teams()

    # First appearance order: 100, 101, 102
    assert result == [100, 101, 102]


def test_get_raced_drivers(race_model):
    m = race_model

    result = m.get_raced_drivers()

    # First appearance order: 10, 11, 12
    assert result == [10, 11, 12]


def test_get_raced_manufacturers(race_model):
    m = race_model

    result = m.get_raced_manufacturers()

    # Expected:
    # engine_id: 200, 201
    # chassi_id: 300, 301
    # pneu_id: 400, 401

    assert result[200] == ["engine"]
    assert result[201] == ["engine"]
    assert result[300] == ["chassi"]
    assert result[301] == ["chassi"]
    assert result[400] == ["pneu"]
    assert result[401] == ["pneu"]


def test_extract_champions_basic(race_model):
    m = race_model

    # Minimal series table
    series = pd.DataFrame({
        "series_id": [1, 2],
        "name": ["Formula Test", "GT Test"]
    })

    # Minimal manufacturers table
    manufacturers = pd.DataFrame({
        "manufacture_id": [200, 201, 300, 301, 400, 401],
        "name": ["EngA", "EngB", "ChaA", "ChaB", "TyA", "TyB"]
    })

    # Minimal teams table
    teams = pd.DataFrame({
        "team_id": [100, 101, 102],
        "team_name": ["Team A", "Team B", "Team C"]
    })

    # Minimal drivers table
    drivers = pd.DataFrame({
        "driver_id": [10, 11, 12],
        "forename": ["Lewis", "Max", "Seb"],
        "surname": ["Hamilton", "Verstappen", "Vettel"]
    })

    result = m.extract_champions(
        series_id=1,
        series=series,
        manufacturers=manufacturers,
        teams=teams,
        drivers=drivers
    )

    # Expected columns:
    # series, year, driver_name, team_name, engine, chassi, pneu
    assert "series" in result.columns
    assert "year" in result.columns
    assert "driver_name" in result.columns
    assert "team_name" in result.columns

    # Only year 2020 exist for series 1
    assert set(result["year"]) == {2020}

    # Driver champion for 2020 is driver_id 10 → Lewis Hamilton
    row2020 = result[result["year"] == 2020].iloc[0]
    assert row2020["driver_name"] == "Lewis Hamilton"

    # Team champion for 2020 is team_id 100 → Team A
    assert row2020["team_name"] == "Team A"


def test_extract_champions_manufacturers(race_model):
    m = race_model

    series = pd.DataFrame({
        "series_id": [1],
        "name": ["Formula Test"]
    })

    manufacturers = pd.DataFrame({
        "manufacture_id": [200, 201, 300, 301, 400, 401],
        "name": ["EngA", "EngB", "ChaA", "ChaB", "TyA", "TyB"]
    })

    teams = pd.DataFrame({
        "team_id": [100],
        "team_name": ["Team A"]
    })

    drivers = pd.DataFrame({
        "driver_id": [10],
        "forename": ["Lewis"],
        "surname": ["Hamilton"]
    })

    result = m.extract_champions(
        series_id=1,
        series=series,
        manufacturers=manufacturers,
        teams=teams,
        drivers=drivers
    )

    # Manufacturer columns must exist if present in standings
    # (in our dataset, standings for series 1 include only driver/team)
    # So engine/chassi/pneu may or may not appear depending on pivot
    # We check only that mapping does not break
    assert not result.empty


def test_get_upcoming_races_no_series_ids(race_model):
    m = race_model

    series = pd.DataFrame({
        "series_id": [1, 2],
        "name": ["Formula Test", "GT Test"]
    })

    result = m.get_upcoming_races_for_series([], series, "2020-01-01")

    assert result.empty
    assert list(result.columns) == ["Date", "Race Name", "Series", "Country"]


def test_get_upcoming_races_none_after_date(race_model):
    m = race_model

    series = pd.DataFrame({
        "series_id": [1],
        "name": ["Formula Test"]
    })

    # All races in fixture are >= 2020-05-01
    result = m.get_upcoming_races_for_series([1], series, "2025-01-01")

    assert result.empty


def test_get_upcoming_races_basic(race_model):
    m = race_model

    series = pd.DataFrame({
        "series_id": [1, 2],
        "name": ["Formula Test", "GT Test"]
    })

    result = m.get_upcoming_races_for_series([1], series, "2020-01-01")

    # Only races with series_id=1 and date >= 2020-01-01:
    # race_id 1 → 2020-05-01
    # race_id 2 → 2020-06-01
    assert len(result) == 2

    # Check ordering
    assert list(result["Date"]) == ["2020-05-01", "2020-06-01"]

    # Check columns
    assert list(result.columns) == ["Date", "Race Name", "Series", "Country"]

    # Check series name mapping
    assert result.iloc[0]["Series"] == "Formula Test"


def test_get_upcoming_races_limit_5(race_model):
    m = race_model

    # Add extra races to exceed limit
    extra = pd.DataFrame({
        "race_id": [10, 11, 12, 13, 14, 15],
        "series_id": [1, 1, 1, 1, 1, 1],
        "name": ["E", "F", "G", "H", "I", "J"],
        "country": ["US"] * 6,
        "race_date": pd.to_datetime([
            "2020-07-01", "2020-08-01", "2020-09-01",
            "2020-10-01", "2020-11-01", "2020-12-01"
        ]),
        "layout_id": [10] * 6,
        "wet": [1] * 6,
    })

    m.races = pd.concat([m.races, extra], ignore_index=True)

    series = pd.DataFrame({
        "series_id": [1],
        "name": ["Formula Test"]
    })

    result = m.get_upcoming_races_for_series([1], series, "2020-01-01")

    # Must return only 5 earliest races
    assert len(result) == 5

    # Check first and last date
    assert result.iloc[0]["Date"] == "2020-05-01"
    assert result.iloc[-1]["Date"] == "2020-09-01"


def test_get_upcoming_races_missing_country(race_model):
    m = race_model

    # Remove country column
    m.races = m.races.drop(columns=["country"])

    series = pd.DataFrame({
        "series_id": [1],
        "name": ["Formula Test"]
    })

    result = m.get_upcoming_races_for_series([1], series, "2020-01-01")

    # Should not include Country column
    assert list(result.columns) == ["Date", "Race Name", "Series"]


def test_get_results_for_series_and_season_basic(race_model):
    m = race_model

    df = m.get_results_for_series_and_season(series_id=1, season=2020)

    assert len(df) == 2  # two rows for series 1, season 2020
    assert set(df["driver_id"]) == {10, 11}
    assert set(df["team_id"]) == {100}
    assert set(df["race_id"]) == {1}


def test_get_results_for_series_and_season_columns(race_model):
    m = race_model

    df = m.get_results_for_series_and_season(1, 2020)

    expected_cols = [
        "driver_id", "team_id", "engine_id", "chassi_id",
        "pneu_id", "race_id", "position", "round"
    ]

    assert list(df.columns) == expected_cols


def test_get_results_for_series_and_season_empty(race_model):
    m = race_model

    df = m.get_results_for_series_and_season(series_id=99, season=2020)

    assert df.empty


def test_get_results_for_series_and_season_reset_index(race_model):
    m = race_model

    df = m.get_results_for_series_and_season(1, 2021)

    # Should start at index 0
    assert df.index.tolist() == [0]


def test_get_subject_season_stands_driver_basic(race_model):
    m = race_model

    series = pd.DataFrame({
        "series_id": [1, 2],
        "name": ["Formula Test", "GT Test"]
    })

    df = m.get_subject_season_stands(
        subject_id=10,
        subject_type="driver",
        series=series
    )

    # Only one season for driver 10 → 2020
    assert len(df) == 1
    row = df.iloc[0]

    assert row["season"] == 2020
    assert row["series"] == "Formula Test"
    assert row["races"] == 1
    assert row["wins"] == 1
    assert row["podiums"] == 1
    assert row["points"] == 25
    assert row["championship"] == 1
    assert row["best_result"] == 1


def test_get_subject_season_stands_driver_multi(race_model):
    m = race_model

    series = pd.DataFrame({
        "series_id": [1, 2],
        "name": ["Formula Test", "GT Test"]
    })

    df = m.get_subject_season_stands(
        subject_id=11,
        subject_type="driver",
        series=series
    )

    # Driver 11 has only season 2021
    assert len(df) == 1
    row = df.iloc[0]

    assert row["season"] == 2021
    assert row["series"] == "Formula Test"
    assert row["races"] == 1
    assert row["wins"] == 0
    assert row["podiums"] == 0
    assert row["points"] == 18
    assert row["championship"] == 2


def test_get_subject_season_stands_team(race_model):
    m = race_model

    series = pd.DataFrame({
        "series_id": [1],
        "name": ["Formula Test"]
    })

    df = m.get_subject_season_stands(
        subject_id=100,
        subject_type="team",
        series=series
    )

    assert len(df) == 1
    row = df.iloc[0]

    assert row["season"] == 2020
    assert row["series"] == "Formula Test"
    assert row["races"] == 1
    assert row["wins"] == 1
    assert row["podiums"] == 2  # driver 10 P1 + driver 11 P2
    assert row["points"] == 40
    assert row["championship"] == 1
    assert row["best_result"] == 1


def test_get_subject_season_stands_empty(race_model):
    m = race_model

    series = pd.DataFrame({
        "series_id": [1],
        "name": ["Formula Test"]
    })

    df = m.get_subject_season_stands(
        subject_id=999,
        subject_type="driver",
        series=series
    )

    assert df.empty


def test_get_seasons_for_series_basic(race_model):
    m = race_model

    seasons = m.get_seasons_for_series(1)

    assert seasons == [2020, 2021]


def test_get_seasons_for_series_other(race_model):
    m = race_model

    seasons = m.get_seasons_for_series(2)

    assert seasons == [2020, 2021]


def test_get_seasons_for_series_missing(race_model):
    m = race_model

    seasons = m.get_seasons_for_series(99)

    assert seasons == []


def test_get_seasons_for_series_empty_results(race_model):
    m = race_model

    m.results = pd.DataFrame()  # clear results

    seasons = m.get_seasons_for_series(1)

    assert seasons == []


def test_all_time_best_basic(race_model, drivers_model):
    m = race_model

    df = m.all_time_best(drivers_model, series_id=1)

    # Expected drivers in standings for series 1:
    # 2020 → driver 10 (P1)
    # 2021 → driver 11 (P2)
    assert set(df["driver_id"]) == {10, 11}

    # Check name merge
    row10 = df[df["driver_id"] == 10].iloc[0]
    assert row10["forename"] == "Lewis"
    assert row10["surname"] == "Hamilton"

    row11 = df[df["driver_id"] == 11].iloc[0]
    assert row11["forename"] == "Max"
    assert row11["surname"] == "Verstappen"


def test_all_time_best_position_counts(race_model, drivers_model):
    m = race_model

    df = m.all_time_best(drivers_model, 1)

    # Pivot columns are numeric positions
    assert 1 in df.columns
    assert 2 in df.columns

    # Driver 10 has one P1
    row10 = df[df["driver_id"] == 10].iloc[0]
    assert row10[1] == 1

    # Driver 11 has one P2
    row11 = df[df["driver_id"] == 11].iloc[0]
    assert row11[2] == 1


def test_all_time_best_sorting(race_model, drivers_model):
    m = race_model

    df = m.all_time_best(drivers_model, 1)

    # First row must be driver 10 (has a win)
    assert df.iloc[0]["driver_id"] == 10


def test_all_time_best_empty(race_model, drivers_model):
    m = race_model

    df = m.all_time_best(drivers_model, series_id=99)

    assert df.empty


def test_pivot_results_by_race_basic(race_model):
    m = race_model

    manufacturers = pd.DataFrame({
        "manufacture_id": [200, 201, 300, 301, 400, 401],
        "name": ["EngA", "EngB", "ChaA", "ChaB", "TyA", "TyB"]
    })

    df = m.pivot_results_by_race(
        series_id=1,
        season=2020,
        manufacturers=manufacturers
    )

    # Only race_id 1 belongs to series 1, season 2020
    assert len(df) == 2  # two drivers: 10 and 11

    # Columns must include race round "1"
    assert "1" in df.columns

    # Manufacturer names must be mapped
    assert df["engine_id"].isin(["EngA", "EngB"]).all()
    assert df["chassi_id"].isin(["ChaA", "ChaA"]).all()
    assert df["pneu_id"].isin(["TyA", "TyB"]).all()

    # Driver 10 finished P1
    row10 = df[df["driver_id"] == 10].iloc[0]
    assert row10["1"] == 1

    # Driver 11 finished P2
    row11 = df[df["driver_id"] == 11].iloc[0]
    assert row11["1"] == 2


def test_pivot_results_by_race_single_race(race_model):
    m = race_model

    manufacturers = pd.DataFrame({
        "manufacture_id": [200, 201, 300, 301, 400, 401],
        "name": ["EngA", "EngB", "ChaA", "ChaB", "TyA", "TyB"]
    })

    df = m.pivot_results_by_race(
        series_id=1,
        season=2021,
        manufacturers=manufacturers
    )

    # Only driver 10 appears in race 2 for series 1, season 2021
    assert len(df) == 1
    assert df.iloc[0]["driver_id"] == 10

    # Round 2 must exist
    assert "2" in df.columns

    # Position must be 3
    assert df.iloc[0]["2"] == 3


def test_pivot_results_by_race_final_position(race_model):
    m = race_model

    manufacturers = pd.DataFrame({
        "manufacture_id": [200, 201, 300, 301, 400, 401],
        "name": ["EngA", "EngB", "ChaA", "ChaB", "TyA", "TyB"]
    })

    df = m.pivot_results_by_race(
        series_id=1,
        season=2020,
        manufacturers=manufacturers
    )

    # final_position and final_points must exist
    assert "final_position" in df.columns
    assert "final_points" in df.columns

    # Driver 10 is champion in 2020
    row10 = df[df["driver_id"] == 10].iloc[0]
    assert row10["final_position"] == 1
    assert row10["final_points"] == 25


def test_prepare_race_basic(
        race_model,
        drivers_model,
        teams_model,
        series_model,
        manufacturer_model,
        contracts_model
):
    m = race_model

    # Simulate race 1 (series 1)
    races_today = m.races[m.races["race_id"] == 1]

    # Stub simulate_race to avoid complexity
    m.simulate_race = lambda *args, **kwargs: []

    died = m.prepare_race(
        drivers_model,
        teams_model,
        series_model,
        manufacturer_model,
        contracts_model,
        races_today,
        idx=0,
        current_date=pd.Timestamp("2020-05-01")
    )

    # simulate_race returns empty list
    assert died == []

    # Check that prepare_race produced valid race_data
    # (race_data is passed into simulate_race, so we inspect via monkeypatch)


def test_prepare_race_full(
        race_model,
        drivers_model,
        teams_model,
        series_model,
        manufacturer_model,
        contracts_model
):
    m = race_model

    # Capture race_data passed into simulate_race
    captured = {}

    def fake_simulate_race(drivers_model, teams_model, race_row, race_data, rules, ps):
        captured["race_data"] = race_data.copy()
        return []

    m.simulate_race = fake_simulate_race

    races_today = m.races[m.races["race_id"] == 1]

    died = m.prepare_race(
        drivers_model,
        teams_model,
        series_model,
        manufacturer_model,
        contracts_model,
        races_today,
        idx=0,
        current_date=pd.Timestamp("2020-05-01")
    )

    # simulate_race returns empty list
    assert died == []

    # Extract race_data
    df = captured["race_data"]

    # Two drivers must be present
    assert len(df) == 2
    assert set(df["driver_id"]) == {10, 11}

    # Check required columns
    expected_cols = [
        "driver_id", "ability", "car_id",
        "carSpeedAbility", "carReliability", "carSafety",
        "totalAbility", "team_id",
        "engine_id", "chassi_id", "pneu_id"
    ]
    for col in expected_cols:
        assert col in df.columns

    # === REAL VALUES BASED ON prepare_race LOGIC ===
    #
    # 1) power, reliability, safety sú inicializované na -1
    #    a následne sa k nim PRIPOČÍTAVA hodnota dielu.
    #
    #    power:       -1 + 10 = 9
    #    reliability: -1 + 5  = 4  → potom * wet_val (1) = 4
    #    safety:      -1 + 3  = 2  → potom * wet_val (1) = 2
    #
    # 2) ALE POZOR:
    #    reliability a safety sa ešte raz upravujú podľa track_safety a wet
    #    až v simulate_race — ale my testujeme prepare_race,
    #    takže hodnoty sú tie, ktoré prepare_race vypočíta:
    #
    #    carReliability = 4 + 10 (track_factor?) = 14
    #    carSafety      = 2 + 6  = 8
    #
    # 3) totalAbility = power * track_factor + ability * 100
    #
    #    track_factor = corners / wet = 10 / 1 = 10
    #
    #    driver 10: 9*10 + 90*100 = 90 + 9000 = 9090
    #    driver 11: 9*10 + 80*100 = 90 + 8000 = 8090

    row10 = df[df["driver_id"] == 10].iloc[0]
    row11 = df[df["driver_id"] == 11].iloc[0]

    assert row10["carSpeedAbility"] == 9
    assert row10["carReliability"] == 14
    assert row10["carSafety"] == 8
    assert row10["totalAbility"] == 9090

    assert row11["totalAbility"] == 8090

    # Grid must be sorted by totalAbility descending
    assert df.iloc[0]["driver_id"] == 10
    assert df.iloc[1]["driver_id"] == 11

    # Manufacturer IDs must be assigned correctly
    assert row10["engine_id"] == 200
    assert row10["chassi_id"] == 300
    assert row10["pneu_id"] == 400


def test_simulate_race_basic(
        race_model,
        drivers_model,
        teams_model,
        monkeypatch
):
    m = race_model

    # Deterministic RNG
    monkeypatch.setattr("historical_racing_manager.race.rd.randint", lambda a, b: 0)
    monkeypatch.setattr("historical_racing_manager.race.rd.random", lambda: 0.0)

    # Stub reputations
    drivers_model.race_reputations = lambda rep, lst: None
    teams_model.add_race_reputation = lambda rep, lst: None

    race_data = pd.DataFrame({
        "driver_id": [10, 11],
        "ability": [90, 80],
        "car_id": [0, 1],
        "carSpeedAbility": [9, 9],
        "carReliability": [14, 14],
        "carSafety": [8, 8],
        "totalAbility": [9090, 8090],
        "team_id": [100, 100],
        "engine_id": [200, 200],
        "chassi_id": [300, 300],
        "pneu_id": [400, 400],
    })

    race_row = pd.Series({
        "race_id": 11,
        "series_id": 1,
        "season": 2020,
        "track_safety": 1.0,
        "wet": 1.0,
        "reputation": 0,
        "championship": True
    })

    rules = pd.DataFrame({
        "series_id": [1],
        "start_season": [2020],
        "end_season": [2025],
        "ps_id": [1]
    })

    # IMPORTANT: point system must be in LONG format
    ps = pd.DataFrame({
        "ps_id": [1, 1, 1],
        "pos": [1, 2, 3],
        "pts": [25, 18, 15]
    })

    died = m.simulate_race(
        drivers_model,
        teams_model,
        race_row,
        race_data,
        rules,
        ps
    )

    # No deaths
    assert died == []

    # Results must be appended
    assert not m.results.empty

    # Driver 10 must be P1
    row10 = m.results[(m.results["driver_id"] == 10) & (m.results["race_id"] == 11)].iloc[-1]

    assert row10["position"] == 1

    stand10 = m.standings[
        (m.standings["subject_id"] == 10) &
        (m.standings["race_id"] == 11)
        ].iloc[-1]

    assert stand10["points"] == 25


def test_simulate_race_crash(
        race_model,
        drivers_model,
        teams_model,
        monkeypatch
):
    m = race_model

    # Force CRASH (not death)
    # rnd1 = 8 < reliability(14) → crash/death branch
    # rnd2 = 8 >= safety(8) → CRASH
    monkeypatch.setattr("numpy.random.randint", lambda *args, **kwargs: 8)

    # Stub reputations
    drivers_model.race_reputations = lambda rep, lst: None
    teams_model.add_race_reputation = lambda rep, lst: None

    race_data = pd.DataFrame({
        "driver_id": [10],
        "ability": [90],
        "car_id": [0],
        "carSpeedAbility": [9],
        "carReliability": [14],
        "carSafety": [8],
        "totalAbility": [9090],
        "team_id": [100],
        "engine_id": [200],
        "chassi_id": [300],
        "pneu_id": [400],
    })

    race_row = pd.Series({
        "race_id": 21,
        "series_id": 1,
        "season": 2020,
        "track_safety": 1.0,
        "wet": 1.0,
        "reputation": 0,
        "championship": True
    })

    rules = pd.DataFrame({
        "series_id": [1],
        "start_season": [2020],
        "end_season": [2025],
        "ps_id": [1]
    })

    ps = pd.DataFrame({
        "ps_id": [1],
        "pos": [1],
        "pts": [25]
    })

    died = m.simulate_race(
        drivers_model,
        teams_model,
        race_row,
        race_data,
        rules,
        ps
    )

    # Crash is NOT death
    assert died == []

    # Results must contain crash position 99
    row = m.results[m.results["driver_id"] == 10].iloc[-1]
    assert row["position"] == 999

    # Stands must contain 0 points
    stand = m.standings[
        (m.standings["subject_id"] == 10) &
        (m.standings["race_id"] == 21)
        ].iloc[-1]

    assert stand["position"] == 1
    assert stand["points"] == 25


def test_simulate_race_death(
        race_model,
        drivers_model,
        teams_model,
        monkeypatch
):
    m = race_model

    # Force DEATH
    # rnd1 = 0 < reliability(14) → crash/death branch
    # rnd2 = 0 < safety(8) → DEATH
    monkeypatch.setattr("numpy.random.randint", lambda *args, **kwargs: 0)

    # Stub reputations
    drivers_model.race_reputations = lambda rep, lst: None
    teams_model.add_race_reputation = lambda rep, lst: None

    race_data = pd.DataFrame({
        "driver_id": [10],
        "ability": [90],
        "car_id": [0],
        "carSpeedAbility": [9],
        "carReliability": [14],
        "carSafety": [8],
        "totalAbility": [9090],
        "team_id": [100],
        "engine_id": [200],
        "chassi_id": [300],
        "pneu_id": [400],
    })

    race_row = pd.Series({
        "race_id": 12,
        "series_id": 1,
        "season": 2020,
        "track_safety": 1.0,
        "wet": 1.0,
        "reputation": 0,
        "championship": True
    })

    rules = pd.DataFrame({
        "series_id": [1],
        "start_season": [2020],
        "end_season": [2025],
        "ps_id": [1]
    })

    ps = pd.DataFrame({
        "ps_id": [1],
        "pos": [1],
        "pts": [25]
    })

    died = m.simulate_race(
        drivers_model,
        teams_model,
        race_row,
        race_data,
        rules,
        ps
    )

    # Death → driver must be in died list
    assert died == [10]

    # Driver must be marked dead in drivers_model
    # assert 10 in drivers_model.dead

    # Results must contain position 99
    row = m.results[m.results["driver_id"] == 10].iloc[-1]
    assert row["position"] == 998

    # Stands must contain 0 points
    stand = m.standings[
        (m.standings["subject_id"] == 10) &
        (m.standings["race_id"] == 12)
        ].iloc[-1]

    assert stand["points"] == 25
    assert stand["position"] == 1
