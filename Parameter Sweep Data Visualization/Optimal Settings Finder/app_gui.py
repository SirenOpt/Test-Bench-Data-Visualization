# app_gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import defaultdict
import os
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import logic modules
from analysis import process_data
from plotting import clear_plot_gui, update_heatmap_gui
from data_loading import load_electrical_data, load_oes_data

class DataLoaderGUI:
    def __init__(self, root):
        self.root = root
        root.title("Electrical + OES Data Loader and Colormap Viewer")
        root.geometry("1200x720")

        # storage
        self.electrical_files = []  # list of dicts: {path,file,power,freq,df}
        self.oes_files = []
        # grouped by (power,freq)
        self.electrical_groups = defaultdict(list)
        self.oes_groups = defaultdict(list)

        # results
        self.electrical_averaged = {}   # (p,f) -> DataFrame (indexed by Order Parameter)
        self.electrical_normalized = {} # (order_param, stat) -> {(p,f): normalized_value}

        self.oes_averaged = {}   # (p,f) -> DataFrame (indexed by wavelength_index)
        self.oes_normalized = {} # (wavelength, stat) -> {(p,f): normalized_value}

        # UI state: checkbox variables
        self.elec_check_vars = {}  # (orderparam,stat) -> tk.IntVar
        self.oes_check_vars = {}   # (wavelength,stat) -> tk.IntVar

        # default folder config
        self.config_path = "default_folder.cfg"
        self.default_folder = None

        # build UI
        self.build_gui()

        # Initialize empty checklists on startup
        self.build_checklists([])

        # load default folder if any
        self.load_default_folder()

    # -------------------------
    # Config for default folder
    # -------------------------
    def load_default_folder(self):
        """Load stored default folder from config file, if it exists."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    folder = f.read().strip()
                    if os.path.isdir(folder):
                        self.default_folder = folder
            except Exception:
                pass

    def set_default_folder(self):
        folder = filedialog.askdirectory(
            title="Select Default Data Folder",
            initialdir=self.default_folder if self.default_folder else "/"
        )
        if folder:
            self.default_folder = folder
            try:
                with open(self.config_path, "w") as f:
                    f.write(folder)
            except Exception:
                pass
            messagebox.showinfo("Default Folder Set", f"Default folder set to:\n{folder}")

    # -------------------------
    # GUI Layout
    # -------------------------
    def build_gui(self):
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill="both", expand=True)

        # Top: table + load buttons
        topframe = ttk.Frame(main)
        topframe.pack(fill="x")

        columns = ("Data Type", "Folder", "Power Range", "Frequency Range", "Files Loaded")
        self.table = ttk.Treeview(topframe, columns=columns, show="headings", height=3)
        for c in columns:
            self.table.heading(c, text=c)
            self.table.column(c, width=200)
        self.table.pack(side="left", fill="x", expand=True)

        self.table.insert("", "end", iid="electrical", values=("Electrical Data", "", "", "", "0"))
        self.table.insert("", "end", iid="oes", values=("OES Data", "", "", "", "0"))

        btncol = ttk.Frame(topframe)
        btncol.pack(side="left", padx=8)
        ttk.Button(btncol, text="Browse", command=self.set_default_folder).pack(pady=6)
        ttk.Button(btncol, text="Load Electrical Data", command=self.load_electrical_folder).pack(pady=6)
        ttk.Button(btncol, text="Load OES Data", command=self.load_oes_folder).pack(pady=6)

        # Middle: wavelength entry, processing, plotting, clear
        midframe = ttk.Frame(main, padding=(0, 8, 0, 8))
        midframe.pack(fill="x")

        ttk.Label(midframe, text="Wavelengths (comma-separated indices):").pack(side="left")
        self.wavelength_entry = ttk.Entry(midframe, width=40)
        self.wavelength_entry.pack(side="left", padx=(6, 12))

        ttk.Button(midframe, text="Process Data", command=self.find_optimal_range).pack(side="left", padx=(0, 6))
        ttk.Button(midframe, text="Find Optimal Range", command=self.update_heatmap).pack(side="left")
        ttk.Button(midframe, text="Clear Plot", command=self.clear_plot).pack(side="left", padx=(6, 0))

        # lower layout
        lower = ttk.Frame(main)
        lower.pack(fill="both", expand=True)

        # heatmap
        heatmap_frame = ttk.Frame(lower)
        heatmap_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.heatmap_container = ttk.LabelFrame(heatmap_frame, text="Power vs Frequency Colormap", padding=6)
        self.heatmap_container.pack(fill="both", expand=True)

        self.fig = Figure(figsize=(6, 5))
        self.ax = self.fig.add_subplot(111)
        self.ax.text(0.5, 0.5, "No data to display\nRun 'Find Optimal Range'", ha="center", va="center")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.heatmap_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Checklist
        checklist_frame = ttk.Frame(lower)
        checklist_frame.pack(side="left", fill="y")

        self.elec_check_frame = ttk.LabelFrame(checklist_frame, text="Electrical Checklist", padding=6)
        self.elec_check_frame.pack(fill="y", padx=4, pady=4)

        self.oes_check_frame = ttk.LabelFrame(checklist_frame, text="OES Checklist (user wavelengths)", padding=6)
        self.oes_check_frame.pack(fill="y", padx=4, pady=4)

        ttk.Label(
            checklist_frame,
            text="Select metrics to include.\nMultiple metrics are summed\n& normalized before plotting."
        ).pack(padx=6, pady=8)

    # -------------------------
    # Clear Plot
    # -------------------------
    def clear_plot(self):
        clear_plot_gui(self)

    # -------------------------
    # Loading folders
    # -------------------------
    def load_electrical_folder(self):
        if self.default_folder:
            try:
                os.chdir(self.default_folder)  # Force Windows to use this dir
            except:
                pass

            folder = filedialog.askdirectory(
                parent=self.root,
                title="Select Electrical Data Folder",
                initialdir=self.default_folder,
                mustexist=True
            )
        else:
            folder = filedialog.askdirectory(
                parent=self.root,
                title="Select Electrical Data Folder",
                mustexist=True
            )
        if not folder:
            return

        loaded = load_electrical_data(self, folder)
        messagebox.showinfo("Loaded", f"Loaded {loaded} electrical CSV files from {folder}.")

        # Update default folder and persist
        self.default_folder = folder
        try:
            with open(self.config_path, "w") as f:
                f.write(folder)
        except Exception:
            pass

    def load_oes_folder(self):
        if self.default_folder:
            try:
                os.chdir(self.default_folder)
            except:
                pass

            folder = filedialog.askdirectory(
                parent=self.root,
                title="Select OES Data Folder",
                initialdir=self.default_folder,
                mustexist=True
            )
        else:
            folder = filedialog.askdirectory(
                parent=self.root,
                title="Select OES Data Folder",
                mustexist=True
            )
        if not folder:
            return

        loaded = load_oes_data(self, folder)
        messagebox.showinfo("Loaded", f"Loaded {loaded} OES CSV files from {folder}.")

        # Update default folder and persist
        self.default_folder = folder
        try:
            with open(self.config_path, "w") as f:
                f.write(folder)
        except Exception:
            pass

    # -------------------------
    # Main processing (Process Data)
    # -------------------------
    def find_optimal_range(self):
        raw = self.wavelength_entry.get().strip()
        wavelengths = []
        if raw:
            try:
                wavelengths = [int(x.strip()) for x in raw.split(',') if x.strip() != ""]
            except Exception:
                messagebox.showerror(
                    "Wavelength parse error",
                    "Use comma-separated integers (e.g. 0,1,5)."
                )
                return

        process_data(self, wavelengths)
        self.build_checklists(wavelengths)
        messagebox.showinfo("Done", "Processing complete.\nUse the checkboxes to build the colormap.")

    # -------------------------
    # Build checklist widgets
    # -------------------------
    def build_checklists(self, wavelengths):
        # Clear previous checklist frames
        for widget in self.elec_check_frame.winfo_children():
            widget.destroy()
        for widget in self.oes_check_frame.winfo_children():
            widget.destroy()
        self.elec_check_vars.clear()
        self.oes_check_vars.clear()

        # Electrical Checklist
        headers = ["Order Parameter", "Mean", "%CV", "Min", "Max"]
        for c, h in enumerate(headers):
            ttk.Label(self.elec_check_frame, text=h, font=("Arial", 9, "bold")).grid(
                row=0, column=c, sticky="w", padx=4
            )

        if not self.electrical_averaged:
            ttk.Label(self.elec_check_frame, text="(No data loaded)").grid(
                row=1, column=0, sticky="w", padx=4
            )
        else:
            order_params = sorted({
                op for df in self.electrical_averaged.values()
                for op in df.index.astype(str)
            })

            for r, op in enumerate(order_params, start=1):
                ttk.Label(self.elec_check_frame, text=op).grid(
                    row=r, column=0, sticky="w", padx=4
                )
                for c, stat in enumerate(["Mean", "%CV", "Min", "Max"], start=1):
                    var = tk.IntVar(value=0)
                    chk = tk.Checkbutton(self.elec_check_frame, variable=var)
                    chk.grid(row=r, column=c, sticky="w")
                    self.elec_check_vars[(op, stat)] = var

        # OES Checklist
        headers2 = ["Wavelength", "mean", "std_dev", "cv_percent", "SNR"]
        for c, h in enumerate(headers2):
            ttk.Label(self.oes_check_frame, text=h, font=("Arial", 9, "bold")).grid(
                row=0, column=c, sticky="w", padx=4
            )

        if not wavelengths:
            ttk.Label(self.oes_check_frame, text="N/A").grid(
                row=1, column=0, sticky="w", padx=4
            )
            for col in range(1, 5):
                chk = tk.Checkbutton(self.oes_check_frame, state="disabled")
                chk.grid(row=1, column=col, sticky="w")
            return

        for r, wl in enumerate(wavelengths, start=1):
            ttk.Label(self.oes_check_frame, text=str(wl)).grid(
                row=r, column=0, sticky="w", padx=4
            )
            for c, stat in enumerate(["mean", "std_dev", "cv_percent", "SNR"], start=1):
                var = tk.IntVar(value=0)
                chk = tk.Checkbutton(self.oes_check_frame, variable=var)
                chk.grid(row=r, column=c, sticky="w")
                self.oes_check_vars[(wl, stat)] = var

    # -------------------------
    # Plot wrapper
    # -------------------------
    def update_heatmap(self):
        update_heatmap_gui(self)