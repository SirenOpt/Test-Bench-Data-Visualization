import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

from file_io import load_data_folder, clear_all_data
from analysis import compute_pvalue_tables, compute_variance_tables
from plotting import plot_parameter
from config_utils import load_last_path, save_last_path


class DataPlotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Visualization")
        self.root.geometry("1250x750")

        # Data containers
        self.current_path = tk.StringVar(value=load_last_path())
        self.dataframes, self.file_names, self.groups = [], [], []
        self.original_groups, self.group_tags, self.group_folders = [], [], []

        self.create_widgets()

    # ---------- GUI ----------
    def create_widgets(self):
        path_frame = ttk.LabelFrame(self.root, text="Base Folder (optional)")
        path_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(path_frame, text="Default Folder:").pack(side="left", padx=5)
        ttk.Entry(path_frame, textvariable=self.current_path, width=60).pack(side="left", padx=5)
        ttk.Button(path_frame, text="Browse", command=self.select_folder).pack(side="left", padx=5)

        data_frame = ttk.LabelFrame(self.root, text="Data Sets")
        data_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(data_frame, text="Add Data Set (Folder)", command=self.add_data_set).pack(side="left", padx=5)
        ttk.Button(data_frame, text="Clear All Data", command=self.clear_all_data_gui).pack(side="left", padx=5)

        table_frame = ttk.LabelFrame(self.root, text="Loaded Files / Groups")
        table_frame.pack(fill="both", expand=False, padx=15, pady=5)
        columns = ("filename", "group", "tag", "folder")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for c, t, w, a in [
            ("filename", "File Name", 350, "w"),
            ("group", "Group #", 80, "center"),
            ("tag", "Group Tag", 150, "w"),
            ("folder", "Folder", 200, "w"),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=a)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        param_frame = ttk.LabelFrame(self.root, text="Parameter and Group Controls")
        param_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(param_frame, text="Order Parameter:").pack(side="left", padx=5)
        self.selected_param = tk.StringVar()
        self.param_combo = ttk.Combobox(param_frame, textvariable=self.selected_param, state="readonly", width=40)
        self.param_combo.pack(side="left", padx=5)
        ttk.Button(param_frame, text="Plot Parameter", command=self.plot_parameter_gui).pack(side="left", padx=5)
        ttk.Button(param_frame, text="Reset Tags", command=self.reset_tags).pack(side="left", padx=15)
        ttk.Button(param_frame, text="Reset Group #s", command=self.reset_groups).pack(side="left", padx=5)

        self.figure = plt.Figure(figsize=(9, 4.5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(10, 10))

    # ---------- GUI actions ----------
    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.current_path.get(), title="Select Folder")
        if folder:
            self.current_path.set(folder)
            save_last_path(folder)

    def add_data_set(self):
        result = load_data_folder(self.root, self.current_path.get(), len(set(self.groups)) + 1)
        if result:
            dfs, fnames, groups, tags, folders = result
            self.dataframes += dfs
            self.file_names += fnames
            self.groups += groups
            self.original_groups += groups
            self.group_tags += tags
            self.group_folders += folders
            self.update_parameters_from_dataframes()
            self.populate_table()

    def clear_all_data_gui(self):
        clear_all_data(self)
        for r in self.tree.get_children():
            self.tree.delete(r)
        self.param_combo["values"] = []
        self.selected_param.set("")

    def update_parameters_from_dataframes(self):
        params = set()
        for df in self.dataframes:
            params.update(df["Order Parameter"].dropna().tolist())
        self.param_combo["values"] = sorted(params)

    def populate_table(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for fname, grp, tag, folder in zip(self.file_names, self.groups, self.group_tags, self.group_folders):
            self.tree.insert("", "end", values=(fname, grp, tag, folder))

    def on_tree_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row_id:
            return
        col_index = int(col.replace("#", "")) - 1
        children = list(self.tree.get_children())
        row_idx = children.index(row_id)
        if col_index == 1:
            combo = ttk.Combobox(self.tree, values=list(range(1, max(self.groups) + 1)), state="readonly")
            x, y, w, h = self.tree.bbox(row_id, col)
            combo.place(x=x, y=y, width=w, height=h)
            combo.set(self.groups[row_idx])

            def save_change(event=None):
                try:
                    self.groups[row_idx] = int(combo.get())
                except Exception:
                    pass
                combo.destroy()
                self.populate_table()

            combo.bind("<<ComboboxSelected>>", save_change)
            combo.focus_set()
        elif col_index == 2:
            entry = ttk.Entry(self.tree)
            x, y, w, h = self.tree.bbox(row_id, col)
            entry.place(x=x, y=y, width=w, height=h)
            entry.insert(0, self.group_tags[row_idx])

            def save_change(event=None):
                new_tag = entry.get().strip() or str(self.groups[row_idx])
                grp = self.groups[row_idx]
                for i, g in enumerate(self.groups):
                    if g == grp:
                        self.group_tags[i] = new_tag
                entry.destroy()
                self.populate_table()

            entry.bind("<Return>", save_change)
            entry.bind("<FocusOut>", save_change)
            entry.focus_set()

    def reset_tags(self):
        for i, g in enumerate(self.groups):
            self.group_tags[i] = str(g)
        self.populate_table()

    def reset_groups(self):
        if not self.original_groups:
            return
        self.groups = self.original_groups.copy()
        self.populate_table()

    def plot_parameter_gui(self):
        param = self.selected_param.get()
        if not param:
            messagebox.showwarning("No Selection", "Select an order parameter.")
            return

        plot_parameter(self.figure, self.dataframes, self.groups, self.group_tags, param)
        self.canvas.draw()
        self.open_tables_popout()

    def open_tables_popout(self):
        p_tables = compute_pvalue_tables(self.dataframes, self.groups, self.group_tags)
        v_tables = compute_variance_tables(self.dataframes, self.groups, self.group_tags)

        popup = tk.Toplevel(self.root)
        popup.title("Analysis Tables")
        popup.geometry("900x300")

        nb = ttk.Notebook(popup)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------- UPDATED TABLE STYLE ----------
        def add_table(parent_nb, tables_dict, tab_label):
            frame = tk.Frame(parent_nb)
            parent_nb.add(frame, text=tab_label)
            inner_nb = ttk.Notebook(frame)
            inner_nb.pack(fill="both", expand=True, padx=10, pady=10)
            if not tables_dict:
                info_tab = tk.Frame(inner_nb)
                tk.Label(info_tab, text="No data available").pack(padx=10, pady=10)
                inner_nb.add(info_tab, text="Info")
                return

            for label, df in tables_dict.items():
                tab = tk.Frame(inner_nb, bg="white")
                cols = list(df.columns)

                # Header
                for cidx, c in enumerate(cols):
                    tk.Label(
                        tab,
                        text=c,
                        bg="#e8e8e8",
                        font=("Segoe UI", 9, "bold"),
                        padx=6,
                        pady=3,
                    ).grid(row=0, column=cidx, sticky="nsew", padx=1, pady=1)

                # Rows
                for ridx, (_, row) in enumerate(df.iterrows(), start=1):
                    for cidx, c in enumerate(cols):
                        v = row.get(c, "")
                        bg = "white"
                        try:
                            val = float(v)
                            if "p" in tab_label.lower():
                                if val <= 0.05:
                                    bg = "#b3ffb3"
                                elif val <= 0.1:
                                    bg = "#ffd699"
                                elif val > 0.1:
                                    bg = "#ff9999"
                            elif "var" in tab_label.lower():
                                if val < 5:
                                    bg = "#b3ffb3"
                                elif val <= 10:
                                    bg = "#ffd699"
                                elif val > 10:
                                    bg = "#ff9999"
                        except Exception:
                            pass

                        tk.Label(
                            tab,
                            text=str(v),
                            bg=bg,
                            padx=6,
                            pady=2,
                            anchor="center",
                        ).grid(row=ridx, column=cidx, sticky="nsew", padx=1, pady=1)

                inner_nb.add(tab, text=label)
        # ---------- END UPDATED TABLE STYLE ----------

        add_table(nb, p_tables, "P-Values")
        add_table(nb, v_tables, "Variance")


