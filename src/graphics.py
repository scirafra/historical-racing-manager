import tkinter as tk
from tkinter import ttk, messagebox


class Graphics:
    def __init__(self, controller):
        self.controller = controller
        self.root = tk.Tk()
        self.root.title("Historical Racing Manager")
        self.root.geometry("1600x900")

        self.name_var = tk.StringVar()
        self.series_var = tk.StringVar()
        self.season_var = tk.StringVar()

        self.setup_menu()
        self.setup_controls()
        self.setup_table()

    def setup_menu(self):
        menu_frame = tk.Frame(self.root)
        menu_frame.pack(pady=10)

        tk.Label(menu_frame, text="Historical Racing Manager:").grid(row=0, column=0, padx=5)
        tk.Entry(menu_frame, textvariable=self.name_var).grid(row=0, column=1, padx=5)

        tk.Button(menu_frame, text="New Game", command=self.on_new_game).grid(
            row=0, column=2, padx=5
        )
        tk.Button(menu_frame, text="Save Game", command=self.on_save_game).grid(
            row=0, column=3, padx=5
        )
        tk.Button(menu_frame, text="Load Game", command=self.on_load_game).grid(
            row=0, column=4, padx=5
        )
        tk.Button(menu_frame, text="End", command=self.root.quit).grid(row=0, column=5, padx=5)

        self.date_label = tk.Label(menu_frame, text="", font=("Arial", 14))
        self.date_label.grid(row=0, column=6, padx=10)

    def setup_controls(self):
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        self.cmb_series = ttk.Combobox(
            control_frame, textvariable=self.series_var, state="readonly"
        )
        self.cmb_series.grid(row=0, column=0, padx=5)
        self.cmb_series.bind("<<ComboboxSelected>>", self.on_series_change)

        self.cmb_season = ttk.Combobox(
            control_frame, textvariable=self.season_var, state="readonly"
        )
        self.cmb_season.grid(row=0, column=1, padx=5)

        tk.Button(control_frame, text="Show", command=self.show_results).grid(
            row=0, column=2, padx=5
        )
        tk.Button(control_frame, text="Next Day", command=lambda: self.sim_step(360)).grid(
            row=0, column=3, padx=5
        )
        tk.Button(control_frame, text="Next Week", command=lambda: self.sim_step(45000)).grid(
            row=0, column=4, padx=5
        )

    def setup_table(self):
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

    def run(self):
        self.root.mainloop()

    # ---- Callbacks ----
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

    def ask_finance_investments(self, human_teams_df):
        """
        Displays a dialog for each human-controlled team to ask for the number of finance employees.
        human_teams_df: DataFrame with at least the columns ['teamID', 'teamName', 'money']
        Return: dict {teamID: number_of_finance_employees}
        """

        investments = {}

        for _, row in human_teams_df.iterrows():
            max_fin = row["money"] // 2500
            if max_fin <= 0:
                continue

            top = tk.Toplevel(self.root)
            top.transient(self.root)
            top.grab_set()

            tk.Label(
                top,
                text=f"Tím: {row['teamName']}\nDostupné financie: {row['money']}\n"
                     f"Zadaj počet finančných zamestnancov (0–{max_fin}):",
            ).pack(padx=10, pady=(10, 0))

            entry = tk.Entry(top)
            entry.pack(padx=10, pady=(0, 10))

            result = {"value": None}

            def on_done():
                val = entry.get()
                if val.isdigit():
                    val = int(val)
                    if 0 <= val <= max_fin:
                        result["value"] = val
                        top.destroy()
                        return
                messagebox.showerror("Chyba", f"Zadaj číslo medzi 0 a {max_fin}")

            def on_cancel():
                result["value"] = 0
                top.destroy()

            btn_frame = tk.Frame(top)
            btn_frame.pack(pady=10)
            tk.Button(btn_frame, text="Potvrdiť", command=on_done).pack(side="left", padx=5)
            tk.Button(btn_frame, text="Zrušiť", command=on_cancel).pack(side="left", padx=5)

            self.root.wait_window(top)

            if result["value"] is not None:
                investments[row["teamID"]] = result["value"]

        return investments
