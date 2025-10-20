import os
import pandas as pd
from tkinter import messagebox, simpledialog, filedialog


def load_data_folder(root, initial_path, next_group_id):
    folder = filedialog.askdirectory(initialdir=initial_path, title="Select Data Set Folder")
    if not folder:
        return None
    tag = simpledialog.askstring("Group Tag", "Enter a tag for this data set (optional):", parent=root)
    if tag is None:
        return None
    if tag.strip() == "":
        tag = f"{next_group_id}"

    new_group_id = next_group_id
    csv_files = [f for f in os.listdir(folder) if f.lower().endswith(".csv")]
    if not csv_files:
        messagebox.showwarning("No CSVs", f"No CSV files found in {folder}")
        return None

    dfs, fnames, groups, tags, folders = [], [], [], [], []
    for fname in csv_files:
        try:
            df = pd.read_csv(os.path.join(folder, fname))
            if set(["Order Parameter", "Mean", "%CV", "Min", "Max"]).issubset(df.columns):
                dfs.append(df)
                fnames.append(fname)
                groups.append(new_group_id)
                tags.append(tag)
                folders.append(os.path.basename(folder))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load {fname}\n\n{e}")

    return dfs, fnames, groups, tags, folders


def clear_all_data(app):
    app.dataframes.clear()
    app.file_names.clear()
    app.groups.clear()
    app.original_groups.clear()
    app.group_tags.clear()
    app.group_folders.clear()