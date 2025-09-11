import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import pandas as pd


class Graphics:
    def __init__(self, controller):
        self.controller = controller
        self.root = tk.Tk()
        self.root.title("Historical Racing Manager")
        self.root.geometry("1600x900")

        self.name_var = tk.StringVar()
        self.series_var = tk.StringVar()
        self.season_var = tk.StringVar()

        self._setup_menu()
        self._setup_controls()
        self._setup_table()

    def _setup_menu(self):
        menu = tk.Frame(self.root)
        menu.pack(pady=10)

        tk.Label(menu, text="Historical Racing Manager:").grid(row=0, column=0, padx=5)
        tk.Entry(menu, textvariable=self.name_var).grid(row=0, column=1, padx=5)

        self._create_button(menu, "New Game", self.on_new_game, 2)
        self._create_button(menu, "Save Game", self.on_save_game, 3)
        self._create_button(menu, "Load Game", self.on_load_game, 4)
        self._create_button(menu, "Exit", self.root.quit, 5)

        self.date_label = tk.Label(menu, text="", font=("Arial", 14))
        self.date_label.grid(row=0, column=6, padx=10)

    def _setup_controls(self):
        controls = tk.Frame(self.root)
        controls.pack(pady=10)

        self.cmb_series = ttk.Combobox(controls, textvariable=self.series_var, state="readonly")
        self.cmb_series.grid(row=0, column=0, padx=5)
        self.cmb_series.bind("<<ComboboxSelected>>", self.on_series_change)

        self.cmb_season = ttk.Combobox(controls, textvariable=self.season_var, state="readonly")
        self.cmb_season.grid(row=0, column=1, padx=5)

        self._create_button(controls, "Show Results", self.show_results, 2)
        self._create_button(controls, "Next Day", lambda: self.sim_step(40000), 3)
        self._create_button(controls, "Next Week", lambda: self.sim_step(360), 4)
        self._create_button(controls, "Show Contracts", self.show_contracts, 5)
        self._create_button(controls, "Terminate Driver", self.terminate_driver_dialog, 6)

    def _setup_table(self):
        self.result_frame = ttk.Frame(self.root)
        self.result_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(self.result_frame, show="headings")
        vsb = ttk.Scrollbar(self.result_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.result_frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.result_frame.rowconfigure(0, weight=1)
        self.result_frame.columnconfigure(0, weight=1)

    def _create_button(self, parent, text, command, column):
        tk.Button(parent, text=text, command=command).grid(row=0, column=column, padx=5)

    def run(self):
        self.root.mainloop()

    def on_new_game(self):
        self.controller.load_game("my_data")
        self.date_label.config(text=self.controller.get_date())
        self.update_series_dropdown()

    def on_save_game(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Please enter a name to save the game.")
            return
        if name in ("my_data", "original", "custom_original"):
            messagebox.showwarning("Invalid Name", "Please use a different game name.")
            return
        self.controller.save_game(name)
        messagebox.showinfo("Saved", f"Game '{name}' has been saved.")

    def on_load_game(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Please enter a name to load the game.")
            return
        if name in ("original", "custom_original"):
            messagebox.showwarning("Invalid Name", "Please use a different game name.")
            return
        if self.controller.load_game(name):
            self.date_label.config(text=self.controller.get_date())
            self.update_series_dropdown()
            messagebox.showinfo("Loaded", f"Game '{name}' has been loaded.")
        else:
            messagebox.showinfo("Files Not Found", "Please enter a valid game name.")

    def on_series_change(self, event=None):
        self.controller.update_seasons(self.series_var.get())
        self.cmb_season["values"] = self.controller.get_season_list()
        if self.cmb_season["values"]:
            self.cmb_season.current(len(self.cmb_season["values"]) - 1)

    def sim_step(self, days):
        self.controller.simulate_days(days)
        self.date_label.config(text=self.controller.get_date())
        self.update_series_dropdown()
        self.show_results()

    def update_series_dropdown(self):
        self.cmb_series["values"] = self.controller.get_series_names()
        if self.cmb_series["values"]:
            self.cmb_series.current(0)
        self.on_series_change()

    def show_results(self):
        df = self.controller.get_results(self.series_var.get(), self.season_var.get())
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)
        for col in df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        for row in df.itertuples(index=False):
            self.tree.insert("", "end", values=row)

    def show_contracts(self):
        df = self.controller.get_active_driver_contracts()
        self.show_dataframe(self.tree, df)

    def terminate_driver_dialog(self):
        df = self.controller.get_active_driver_contracts()
        if df.empty:
            messagebox.showinfo("No Contracts", "No active contracts to terminate.")
            return

        labels = ["Enter team ID:", "Enter driver ID to terminate:"]
        entry = self._open_selection_dialog(pd.DataFrame(), [], labels)
        if len(entry) == 2:
            try:
                team_id = int(entry[0])
                driver_id = int(entry[1])
                self.controller.kick_driver(team_id, driver_id)
                messagebox.showinfo("Contract Terminated", f"Driver {driver_id} removed from team {team_id}.")
            except Exception:
                messagebox.showerror("Error", "Invalid input. Please enter valid numeric IDs.")

    def ask_finance_investments(self, human_teams_df):
        investments = {}
        for _, row in human_teams_df.iterrows():
            max_fin = row["money"] // 2500
            if max_fin <= 0:
                continue

            labels = [
                f"Team: {row['teamName']}\nAvailable funds: {row['money']}\nEnter number of finance employees (0–{max_fin}):"
            ]
            entry = self._open_selection_dialog(pd.DataFrame(), [], labels, max_fin=max_fin)
            if entry and entry[0].isdigit():
                investments[row["teamID"]] = int(entry[0])
        return investments

    def ask_driver_contracts(self, human_teams_df, available_drivers_df, year) -> dict:
        result = {}
        drivers = available_drivers_df.copy()
        drivers["Age"] = year - drivers["year"]
        drivers["maxLen"] = np.minimum(4, drivers["Age"].apply(lambda a: max(1, 40 - a)))
        drivers["minSalary"] = 25000
        drivers = drivers.rename(columns={"forename": "Forename", "surname": "Surname"})
        keep = ["Forename", "Surname", "Age", "minSalary"]

        for _, team in human_teams_df.iterrows():
            labels = [
                f"Team: {team['teamName']} | Budget: {team['money']}\nEnter driver index (0–{len(drivers) - 1}):",
                "Salary:",
                "Contract length (0–4):",
            ]
            entry = self._open_selection_dialog(drivers, keep, labels)
            if len(entry) == 3:
                try:
                    d, m, l = map(int, entry)
                    driver_id = drivers.iloc[d]["driverID"]
                    result[team["teamID"]] = (driver_id, m, l)
                except Exception:
                    result[team["teamID"]] = None
                else:
                    result[team["teamID"]] = None
                return result

                def ask_car_part_contracts(self, human_teams_df, car_parts_df, year) -> dict:
                    result = {}
                    for _, team in human_teams_df.iterrows():
                        result[team["teamID"]] = {}
                        for part_type, label in [("e", "Engine"), ("c", "Chassi"), ("p", "Tyre")]:
                            parts = car_parts_df[
                                (car_parts_df["partType"] == part_type) & (car_parts_df["year"] == year)
                                ].copy()
                            parts = parts.rename(columns={"cost": "Cost"})
                            keep = ["manufacturerID", "Cost"]
                            labels = [
                                f"Team: {team['teamName']} | Component: {label} | Budget: {team['money']}\nEnter index (0–{len(parts) - 1}):",
                                "Contract length (0–4):",
                            ]
                            entry = self._open_selection_dialog(parts, keep, labels)
                            if len(entry) == 2:
                                try:
                                    d, l = map(int, entry)
                                    manufacturer_id = parts.iloc[d]["manufacturerID"]
                                    result[team["teamID"]][part_type] = (manufacturer_id, l)
                                except Exception:
                                    result[team["teamID"]][part_type] = None
                            else:
                                result[team["teamID"]][part_type] = None
                    return result

    def _open_selection_dialog(self, df, keep, labels, max_fin=None) -> list:
        top = tk.Toplevel(self.root)
        top.transient(self.root)
        top.grab_set()

        entries = []
        for label in labels:
            tk.Label(top, text=label).pack(padx=10, pady=(10, 0))
            e = tk.Entry(top)
            e.pack(padx=10, pady=(0, 10))
            entries.append(e)

        result = []

        def on_confirm():
            for e in entries:
                val = e.get()
                if max_fin is not None and val.isdigit():
                    if not (0 <= int(val) <= max_fin):
                        messagebox.showerror("Error", f"Please enter a number between 0 and {max_fin}")
                        return
                result.append(val)
            top.destroy()

        def on_cancel():
            result.clear()
            top.destroy()

        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Confirm", command=on_confirm).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="left", padx=5)

        if not df.empty and keep:
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

            self.show_dataframe(tree, df[keep])

        self.root.wait_window(top)
        return result

    def show_dataframe(self, tree, dataframe):
        tree["columns"] = list(dataframe.columns)
        tree["show"] = "headings"

        for col in dataframe.columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")

        for _, row in dataframe.iterrows():
            tree.insert("", "end", values=list(row))

    def ask_car_part_contracts(self, human_teams_df, car_parts_df, year) -> dict:
        result = {}
        for _, team in human_teams_df.iterrows():
            result[team["teamID"]] = {}
            for part_type, label in [("e", "Engine"), ("c", "Chassi"), ("p", "Tyre")]:
                parts = car_parts_df[
                    (car_parts_df["partType"] == part_type) & (car_parts_df["year"] == year)
                    ].copy()
                parts = parts.rename(columns={"cost": "Cost"})
                keep = ["manufacturerID", "Cost"]
                labels = [
                    f"Team: {team['teamName']} | Component: {label} | Budget: {team['money']}\nEnter index (0–{len(parts) - 1}):",
                    "Contract length (0–4):",
                ]
                entry = self._open_selection_dialog(parts, keep, labels)
                if len(entry) == 2:
                    try:
                        d, l = map(int, entry)
                        manufacturer_id = parts.iloc[d]["manufacturerID"]
                        result[team["teamID"]][part_type] = (manufacturer_id, l)
                    except Exception:
                        result[team["teamID"]][part_type] = None
                else:
                    result[team["teamID"]][part_type] = None
        return result
