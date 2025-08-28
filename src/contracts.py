import os
import random as rd
import tkinter as tk
from tkinter import ttk

import numpy as np
import pandas as pd

import manufacturer as mf
import teams as tm

CScontract = pd.DataFrame()
DTcontract = pd.DataFrame()
STcontract = pd.DataFrame()
MScontract = pd.DataFrame()
MTcontract = pd.DataFrame()


def load(name):
    global CScontract
    global DTcontract
    global STcontract
    global MScontract
    global MTcontract

    CScontract = pd.DataFrame(columns=CScontract.columns)
    DTcontract = pd.DataFrame(columns=DTcontract.columns)
    STcontract = pd.DataFrame(columns=STcontract.columns)
    MScontract = pd.DataFrame(columns=MScontract.columns)
    MTcontract = pd.DataFrame(columns=MTcontract.columns)
    if not os.path.exists(name + "CScontract.csv"):
        return False
    if not os.path.exists(name + "DTcontract.csv"):
        return False
    if not os.path.exists(name + "STcontract.csv"):
        return False
    if not os.path.exists(name + "MScontract.csv"):
        return False
    if not os.path.exists(name + "MTcontract.csv"):
        return False

    CScontract = pd.read_csv(name + "CScontract.csv")
    DTcontract = pd.read_csv(name + "DTcontract.csv")
    STcontract = pd.read_csv(name + "STcontract.csv")
    MScontract = pd.read_csv(name + "MScontract.csv")
    MTcontract = pd.read_csv(name + "MTcontract.csv")
    return True


def save(name):
    if len(name) > 0:
        STcontract.to_csv(name + "STcontract.csv", index=False)
        DTcontract.to_csv(name + "DTcontract.csv", index=False)
        CScontract.to_csv(name + "CScontract.csv", index=False)
        MScontract.to_csv(name + "MScontract.csv", index=False)
        MTcontract.to_csv(name + "MTcontract.csv", index=False)


def show_dataframe(tree, dataframe):
    cols = list(dataframe.columns)

    tree["columns"] = cols
    tree["show"] = "tree headings"

    tree.heading("#0", text="ID")
    tree.column("#0", width=50, anchor="center")

    for col in cols:
        tree.heading(col, text=col)
        tree.column(col, width=100, anchor="center")

    for idx, row in dataframe.iterrows():
        tree.insert("", "end", text=str(idx), values=list(row))


def open_window(parent, labels, spandas, keep, what):
    top = tk.Toplevel(parent)
    top.transient(parent)
    top.grab_set()
    entries = []
    for text in labels:
        tk.Label(top, text=text).pack(padx=10, pady=(10, 0))
        e = tk.Entry(top)
        e.pack(padx=10, pady=(0, 10))
        entries.append(e)

    result = []

    def on_done():

        for e in entries:
            result.append(e.get())
        good = True
        if what == "D":
            d = result[0]
            if d.isdigit():
                d = int(d)
                if d < 0 or d >= len(spandas):
                    good = False

            else:
                good = False
            m = result[1]
            if m.isdigit() and good:
                m = int(m)
                if m < spandas.loc[d, "minSalary"]:
                    good = False
            else:
                good = False
            l = result[2]
            if l.isdigit():
                l = int(l)
                if l < 0 or l > 4:
                    good = False
            else:
                good = False
        if what == "P":
            d = result[0]
            if d.isdigit():
                d = int(d)
                if d < 0 or d >= len(spandas):
                    good = False
            else:
                good = False
            l = result[1]
            if l.isdigit():
                l = int(l)
                if l < 0 or l > 4:
                    good = False
            else:
                good = False
        if good:
            top.destroy()
        else:
            result.clear()

    def on_cancel():
        top.destroy()

    btn_frame = tk.Frame(top)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="Offer", command=on_done).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Give Up", command=on_cancel).pack(side="left", padx=5)

    frame = ttk.Frame(top)
    frame.pack(fill="both", expand=True)

    tree = ttk.Treeview(frame)
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    show_dataframe(tree, spandas[keep])

    parent.wait_window(top)
    return result


