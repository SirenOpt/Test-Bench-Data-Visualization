import pandas as pd
import os, json

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

class DataManager:
    """
    Manages datasets loaded from folders and their metadata (groups, tags, filenames).
    """

    def __init__(self):
        self.dataframes = []      # list of pd.DataFrame
        self.file_names = []      # parallel list of filenames
        self.groups = []          # integer group id per dataframe
        self.group_tags = []      # human-friendly tag per group (parallel to dataframes)
        self.group_folders = []   # folder each dataframe came from
        self.original_groups = []
        self.original_tags = []

    def clear_all(self):
        self.__init__()

    def _valid_df(self, df):
        return {"wavelength_index", "mean", "std_dev", "cv_percent"}.issubset(df.columns)

    def add_data_set_from_folder(self, folder, tag=None, group_id=None):
        """
        Load CSV files inside `folder`. Returns number of files loaded.
        The caller (GUI) handles asking user for folder and tag.
        """
        loaded = 0
        if group_id is None:
            group_id = len(set(self.groups)) + 1
        csv_files = [f for f in os.listdir(folder) if f.lower().endswith('.csv')]
        for f in csv_files:
            path = os.path.join(folder, f)
            try:
                df = pd.read_csv(path)
                if self._valid_df(df):
                    df['wavelength_index'] = pd.to_numeric(df['wavelength_index'], errors='coerce')
                    df = df.dropna(subset=['wavelength_index']).copy()
                    self.dataframes.append(df)
                    self.file_names.append(f)
                    self.groups.append(group_id)
                    self.group_tags.append(tag if tag is not None else f"Group {group_id}")
                    self.group_folders.append(folder)
                    loaded += 1
            except Exception:
                # caller (GUI) should show error messages to user if necessary
                continue
        if loaded > 0:
            self.original_groups.extend([group_id] * loaded)
            self.original_tags.extend([tag if tag is not None else f"Group {group_id}"] * loaded)
        return loaded

    def reset_tags(self):
        self.group_tags = [f"Group {g}" for g in self.groups]

    def reset_groups(self):
        if self.original_groups:
            self.groups = self.original_groups.copy()
            self.group_tags = self.original_tags.copy()