import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog, Toplevel
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from data_manager import load_last_path, save_last_path
from data_manager import DataManager
from plotter import plot_oes_data
from analysis import calculate_group_means, calculate_group_cv, calculate_group_cv_normalized, calculate_group_pvalues_raw, calculate_signal_to_noise, calculate_group_std_and_rsd_by_wavelength, calculate_group_drift_first_last, calculate_group_drift_min_max
# from itertools import combinations

class DataPlotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OES Data Visualization")
        self.root.geometry("1150x950")

        self.current_path = tk.StringVar(value=load_last_path())
        self.data_mgr = DataManager()

        # Matplotlib canvas holder (will be created when plotting)
        self.figure = None
        self.canvas = None

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
        ttk.Button(data_frame, text="Clear All Data", command=self.clear_all_data).pack(side="left", padx=5)

        table_frame = ttk.LabelFrame(self.root, text="Loaded Files and Groups")
        table_frame.pack(fill="x", padx=15, pady=5)
        columns = ("filename", "group", "tag", "folder")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for c, w in zip(columns, [300, 80, 150, 300]):
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # disable mouse wheel native scrolling on tree to avoid weird focus issues
        self.tree.bind("<MouseWheel>", lambda e: "break")
        self.tree.bind("<Button-4>", lambda e: "break")
        self.tree.bind("<Button-5>", lambda e: "break")
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        control_frame = ttk.LabelFrame(self.root, text="Plot Controls")
        control_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(control_frame, text="Wavelengths (comma separated):").pack(side="left", padx=5)
        self.wavelength_entry = ttk.Entry(control_frame, width=40)
        self.wavelength_entry.pack(side="left", padx=5)
        ttk.Button(control_frame, text="Plot Data", command=self.plot_data).pack(side="left", padx=10)
        ttk.Button(control_frame, text="Reset Tags", command=self.reset_tags).pack(side="left", padx=10)
        ttk.Button(control_frame, text="Reset Groups", command=self.reset_groups).pack(side="left", padx=10)
        ttk.Button(control_frame, text="Plot Normalized Intensity", command=self.show_normalized_intensity_popup).pack(side="left", padx=10)

        # Placeholder figure initially
        import matplotlib.pyplot as plt
        self.figure = plt.Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # ---------- Config and folder selection ----------
    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.current_path.get(), title="Select Folder")
        if folder:
            self.current_path.set(folder)
            save_last_path(folder)

    # ---------- Data management GUI glue ----------
    def add_data_set(self):
        folder = filedialog.askdirectory(initialdir=self.current_path.get(), title="Select Data Set Folder")
        if not folder:
            return
        tag = simpledialog.askstring("Group Tag", "Enter a tag for this data set:", parent=self.root)
        if not tag:
            tag = f"Group {len(set(self.data_mgr.groups)) + 1}"
        group_id = len(set(self.data_mgr.groups)) + 1

        loaded = self.data_mgr.add_data_set_from_folder(folder, tag=tag, group_id=group_id)
        if loaded == 0:
            messagebox.showwarning("No CSVs", f"No CSV files found or valid in {folder}")
            return
        self.populate_table()
        # messagebox.showinfo("Loaded", f"Loaded {loaded} files from:\n{folder}")

    def clear_all_data(self):
        self.data_mgr.clear_all()
        self.populate_table()

    def populate_table(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for name, grp, tag, folder in zip(self.data_mgr.file_names, self.data_mgr.groups,
                                          self.data_mgr.group_tags, self.data_mgr.group_folders):
            self.tree.insert("", "end", values=(name, grp, tag, os.path.basename(folder)))

    def on_tree_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row_id:
            return
        col_idx = int(col.replace("#", "")) - 1
        row_i = list(self.tree.get_children()).index(row_id)
        if col_idx == 1:
            # edit group using combobox
            x, y, w, h = self.tree.bbox(row_id, col)
            entry = ttk.Combobox(self.tree, values=sorted(set(self.data_mgr.groups)), state="readonly")
            entry.place(x=x, y=y, width=w, height=h)
            entry.set(self.data_mgr.groups[row_i])
            entry.bind("<<ComboboxSelected>>", lambda e: self._save_group_change(row_i, entry))
        elif col_idx == 2:
            # edit tag using entry
            x, y, w, h = self.tree.bbox(row_id, col)
            entry = ttk.Entry(self.tree); entry.place(x=x, y=y, width=w, height=h)
            entry.insert(0, self.data_mgr.group_tags[row_i])
            entry.bind("<Return>", lambda e: self._save_tag_change(row_i, entry))
            entry.bind("<FocusOut>", lambda e: self._save_tag_change(row_i, entry))
            entry.focus_set()

    def _save_tag_change(self, row_i, entry):
        new_tag = entry.get().strip()
        grp_num = self.data_mgr.groups[row_i]
        for i, g in enumerate(self.data_mgr.groups):
            if g == grp_num:
                self.data_mgr.group_tags[i] = new_tag
        entry.destroy()
        self.populate_table()

    def _save_group_change(self, row_i, combo):
        try:
            self.data_mgr.groups[row_i] = int(combo.get())
        except Exception:
            pass
        combo.destroy()
        self.populate_table()

    def reset_tags(self):
        self.data_mgr.reset_tags()
        self.populate_table()

    def reset_groups(self):
        self.data_mgr.reset_groups()
        self.populate_table()

    # ---------- Plot ----------
    def plot_data(self):
        if not self.data_mgr.dataframes:
            messagebox.showwarning("No Data", "Add at least one dataset first.")
            return
        try:
            wavelengths = [float(x.strip()) for x in self.wavelength_entry.get().split(",") if x.strip()]
        except ValueError:
            messagebox.showerror("Error", "Invalid wavelength entry.")
            return
        if not wavelengths:
            messagebox.showwarning("No wavelengths", "Enter at least one wavelength to plot.")
            return

        try:
            main_fig = plot_oes_data(
                self.data_mgr.dataframes,
                self.data_mgr.groups,
                self.data_mgr.group_tags,
                wavelengths
            )
        except Exception as e:
            messagebox.showerror("Plot Error", f"Failed to create plot:\n{e}")
            return

        # Replace main canvas with new figure
        if self.canvas:
            try:
                self.canvas.get_tk_widget().pack_forget()
            except Exception:
                pass

        self.figure = main_fig
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas.draw()

        # Show analysis popup
        self.show_analysis_popup(wavelengths)

    def show_analysis_popup(self, wavelengths):
        import numpy as np
        from tkinter import Toplevel, ttk

        # --- Color helpers ---
        def get_pvalue_color(v):
            if v is None or np.isnan(v):
                return "white"
            if v <= 0.05: return "#b3ffb3"
            elif v <= 0.1: return "#ffd699"
            else: return "#ff9999"

        def get_cv_color(v):
            if v is None or np.isnan(v):
                return "white"
            # Using same thresholds you used previously in this file (5,10)
            if v <= 5: return "#b3ffb3"
            elif v <= 10: return "#ffd699"
            else: return "#ff9999"

        # Close existing popup
        if hasattr(self, 'analysis_popup') and self.analysis_popup:
            try:
                self.analysis_popup.destroy()
            except Exception:
                pass

        self.analysis_popup = Toplevel(self.root)
        self.analysis_popup.title("Data Analysis")
        self.analysis_popup.geometry("1200x800")

        main_notebook = ttk.Notebook(self.analysis_popup)
        main_notebook.pack(fill="both", expand=True)

        # ---------- Generic label-grid table function ----------
        def add_label_table(parent_nb, tables_dict, tab_label, headers_override=None, cell_color_callback=None):
            """
            parent_nb: ttk.Notebook instance (parent)
            tables_dict: dict where key = subtab label, value = list of rows (iterable of iterables)
            tab_label: top-level tab label (string)
            headers_override: dict mapping subtab label -> headers list (optional)
            cell_color_callback: function(tab_label, subtab_label, r_idx, c_idx, val) -> bg color string or None
            """
            frame = tk.Frame(parent_nb)
            parent_nb.add(frame, text=tab_label)
            inner_nb = ttk.Notebook(frame)
            inner_nb.pack(fill="both", expand=True, padx=10, pady=10)

            if not tables_dict:
                info_tab = tk.Frame(inner_nb)
                tk.Label(info_tab, text="No data available").pack(padx=10, pady=10)
                inner_nb.add(info_tab, text="Info")
                return

            for label, rows in tables_dict.items():
                tab = tk.Frame(inner_nb, bg="white")
                inner_nb.add(tab, text=label)
                # Determine headers
                headers = headers_override.get(label) if headers_override and label in headers_override else None
                if not headers:
                    # infer headers from first row length (generic names)
                    first_row = rows[0] if rows else []
                    headers = [f"Col {i}" for i in range(len(first_row))]

                # create header labels
                for cidx, c in enumerate(headers):
                    hdr = tk.Label(tab, text=c, bg="#e8e8e8", font=("Segoe UI", 9, "bold"), padx=6, pady=3)
                    hdr.grid(row=0, column=cidx, sticky="nsew", padx=1, pady=1)
                    tab.grid_columnconfigure(cidx, weight=1, uniform="col")

                # populate rows and per-cell coloring
                for ridx, row in enumerate(rows, start=1):
                    for cidx, val in enumerate(row):
                        text_val = val
                        # Format numeric nicely
                        if isinstance(val, float) or isinstance(val, np.floating):
                            # choose formatting based on magnitude
                            text_val = f"{val:.3f}"
                        elif isinstance(val, (int, np.integer)):
                            text_val = str(val)
                        else:
                            # leave strings as-is
                            text_val = str(val)

                        bg = "white"
                        if cell_color_callback:
                            try:
                                custom_bg = cell_color_callback(tab_label, label, ridx-1, cidx, val)
                                if custom_bg:
                                    bg = custom_bg
                            except Exception:
                                bg = "white"

                        lbl = tk.Label(tab, text=text_val, bg=bg, padx=6, pady=2, anchor="center")
                        lbl.grid(row=ridx, column=cidx, sticky="nsew", padx=1, pady=1)

                # ensure rows expand
                for rr in range(len(rows)+1):
                    tab.grid_rowconfigure(rr, weight=0)
                # small stretch for whole tab
                tab.grid_rowconfigure(0, weight=0)
                tab.grid_columnconfigure(len(headers)-1, weight=1)

        # ---------- 1. Mean Tab (no color) ----------
        group_means = calculate_group_means(self.data_mgr.dataframes, self.data_mgr.groups, wavelengths)
        mean_tables = {}
        mean_headers = {}
        for g, data in group_means.items():
            tag = next((t for i, t in enumerate(self.data_mgr.group_tags) if self.data_mgr.groups[i] == g), f"Group {g}")
            rows = []
            for wl, vals in sorted(data.items()):
                rows.append([wl, round(vals['mean'], 3), round(vals['std_dev'], 3), round(vals['cv_percent'], 3)])
            mean_tables[tag] = rows
            mean_headers[tag] = ["Wavelength", "Mean", "Std Dev", "%CV"]

        add_label_table(main_notebook, mean_tables, "Mean", headers_override=mean_headers, cell_color_callback=None)

        # ---------- 2. Group %CV Tab ----------
        group_cv_raw = calculate_group_cv(self.data_mgr.dataframes, self.data_mgr.groups, wavelengths)
        group_cv_norm = calculate_group_cv_normalized(self.data_mgr.dataframes, self.data_mgr.groups, wavelengths)
        cv_tables = {}
        cv_headers = {}
        for g in sorted(set(self.data_mgr.groups)):
            tag = next((t for i, t in enumerate(self.data_mgr.group_tags) if self.data_mgr.groups[i] == g), f"Group {g}")
            rows = []
            for wl in wavelengths:
                raw = group_cv_raw[g].get(wl, np.nan)
                norm = group_cv_norm[g].get(wl, np.nan)
                rows.append([wl, raw, norm])
            cv_tables[tag] = rows
            cv_headers[tag] = ["Wavelength", "Group %CV", "Group %CV (Norm.)"]

        def cv_cell_color(top_label, sub_label, r_idx, c_idx, val):
            # c_idx 1 = raw CV, c_idx 2 = normalized CV
            if c_idx in (1, 2) and val is not None and not np.isnan(val):
                return get_cv_color(val)
            return "white"

        add_label_table(main_notebook, cv_tables, "Group %CV", headers_override=cv_headers, cell_color_callback=cv_cell_color)

        # ---------- 3. P-Values Tab (Raw) ----------
        pvalues_raw = calculate_group_pvalues_raw(self.data_mgr.dataframes, self.data_mgr.groups, wavelengths)
        pval_tables = {}
        pval_headers = {}
        for (g1, g2), vals in pvalues_raw.items():
            tag1 = next((t for i, t in enumerate(self.data_mgr.group_tags) if self.data_mgr.groups[i] == g1), f"Group {g1}")
            tag2 = next((t for i, t in enumerate(self.data_mgr.group_tags) if self.data_mgr.groups[i] == g2), f"Group {g2}")
            sublabel = f"{tag1} vs {tag2}"
            rows = []
            for wl, pv in sorted(vals.items()):
                # ensure numpy nan handled
                pv_val = np.nan if pv is np.nan else pv
                rows.append([wl, pv_val])
            pval_tables[sublabel] = rows
            pval_headers[sublabel] = ["Wavelength", "P-Value"]

        def pval_cell_color(top_label, sub_label, r_idx, c_idx, val):
            if c_idx == 1:
                try:
                    if val is None or np.isnan(val):
                        return "white"
                except Exception:
                    return "white"
                return get_pvalue_color(val)
            return "white"

        add_label_table(main_notebook, pval_tables, "P-Values", headers_override=pval_headers, cell_color_callback=pval_cell_color)

        # ---------- Group (STD) Tab ----------
        peak_wavelengths = [float(w.strip()) for w in self.wavelength_entry.get().split(",") if w.strip()]

        group_std_rsd_results = calculate_group_std_and_rsd_by_wavelength(
            self.data_mgr.dataframes,
            self.data_mgr.groups,
            self.data_mgr.group_tags,
            peak_wavelengths
        )

        if group_std_rsd_results:
            std_tables = {}
            std_headers = {}

            for group_label, per_wl_stats in group_std_rsd_results.items():
                rows = []
                for wl in peak_wavelengths:
                    vals = per_wl_stats.get(wl, {})
                    std_val = vals.get("STD", np.nan)
                    rsd_val = vals.get("RSD", np.nan)
                    rows.append([wl, std_val, rsd_val])
                std_tables[group_label] = rows
                std_headers[group_label] = ["Wavelength", "Std. Dev.", "RSD (%)"]

            add_label_table(
                main_notebook,
                std_tables,
                "Group (STD)",
                headers_override=std_headers,
                cell_color_callback=None
            )

        # ---------- Signal to Noise Ratio Tab ----------
        snr_info = calculate_signal_to_noise(
            self.data_mgr.dataframes,
            self.data_mgr.groups,
            self.data_mgr.group_tags,
            peak_wavelengths
        )

        if snr_info:
            snr_tables = {}
            snr_headers = {}
            first_key = next(iter(snr_info)) if snr_info else None
            if first_key is not None:
                group_cols = list(snr_info[first_key].keys())
            else:
                group_cols = []

            # We'll make one subtab per group column showing Wavelength + value
            for tag in group_cols:
                rows = []
                for wl in peak_wavelengths:
                    vals = snr_info.get(wl, {})
                    v = vals.get(tag, np.nan)
                    rows.append([wl, v])
                snr_tables[tag] = rows
                snr_headers[tag] = ["Wavelength", tag]

            add_label_table(main_notebook, snr_tables, "Signal to Noise Ratio", headers_override=snr_headers, cell_color_callback=None)
        #
        # ---------- Group Drift Tab ----------
        peak_wavelengths = [float(w.strip()) for w in self.wavelength_entry.get().split(",") if w.strip()]

        # Calculate both drift types
        drift_first_last = calculate_group_drift_first_last(
            self.data_mgr.dataframes,
            self.data_mgr.groups,
            self.data_mgr.group_tags,
            peak_wavelengths
        )

        drift_min_max = calculate_group_drift_min_max(
            self.data_mgr.dataframes,
            self.data_mgr.groups,
            self.data_mgr.group_tags,
            peak_wavelengths
        )

        # Merge both results for display
        if drift_first_last or drift_min_max:
            drift_tables = {}
            drift_headers = {}

            # Collect all group labels to ensure consistent tabs
            all_group_labels = set(drift_first_last.keys()) | set(drift_min_max.keys())

            for group_label in all_group_labels:
                rows = []
                for wl in peak_wavelengths:
                    drift_fl = drift_first_last.get(group_label, {}).get(wl, np.nan)
                    drift_mm = drift_min_max.get(group_label, {}).get(wl, np.nan)

                    # Compute Avg Drift safely
                    if not np.isnan(drift_fl) and not np.isnan(drift_mm):
                        drift_avg = (drift_fl + drift_mm) / 2.0
                    else:
                        drift_avg = np.nan

                    rows.append([wl, drift_fl, drift_mm, drift_avg])

                drift_tables[group_label] = rows
                drift_headers[group_label] = [
                    "Wavelength",
                    "% Drift (First–Last)",
                    "% Drift (Min–Max)",
                    "Avg Drift (%)"
                ]

            add_label_table(
                main_notebook,
                drift_tables,
                "Group Drift",
                headers_override=drift_headers,
                cell_color_callback=None
            )

    def show_normalized_intensity_popup(self):
        if not self.data_mgr.dataframes:
            messagebox.showwarning("No Data", "Add at least one dataset first.")
            return

        # Close existing popup if present
        if hasattr(self, 'norm_intensity_popup') and self.norm_intensity_popup:
            try:
                self.norm_intensity_popup.destroy()
            except Exception:
                pass

        self.norm_intensity_popup = Toplevel(self.root)
        self.norm_intensity_popup.title("Normalized Intensity vs Wavelength")
        self.norm_intensity_popup.geometry("1000x700")

        # Prepare figure
        fig = plt.Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)

        # Get all unique groups
        groups = sorted(set(self.data_mgr.groups))
        colors = plt.cm.tab10.colors

        for i, g in enumerate(groups):
            # Get indices of dataframes in this group
            idxs = [j for j, grp in enumerate(self.data_mgr.groups) if grp == g]
            tag = next((t for j, t in enumerate(self.data_mgr.group_tags) if self.data_mgr.groups[j] == g),
                    f"Group {g}")

            # Combine the dataframes for this group
            group_dfs = [self.data_mgr.dataframes[j] for j in idxs]
            # Merge mean values by wavelength index
            wl_values = sorted(set(np.concatenate([df['wavelength_index'].values for df in group_dfs])))
            mean_vals = []
            for wl in wl_values:
                vals = [df.loc[df['wavelength_index'] == wl, 'mean'].values[0]
                        for df in group_dfs if wl in df['wavelength_index'].values]
                if vals:
                    mean_vals.append(np.mean(vals))
                else:
                    mean_vals.append(np.nan)

            # Normalize by total sum of mean values
            mean_vals = np.array(mean_vals)
            if np.nansum(mean_vals) != 0:
                norm_vals = mean_vals / np.nansum(mean_vals)
            else:
                norm_vals = mean_vals

            # Plot without markers
            ax.plot(wl_values, norm_vals, label=tag, color=colors[i % len(colors)])

        # Draw dashed vertical lines at each user-defined wavelength
        for wl in self.wavelength_entry.get().split(","):
            try:
                wl_val = float(wl.strip())
                ax.axvline(x=wl_val, linestyle='--', color='gray', alpha=0.7)
            except ValueError:
                continue  # ignore invalid entries

        ax.set_xlabel("Wavelength Index")
        ax.set_ylabel("Normalized Mean Intensity")
        ax.set_title("Normalized Mean Intensity vs Wavelength")
        ax.legend()
        ax.grid(True)
        fig.tight_layout()

        # Add canvas to popup
        canvas = FigureCanvasTkAgg(fig, master=self.norm_intensity_popup)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.draw()