def disable_contracts(drivers):
    for d in drivers:
        DTcontract.loc[DTcontract["driverID"] == d, "active"] = False


def sign_car_part_contracts(active_series, dat, car_parts, root):
    global MTcontract
    alive = True
    active_series = active_series.sort_values(by="reputation", ascending=True)
    active_series = active_series.reset_index(drop=True)
    new_contracts = MTcontract.head(0).copy()
    tm.teams = tm.teams.sort_values(by="reputation", ascending=True)

    active_contracts = MTcontract[
        (MTcontract["startYear"] <= dat.year) & (MTcontract["endYear"] >= dat.year)
    ]
    human_teams = tm.teams[
        (tm.teams["ai"] == False)
        & (tm.teams["found"] <= dat.year)
        & (tm.teams["folded"] >= dat.year)
    ]
    will_pay = active_contracts[(active_contracts["teamID"].isin(human_teams["teamID"]))]

    pay_by_team = will_pay.groupby("teamID")["cost"].sum()

    for team_id, total_cost in pay_by_team.items():
        tm.teams.loc[tm.teams["teamID"] == team_id, "money"] -= total_cost
    for si in active_series["seriesID"]:
        series_car_parts = car_parts[
            (car_parts["seriesID"] == si) & (car_parts["year"] == dat.year)
        ]
        teams_in_series = STcontract[STcontract["seriesID"] == si]["teamID"]
        for h in ["e", "c", "p"]:
            type_car_part = series_car_parts[(series_car_parts["partType"] == h)]
            type_car_part = type_car_part.reset_index(drop=True)
            type_car_part = pd.merge(
                type_car_part,
                mf.manufacturers,
                left_on=["manufacturerID"],
                right_on=["manufacturerID"],
                how="left",
            )
            type_car_part["cost"] = type_car_part["cost"].astype(int)

            type_car_part.rename(columns={"cost": "Cost"}, inplace=True)
            type_car_part.rename(columns={"name": "Name"}, inplace=True)

            for j in teams_in_series:

                current_contract = active_contracts[
                    (active_contracts["seriesID"] == si)
                    & (active_contracts["teamID"] == j)
                    & (active_contracts["partType"] == h)
                ]
                if len(current_contract) == 0:
                    if j in human_teams["teamID"].values and alive:
                        manufacturer = 0
                        contract_len = 0

                        suciastka = ""
                        if h == "e":
                            suciastka = "Engine"
                        elif h == "c":
                            suciastka = "Chassi"
                        elif h == "p":
                            suciastka = "Tyre"

                        keep = ["Name", "Cost"]

                        labels = [
                            f"Component: {suciastka}, year {dat.year}, available finance: {tm.teams.loc[tm.teams['teamID'] == j, 'money'].values[0]}\nChoose index (0–{len(type_car_part) - 1}):",
                            f"Contract length (0–4):",
                        ]
                        result = open_window(root, labels, type_car_part, keep, "P")

                        if len(result) != 2:
                            tm.kill_human_teams()
                            sampled_row = type_car_part.sample(1).iloc[0]

                            manufacturer = sampled_row["manufacturerID"]
                            cost = sampled_row["Cost"]

                            contract_len = rd.randint(0, 4)
                            alive = False
                        else:
                            d_str, l_str = result

                            if not d_str:
                                continue
                            d, l = int(d_str), int(l_str)
                            manufacturer = type_car_part.iloc[d]["manufacturerID"]
                            cost = type_car_part.iloc[d]["Cost"]
                            contract_len = l
                    else:
                        sampled_row = type_car_part.sample(1).iloc[0]

                        manufacturer = sampled_row["manufacturerID"]
                        cost = sampled_row["Cost"]

                        contract_len = rd.randint(0, 4)

                    new_contracts.loc[len(new_contracts)] = [
                        si,
                        j,
                        manufacturer,
                        h,
                        dat.year,
                        dat.year + contract_len,
                        cost,
                    ]
                    tm.teams.loc[tm.teams["teamID"] == j, "money"] -= cost

    MTcontract = pd.concat([MTcontract, new_contracts], ignore_index=True)


