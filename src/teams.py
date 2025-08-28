import os
import tkinter as tk

import pandas as pd

teams = pd.DataFrame()


def load(name):
    global teams

    teams = pd.DataFrame(columns=teams.columns)
    if not os.path.exists(name + "teams.csv"):
        return False
    teams = pd.read_csv(name + "teams.csv")
    return True


def save(name):
    if len(name) > 0:
        teams.to_csv(name + "teams.csv", index=False)


def max_affordable_fin(money):
    return money // 250


def kill_human_teams():
    global teams
    teams["ai"] = True


def open_window(parent, labels, max_fin):
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
        d = result[0]
        if d.isdigit():
            d = int(d)
            if d > max_fin or d < 0:
                good = False
        else:
            good = False
        if good:
            top.destroy()
        else:
            result.clear()

    def on_cancel():
        result.append(0)
        top.destroy()

    btn_frame = tk.Frame(top)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="Hire", command=on_done).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Hire 0 employees", command=on_cancel).pack(side="left", padx=5)

    parent.wait_window(top)
    return result


def invest_fin_all(dat, root):
    global teams
    human_teams = teams[
        (teams["ai"] == False) & (teams["found"] <= dat.year) & (teams["folded"] >= dat.year)
    ]
    for i, row in human_teams.iterrows():
        if row["money"] >= 0:
            max_fin = row["money"] // 2500

            if max_fin == 0:
                continue

            labels = [
                f"Available finance: {row['money']}, year {dat.year}\nSelect the number of financial employees (0–{max_fin}):"
            ]
            res = open_window(root, labels, max_fin)
            if not res:
                continue
            d_str = res[0]
            user_input = int(d_str)

            if 0 <= user_input <= max_fin:
                human_teams.at[i, "money"] -= user_input * 2500
                human_teams.at[i, "fin"] = user_input

        else:

            kill_human_teams()
    teams.set_index("teamID", inplace=True)
    human_teams.set_index("teamID", inplace=True)

    teams.update(human_teams)

    teams.reset_index(inplace=True)


def update_money_fin(row):
    money = row["money"]
    fin = row["fin"]
    earn_coeficient = [12000, 11000, 10000, 9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000, 1000, 0]
    for i in range(len(earn_coeficient)):
        if fin <= 0:
            break
        coef = earn_coeficient[i] if i < len(earn_coeficient) else earn_coeficient[-1]
        used = min(fin, 100)
        money += coef * used
        fin -= used

    row["money"] = int(money)
    row["fin"] = int(fin)
    return row


def race_reputations(reputation, results):
    global teams
    for i in range(len(results)):
        teams.loc[teams["teamID"] == results[i], "reputation"] += reputation // (i + 1)


def update_reputations():
    global teams

    earn_coeficient = [500, 400, 300, 200, 100, 0]
    human_teams = teams[(teams["ai"] == False)]

    teams = teams.apply(update_money_fin, axis=1)

    teams.loc[teams["teamID"].isin(teams["teamID"]), "reputation"] = (
        teams.loc[teams["teamID"].isin(teams["teamID"]), "teamID"].map(
            teams.set_index("teamID")["reputation"]
        )
        // 2
    )
