from tkinter import ttk, messagebox
from typing import Optional

import customtkinter as ctk
import pandas as pd

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class Graphics:
    def __init__(self, controller):
        self.controller = controller
        self.root = ctk.CTk()
        self.root.title("Historical Racing Manager")
        self.root.geometry("1600x900")

        self.name_var = ctk.StringVar()
        self.var_1 = ctk.StringVar()
        self.var_2 = ctk.StringVar()
        self.selected_team = ctk.StringVar()

        # self._setup_menu()
        self._setup_team_selector()
        self._setup_controls()
        self._setup_tabview()

    def _setup_team_selector(self):
        """Horný riadok s prepinátkom tímov (Team Selector)."""
        frame = ctk.CTkFrame(self.root)
        frame.pack(pady=(10, 0), fill="x")

        ctk.CTkLabel(frame, text="Select Team:", font=("Arial", 14, "bold")).pack(side="left", padx=10)

        self.team_selector = ctk.CTkComboBox(
            frame,
            variable=self.selected_team,
            state="readonly",
            width=250,
            command=self.on_team_change
        )
        self.team_selector.pack(side="left", padx=10)
        self._update_team_selector()

    def _update_team_selector(self):
        try:
            team_display = self.controller.get_team_selector_values()  # <- controller vráti ["Ferrari (ID 1)", "McLaren (ID 2)"]
            self.team_selector.configure(values=team_display)
            if team_display:
                self.team_selector.set(team_display[0])
        except Exception as e:
            print(f" Failed to update team selector: {e}")
            self.team_selector.configure(values=["No teams loaded"])
            self.team_selector.set("No teams loaded")


        except Exception as e:
            print(f" Failed to update team selector: {e}")
            self.team_selector.configure(values=["No teams loaded"])
            self.team_selector.set("No teams loaded")

    def refresh_myteam_tab(self):
        """Reloads the My Team tab content according to the active team."""
        try:
            if not hasattr(self, "tab_myteam"):
                return  # tab ešte neexistuje

            # Vyčisti obsah tabu (ponecháme rámec)
            for widget in self.tab_myteam.winfo_children():
                widget.destroy()

            # Znova vytvor GUI pre aktuálny tím
            self._create_myteam(self.tab_myteam)

        except Exception as e:
            print(f" My Team tab refresh failed: {e}")

    def on_team_change(self, value):
        try:
            self.controller.set_active_team(value.split(" (")[0])
            team_info = self.controller.get_active_team_info()  # <- controller vráti {"name": ..., "budget": ...}

            self.myteam_name_label.configure(text=team_info["name"])
            self.myteam_budget_label.configure(text=f"Total Budget: {team_info['budget']:,} €")

            self.refresh_myteam_tab()

        except Exception as e:
            print(f" Failed to change team: {e}")

    # Theme
    def change_theme(self, mode: str):
        try:
            ctk.set_appearance_mode(mode)
        except Exception as e:
            messagebox.showerror("Theme Error", f"Could not change theme: {e}")

    # UI setup
    def _setup_menu(self):
        menu = ctk.CTkFrame(self.root)
        menu.pack(pady=10, fill="x")

        # sem už len možno logo alebo nič
        ctk.CTkLabel(menu, text="Historical Racing Manager", font=("Arial", 16)).pack(side="left", padx=10)

    def _setup_controls(self):
        controls = ctk.CTkFrame(self.root)
        controls.pack(pady=10, fill="x")

        self.cmb_1 = ctk.CTkComboBox(controls, variable=self.var_1, state="readonly")
        self.cmb_1.grid(row=0, column=0, padx=5)
        self.cmb_1.bind("<<ComboboxSelected>>", self.on_series_change)

        self.cmb_2 = ctk.CTkComboBox(controls, variable=self.var_2, state="readonly")
        self.cmb_2.grid(row=0, column=1, padx=5)

        self._create_button(controls, "Show Results", self.show_results, 2)
        self._create_button(controls, "Next Day", lambda: self.sim_step(40000), 3)
        self._create_button(controls, "Next Week", lambda: self.sim_step(7), 4)
        self._create_button(controls, "Next Year", lambda: self.sim_step(1500), 5)

        self.date_label = ctk.CTkLabel(controls, text="", font=("Arial", 14))
        self.date_label.grid(row=0, column=9, padx=10, sticky="e")

    def _setup_tabview(self):
        self.tabview = ctk.CTkTabview(self.root, command=self.on_tab_change)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        tabs = ["Game", "Drivers", "Teams", "Manufacturers", "Series", "Seasons", "My Team"]
        self.trees = {}

        for name in tabs:
            if name == "Game":
                game_tab = self.tabview.add("Game")
                self._create_game_tab(game_tab)

            elif name == "My Team":
                myteam_tab = self.tabview.add("My Team")
                self._create_myteam(myteam_tab)
                self.tab_myteam = myteam_tab

            else:
                tab = self.tabview.add(name)
                self.trees[name] = self._create_tree_in_tab(tab)

        # Odkazy na ostatné tabuľky
        self.tab_drivers = self.trees["Drivers"]
        self.tab_teams = self.trees["Teams"]
        self.tab_manufacturers = self.trees["Manufacturers"]
        self.tab_series = self.trees["Series"]
        self.tab_results = self.trees["Seasons"]

        # Ovládacie tlačidlá pre My Team – presunuté úplne dole
        team_controls = ctk.CTkFrame(self.tab_myteam)
        team_controls.pack(pady=(5, 10), fill="x")

        ctk.CTkButton(team_controls, text="Offer Contract", command=self.offer_contract).pack(side="left", padx=5,
                                                                                              pady=5)
        ctk.CTkButton(team_controls, text="Terminate Contract", command=self.terminate_contract).pack(side="left",
                                                                                                      padx=5, pady=5)
        ctk.CTkButton(team_controls, text="Build Own Part", command=self.create_own_part).pack(side="left", padx=5,
                                                                                               pady=5)
        ctk.CTkButton(team_controls, text="Invest in Marketing", command=self.invest_in_marketing).pack(side="left",
                                                                                                        padx=5, pady=5)

    def _create_myteam(self, parent):
        try:
            data = self.controller.get_myteam_tab_data()

            # HEADER
            header = ctk.CTkFrame(parent)
            header.pack(fill="x", padx=10, pady=(5, 10))

            self.myteam_name_label = ctk.CTkLabel(header, text=data["team_name"], font=("Arial", 18, "bold"))
            self.myteam_name_label.pack(side="left", padx=10)

            formatted_budget = f"€{data['budget']:,.0f}".replace(",", " ")
            self.myteam_budget_label = ctk.CTkLabel(header, text=f"Total Budget: {formatted_budget}",
                                                    font=("Arial", 14))
            self.myteam_budget_label.pack(side="right", padx=10)

            # MAIN SECTION – DRIVERS a COMPONENTS POD SEBOU
            main_frame = ctk.CTkFrame(parent)
            main_frame.pack(fill="both", expand=False, padx=10, pady=(0, 5))

            main_frame.columnconfigure(0, weight=1)

            # DRIVERS (hore)
            drivers_frame = ctk.CTkFrame(main_frame)
            drivers_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(drivers_frame, text="Drivers", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)

            tree_drivers = ttk.Treeview(drivers_frame, show="headings", height=6)
            tree_drivers.pack(fill="x", padx=5, pady=5)
            self._populate_treeview(tree_drivers, data["drivers"])

            # COMPONENTS (dole)
            components_frame = ctk.CTkFrame(main_frame)
            components_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(components_frame, text="Components", font=("Arial", 14, "bold")).pack(anchor="w", padx=5,
                                                                                               pady=5)

            tree_parts = ttk.Treeview(components_frame, show="headings", height=6)
            tree_parts.pack(fill="x", padx=5, pady=5)
            self._populate_treeview(tree_parts, data["components"])

            # STAFF + RACES
            info_frame = ctk.CTkFrame(parent)
            info_frame.pack(fill="x", padx=10, pady=(0, 5))
            info_frame.columnconfigure(0, weight=1)
            info_frame.columnconfigure(1, weight=1)

            # STAFF
            left_info = ctk.CTkFrame(info_frame)
            left_info.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(left_info, text="Staff", font=("Arial", 13, "bold")).pack(anchor="w", padx=5, pady=5)
            tree_staff = ttk.Treeview(left_info, show="headings", height=4)
            tree_staff.pack(fill="x", padx=5, pady=5)
            self._populate_treeview(tree_staff, data["staff"])

            # RACES
            right_info = ctk.CTkFrame(info_frame)
            right_info.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(right_info, text="Upcoming Races", font=("Arial", 13, "bold")).pack(anchor="w", padx=5, pady=5)
            tree_races = ttk.Treeview(right_info, show="headings", height=4)
            tree_races.pack(fill="x", padx=5, pady=5)
            self._populate_treeview(tree_races, data["races"])

        except Exception as e:
            print(f"️ Failed to build My Team tab: {e}")

    def on_tab_change(self, event=None):
        current_tab = self.tabview.get()

        # Ak ide o tab My Team → refresh
        if current_tab == "My Team":
            self.refresh_myteam_tab()

        # Štandardné správanie (aktualizácia comboboxov a výsledkov)
        try:
            self.update_dropdown()
            self.show_results()
        except Exception as e:
            print(f"Tab change error: {e}")

    def _create_game_tab(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Game Name:").grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkEntry(frame, textvariable=self.name_var).grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkButton(frame, text="New Game", command=self.on_new_game).grid(row=1, column=0, padx=5, pady=5)
        ctk.CTkButton(frame, text="Save Game", command=self.on_save_game).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkButton(frame, text="Load Game", command=self.on_load_game).grid(row=2, column=0, padx=5, pady=5)
        ctk.CTkButton(frame, text="Exit", command=self.root.quit).grid(row=2, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame, text="Theme:").grid(row=3, column=0, padx=5, pady=5)
        self.theme_option = ctk.CTkOptionMenu(
            frame,
            values=["Light", "Dark"],
            command=self.change_theme
        )
        self.theme_option.grid(row=3, column=1, padx=5, pady=5)
        self.theme_option.set("System")

    def _create_tree_in_tab(self, tab):
        tree = ttk.Treeview(tab, show="headings")
        vsb = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tab, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=1)
        return tree

    def _create_button(self, parent, text, command, column):
        ctk.CTkButton(parent, text=text, command=command).grid(row=0, column=column, padx=5)

    # Main loop
    def run(self):
        try:
            self.update_dropdown()
        except Exception:
            pass
        self.root.mainloop()

    # --- Game management ---
    def on_new_game(self):
        try:
            ok = self.controller.load_game("my_data")
            if ok:
                self.date_label.configure(text=self.controller.get_date())
                self._update_team_selector()
                self.refresh_myteam_tab()
                messagebox.showinfo("New Game", "New game has been started successfully.")
            else:
                messagebox.showwarning("Error", "Failed to start a new game.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start new game: {e}")

    def on_save_game(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Please enter a name to save the game.")
            return
        if name in ("my_data", "original", "custom_original"):
            messagebox.showwarning("Invalid Name", "Please use a different game name.")
            return
        try:
            msg = self.controller.save_game(name)
            messagebox.showinfo("Saved", msg)
        except Exception as e:
            messagebox.showerror("Error", f"Saving failed: {e}")

    def on_load_game(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Please enter a name to load the game.")
            return
        try:
            ok = self.controller.load_game(name)
            if ok:
                self.date_label.configure(text=self.controller.get_date())
                self._update_team_selector()
                self.refresh_myteam_tab()
                messagebox.showinfo("Loaded", f"Game '{name}' has been loaded successfully.")
            else:
                messagebox.showwarning("Not Found", "Game not found or missing files.")
        except Exception as e:
            messagebox.showerror("Error", f"Loading failed: {e}")

    # --- Simulation ---
    def on_series_change(self, event=None):
        try:
            self.controller.update_seasons(self.var_1.get())
            seasons = self.controller.get_season_list()
            self.cmb_2.configure(values=seasons)
            if seasons:
                self.cmb_2.set(seasons[-1])
        except Exception:
            pass

    def on_subject_change(self, list_2: list):
        try:

            self.cmb_2.configure(values=list_2)
            self.cmb_2.set(list_2[-1])
        except Exception:
            pass

    def sim_step(self, days: int):
        try:
            self.controller.simulate_days(days)
            self.date_label.configure(text=self.controller.get_date())
            self.update_dropdown()
            self.show_results()

            # Obnov aj My Team tab (ak existuje)
            if hasattr(self, "tab_myteam"):
                self.refresh_myteam_tab()

        except Exception as e:
            messagebox.showerror("Simulation Error", str(e))

    def update_dropdown(self):
        try:
            current_tab = self.tabview.get()

            # teraz podľa tabu nastavíš správny combobox
            if current_tab == "Seasons":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                self.cmb_1.set(items[0])
                self.on_series_change()

            elif current_tab == "Drivers":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                self.cmb_1.set(items[0])
                self.on_subject_change([""])

            elif current_tab == "Teams":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                self.cmb_1.set(items[0])
                self.on_subject_change([""])

            elif current_tab == "Manufacturers":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                self.cmb_1.set(items[0])
                self.on_subject_change(["engine", "chassi", "pneu"])

            elif current_tab == "Series":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                self.cmb_1.set(items[0])
                self.on_subject_change([""])

        except Exception as e:
            print(f"update_dropdown error: {e}")

    def show_results(self):
        try:
            current_tab = self.tabview.get()
            if current_tab == "Seasons":
                df = self.controller.get_results(self.var_1.get(), self.var_2.get())
                self._populate_treeview(self.tab_results, df)
            elif current_tab == "Manufacturers":

                df = self.controller.get_stats(self.var_1.get(), current_tab, self.var_2.get())
                self._populate_treeview(self.tab_manufacturers, df)
            elif current_tab == "Teams":

                df = self.controller.get_stats(self.var_1.get(), current_tab, "")
                self._populate_treeview(self.tab_teams, df)
            elif current_tab == "Drivers":

                df = self.controller.get_stats(self.var_1.get(), current_tab, "")
                self._populate_treeview(self.tab_drivers, df)
            elif current_tab == "Series":

                df = self.controller.get_stats(self.var_1.get(), current_tab, "")
                self._populate_treeview(self.tab_series, df)
        except Exception as e:
            messagebox.showerror("Error", f"Could not get results: {e}")

    # --- My Team actions ---
    def offer_contract(self):
        try:
            team = self.controller.get_active_team()
            if not team:
                messagebox.showwarning("No Team Selected", "Please select a team first.")
                return

            confirm = messagebox.askyesno("Offer Contract", f"Do you want to offer a new contract for team {team}?")
            if confirm:
                result = self.controller.offer_contract_to_driver()  # Controller rieši všetko
                messagebox.showinfo("Contract Offered", result)
                self.refresh_myteam_tab()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to offer contract: {e}")

    def terminate_contract(self):
        try:
            team = self.controller.get_active_team()
            if not team:
                messagebox.showwarning("No Team Selected", "Please select a team first.")
                return

            confirm = messagebox.askyesno("Terminate Contract", f"Do you want to terminate a contract in {team}?")
            if confirm:
                result = self.controller.terminate_driver_contract()
                messagebox.showinfo("Contract Terminated", result)
                self.refresh_myteam_tab()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to terminate contract: {e}")

    def create_own_part(self):
        try:
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Create Own Part")
            dialog.geometry("400x200")

            ctk.CTkLabel(dialog, text="Part Type:").pack(pady=5)
            part_type_var = ctk.StringVar()
            ctk.CTkComboBox(dialog, variable=part_type_var, values=["engine", "chassi", "pneu"]).pack(pady=5)

            ctk.CTkLabel(dialog, text="Development Cost (€):").pack(pady=5)
            cost_var = ctk.StringVar()
            ctk.CTkEntry(dialog, textvariable=cost_var).pack(pady=5)

            def confirm():
                try:
                    part_type = part_type_var.get()
                    cost = int(cost_var.get())
                    msg = self.controller.create_own_part(part_type, cost)
                    messagebox.showinfo("Success", msg)
                    dialog.destroy()
                    self.refresh_myteam_tab()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to create part: {e}")

            ctk.CTkButton(dialog, text="Confirm", command=confirm).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open dialog: {e}")

    def invest_in_marketing(self):
        try:
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Invest in Marketing")
            dialog.geometry("350x180")

            ctk.CTkLabel(dialog, text="Enter investment amount (€):").pack(pady=5)
            amount_var = ctk.StringVar()
            ctk.CTkEntry(dialog, textvariable=amount_var).pack(pady=5)

            def confirm():
                try:
                    amount = int(amount_var.get())
                    msg = self.controller.invest_in_marketing(amount)
                    messagebox.showinfo("Investment", msg)
                    dialog.destroy()
                    self.refresh_myteam_tab()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to invest: {e}")

            ctk.CTkButton(dialog, text="Confirm", command=confirm).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open dialog: {e}")

    # --- Utility ---
    def _populate_treeview(self, tree: ttk.Treeview, dataframe: Optional[pd.DataFrame]):
        try:
            tree.delete(*tree.get_children())
            if dataframe is None or dataframe.empty:
                tree["columns"] = ["info"]
                tree.heading("info", text="Info")
                tree.column("info", width=600, anchor="center")
                tree.insert("", "end", values=("No data",))
                return

            df = dataframe.copy()
            cols = [str(c) for c in df.columns]
            tree["columns"] = cols
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=120, anchor="center")

            for row in df.itertuples(index=False):
                vals = []
                for v in row:
                    if pd.isna(v):
                        vals.append("")
                    else:
                        vals.append(v)
                tree.insert("", "end", values=vals)
        except Exception as e:
            messagebox.showerror("Error", f"Could not populate view: {e}")
