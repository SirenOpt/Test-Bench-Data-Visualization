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


def compute_variance_tables(dataframes, groups, group_tags):
    order_params, group_ids, _ = compute_group_summaries(dataframes, groups)
    variance_tables = {}
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
                if len(vals) < 2 or np.mean(vals) == 0:
                    row[col] = np.nan
                else:
                    row[col] = float(abs(np.std(vals, ddof=1) / np.mean(vals) * 100.0))
            rows.append(row)
        label = next((t for i, t in enumerate(group_tags) if groups[i] == g), str(g))
        variance_tables[f"Group {g}: {label}"] = pd.DataFrame(rows)
    return variance_tables