def sign_driver_contracts(
    active_series, dat, DTcontract, active_drivers, rules, STcontract, temp, root
):
    active_series = active_series.sort_values(by="reputation", ascending=True)
    active_series = active_series.reset_index(drop=True)

    tm.teams = tm.teams.sort_values(by="reputation", ascending=True)
    alive = True

    for si in active_series["seriesID"]:
        cd = DTcontract[
            (DTcontract["active"] == True)
            & (DTcontract["startYear"] <= dat.year)
            & (DTcontract["endYear"] >= dat.year)
            & (
                DTcontract["wanted_reputation"]
                <= active_series.loc[active_series["seriesID"] == si, "reputation"].values[0]
            )
        ]["driverID"]
    active_drivers["minSalary"] = 2000000 / (active_drivers.index + 1)
    x = 0
    for si in active_series["seriesID"]:
        active_rules = rules[(rules["startSeason"] <= dat.year) & (rules["endSeason"] >= dat.year)]
        max_age = active_rules[active_rules["seriesID"] == si]["maxAge"].iloc[0]
        min_age = active_rules[active_rules["seriesID"] == si]["minAge"].iloc[0]
        available_drivers = active_drivers[
            (active_drivers["year"] >= dat.year - max_age)
            & (active_drivers["year"] <= dat.year - min_age)
        ].copy()
        available_drivers["age"] = dat.year - available_drivers["year"]
        if temp:
            available_drivers["maxLen"] = 1
        else:
            available_drivers["maxLen"] = np.minimum(4, max_age - available_drivers["age"])
        cd = DTcontract[
            (DTcontract["active"] == True)
            & (DTcontract["startYear"] <= dat.year)
            & (DTcontract["endYear"] >= dat.year)
            & (
                DTcontract["wanted_reputation"]
                <= active_series.loc[active_series["seriesID"] == si, "reputation"].values[0]
            )
        ]
        contracted_drivers = cd["driverID"]
        human_teams = tm.teams[
            (tm.teams["ai"] == False)
            & (tm.teams["found"] <= dat.year)
            & (tm.teams["folded"] >= dat.year)
        ]
        will_pay = cd[
            (
                cd["wanted_reputation"]
                == active_series.loc[active_series["seriesID"] == si, "reputation"].values[0]
            )
            & (cd["teamID"].isin(human_teams["teamID"]))
        ]
        salary_by_team = will_pay.groupby("teamID")["salary"].sum()

        for team_id, total_salary in salary_by_team.items():
            tm.teams.loc[tm.teams["teamID"] == team_id, "money"] -= total_salary

        non_contracted_drivers = available_drivers[
            ~available_drivers["driverID"].isin(contracted_drivers)
        ]

        active_DTcontracts = DTcontract[
            (DTcontract["active"] == True)
            & (DTcontract["startYear"] <= dat.year)
            & (DTcontract["endYear"] >= dat.year)
            & (
                DTcontract["wanted_reputation"]
                <= active_series.loc[active_series["seriesID"] == si, "reputation"].values[0]
            )
        ]

        max_cars = active_rules[active_rules["seriesID"] == si]["maxCars"]

        if len(max_cars) != 0:

            teams_in_series = STcontract[STcontract["seriesID"] == si]["teamID"]

            active_contracts_per_team = active_DTcontracts[
                active_DTcontracts["teamID"].isin(teams_in_series)
            ]

            contract_counts = (
                active_contracts_per_team.groupby("teamID")
                .size()
                .reset_index(name="activeContracts")
            )

            all_teams_in_series = (
                pd.DataFrame(teams_in_series)
                .merge(contract_counts, on="teamID", how="left")
                .fillna(0)
            )

            all_teams_in_series["activeContracts"] = all_teams_in_series["activeContracts"].astype(
                int
            )

            all_teams_in_series = pd.merge(all_teams_in_series, tm.teams, on="teamID")

            non_contracted_drivers = non_contracted_drivers.reset_index(drop=True)
            for i in range(max_cars.iloc[0]):
                for j in range(len(all_teams_in_series)):

                    if (
                        all_teams_in_series.iloc[j]["activeContracts"] == i
                        and len(non_contracted_drivers) > 0
                    ):
                        if all_teams_in_series.iloc[j]["ai"] == False and alive:
                            show_drivers = non_contracted_drivers[
                                ["driverID", "forename", "surname", "year", "maxLen", "minSalary"]
                            ]
                            show_drivers = show_drivers.rename(
                                columns={
                                    "forename": "Forename",
                                    "surname": "Surname",
                                    "year": "Birth year",
                                }
                            )
                            show_drivers = show_drivers.sort_values(by="Surname", ascending=True)
                            show_drivers = show_drivers.reset_index(drop=True)

                            labels = [
                                f"Available finance: {tm.teams.loc[tm.teams['teamID'] == all_teams_in_series.iloc[j]['teamID'], 'money'].values[0]} , year {dat.year}\nChoose index (0–{len(show_drivers) - 1}):",
                                f"Salary:",
                                f"Contract length (0–4):",
                            ]
                            keep = ["Forename", "Surname", "Birth year"]
                            result = open_window(root, labels, show_drivers, keep, "D")

                            if len(result) != 3:
                                tm.kill_human_teams()
                                d = 0
                                DTcontract.loc[
                                    DTcontract["driverID"]
                                    == non_contracted_drivers.iloc[d]["driverID"],
                                    "active",
                                ] = False
                                DTcontract.loc[len(DTcontract)] = [
                                    non_contracted_drivers.iloc[d]["driverID"],
                                    all_teams_in_series.iloc[j]["teamID"],
                                    25000,
                                    active_series.loc[
                                        active_series["seriesID"] == si, "reputation"
                                    ].values[0],
                                    dat.year,
                                    dat.year
                                    + rd.randint(
                                        0, min(4, non_contracted_drivers.iloc[d]["maxLen"])
                                    ),
                                    True,
                                ]
                                non_contracted_drivers = non_contracted_drivers.drop(d)
                                alive = False
                            else:
                                d_str, m_str, l_str = result
                                if not d_str:
                                    continue
                                d, m, l = int(d_str), int(m_str), int(l_str)

                                tm.teams.loc[
                                    tm.teams["teamID"] == all_teams_in_series.iloc[j]["teamID"],
                                    "money",
                                ] -= m
                                DTcontract.loc[
                                    DTcontract["driverID"] == show_drivers.iloc[d]["driverID"],
                                    "active",
                                ] = False
                                DTcontract.loc[len(DTcontract)] = [
                                    show_drivers.iloc[d]["driverID"],
                                    all_teams_in_series.iloc[j]["teamID"],
                                    m,
                                    active_series.loc[
                                        active_series["seriesID"] == si, "reputation"
                                    ].values[0],
                                    dat.year,
                                    dat.year + l,
                                    True,
                                ]
                                non_contracted_drivers = non_contracted_drivers[
                                    non_contracted_drivers["driverID"]
                                    != show_drivers.iloc[d]["driverID"]
                                ]
                        else:

                            d = 0
                            DTcontract.loc[
                                DTcontract["driverID"]
                                == non_contracted_drivers.iloc[d]["driverID"],
                                "active",
                            ] = False
                            DTcontract.loc[len(DTcontract)] = [
                                non_contracted_drivers.iloc[d]["driverID"],
                                all_teams_in_series.iloc[j]["teamID"],
                                25000,
                                active_series.loc[
                                    active_series["seriesID"] == si, "reputation"
                                ].values[0],
                                dat.year,
                                dat.year
                                + rd.randint(0, min(4, non_contracted_drivers.iloc[d]["maxLen"])),
                                True,
                            ]
                            non_contracted_drivers = non_contracted_drivers.drop(d)
                        all_teams_in_series.at[j, "activeContracts"] += 1

                        non_contracted_drivers = non_contracted_drivers.reset_index(drop=True)
                        x += 1

    return DTcontract
