import numpy as np
import pandas as pd
from scipy.stats import ttest_ind_from_stats

def compute_group_summaries(dataframes, groups):
    order_params = sorted({p for df in dataframes for p in df["Order Parameter"].dropna()})
    group_ids = sorted(set(groups))
    group_summary = {g: {} for g in group_ids}
    for g in group_ids:
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]
        n_files = len(group_dfs)
        for param in order_params:
            vals = {k: [] for k in ["Mean", "%CV", "Min", "Max"]}
            for df in group_dfs:
                r = df[df["Order Parameter"] == param]
                if not r.empty:
                    for k in vals:
                        vals[k].extend(r[k].astype(float).tolist())
            means = {k: (np.mean(vals[k]) if vals[k] else np.nan) for k in vals}
            std_est = abs(means["Mean"] * (means["%CV"] / 100.0)) if not np.isnan(means["%CV"]) else np.nan
            group_summary[g][param] = {**means, "n": n_files, "std": std_est}
    return order_params, group_ids, group_summary


def compute_pvalue_tables(dataframes, groups, group_tags):
    order_params, group_ids, group_summary = compute_group_summaries(dataframes, groups)
    tables = {}
    if len(group_ids) < 2:
        return tables
    tag_map = {g: next((t for i, t in enumerate(group_tags) if groups[i] == g), f"Group {g}") for g in group_ids}
    for i in range(len(group_ids)):
        for j in range(i + 1, len(group_ids)):
            g1, g2 = group_ids[i], group_ids[j]
            label = f"{tag_map[g1]} vs {tag_map[g2]}"
            rows = []
            for param in order_params:
                row = {"Order Parameter": param}
                for col in ["Mean", "%CV", "Min", "Max"]:
                    e1, e2 = group_summary[g1][param], group_summary[g2][param]
                    m1, s1, n1 = e1[col], e1["std"], e1["n"]
                    m2, s2, n2 = e2[col], e2["std"], e2["n"]
                    if n1 <= 0 or n2 <= 0 or np.isnan(m1) or np.isnan(m2) or np.isnan(s1) or np.isnan(s2):
                        row[col] = np.nan
                    else:
                        try:
                            _, p = ttest_ind_from_stats(m1, s1, n1, m2, s2, n2, equal_var=False)
                            row[col] = float(p) if not np.isnan(p) else np.nan
                        except Exception:
                            row[col] = np.nan
                rows.append(row)
            tables[label] = pd.DataFrame(rows)
    return tables



def compute_mean_tables(dataframes, groups, group_tags):
    order_params, group_ids, _ = compute_group_summaries(dataframes, groups)
    mean_tables = {}

    for g in group_ids:
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]
        rows = []

        for param in order_params:
            row = {"Order Parameter": param}
            for col in ["Mean", "%CV", "Min", "Max"]:
                vals = []
                for df in group_dfs:
                    r = df[df["Order Parameter"] == param]
                    if not r.empty:
                        vals.extend(r[col].astype(float).tolist())
                
                row[col] = float(np.mean(vals)) if len(vals) > 0 else np.nan

            rows.append(row)

        label = next((t for i, t in enumerate(group_tags) if groups[i] == g), str(g))
        mean_tables[f"Group {g}: {label}"] = pd.DataFrame(rows)
    return mean_tables

def compute_group_cv_tables(dataframes, groups, group_tags):
    """
    Compute Group %CV directly from the input data, without using summaries.
    CV = (Population STD / Mean) * 100
    Works on Mean, Min, and Max columns for each Order Parameter.
    """

    group_ids = sorted(set(groups))
    cv_tables = {}

    # Determine all order parameters across all files
    order_params = sorted(
        set().union(*[df["Order Parameter"].unique() for df in dataframes])
    )

    for g in group_ids:
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]
        rows = []

        for param in order_params:
            row = {"Order Parameter": param}

            for col in ["Mean", "Min", "Max"]:
                # Collect all values for this parameter and column
                vals = []
                for df in group_dfs:
                    r = df[df["Order Parameter"] == param]
                    if not r.empty and col in r.columns:
                        try:
                            vals.extend(r[col].astype(float).tolist())
                        except Exception:
                            pass

                # Compute CV = (STD / MEAN) * 100
                if len(vals) > 1:
                    mean_val = np.mean(vals)
                    std_val = np.std(vals, ddof=0)
                    cv = (std_val / mean_val) * 100 if mean_val != 0 else np.nan
                else:
                    cv = np.nan

                # Only store the percent value
                row[f"{col} (Group %CV)"] = round(cv, 3) if not np.isnan(cv) else ""

            rows.append(row)

        label = next((t for i, t in enumerate(group_tags) if groups[i] == g), str(g))
        cv_tables[f"Group {g}: {label}"] = pd.DataFrame(rows)

    return cv_tables

def compute_drift_first_last_tables(dataframes, groups, group_tags):
    """
    Computes % Drift (First–Last) for each statistic:
    Mean, %CV, Min, Max
    
    Drift = (last - first) / last * 100
    """

    group_ids = sorted(set(groups))
    drift_tables = {}

    order_params = sorted(
        set().union(*[df["Order Parameter"].dropna().unique() for df in dataframes])
    )

    for g in group_ids:
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]

        rows = []
        for param in order_params:

            col_series = {col: [] for col in ["Mean", "%CV", "Min", "Max"]}

            for df in group_dfs:
                r = df[df["Order Parameter"] == param]
                if not r.empty:
                    for col in col_series:
                        try:
                            col_series[col].append(float(r[col].iloc[0]))
                        except:
                            pass

            drift_row = {"Order Parameter": param}

            for col in ["Mean", "%CV", "Min", "Max"]:
                values = col_series[col]
                if len(values) >= 2:
                    first, last = values[0], values[-1]
                    drift = ((last - first) / last * 100) if last != 0 else float("nan")
                else:
                    drift = float("nan")

                drift_row[col] = drift

            rows.append(drift_row)

        label = next((t for i, t in enumerate(group_tags) if groups[i] == g), str(g))
        drift_tables[f"Group {g}: {label}"] = pd.DataFrame(rows)

    return drift_tables

def compute_drift_min_max_tables(dataframes, groups, group_tags):
    """
    Computes % Drift (Min–Max) for each statistic:
    Mean, %CV, Min, Max
    
    Drift = (min_val - max_val) / max_val * 100
    """

    group_ids = sorted(set(groups))
    drift_tables = {}

    order_params = sorted(
        set().union(*[df["Order Parameter"].dropna().unique() for df in dataframes])
    )

    for g in group_ids:
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]

        rows = []
        for param in order_params:

            col_series = {col: [] for col in ["Mean", "%CV", "Min", "Max"]}

            # collect all values for each stat
            for df in group_dfs:
                r = df[df["Order Parameter"] == param]
                if not r.empty:
                    for col in col_series:
                        try:
                            col_series[col].append(float(r[col].iloc[0]))
                        except:
                            pass

            drift_row = {"Order Parameter": param}

            for col in ["Mean", "%CV", "Min", "Max"]:
                values = col_series[col]
                if len(values) >= 2:
                    min_val = min(values)
                    max_val = max(values)
                    drift = ((min_val - max_val) / max_val * 100) if max_val != 0 else float("nan")
                else:
                    drift = float("nan")

                drift_row[col] = drift

            rows.append(drift_row)

        label = next((t for i, t in enumerate(group_tags) if groups[i] == g), str(g))
        drift_tables[f"Group {g}: {label}"] = pd.DataFrame(rows)

    return drift_tables