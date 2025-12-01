import os, json, re
import pandas as pd
from tkinter import messagebox, simpledialog, filedialog

CONFIG_FILE = "settings.json"

def load_last_path():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get("last_path", os.getcwd())
        except Exception:
            pass
    return os.getcwd()

def save_last_path(path):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"last_path": path}, f)
    except Exception:
        pass

def parse_power_freq_from_filename(fname):
    """
    Parse filename for numeric tokens -> return (power_str, freq_str)
    Example: 20251015_125714-Al_Spot-3min-T1-2000-18-2.5.tdms_summary.csv
             -> ("2000", "18")
    Heuristic: use numeric tokens; prefer tokens[-3], tokens[-2] for power/freq.
    """
    tokens = re.findall(r'\d+(?:\.\d+)?', fname)
    if len(tokens) >= 3:
        return tokens[-3], tokens[-2]
    elif len(tokens) >= 2:
        return tokens[-2], tokens[-1]
    else:
        return None, None

def load_data_folder_auto(initial_path):
    """Load CSV files automatically; no dialogs or tag prompts."""
    folder = filedialog.askdirectory(initialdir=initial_path, title="Select Data Folder")
    if not folder:
        return None

    csv_files = [f for f in os.listdir(folder) if f.lower().endswith(".csv")]
    if not csv_files:
        messagebox.showwarning("No CSVs", f"No CSV files found in {folder}")
        return None

    dfs, fnames = [], []
    powers, freqs = [], []
    tags, folders = [], []
    for fname in csv_files:
        fullpath = os.path.join(folder, fname)
        try:
            df = pd.read_csv(fullpath)
            # expected columns in your reference
            if set(["Order Parameter", "Mean", "%CV", "Min", "Max"]).issubset(df.columns):
                p, f = parse_power_freq_from_filename(fname)
                tag = f"P{p}_F{f}" if (p and f) else "Unknown"
                dfs.append(df)
                fnames.append(fname)
                powers.append(p)
                freqs.append(f)
                tags.append(tag)
                folders.append(os.path.basename(folder))
            else:
                messagebox.showwarning("Skipped", f"{fname} missing required columns — skipped.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load {fname}\n\n{e}")

    return dfs, fnames, powers, freqs, tags, folders

def clear_all_data(app):
    app.dataframes.clear()
    app.file_names.clear()
    app.groups.clear()
    app.groups_freq.clear()
    app.group_tags.clear()
    app.group_folders.clear()
    app.power_group_map.clear()
    app.freq_group_map.clear()
    app.power_values_per_file.clear()
    app.freq_values_per_file.clear()