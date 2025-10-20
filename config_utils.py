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