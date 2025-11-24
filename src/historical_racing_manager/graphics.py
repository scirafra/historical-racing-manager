from tkinter import ttk, messagebox
from typing import Optional

import customtkinter as ctk
import pandas as pd

from historical_racing_manager.consts import (
    WINDOW_TITLE, WINDOW_SIZE, DEFAULT_THEME, DEFAULT_COLOR_THEME,
    TAB_NAMES, TEAM_SELECTOR_WIDTH, SIMULATION_STEPS, CONTRACT_MIN_LENGTH,
    CONTRACT_MAX_LENGTH, DEFAULT_SALARY, CONTRACT_YEARS,
    PART_TYPES, COLUMN_LABELS
)

ctk.set_appearance_mode(DEFAULT_THEME)
ctk.set_default_color_theme(DEFAULT_COLOR_THEME)


class Graphics:
    def __init__(self, controller):
        self.controller = controller
        self.root = ctk.CTk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)

        self.name_var = ctk.StringVar()
        self.var_1 = ctk.StringVar()
        self.var_2 = ctk.StringVar()
        self.selected_team = ctk.StringVar()

        # Optional top menu (logo or nothing)
        # self._setup_menu()
        self._setup_team_selector()
        self._setup_controls()
        self._setup_tabview()

    def _setup_team_selector(self):
        """Top row with the team selection combobox."""
        frame = ctk.CTkFrame(self.root)
        frame.pack(pady=(10, 0), fill="x")

        ctk.CTkLabel(frame, text="Select Team:", font=("Arial", 14, "bold")).pack(side="left", padx=10)

        self.team_selector = ctk.CTkComboBox(
            frame,
            variable=self.selected_team,
            state="readonly",
            width=TEAM_SELECTOR_WIDTH,
            command=self.on_team_change
        )
        self.team_selector.pack(side="left", padx=10)
        self._update_team_selector()

    def _update_team_selector(self):
        """Refresh values of the team selector combobox."""
        try:
            # Example format: ["Ferrari (Owner 1)", "McLaren (Owner 2)"]
            team_display = self.controller.get_team_selector_values()
            self.team_selector.configure(values=team_display)
            if team_display:
                self.team_selector.set(team_display[0])
        except Exception as e:
            print(f" Failed to update team selector: {e}")
            self.team_selector.configure(values=["No teams loaded"])
            self.team_selector.set("No teams loaded")

    def refresh_myteam_tab(self):
        """Reload the My Team tab content according to the active team."""
        try:
            if not hasattr(self, "tab_myteam"):
                return  # Tab doesn’t exist yet

            # Clear the tab content (keep the container frame)
            for widget in self.tab_myteam.winfo_children():
                widget.destroy()

            # Rebuild GUI for the current team
            self._create_myteam(self.tab_myteam)

        except Exception as e:
            print(f" My Team tab refresh failed: {e}")

    def on_team_change(self, value):
        """Handle team selection change and refresh the My Team tab."""
        try:
            self.controller.set_active_team(value.split(" (")[0])
            # Controller returns {"name": ..., "budget": ...}
            team_info = self.controller.get_active_team_info()

            self.myteam_name_label.configure(text=team_info["name"])
            self.myteam_budget_label.configure(text=f"Total Budget: {team_info['budget']:,} €")

            self.refresh_myteam_tab()

        except Exception as e:
            print(f" Failed to change team: {e}")

    # Theme
    def change_theme(self, mode: str):
        """Change application theme to Light or Dark."""
        try:
            ctk.set_appearance_mode(mode)
        except Exception as e:
            messagebox.showerror("Theme Error", f"Could not change theme: {e}")

    # UI setup
    def _setup_menu(self):
        """Optional top menu (currently unused)."""
        menu = ctk.CTkFrame(self.root)
        menu.pack(pady=10, fill="x")
        ctk.CTkLabel(menu, text="Historical Racing Manager", font=("Arial", 16)).pack(side="left", padx=10)

    def _setup_controls(self):
        """Top controls for selecting subject and season, plus simulation shortcuts."""
        controls = ctk.CTkFrame(self.root)
        controls.pack(pady=10, fill="x")

        self.cmb_1 = ctk.CTkComboBox(controls, variable=self.var_1, state="readonly")
        self.cmb_1.grid(row=0, column=0, padx=5)
        self.cmb_1.bind("<<ComboboxSelected>>", self.on_series_change)

        self.cmb_2 = ctk.CTkComboBox(controls, variable=self.var_2, state="readonly")
        self.cmb_2.grid(row=0, column=1, padx=5)

        self._create_button(controls, "Show Results", self.show_results, 2)

        # Simulation shortcuts
        for idx, (label, days) in enumerate(SIMULATION_STEPS.items(), start=3):
            self._create_button(controls, label, lambda d=days: self.sim_step(d), idx)

        self.date_label = ctk.CTkLabel(controls, text="", font=("Arial", 14))
        self.date_label.grid(row=0, column=9, padx=10, sticky="e")

    def _setup_tabview(self):
        """Create the tab view and initialize tabs."""
        self.tabview = ctk.CTkTabview(self.root, command=self.on_tab_change)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        tabs = TAB_NAMES
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

        # References to treeviews in other tabs
        self.tab_drivers = self.trees["Drivers"]
        self.tab_teams = self.trees["Teams"]
        self.tab_manufacturers = self.trees["Manufacturers"]
        self.tab_series = self.trees["Series"]
        self.tab_results = self.trees["Seasons"]

    def _create_myteam(self, parent):
        """Build the My Team tab layout with Drivers, Components, Staff, and Upcoming Races."""
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

            # MAIN SECTION – vertical: Drivers on top, Components below
            main_frame = ctk.CTkFrame(parent)
            main_frame.pack(fill="both", expand=False, padx=10, pady=(0, 5))
            main_frame.columnconfigure(0, weight=1)

            # DRIVERS (top)
            drivers_frame = ctk.CTkFrame(main_frame)
            drivers_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(drivers_frame, text="Drivers", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)

            tree_drivers = ttk.Treeview(drivers_frame, show="headings", height=6)
            tree_drivers.pack(fill="x", padx=5, pady=5)
            self._populate_treeview(tree_drivers, data["drivers"])

            # COMPONENTS (bottom)
            components_frame = ctk.CTkFrame(main_frame)
            components_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(components_frame, text="Components", font=("Arial", 14, "bold")).pack(anchor="w", padx=5,
                                                                                               pady=5)

            tree_parts = ttk.Treeview(components_frame, show="headings", height=6)
            tree_parts.pack(fill="x", padx=5, pady=5)
            self._populate_treeview(tree_parts, data["components"])

            # STAFF + RACES section
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

            # Controls for actions at the bottom of My Team
            # Attach to the current parent (not a stored tab reference) for clean refreshes
            team_controls = ctk.CTkFrame(parent)
            team_controls.pack(pady=(5, 10), fill="x")

            ctk.CTkButton(team_controls, text="Offer Driver Contract For This Year",
                          command=lambda: self.offer_contract(next_year=False)).pack(side="left", padx=5, pady=5)

            ctk.CTkButton(team_controls, text="Offer Driver Contract For Next Year",
                          command=lambda: self.offer_contract(next_year=True)).pack(side="left", padx=5, pady=5)

            ctk.CTkButton(team_controls, text="Offer Car Part Contract",
                          command=self.offer_car_part_contract).pack(side="left", padx=5, pady=5)

            ctk.CTkButton(team_controls, text="Terminate Contract",
                          command=self.terminate_contract).pack(side="left", padx=5, pady=5)

            # If your backend uses finance for this control, consider aligning the label
            ctk.CTkButton(team_controls, text="Invest in Marketing", command=self.invest_in_marketing).pack(
                side="left", padx=5, pady=5
            )

        except Exception as e:
            print(f"️ Failed to build My Team tab: {e}")

    def on_tab_change(self, event=None):
        """Handle tab change: refresh My Team tab and update dropdowns/results."""
        current_tab = self.tabview.get()

        # Refresh My Team on tab activation
        if current_tab == "My Team":
            self.refresh_myteam_tab()

        # Standard behavior: update selectors and results
        try:
            self.update_dropdown()
            self.show_results()
        except Exception as e:
            print(f"Tab change error: {e}")

    def _create_game_tab(self, parent):
        """Build the Game tab with save/load controls and theme switcher."""
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
        """Create a treeview with scrollbars inside a tab."""
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
        """Helper to create a button in a single row at a given column."""
        ctk.CTkButton(parent, text=text, command=command).grid(row=0, column=column, padx=5)

    # Main loop
    def run(self):
        """Start the GUI event loop."""
        try:
            self.update_dropdown()
        except Exception:
            pass
        self.root.mainloop()

    # --- Game management ---
    def on_new_game(self):
        """Initialize a new game from 'my_data' and refresh UI state."""
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
        """Save the current game using the provided name."""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Please enter a name to save the game.")
            return
        if name in ("my_data", "original", "custom_original"):
            messagebox.showwarning("Invalid Name", "Please use a different game name.")
            return
        try:
            # Controller returns None; show a consistent message
            self.controller.save_game(name)
            messagebox.showinfo("Saved", f"Game '{name}' has been saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Saving failed: {e}")

    def on_load_game(self):
        """Load a saved game and refresh the UI."""
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
        """Update season list when the series combobox changes."""
        try:
            self.controller.update_seasons(self.var_1.get())
            seasons = self.controller.get_season_list()
            self.cmb_2.configure(values=seasons)
            if seasons:
                self.cmb_2.set(seasons[-1])
        except Exception:
            pass

    def on_subject_change(self, list_2: list):
        """Update second-level combobox values for stats views."""
        try:
            self.cmb_2.configure(values=list_2)
            self.cmb_2.set(list_2[-1] if list_2 else "")
        except Exception:
            pass

    def sim_step(self, days: int):
        """Advance the simulation by a given number of days and refresh UI state."""
        try:
            self.controller.simulate_days(days)
            self.date_label.configure(text=self.controller.get_date())
            self.update_dropdown()
            self.show_results()

            # Refresh My Team tab if present
            if hasattr(self, "tab_myteam"):
                self.refresh_myteam_tab()

        except Exception as e:
            messagebox.showerror("Simulation Error", str(e))

    def update_dropdown(self):
        """Update top comboboxes according to the active tab."""
        try:
            current_tab = self.tabview.get()

            # Set the correct combobox values based on the active tab
            if current_tab == "Seasons":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                if items:
                    self.cmb_1.set(items[0])
                self.on_series_change()

            elif current_tab == "Drivers":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                if items:
                    self.cmb_1.set(items[0])
                self.on_subject_change([""])

            elif current_tab == "Teams":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                if items:
                    self.cmb_1.set(items[0])
                self.on_subject_change([""])

            elif current_tab == "Manufacturers":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                if items:
                    self.cmb_1.set(items[0])
                self.on_subject_change(["engine", "chassi", "pneu"])

            elif current_tab == "Series":
                items = self.controller.get_names(current_tab)
                self.cmb_1.configure(values=items)
                if items:
                    self.cmb_1.set(items[0])
                self.on_subject_change([""])

        except Exception as e:
            print(f"update_dropdown error: {e}")

    def show_results(self):
        """Populate the current tab’s treeview with results/statistics."""
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
    def offer_contract(self, next_year: bool):
        """Open a dialog to offer a driver contract for this or next year."""
        try:
            team = self.controller.get_active_team()
            if not team:
                messagebox.showwarning("No Team Selected", "Please select a team first.")
                return

            # Get available drivers from the controller
            df = self.controller.get_available_drivers_for_offer(next_year=next_year)
            if df.empty:
                messagebox.showinfo("No Available Drivers", "No drivers are currently available for contracts.")
                return

            # Dialog window
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Offer Contract to Driver")
            dialog.geometry("500x400")

            ctk.CTkLabel(dialog, text="Select Driver:", font=("Arial", 13, "bold")).pack(pady=5)
            driver_names = [f"{row.forename} {row.surname} ({row.nationality})" for _, row in df.iterrows()]
            driver_ids = list(df["driverID"])
            driver_var = ctk.StringVar()
            driver_box = ctk.CTkComboBox(dialog, variable=driver_var, values=driver_names, state="readonly", width=300)
            driver_box.pack(pady=5)
            if driver_names:
                driver_box.set(driver_names[0])

            ctk.CTkLabel(dialog, text="Salary Offer (€):").pack(pady=5)
            salary_var = ctk.StringVar(value=str(DEFAULT_SALARY))
            ctk.CTkEntry(dialog, textvariable=salary_var).pack(pady=5)

            ctk.CTkLabel(dialog, text="Contract Length (years):").pack(pady=5)
            length_var = ctk.IntVar(value=2)

            frame = ctk.CTkFrame(dialog)
            frame.pack(pady=5)

            def increase_length():
                if length_var.get() < CONTRACT_MAX_LENGTH:
                    length_var.set(length_var.get() + 1)

            def decrease_length():
                if length_var.get() > CONTRACT_MIN_LENGTH:
                    length_var.set(length_var.get() - 1)

            ctk.CTkButton(frame, text="-", command=decrease_length, width=30).pack(side="left", padx=5)
            ctk.CTkLabel(frame, textvariable=length_var, width=50).pack(side="left")
            ctk.CTkButton(frame, text="+", command=increase_length, width=30).pack(side="left", padx=5)

            def confirm_offer():
                """Confirm and submit the contract offer via controller."""
                try:
                    idx = driver_names.index(driver_var.get())
                    driver_id = driver_ids[idx]
                    salary = int(salary_var.get())
                    length = int(length_var.get())

                    success = self.controller.offer_driver_contract(driver_id, salary, length, next_year)
                    if success:
                        messagebox.showinfo("Success", "Contract offer created successfully.")
                        dialog.destroy()
                        self.refresh_myteam_tab()
                    else:
                        messagebox.showwarning("Failed", "Could not create contract offer.")
                except Exception as e:
                    messagebox.showerror("Error", f"Offer failed: {e}")

            ctk.CTkButton(dialog, text="Confirm Offer", command=confirm_offer).pack(pady=15)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to offer contract: {e}")

    def terminate_contract(self):
        """Open a dialog to terminate a driver contract."""
        try:
            team = self.controller.get_active_team()
            if not team:
                messagebox.showwarning("No Team Selected", "Please select a team first.")
                return

            df = self.controller.get_terminable_contracts_for_team()
            if df.empty:
                messagebox.showinfo("No Contracts", "No active contracts available for termination.")
                return

            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Terminate Driver Contract")
            dialog.geometry("500x400")

            ctk.CTkLabel(dialog, text="Select Driver to Terminate:", font=("Arial", 13, "bold")).pack(pady=5)
            driver_names = [
                f"{row.forename} {row.surname} ({row.nationality}) – Cost: €{row.termination_cost:,} – {'Current contract' if row.current else 'Future contract'}"
                for _, row in df.iterrows()
            ]

            driver_ids = list(df["driverID"])
            driver_var = ctk.StringVar()
            driver_box = ctk.CTkComboBox(dialog, variable=driver_var, values=driver_names, state="readonly", width=400)
            driver_box.pack(pady=5)
            if driver_names:
                driver_box.set(driver_names[0])

            def confirm_termination():
                """Confirm and submit the termination via controller."""
                try:
                    idx = driver_names.index(driver_var.get())
                    driver_id = driver_ids[idx]
                    row = df.iloc[idx]
                    result = self.controller.terminate_driver_contract_by_id(driver_id, row.termination_cost,
                                                                             row.current)

                    messagebox.showinfo("Contract Terminated", result)
                    dialog.destroy()
                    self.refresh_myteam_tab()
                except Exception as e:
                    messagebox.showerror("Error", f"Termination failed: {e}")

            ctk.CTkButton(dialog, text="Confirm Termination", command=confirm_termination).pack(pady=15)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to terminate contract: {e}")

    def offer_car_part_contract(self):
        """Open a dialog to offer a car part contract."""
        try:
            team = self.controller.get_active_team()
            if not team:
                messagebox.showwarning("No Team Selected", "Please select a team first.")
                return

            parts_df = self.controller.get_available_car_parts()
            if parts_df.empty:
                messagebox.showinfo("No Parts Available", "No car parts available for contract.")
                return

            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Offer Car Part Contract")
            dialog.geometry("500x400")

            ctk.CTkLabel(dialog, text="Select Part:", font=("Arial", 13, "bold")).pack(pady=5)

            part_names = [f"{row.manufacturer_name} ({row.partType}) – Cost: €{row.cost}" for _, row in
                          parts_df.iterrows()]
            part_ids = list(parts_df["partID"])

            part_var = ctk.StringVar()
            part_box = ctk.CTkComboBox(dialog, variable=part_var, values=part_names, state="readonly", width=300)
            part_box.pack(pady=5)
            if part_names:
                part_box.set(part_names[0])

            ctk.CTkLabel(dialog, text="Contract Length (years):").pack(pady=5)
            length_var = ctk.IntVar(value=2)
            frame = ctk.CTkFrame(dialog)
            frame.pack(pady=5)

            def increase_length():
                if length_var.get() < 4:
                    length_var.set(length_var.get() + 1)

            def decrease_length():
                if length_var.get() > 1:
                    length_var.set(length_var.get() - 1)

            ctk.CTkButton(frame, text="-", command=decrease_length, width=30).pack(side="left", padx=5)
            ctk.CTkLabel(frame, textvariable=length_var, width=50).pack(side="left")
            ctk.CTkButton(frame, text="+", command=increase_length, width=30).pack(side="left", padx=5)

            ctk.CTkLabel(dialog, text="Start Year:").pack(pady=5)
            year_var = ctk.StringVar(value="Current Year")
            year_box = ctk.CTkComboBox(dialog, variable=year_var, values=CONTRACT_YEARS, state="readonly", width=150)
            year_box.pack(pady=5)

            def confirm_offer():
                """Confirm and submit the part contract via controller."""
                try:
                    idx = part_names.index(part_var.get())
                    part_id = part_ids[idx]
                    length = int(length_var.get())

                    row = parts_df.iloc[idx]
                    price = int(row.cost)
                    manufacturer_id = int(row.manufacturerID)
                    part_type = row.partType
                    start_year = self.controller.get_year()
                    if year_var.get() == "Next Year":
                        start_year += 1

                    success = self.controller.offer_car_part_contract(manufacturer_id, length, price, start_year,
                                                                      part_type)

                    if success:
                        messagebox.showinfo("Success", "Car part contract offer created.")
                        dialog.destroy()
                        self.refresh_myteam_tab()
                    else:
                        messagebox.showwarning("Failed", "Could not create car part contract.")
                except Exception as e:
                    messagebox.showerror("Error", f"Offer failed: {e}")

            ctk.CTkButton(dialog, text="Confirm Offer", command=confirm_offer).pack(pady=15)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to offer car part contract: {e}")

    def create_own_part(self):
        """Open a dialog to define and confirm development of an own car part."""
        try:
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Create Own Part")
            dialog.geometry("400x200")

            ctk.CTkLabel(dialog, text="Part Type:").pack(pady=5)
            part_type_var = ctk.StringVar()
            ctk.CTkComboBox(dialog, variable=part_type_var, values=PART_TYPES)

            ctk.CTkLabel(dialog, text="Development Cost (€):").pack(pady=5)
            cost_var = ctk.StringVar()
            ctk.CTkEntry(dialog, textvariable=cost_var).pack(pady=5)

            def confirm():
                """Confirm and send development request to controller."""
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
        """Open a dialog to adjust marketing/finance staff with cost preview."""
        try:
            team = self.controller.get_active_team()
            if not team:
                messagebox.showwarning("No Team Selected", "Please select a team first.")
                return

            current, max_staff, hire_cost, fire_cost = self.controller.get_team_money_and_finance_employees()

            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Adjust Marketing Staff")
            dialog.geometry("400x250")

            ctk.CTkLabel(dialog, text=f"Current staff: {current}", font=("Arial", 13)).pack(pady=5)
            ctk.CTkLabel(dialog, text=f"Hire cost: €{hire_cost} / Fire cost: €{fire_cost}", font=("Arial", 12)).pack(
                pady=5)

            staff_var = ctk.IntVar(value=current)
            cost_var = ctk.StringVar()

            def update_cost(*_):
                """Compute and display the cost preview based on slider target."""
                target = staff_var.get()
                delta = target - current
                if delta > 0:
                    cost = delta * hire_cost
                    cost_var.set(f"Hiring {delta} → Cost: €{cost}")
                    return target, cost
                elif delta < 0:
                    cost = abs(delta) * fire_cost
                    cost_var.set(f"Firing {abs(delta)} → Cost: €{cost}")
                    return target, cost
                else:
                    cost_var.set("No change")
                    return current, 0

            ctk.CTkSlider(dialog, from_=0, to=max_staff, number_of_steps=max_staff, variable=staff_var,
                          command=update_cost).pack(pady=10)
            ctk.CTkLabel(dialog, textvariable=cost_var, font=("Arial", 12, "bold")).pack(pady=5)
            update_cost()

            def confirm():
                """Submit the staff adjustment via controller."""
                try:
                    new_employees, cost = update_cost()
                    msg = self.controller.adjust_marketing_staff(new_employees, cost)
                    messagebox.showinfo("Marketing Update", msg)
                    dialog.destroy()
                    self.refresh_myteam_tab()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update staff: {e}")

            ctk.CTkButton(dialog, text="Confirm", command=confirm).pack(pady=15)

        except Exception as e:
            messagebox.showerror("Error", f"Could not open dialog: {e}")

    # --- Utility ---
    def _populate_treeview(self, tree: ttk.Treeview, dataframe: Optional[pd.DataFrame]):
        """Populate a ttk.Treeview from a pandas DataFrame, with readable column labels."""
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

            # Ensure unique displayed labels (if duplicates occur)
            display_labels = {}
            used_labels = {}
            for col in cols:
                label = COLUMN_LABELS.get(col, col.replace("_", " ").title())
                if label in used_labels:
                    used_labels[label] += 1
                    label = f"{label} {used_labels[label]}"
                else:
                    used_labels[label] = 1
                display_labels[col] = label

            for col in cols:
                tree.heading(col, text=display_labels[col])
                tree.column(col, width=120, anchor="center")

            for row in df.itertuples(index=False):
                vals = ["" if pd.isna(v) else v for v in row]
                tree.insert("", "end", values=vals)

        except Exception as e:
            messagebox.showerror("Error", f"Could not populate view: {e}")
