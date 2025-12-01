import pandas as pd
import os, json, re

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
    tokens = re.findall(r'\d+(?:\.\d+)?', fname)
    if len(tokens) >= 3:
        return tokens[-3], tokens[-2]
    elif len(tokens) >= 2:
        return tokens[-2], tokens[-1]
    else:
        return None, None

class DataManager:
    def __init__(self):
        self.dataframes = []
        self.file_names = []
        self.groups_power = []
        self.groups_freq = []
        self.auto_tags = []
        self.group_folders = []

    def clear_all(self):
        self.__init__()

    def _valid_df(self, df):
        return {"wavelength_index", "mean", "std_dev", "cv_percent"}.issubset(df.columns)

    def add_data_set_from_folder_auto(self, folder):
        loaded = 0
        csv_files = [f for f in os.listdir(folder) if f.lower().endswith(".csv")]
        for f in csv_files:
            path = os.path.join(folder, f)
            try:
                df = pd.read_csv(path)
                if self._valid_df(df):
                    p, freq = parse_power_freq_from_filename(f)
                    tag = f"P{p}_F{freq}" if (p and freq) else "Unknown"
                    df['wavelength_index'] = pd.to_numeric(df['wavelength_index'], errors='coerce')
                    df = df.dropna(subset=['wavelength_index']).copy()
                    self.dataframes.append(df)
                    self.file_names.append(f)
                    self.groups_power.append(p)
                    self.groups_freq.append(freq)
                    self.auto_tags.append(tag)
                    self.group_folders.append(folder)
                    loaded += 1
            except Exception:
                continue
        return loaded