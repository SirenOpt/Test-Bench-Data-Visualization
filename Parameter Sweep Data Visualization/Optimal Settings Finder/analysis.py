import numpy as np
import pandas as pd


def is_electrical_df(df):
    cols = [c.strip().lower() for c in df.columns]
    return ("order parameter" in cols) and ("mean" in cols)


def is_oes_df(df):
    cols = [c.strip().lower() for c in df.columns]
    return (
        ("wavelength_index" in cols)
        or ("wavelength index" in cols)
        or (len(df.columns) >= 1)
    ) and ("mean" in cols)


def normalize_dict_values_absolute(d):
    """
    Normalizes values using absolute value.
    Returns values in range [0, 1].
    """
    vals = np.array([abs(v) for v in d.values()], dtype=float)
    if vals.size == 0:
        return d.copy()

    denom = np.nanmax(vals)
    if denom == 0 or np.isnan(denom):
        return {k: 0.0 for k in d.keys()}

    return {k: abs(v) / denom for k, v in d.items()}


def process_data(gui, wavelengths):
    """
    This is the logic from DataLoaderGUI.find_optimal_range, but pulled out so
    the GUI method just parses wavelengths and calls this.
    Operates on gui.electrical_groups, gui.oes_groups, and fills:
        gui.electrical_averaged
        gui.electrical_normalized
        gui.oes_averaged
        gui.oes_normalized
    """
    # ---------- Electrical averaging ----------
    gui.electrical_averaged.clear()
    for key, dfs in gui.electrical_groups.items():
        canonical_dfs = []
        for df in dfs:
            cols_map = {c.strip().lower(): c for c in df.columns}
            if "order parameter" not in cols_map:
                continue

            idx_col = cols_map["order parameter"]

            def find_col(possible):
                for n in possible:
                    if n in cols_map:
                        return cols_map[n]
                return None

            mean_col = find_col(["mean"])
            cv_col   = find_col(["%cv", "cv", "cv_percent", "cv percent"])
            min_col  = find_col(["min"])
            max_col  = find_col(["max"])

            can = pd.DataFrame(index=df[idx_col].astype(str))
            can["Mean"] = pd.to_numeric(df[mean_col], errors="coerce").values if mean_col else np.nan
            can["%CV"]  = pd.to_numeric(df[cv_col],   errors="coerce").values if cv_col else np.nan
            can["Min"]  = pd.to_numeric(df[min_col],  errors="coerce").values if min_col else np.nan
            can["Max"]  = pd.to_numeric(df[max_col],  errors="coerce").values if max_col else np.nan
            can.index.name = "Order Parameter"
            canonical_dfs.append(can)

        if not canonical_dfs:
            continue

        concat = pd.concat(canonical_dfs, axis=0, keys=range(len(canonical_dfs)))
        avg = concat.groupby(level=1).mean()
        gui.electrical_averaged[key] = avg

    # Electrical normalization
    gui.electrical_normalized.clear()
    order_params = set()
    for df in gui.electrical_averaged.values():
        order_params.update(df.index.astype(str).tolist())
    stats = ["Mean", "%CV", "Min", "Max"]

    for op in order_params:
        for stat in stats:
            vals = {}
            for key, df in gui.electrical_averaged.items():
                if op in df.index and stat in df.columns:
                    v = df.loc[op, stat]
                    if pd.isna(v):
                        continue
                    vals[key] = float(v)
            if vals:
                norm = normalize_dict_values_absolute(vals)
                # Invert %CV only
                if stat == "%CV":
                    norm = {k: 1 - v for k, v in norm.items()}
                gui.electrical_normalized[(op, stat)] = norm

    # ---------- OES averaging ----------
    gui.oes_averaged.clear()
    for key, dfs in gui.oes_groups.items():
        canon = []
        for df in dfs:
            cols_map = {c.strip().lower(): c for c in df.columns}

            if "wavelength_index" in cols_map:
                idx_col = cols_map["wavelength_index"]
            elif "wavelength index" in cols_map:
                idx_col = cols_map["wavelength index"]
            else:
                idx_col = df.columns[0]

            mean_col = cols_map.get("mean")
            std_col = cols_map.get("std_dev") or cols_map.get("std dev") or cols_map.get("std")
            cv_col  = cols_map.get("cv_percent") or cols_map.get("cv percent") or cols_map.get("cv")

            can = pd.DataFrame()
            try:
                can["wavelength_index"] = df[idx_col].astype(int).values
            except Exception:
                can["wavelength_index"] = np.arange(len(df))

            can["mean"] = pd.to_numeric(df[mean_col], errors="coerce").values if mean_col else np.nan
            can["std_dev"] = pd.to_numeric(df[std_col], errors="coerce").values if std_col else np.nan
            can["cv_percent"] = pd.to_numeric(df[cv_col], errors="coerce").values if cv_col else np.nan

            can = can.set_index("wavelength_index")
            canon.append(can)

        if canon:
            concat = pd.concat(canon, axis=0, keys=range(len(canon)))
            avg = concat.groupby(level=1).mean()
            gui.oes_averaged[key] = avg

    # ---------- OES normalization ----------
    gui.oes_normalized.clear()
    if wavelengths:
        for wl in wavelengths:
            statmaps = {"mean": {}, "std_dev": {}, "cv_percent": {}, "SNR": {}}
            for key, df in gui.oes_averaged.items():
                if wl in df.index:
                    m = df.loc[wl, "mean"] if "mean" in df.columns else np.nan
                    s = df.loc[wl, "std_dev"] if "std_dev" in df.columns else np.nan
                    cv = df.loc[wl, "cv_percent"] if "cv_percent" in df.columns else np.nan

                    if not pd.isna(m):
                        statmaps["mean"][key] = float(m)
                    if not pd.isna(s):
                        statmaps["std_dev"][key] = float(s)
                    if not pd.isna(cv):
                        statmaps["cv_percent"][key] = float(cv)
                    if (not pd.isna(m)) and (not pd.isna(s)) and s != 0:
                        statmaps["SNR"][key] = float(abs(m / s))

            for stat, mapping in statmaps.items():
                if mapping:
                    norm = normalize_dict_values_absolute(mapping)
                    # Invert metrics where lower is better
                    if stat in ("std_dev", "cv_percent"):
                        norm = {k: 1 - v for k, v in norm.items()}
                    gui.oes_normalized[(wl, stat)] = norm