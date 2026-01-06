from datetime import datetime

import pandas as pd
import pytest

from historical_racing_manager.teams import TeamsModel


# === Fixtures ===
@pytest.fixture
def model():
    m = TeamsModel()
    m.teams = pd.DataFrame({
        "team_id": [1, 2, 3],
        "team_name": ["Alpha", "Beta", "Gamma"],
        "owner_id": [10, 0, 20],  # 10,20 = human; 0 = AI
        "money": [100000, 50000, -20000],
        "finance_employees": [5, 0, 10],
        "design_employees": [2, 1, 3],
        "reputation": [100, 50, 20],
        "found": [2000, 2005, 2010],
        "folded": [2030, 2030, 2020],
    })
    return m


# === Tests: basic getters ===

def test_get_finance_employee_salary(model):
    assert model.get_finance_employee_salary() == model.finance_employee_salary


def test_get_kick_employee_price(model):
    assert model.get_kick_employee_price() == model.kick_employee_price


# === Tests: _get_teams_light ===

def test_get_teams_light(model):
    df = model._get_teams_light()
    assert list(df.columns) == ["team_id", "team_name"]
    assert len(df) == 3


def test_get_teams_light_missing_columns():
    m = TeamsModel()
    m.teams = pd.DataFrame({"team_id": [1]})
    df = m._get_teams_light()
    assert "team_name" in df.columns


# === Tests: get_team_names ===

def test_get_team_names(model):
    names = model.get_team_names([1, 3, 999])
    assert names == ["Alpha", "Gamma", ""]


# === Tests: get_teams ===

def test_get_teams(model):
    df = model.get_teams()
    assert list(df.columns) == ["team_id", "team_name", "owner_id"]
    assert len(df) == 3


def test_get_teams_empty():
    m = TeamsModel()
    df = m.get_teams()
    assert list(df.columns) == ["team_id", "team_name", "owner_id"]
    assert df.empty


# === Tests: get_teams_id ===

def test_get_teams_id(model):
    assert model.get_teams_id("Alpha") == 1
    assert model.get_teams_id("Unknown") is None


# === Tests: human team mask ===

def test_get_human_team_mask(model):
    mask = model.get_human_team_mask(2020)
    assert mask.tolist() == [True, False, True]


def test_get_human_teams(model):
    df = model.get_human_teams(datetime(year=2020, month=1, day=1))
    assert set(df["team_id"]) == {1, 3}


# === Tests: get_team_staff_counts ===

def test_get_team_staff_counts(model):
    df = model.get_team_staff_counts(1)
    assert df.iloc[0]["finance_employees"] == 5
    assert df.iloc[0]["design_employees"] == 2


# === Tests: invest_finance ===

def test_invest_finance_valid(model):
    year = 2020
    model.invest_finance(year, {1: 3})  # team 1 is human

    t1 = model.teams.loc[model.teams["team_id"] == 1].iloc[0]
    assert t1["finance_employees"] == 3
    assert t1["money"] == 100000 - 3 * model.finance_employee_salary


# === Tests: update_money ===

def test_update_money(model):
    before = model.teams["money"].copy()
    model.update_money()
    after = model.teams["money"]

    # money must change for teams with finance employees
    assert (after != before).any()


# === Tests: change_finance_employees ===

def test_change_finance_employees(model, capsys):
    model.change_finance_employees(1, 99)
    assert model.teams.loc[model.teams["team_id"] == 1, "finance_employees"].iloc[0] == 99


def test_change_finance_employees_invalid(model, capsys):
    model.change_finance_employees(999, 5)
    captured = capsys.readouterr().out
    assert "does not exist" in captured


# === Tests: deduct_money ===

def test_deduct_money(model):
    model.deduct_money(1, 5000)
    assert model.teams.loc[model.teams["team_id"] == 1, "money"].iloc[0] == 95000


def test_deduct_money_invalid(model, capsys):
    model.deduct_money(999, 5000)
    captured = capsys.readouterr().out
    assert "does not exist" in captured


# === Tests: get_team_finance_info ===

def test_get_team_finance_info(model):
    info = model.get_team_finance_info(1)
    assert info["team_id"] == 1
    assert info["money"] == 100000
    assert info["finance_employees"] == 5


def test_get_team_finance_info_invalid(model):
    info = model.get_team_finance_info(999)
    assert info == {}


# === Tests: halve_reputations ===

def test_halve_reputations(model):
    model.halve_reputations()
    assert model.teams["reputation"].tolist() == [50, 25, 10]


# === Tests: update_reputations_and_money ===

def test_update_reputations_and_money(model):
    before_rep = model.teams["reputation"].copy()
    model.update_reputations_and_money()
    after_rep = model.teams["reputation"]

    assert (after_rep < before_rep).all()


# === Tests: add_race_reputation ===

def test_add_race_reputation(model):
    model.add_race_reputation(100, [1, 2, 3])

    # winner gets +100
    assert model.teams.loc[model.teams["team_id"] == 1, "reputation"].iloc[0] == 200

    # second gets +50
    assert model.teams.loc[model.teams["team_id"] == 2, "reputation"].iloc[0] == 100

    # third gets +33
    assert model.teams.loc[model.teams["team_id"] == 3, "reputation"].iloc[0] == 53


# === Tests: auto_invest_ai_finance ===

def test_auto_invest_ai_finance(model):
    model.auto_invest_ai_finance()

    ai_team = model.teams.loc[model.teams["team_id"] == 2].iloc[0]
    assert ai_team["finance_employees"] >= 0
    assert ai_team["money"] <= 50000


# === Tests: check_debt ===

def test_check_debt(model):
    model.check_debt()

    # team 3 had -20000 → must be reset
    t3 = model.teams.loc[model.teams["team_id"] == 3].iloc[0]
    assert t3["owner_id"] == 0
    assert t3["money"] == 10_000_000
