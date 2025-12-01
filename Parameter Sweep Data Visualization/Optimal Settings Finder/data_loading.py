# data_loading.py
import os
import re
import pandas as pd

#from .analysis import is_electrical_df, is_oes_df  # if using as package
# If not using a package, change this import to:
from analysis import is_electrical_df, is_oes_df


def parse_power_freq_from_filename(fname):
    """
    Extract power and frequency from filenames like:
    20251028_110700-Al_30sec_T2-1500-10-2.5.tdms_summary.csv

    Assumes the last three numeric tokens before '.tdms_summary' are:
        - power
        - frequency
        - another numeric parameter
    """
    base = os.path.basename(fname)
    name, _ = os.path.splitext(base)   # strips .csv, leaves ...tdms_summary

    # Try strict pattern first
    m = re.search(
        r'-([0-9]+(?:\.[0-9]+)?)-([0-9]+(?:\.[0-9]+)?)-[0-9]+(?:\.[0-9]+)?\.tdms_summary$',
        name
    )
    if m:
        try:
            power = float(m.group(1))
            freq = float(m.group(2))
            return power, freq
        except ValueError:
            return None, None

    # Fallback: last three numeric tokens
    nums = re.findall(r'(\d+(?:\.\d+)?)', name)
    if len(nums) >= 3:
        try:
            power = float(nums[-3])
            freq = float(nums[-2])
            return power, freq
        except ValueError:
            return None, None

    return None, None


def groups_minmax(groups):
    """Compute global power / frequency min/max for groups keyed by (power, freq)."""
    powers = [k[0] for k in groups.keys() if k[0] is not None]
    freqs = [k[1] for k in groups.keys() if k[1] is not None]
    pmin, pmax = (min(powers), max(powers)) if powers else (None, None)
    fmin, fmax = (min(freqs), max(freqs)) if freqs else (None, None)
    return pmin, pmax, fmin, fmax


def load_electrical_data(gui, folder):
    """
    Load electrical CSV files from folder into the gui.electrical_files and gui.electrical_groups.
    This is the logic previously inside DataLoaderGUI.load_electrical_folder.
    """
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".csv")]
    loaded = 0
    for fpath in files:
        try:
            df = pd.read_csv(fpath)
        except Exception:
            continue
        if not is_electrical_df(df):
            continue
        from data_loading import parse_power_freq_from_filename as _parse  # or just parse_power_freq_from_filename
        power, freq = _parse(fpath)
        gui.electrical_files.append({
            "path": fpath,
            "file": os.path.basename(fpath),
            "power": power,
            "freq": freq,
            "df": df
        })
        loaded += 1

    gui.electrical_groups.clear()
    for item in gui.electrical_files:
        key = (item["power"], item["freq"])
        gui.electrical_groups[key].append(item["df"])

    pmin, pmax, fmin, fmax = groups_minmax(gui.electrical_groups)
    gui.table.item(
        "electrical",
        values=(
            "Electrical Data",
            os.path.basename(folder),
            f"{pmin} – {pmax}" if pmin is not None else "N/A",
            f"{fmin} – {fmax}" if fmin is not None else "N/A",
            str(len(gui.electrical_files))
        )
    )
    return loaded


def load_oes_data(gui, folder):
    """
    Load OES CSV files from folder into gui.oes_files and gui.oes_groups.
    This is the logic previously inside DataLoaderGUI.load_oes_folder.
    """
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".csv")]
    loaded = 0
    for fpath in files:
        try:
            df = pd.read_csv(fpath)
        except Exception:
            continue
        if not is_oes_df(df):
            continue
        from data_loading import parse_power_freq_from_filename as _parse  # or just parse_power_freq_from_filename
        power, freq = _parse(fpath)

        cols_map = {c.strip().lower(): c for c in df.columns}
        if "wavelength_index" in cols_map:
            idx_col = cols_map["wavelength_index"]
        elif "wavelength index" in cols_map:
            idx_col = cols_map["wavelength index"]
        else:
            idx_col = df.columns[0]

        gui.oes_files.append({
            "path": fpath,
            "file": os.path.basename(fpath),
            "power": power,
            "freq": freq,
            "df": df,
            "idx_col": idx_col
        })
        loaded += 1

    gui.oes_groups.clear()
    for item in gui.oes_files:
        key = (item["power"], item["freq"])
        gui.oes_groups[key].append(item["df"])

    pmin, pmax, fmin, fmax = groups_minmax(gui.oes_groups)
    gui.table.item(
        "oes",
        values=(
            "OES Data",
            os.path.basename(folder),
            f"{pmin} – {pmax}" if pmin is not None else "N/A",
            f"{fmin} – {fmax}" if fmin is not None else "N/A",
            str(len(gui.oes_files))
        )
    )
    return loaded