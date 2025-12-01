import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.stats import ttest_ind_from_stats
from data_manager import DataManager, load_last_path, save_last_path


class DataPlotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OES Data Visualization")
        self.root.geometry("1250x950")

        self.current_path = tk.StringVar(value=load_last_path())
        self.data_mgr = DataManager()

        self.figure = None
        self.canvas = None

        self.create_widgets()

    def create_widgets(self):
        # ---- Folder Controls ----
        path_frame = ttk.LabelFrame(self.root, text="Base Folder (optional)")
        path_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(path_frame, text="Default Folder:").pack(side="left", padx=5)
        ttk.Entry(path_frame, textvariable=self.current_path, width=60).pack(side="left", padx=5)
        ttk.Button(path_frame, text="Browse", command=self.select_folder).pack(side="left", padx=5)

        # ---- Data Controls ----
        data_frame = ttk.LabelFrame(self.root, text="Data Sets")
        data_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(data_frame, text="Add Data Set (Folder)", command=self.add_data_set_auto).pack(side="left", padx=5)
        ttk.Button(data_frame, text="Clear All Data", command=self.clear_all_data).pack(side="left", padx=5)

        # ---- Table ----
        table_frame = ttk.LabelFrame(self.root, text="Loaded Files and Groups")
        table_frame.pack(fill="x", padx=15, pady=5)
        columns = ("filename", "power", "freq", "tag", "folder")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for c, w in zip(columns, [250, 100, 100, 150, 250]):
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # ---- Plot Controls ----
        control_frame = ttk.LabelFrame(self.root, text="Plot Controls")
        control_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(control_frame, text="Wavelength:").pack(side="left", padx=5)
        self.wavelength_entry = ttk.Entry(control_frame, width=10)
        self.wavelength_entry.pack(side="left", padx=5)

        ttk.Label(control_frame, text="Statistic:").pack(side="left", padx=5)
        self.statistic_var = tk.StringVar(value="Mean")
        self.stat_combo = ttk.Combobox(
            control_frame,
            textvariable=self.statistic_var,
            values=["Mean", "Standard Deviation", "% CV", "SNR"],
            width=20,
            state="readonly"
        )
        self.stat_combo.pack(side="left", padx=5)

        ttk.Label(control_frame, text="Folder:").pack(side="left", padx=5)
        self.folder_var = tk.StringVar()
        self.folder_combo = ttk.Combobox(control_frame, textvariable=self.folder_var, state="readonly", width=15)
        self.folder_combo.pack(side="left", padx=5)

        ttk.Label(control_frame, text="Compare:").pack(side="left", padx=5)
        self.compare_var = tk.StringVar()
        self.compare_combo = ttk.Combobox(control_frame, textvariable=self.compare_var, state="readonly", width=20)
        self.compare_combo.pack(side="left", padx=5)

        ttk.Button(control_frame, text="Plot Heatmap", command=self.plot_heatmap).pack(side="left", padx=10)
        ttk.Button(control_frame, text="Plot P-Values", command=self.plot_pvalues).pack(side="left", padx=10)

        # ---- Matplotlib Figure ----
        self.figure = plt.Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # ---------- Data Management ----------
    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.current_path.get(), title="Select Folder")
        if folder:
            self.current_path.set(folder)
            save_last_path(folder)

    def add_data_set_auto(self):
        folder = filedialog.askdirectory(initialdir=self.current_path.get(), title="Select Data Folder")
        if not folder:
            return
        loaded = self.data_mgr.add_data_set_from_folder_auto(folder)
        if loaded == 0:
            messagebox.showwarning("No CSVs", f"No valid CSVs found in {folder}")
            return
        self.populate_table()
        self.update_folder_dropdown()

    def clear_all_data(self):
        self.data_mgr.clear_all()
        self.populate_table()
        self.update_folder_dropdown()

    def populate_table(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for name, power, freq, tag, folder in zip(
            self.data_mgr.file_names, self.data_mgr.groups_power, self.data_mgr.groups_freq,
            self.data_mgr.auto_tags, self.data_mgr.group_folders
        ):
            self.tree.insert("", "end", values=(name, power, freq, tag, os.path.basename(folder)))

    def update_folder_dropdown(self):
        folder_names = sorted(set(os.path.basename(f) for f in self.data_mgr.group_folders))
        self.folder_combo['values'] = folder_names
        if folder_names:
            self.folder_var.set(folder_names[0])

        # Update comparison dropdown
        compare_options = []
        for i in range(len(folder_names)):
            for j in range(i + 1, len(folder_names)):
                compare_options.append(f"{folder_names[i]} vs {folder_names[j]}")
        self.compare_combo['values'] = compare_options
        if compare_options:
            self.compare_var.set(compare_options[0])

    # ---------- Plotting ----------
    def plot_heatmap(self):
        try:
            wl = float(self.wavelength_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Wavelength", "Please enter a valid number for Wavelength.")
            return

        statistic = self.statistic_var.get()
        selected_folder_name = self.folder_var.get()
        if not selected_folder_name:
            messagebox.showwarning("No Folder", "No folder selected.")
            return

        # Filter datasets by folder name
        filtered_data = [(df, p, f) for df, p, f, folder in zip(
            self.data_mgr.dataframes, self.data_mgr.groups_power,
            self.data_mgr.groups_freq, self.data_mgr.group_folders
        ) if os.path.basename(folder) == selected_folder_name]

        if not filtered_data:
            messagebox.showwarning("No Data", f"No data found for folder {selected_folder_name}.")
            return

        # Aggregate (Power, Freq) -> values
        data_dict = {}
        for df, power, freq in filtered_data:
            try:
                idx = (np.abs(df['wavelength_index'] - wl)).idxmin()
            except Exception:
                continue

            if statistic in ["Mean", "Standard Deviation", "% CV"]:
                if statistic == "Mean":
                    val = df.at[idx, "mean"]
                elif statistic == "Standard Deviation":
                    val = df.at[idx, "std_dev"]
                elif statistic == "% CV":
                    val = df.at[idx, "cv_percent"]

                key = (power, freq)
                data_dict.setdefault(key, []).append(val)

            elif statistic == "SNR":
                key = (power, freq)
                mean_val = df.at[idx, "mean"]
                std_val = df.at[idx, "std_dev"]
                data_dict.setdefault(key, []).append((mean_val, std_val))

        powers_sorted = sorted(set([k[0] for k in data_dict.keys()]))
        freqs_sorted = sorted(set([k[1] for k in data_dict.keys()]))

        heatmap_data = np.full((len(powers_sorted), len(freqs_sorted)), np.nan)
        for i, p in enumerate(powers_sorted):
            for j, f in enumerate(freqs_sorted):
                vals = data_dict.get((p, f), [])
                if not vals:
                    continue

                if statistic == "SNR":
                    means = [v[0] for v in vals]
                    stds = [v[1] for v in vals if v[1] != 0]
                    if stds and np.mean(stds) != 0:
                        heatmap_data[i, j] = abs(np.mean(means) / np.mean(stds))
                else:
                    heatmap_data[i, j] = np.mean(vals)

        # ---- Plot Heatmap ----
        self.figure.clf()
        ax = self.figure.add_subplot(111)
        c = ax.imshow(
            heatmap_data,
            aspect='auto',
            origin='lower',
            interpolation='nearest',
            cmap='cividis'
        )

        ax.set_xticks(np.arange(len(freqs_sorted)))
        ax.set_yticks(np.arange(len(powers_sorted)))
        ax.set_xticklabels(freqs_sorted)
        ax.set_yticklabels(powers_sorted)
        ax.set_xlabel("Frequency")
        ax.set_ylabel("Power")
        ax.set_title(f"Heatmap — {statistic} at Wavelength {wl}")

        self.figure.colorbar(c, ax=ax, label=statistic)
        self.canvas.draw()

    def plot_pvalues(self):
        try:
            wl = float(self.wavelength_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Wavelength", "Please enter a valid number for Wavelength.")
            return

        statistic = self.statistic_var.get()
        compare_text = self.compare_var.get()
        if "vs" not in compare_text:
            messagebox.showwarning("Invalid Comparison", "Please select two folders to compare.")
            return

        folder1_name, folder2_name = [x.strip() for x in compare_text.split("vs")]

        folder1_data = [(df, p, f) for df, p, f, folder in zip(
            self.data_mgr.dataframes, self.data_mgr.groups_power,
            self.data_mgr.groups_freq, self.data_mgr.group_folders
        ) if os.path.basename(folder) == folder1_name]

        folder2_data = [(df, p, f) for df, p, f, folder in zip(
            self.data_mgr.dataframes, self.data_mgr.groups_power,
            self.data_mgr.groups_freq, self.data_mgr.group_folders
        ) if os.path.basename(folder) == folder2_name]

        if not folder1_data or not folder2_data:
            messagebox.showwarning("No Data", "One or both folders have no data.")
            return

        def compute_stats(folder_data):
            stats_dict = {}
            for df, power, freq in folder_data:
                idx = (np.abs(df['wavelength_index'] - wl)).idxmin()
                if statistic == "Mean":
                    val = df.at[idx, "mean"]
                    std = df.at[idx, "std_dev"]
                elif statistic == "Standard Deviation":
                    val = df.at[idx, "std_dev"]
                    std = 0
                elif statistic == "% CV":
                    val = df.at[idx, "cv_percent"]
                    std = df["cv_percent"].std()
                else:
                    val, std = np.nan, np.nan
                key = (power, freq)
                if key not in stats_dict:
                    stats_dict[key] = []
                stats_dict[key].append((val, std))
            return stats_dict

        stats1 = compute_stats(folder1_data)
        stats2 = compute_stats(folder2_data)

        powers = sorted(set([k[0] for k in stats1.keys()] + [k[0] for k in stats2.keys()]))
        freqs = sorted(set([k[1] for k in stats1.keys()] + [k[1] for k in stats2.keys()]))

        heatmap_data = np.full((len(powers), len(freqs)), np.nan)

        for i, p in enumerate(powers):
            for j, f in enumerate(freqs):
                if (p, f) in stats1 and (p, f) in stats2:
                    v1 = [x[0] for x in stats1[(p, f)] if not np.isnan(x[0])]
                    v2 = [x[0] for x in stats2[(p, f)] if not np.isnan(x[0])]
                    if len(v1) > 1 and len(v2) > 1:
                        mean1, std1, n1 = np.mean(v1), np.std(v1, ddof=1), len(v1)
                        mean2, std2, n2 = np.mean(v2), np.std(v2, ddof=1), len(v2)
                        _, pval = ttest_ind_from_stats(mean1, std1, n1, mean2, std2, n2, equal_var=False)
                        heatmap_data[i, j] = pval

        self.figure.clf()
        ax = self.figure.add_subplot(111)
        c = ax.imshow(
            heatmap_data,
            aspect='auto',
            origin='lower',
            interpolation='nearest',
            cmap='plasma_r',
            vmin=0,
            vmax=0.05
        )

        ax.set_xticks(np.arange(len(freqs)))
        ax.set_yticks(np.arange(len(powers)))
        ax.set_xticklabels(freqs)
        ax.set_yticklabels(powers)
        ax.set_xlabel("Frequency")
        ax.set_ylabel("Power")
        ax.set_title(f"P-Values — {folder1_name} vs {folder2_name} at Wavelength {wl}")

        self.figure.colorbar(c, ax=ax, label="P-Value")
        self.canvas.draw()
