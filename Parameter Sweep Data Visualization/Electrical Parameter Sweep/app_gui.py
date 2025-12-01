import tkinter as tk
import matplotlib.pyplot as plt
from tkinter import messagebox, filedialog, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
from scipy.stats import ttest_ind_from_stats
from file_io import load_last_path, load_data_folder_auto, save_last_path, clear_all_data

class DataPlotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Visualization - Heatmap")
        self.root.geometry("1400x800")

        # path
        self.current_path = tk.StringVar(value=load_last_path())

        # data lists
        self.dataframes = []
        self.file_names = []
        self.groups = []
        self.groups_freq = []
        self.power_values_per_file = []
        self.freq_values_per_file = []

        self.power_group_map = {}
        self.freq_group_map = {}

        self.group_tags = []
        self.group_folders = []

        # GUI
        self.create_widgets()
        self.update_folder_combo()  # initialize dropdowns

    def create_widgets(self):
        # Top folder selection
        path_frame = ttk.LabelFrame(self.root, text="Base Folder (optional)")
        path_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(path_frame, text="Default Folder:").pack(side="left", padx=5)
        ttk.Entry(path_frame, textvariable=self.current_path, width=60).pack(side="left", padx=5)
        ttk.Button(path_frame, text="Browse", command=self.select_folder).pack(side="left", padx=5)

        # Data set controls
        data_frame = ttk.LabelFrame(self.root, text="Data Sets")
        data_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(data_frame, text="Add Data Set", command=self.add_data_set).pack(side="left", padx=5)
        ttk.Button(data_frame, text="Clear All Data", command=self.clear_all_data_gui).pack(side="left", padx=5)

        # Table of loaded files
        table_frame = ttk.LabelFrame(self.root, text="Loaded Files / Groups")
        table_frame.pack(fill="both", expand=False, padx=15, pady=5)
        columns = ("filename", "group_power", "group_freq", "tag", "folder")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for c, t, w, a in [
            ("filename", "File Name", 350, "w"),
            ("group_power", "Group (Power)", 120, "center"),
            ("group_freq", "Group (Freq)", 120, "center"),
            ("tag", "Auto Tag", 160, "w"),
            ("folder", "Folder", 200, "w"),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=a)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Heatmap controls
        param_frame = ttk.LabelFrame(self.root, text="Heatmap Controls")
        param_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(param_frame, text="Order Parameter:").pack(side="left", padx=(6,2))
        self.selected_param = tk.StringVar()
        self.param_combo = ttk.Combobox(param_frame, textvariable=self.selected_param, state="readonly", width=40)
        self.param_combo.pack(side="left", padx=5)

        ttk.Label(param_frame, text="Statistic:").pack(side="left", padx=(12,2))
        self.selected_stat = tk.StringVar()
        self.stat_combo = ttk.Combobox(param_frame, textvariable=self.selected_stat, state="readonly", width=12)
        self.stat_combo["values"] = ["Mean", "%CV", "Min", "Max"]
        self.stat_combo.set("Mean")
        self.stat_combo.pack(side="left", padx=5)

        ttk.Label(param_frame, text="Folder:").pack(side="left", padx=(12,2))
        self.selected_folder = tk.StringVar()
        self.folder_combo = ttk.Combobox(param_frame, textvariable=self.selected_folder, state="readonly", width=18)
        self.folder_combo.pack(side="left", padx=5)

        # Single Compare Folder dropdown
        ttk.Label(param_frame, text="Compare:").pack(side="left", padx=(12,2))
        self.compare_selection = tk.StringVar()
        self.compare_combo = ttk.Combobox(param_frame, textvariable=self.compare_selection, state="readonly", width=30)
        self.compare_combo.pack(side="left", padx=2)

        ttk.Button(param_frame, text="Plot Heatmap", command=self.plot_heatmap_gui).pack(side="left", padx=12)
        ttk.Button(param_frame, text="Plot P-Values", command=self.plot_pvalue_gui).pack(side="left", padx=6)

        self.figure = plt.Figure(figsize=(10, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(10,10))

    # ---------- GUI Actions ----------
    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.current_path.get(), title="Select Folder")
        if folder:
            self.current_path.set(folder)
            save_last_path(folder)

    def add_data_set(self):
        result = load_data_folder_auto(self.current_path.get())
        if not result:
            return
        dfs, fnames, powers, freqs, tags, folders = result

        for p in powers:
            key = str(p) if p is not None else "__UNKNOWN_POWER__"
            if key not in self.power_group_map:
                self.power_group_map[key] = len(self.power_group_map) + 1
        for f in freqs:
            key = str(f) if f is not None else "__UNKNOWN_FREQ__"
            if key not in self.freq_group_map:
                self.freq_group_map[key] = len(self.freq_group_map) + 1

        for df, fname, p, f, tag, folder in zip(dfs, fnames, powers, freqs, tags, folders):
            self.dataframes.append(df)
            self.file_names.append(fname)
            p_key = str(p) if p is not None else "__UNKNOWN_POWER__"
            f_key = str(f) if f is not None else "__UNKNOWN_FREQ__"
            self.groups.append(self.power_group_map[p_key])
            self.groups_freq.append(self.freq_group_map[f_key])
            self.power_values_per_file.append(p_key)
            self.freq_values_per_file.append(f_key)
            self.group_tags.append(tag)
            self.group_folders.append(folder)

        self.update_parameters_from_dataframes()
        self.update_folder_combo()
        self.populate_table()

    def clear_all_data_gui(self):
        clear_all_data(self)
        for r in self.tree.get_children():
            self.tree.delete(r)
        self.param_combo["values"] = []
        self.selected_param.set("")
        self.update_folder_combo()
        self.figure.clf()
        self.canvas.draw()

    def update_parameters_from_dataframes(self):
        params = set()
        for df in self.dataframes:
            params.update(df["Order Parameter"].dropna().tolist())
        vals = sorted(params, key=lambda s: str(s))
        self.param_combo["values"] = vals
        if vals and not self.selected_param.get():
            self.selected_param.set(vals[0])

    # ---------- Folder dropdown updates ----------
    def update_folder_combo(self):
        unique_folders = sorted(set(self.group_folders))
        values = ["All Folders"] + unique_folders
        self.folder_combo["values"] = values
        if not self.selected_folder.get() or self.selected_folder.get() not in values:
            self.selected_folder.set("All Folders")

        # Update single Compare dropdown with all folder pairs
        options = [f"{a} vs {b}" for i, a in enumerate(unique_folders) for j, b in enumerate(unique_folders) if i < j]
        self.compare_combo["values"] = options
        if options:
            if self.compare_selection.get() not in options:
                self.compare_selection.set(options[0])

    def populate_table(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for fname, gp, gf, tag, folder in zip(self.file_names, self.groups, self.groups_freq, self.group_tags, self.group_folders):
            self.tree.insert("", "end", values=(fname, gp, gf, tag, folder))

    def _numeric_sort_key(self, s):
        try:
            if s is None:
                return (1e18, str(s))
            if isinstance(s, (int,float)):
                return (0,float(s))
            return (0,float(s))
        except Exception:
            return (1,str(s))

    # ---------- Heatmap ----------
    def build_heatmap_dataframe(self, order_param, stat_column, folder_filter=None):
        if not self.dataframes:
            return None
        include_all = (folder_filter is None) or (folder_filter=="All Folders")
        included_indices = [i for i,fld in enumerate(self.group_folders) if include_all or fld==folder_filter]
        if not included_indices:
            return None

        included_powers = [self.power_values_per_file[i] for i in included_indices]
        included_freqs  = [self.freq_values_per_file[i] for i in included_indices]
        unique_powers = sorted(set(included_powers), key=self._numeric_sort_key)
        unique_freqs  = sorted(set(included_freqs), key=self._numeric_sort_key)
        heat_df = pd.DataFrame(index=unique_powers, columns=unique_freqs, dtype=float)
        cell_values = {(p,f): [] for p in unique_powers for f in unique_freqs}

        for idx in included_indices:
            df = self.dataframes[idx]
            p = self.power_values_per_file[idx]
            f = self.freq_values_per_file[idx]
            row = df[df["Order Parameter"]==order_param]
            value = np.nan
            if not row.empty:
                try:
                    value = float(row.iloc[0].get(stat_column, np.nan))
                except Exception:
                    value = np.nan
            cell_values[(p,f)].append(value)

        for (p,f), vals in cell_values.items():
            numeric_vals = [v for v in vals if v is not None and (not (isinstance(v,float) and np.isnan(v)))]
            heat_df.at[p,f] = float(np.mean(numeric_vals)) if numeric_vals else np.nan
        return heat_df

    def plot_heatmap_gui(self):
        order_param = self.selected_param.get()
        stat_col = self.selected_stat.get()
        folder = self.selected_folder.get() if self.selected_folder.get() else "All Folders"
        if not order_param or not stat_col:
            messagebox.showwarning("Selection required", "Please select Order Parameter and Statistic.")
            return

        heat_df = self.build_heatmap_dataframe(order_param, stat_col, folder_filter=folder)
        if heat_df is None:
            messagebox.showwarning("No data", f"No files found for folder '{folder}'.")
            return

        self.figure.clf()
        ax = self.figure.add_subplot(111)
        data = heat_df.values.astype(float)
        cmap = plt.get_cmap("cividis").copy()
        cmap.set_bad(color='white')
        im = ax.imshow(data, interpolation='nearest', aspect='auto', cmap=cmap)
        ax.set_yticks(np.arange(len(heat_df.index)))
        ax.set_yticklabels([str(x) for x in heat_df.index])
        ax.set_xticks(np.arange(len(heat_df.columns)))
        ax.set_xticklabels([str(x) for x in heat_df.columns], rotation=45, ha="right")
        ax.invert_yaxis()   # ← FIXES Y-AXIS ORDER
        ax.set_xlabel("Frequency")
        ax.set_ylabel("Power")
        ax.set_title(f"{order_param} — {stat_col} (Power vs Frequency)")
        cbar = self.figure.colorbar(im, ax=ax)
        cbar.set_label(stat_col)
        self.canvas.draw()

    # ---------- P-Value Calculation ----------
    def calculate_pvalue_dataframe(self, order_param, stat_col, folderA, folderB):
        # Filter indices by folder
        idxA = [i for i,f in enumerate(self.group_folders) if f==folderA]
        idxB = [i for i,f in enumerate(self.group_folders) if f==folderB]
        if not idxA or not idxB:
            return None

        unique_powers = sorted(set(self.power_values_per_file), key=self._numeric_sort_key)
        unique_freqs  = sorted(set(self.freq_values_per_file), key=self._numeric_sort_key)
        pval_df = pd.DataFrame(index=unique_powers, columns=unique_freqs, dtype=float)

        for p in unique_powers:
            for f in unique_freqs:
                valsA = []
                for i in idxA:
                    if self.power_values_per_file[i]==p and self.freq_values_per_file[i]==f:
                        df = self.dataframes[i]
                        row = df[df["Order Parameter"]==order_param]
                        if not row.empty:
                            try:
                                val = float(row.iloc[0].get(stat_col, np.nan))
                                if not np.isnan(val):
                                    valsA.append(val)
                            except: pass
                valsB = []
                for i in idxB:
                    if self.power_values_per_file[i]==p and self.freq_values_per_file[i]==f:
                        df = self.dataframes[i]
                        row = df[df["Order Parameter"]==order_param]
                        if not row.empty:
                            try:
                                val = float(row.iloc[0].get(stat_col, np.nan))
                                if not np.isnan(val):
                                    valsB.append(val)
                            except: pass
                try:
                    if valsA and valsB:
                        # ttest using means, std
                        meanA, stdA, nA = np.mean(valsA), np.std(valsA, ddof=1), len(valsA)
                        meanB, stdB, nB = np.mean(valsB), np.std(valsB, ddof=1), len(valsB)
                        t_stat, p_value = ttest_ind_from_stats(mean1=meanA, std1=stdA, nobs1=nA,
                                                              mean2=meanB, std2=stdB, nobs2=nB, equal_var=False)
                        pval_df.at[p,f] = p_value
                    else:
                        pval_df.at[p,f] = np.nan
                except:
                    pval_df.at[p,f] = np.nan
        return pval_df

    def plot_pvalue_gui(self):
        order_param = self.selected_param.get()
        stat_col = self.selected_stat.get()
        selected = self.compare_selection.get()
        if not order_param or not stat_col:
            messagebox.showwarning("Selection required", "Please select Order Parameter and Statistic.")
            return
        if not selected or " vs " not in selected:
            messagebox.showwarning("Selection required", "Please select two folders to compare.")
            return
        folderA, folderB = selected.split(" vs ")

        pval_df = self.calculate_pvalue_dataframe(order_param, stat_col, folderA, folderB)
        if pval_df is None or pval_df.empty:
            messagebox.showwarning("No data", f"No matching data between {folderA} and {folderB}.")
            return

        self.figure.clf()
        ax = self.figure.add_subplot(111)
        data = pval_df.values.astype(float)
        cmap = plt.get_cmap("plasma_r").copy()
        cmap.set_bad(color='white')
        im = ax.imshow(data, interpolation='nearest', aspect='auto', cmap=cmap, vmin=0, vmax=0.05)
        ax.set_yticks(np.arange(len(pval_df.index)))
        ax.set_yticklabels([str(x) for x in pval_df.index])
        ax.set_xticks(np.arange(len(pval_df.columns)))
        ax.set_xticklabels([str(x) for x in pval_df.columns], rotation=45, ha="right")
        ax.invert_yaxis()   # ← FIX HERE TOO
        ax.set_xlabel("Frequency")
        ax.set_ylabel("Power")
        ax.set_title(f"P-Values — {order_param} ({stat_col}) — {folderA} vs {folderB}")
        cbar = self.figure.colorbar(im, ax=ax)
        cbar.set_label("P-Value")
        self.canvas.draw()