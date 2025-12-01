import pandas as pd
import numpy as np
from itertools import combinations
from scipy.stats import ttest_ind_from_stats

def calculate_group_means(dataframes, groups, wavelengths):
    """
    Returns a dictionary:
      group_id -> {wavelength -> {'mean': ..., 'std_dev': ..., 'cv_percent': ...}}
    """
    result = {}
    for g in sorted(set(groups)):
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]
        result[g] = {}
        for wl in wavelengths:
            # collect values from all dfs in the group
            means = []
            stds = []
            cvs = []
            for df in group_dfs:
                row = df[df["wavelength_index"] == wl]
                if not row.empty:
                    means.append(row["mean"].values[0])
                    stds.append(row["std_dev"].values[0])
                    cvs.append(row["cv_percent"].values[0])
            if means:
                result[g][wl] = {
                    "mean": np.mean(means),
                    "std_dev": np.mean(stds),
                    "cv_percent": np.mean(cvs)
                }
            else:
                result[g][wl] = {"mean": np.nan, "std_dev": np.nan, "cv_percent": np.nan}
    return result

def calculate_group_cv(dataframes, groups, wavelengths):
    """
    Returns a dictionary:
      group_id -> {wavelength -> CV% of mean values in the group}
    """
    result = {}
    for g in sorted(set(groups)):
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]
        result[g] = {}
        for wl in wavelengths:
            means = [df[df["wavelength_index"] == wl]["mean"].values[0]
                     for df in group_dfs if not df[df["wavelength_index"] == wl].empty]
            if means:
                mean_val = np.mean(means)
                std_val = np.std(means, ddof=1)
                cv_percent = (std_val / mean_val) * 100 if mean_val != 0 else np.nan
                result[g][wl] = cv_percent
            else:
                result[g][wl] = np.nan
    return result

def calculate_group_cv_normalized(dataframes, groups, wavelengths):
    """
    Normalizes each dataset by the sum of all its means across wavelengths, then computes CV%.
    Returns:
      group_id -> {wavelength -> CV%}
    """
    result = {}
    for g in sorted(set(groups)):
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]
        result[g] = {}
        for wl in wavelengths:
            norm_means = []
            for df in group_dfs:
                row = df[df["wavelength_index"] == wl]
                if not row.empty:
                    total = df["mean"].sum()
                    norm_mean = row["mean"].values[0] / total if total != 0 else 0
                    norm_means.append(norm_mean)
            if norm_means:
                mean_val = np.mean(norm_means)
                std_val = np.std(norm_means, ddof=1)
                cv_percent = (std_val / mean_val) * 100 if mean_val != 0 else np.nan
                result[g][wl] = cv_percent
            else:
                result[g][wl] = np.nan
    return result

def calculate_group_pvalues(dataframes, groups, wavelengths):
    """
    Returns a nested dictionary:
      (group1, group2) -> {wavelength -> p-value}
    Uses t-test with means and std of normalized data.
    """
    group_norm_means = {g: {} for g in sorted(set(groups))}

    # Precompute normalized means
    for g in sorted(set(groups)):
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]
        for wl in wavelengths:
            norm_means = []
            for df in group_dfs:
                row = df[df["wavelength_index"] == wl]
                if not row.empty:
                    total = df["mean"].sum()
                    norm_mean = row["mean"].values[0] / total if total != 0 else 0
                    norm_means.append(norm_mean)
            group_norm_means[g][wl] = norm_means

    # Calculate p-values
    pvalues = {}
    for g1, g2 in combinations(sorted(set(groups)), 2):
        pvalues[(g1, g2)] = {}
        for wl in wavelengths:
            vals1 = group_norm_means[g1][wl]
            vals2 = group_norm_means[g2][wl]
            if len(vals1) < 2 or len(vals2) < 2:
                pvalues[(g1, g2)][wl] = np.nan
            else:
                mean1, std1, n1 = np.mean(vals1), np.std(vals1, ddof=1), len(vals1)
                mean2, std2, n2 = np.mean(vals2), np.std(vals2, ddof=1), len(vals2)
                t_stat, p_val = ttest_ind_from_stats(mean1, std1, n1, mean2, std2, n2)
                pvalues[(g1, g2)][wl] = p_val
    return pvalues

def calculate_group_pvalues_raw(dataframes, groups, wavelengths):
    """
    Calculates p-values using raw mean values for each wavelength.
    Returns a nested dictionary:
      (group1, group2) -> {wavelength -> p-value}
    """
    # Organize data per group
    group_means = {g: {} for g in sorted(set(groups))}
    for g in sorted(set(groups)):
        group_dfs = [df for df, grp in zip(dataframes, groups) if grp == g]
        for wl in wavelengths:
            vals = [df[df["wavelength_index"]==wl]["mean"].values[0]
                    for df in group_dfs if not df[df["wavelength_index"]==wl].empty]
            group_means[g][wl] = vals

    # Compute t-test between groups
    pvalues = {}
    for g1, g2 in combinations(sorted(set(groups)), 2):
        pvalues[(g1,g2)] = {}
        for wl in wavelengths:
            vals1 = group_means[g1][wl]
            vals2 = group_means[g2][wl]
            if len(vals1) < 2 or len(vals2) < 2:
                pvalues[(g1,g2)][wl] = np.nan
            else:
                mean1, std1, n1 = np.mean(vals1), np.std(vals1, ddof=1), len(vals1)
                mean2, std2, n2 = np.mean(vals2), np.std(vals2, ddof=1), len(vals2)
                _, pv = ttest_ind_from_stats(mean1, std1, n1, mean2, std2, n2)
                pvalues[(g1,g2)][wl] = pv
    return pvalues

def calculate_signal_to_noise(dataframes, groups, group_tags, peak_wavelengths):
    """
    For each requested peak_wavelength, compute average signal-to-noise ratio per group:
      SNR per dataset = |mean / std_dev| at that wavelength (if std != 0)
      Then average SNR across datasets in the group.
    Returns dict:
      { peak_wavelength: { group_tag: avg_snr, ... }, ... }
    """
    if not dataframes:
        return {}

    results = {}
    groups_sorted = sorted(set(groups))

    # Map group number -> tag (first occurrence)
    tags_by_group = {}
    for g in groups_sorted:
        idx = next((i for i, grp in enumerate(groups) if grp == g), None)
        tags_by_group[g] = group_tags[idx] if idx is not None else f"Group {g}"

    for peak in peak_wavelengths:
        peak = float(peak)
        snr_per_group = {}
        for g in groups_sorted:
            idxs = [i for i, grp in enumerate(groups) if grp == g]
            group_dfs = [dataframes[i] for i in idxs]
            snrs = []
            for df in group_dfs:
                # If exact wavelength present, use it; otherwise interpolate mean/std
                if peak in df['wavelength_index'].values:
                    row = df.loc[df['wavelength_index'] == peak].iloc[0]
                    mean_val = float(row['mean'])
                    std_val = float(row['std_dev'])
                else:
                    # Interpolate using available wavelengths
                    x = df['wavelength_index'].values.astype(float)
                    y_mean = df['mean'].values.astype(float)
                    y_std = df['std_dev'].values.astype(float)
                    if x.size < 2:
                        continue
                    mean_val = float(np.interp(peak, x, y_mean, left=np.nan, right=np.nan))
                    std_val = float(np.interp(peak, x, y_std, left=np.nan, right=np.nan))
                if not np.isnan(mean_val) and not np.isnan(std_val) and std_val != 0:
                    snrs.append(abs(mean_val / std_val))
            snr_per_group[tags_by_group[g]] = (np.mean(snrs) if snrs else np.nan)
        results[peak] = snr_per_group

    return results

def calculate_group_std_and_rsd_by_wavelength(dataframes, groups, dataset_tags, peak_wavelengths):
    """
    For each group and requested peak_wavelength, compute both:
      - Standard Deviation (STD)
      - Relative Standard Deviation (RSD = (STD / mean) * 100)
    of the raw mean intensity values across all datasets in that group.

    Returns:
      {
        group_label: {
          wavelength: {"STD": std_val, "RSD": rsd_val},
          ...
        },
        ...
      }
    """
    if not dataframes or not groups or not dataset_tags:
        return {}

    # Keep group order consistent with input
    unique_groups_in_order = []
    for g in groups:
        if g not in unique_groups_in_order:
            unique_groups_in_order.append(g)

    idxs_by_group = {g: [i for i, gg in enumerate(groups) if gg == g] for g in unique_groups_in_order}

    # Group label mapping
    group_labels = {}
    for g, idxs in idxs_by_group.items():
        first_tag = dataset_tags[idxs[0]] if idxs else None
        group_labels[g] = first_tag if first_tag else f"Group {g}"

    results = {}

    for g in unique_groups_in_order:
        idxs = idxs_by_group[g]
        if not idxs:
            continue

        group_label = group_labels[g]
        group_result = {}

        # Collect wavelength and mean data for each dataset
        ds_series = {}
        for i in idxs:
            df = dataframes[i]
            wl = df['wavelength_index'].to_numpy(dtype=float)
            mean_vals = df['mean'].to_numpy(dtype=float)
            ds_series[i] = (wl, mean_vals)

        # Compute STD and RSD for each wavelength
        for peak in map(float, peak_wavelengths):
            ds_values = []
            for i in idxs:
                wl, vals = ds_series[i]
                if wl.size == 0:
                    ds_values.append(np.nan)
                else:
                    ds_values.append(np.interp(peak, wl, vals, left=np.nan, right=np.nan))

            vals_array = np.array(ds_values, dtype=float)
            if np.any(~np.isnan(vals_array)):
                mean_val = np.nanmean(vals_array)
                std_val = np.nanstd(vals_array, ddof=1)
                if mean_val != 0 and not np.isnan(mean_val):
                    rsd_val = (std_val / mean_val) * 100.0
                else:
                    rsd_val = np.nan
            else:
                std_val = np.nan
                rsd_val = np.nan

            group_result[peak] = {"STD": std_val, "RSD": rsd_val}

        results[group_label] = group_result

    return results

def calculate_group_drift_first_last(dataframes, groups, dataset_tags, peak_wavelengths):
    """
    For each group and requested peak_wavelength, compute the percent drift
    between the first and last dataset in that group:

        % Drift = ((Last Value - First Value) / Last Value) * 100

    Values are based on the raw 'mean' values at the given wavelength.
    Linear interpolation is used if the wavelength isn't exactly present.
    """
    if not dataframes or not groups or not dataset_tags:
        return {}

    # Keep order stable
    unique_groups_in_order = []
    for g in groups:
        if g not in unique_groups_in_order:
            unique_groups_in_order.append(g)

    idxs_by_group = {g: [i for i, gg in enumerate(groups) if gg == g] for g in unique_groups_in_order}
    group_labels = {g: dataset_tags[idxs[0]] if idxs else f"Group {g}" for g, idxs in idxs_by_group.items()}

    results = {}

    for g in unique_groups_in_order:
        idxs = idxs_by_group[g]
        if len(idxs) < 2:
            continue  # Need at least two datasets to compute drift

        group_label = group_labels[g]
        group_result = {}

        # Build list of interpolated means for each dataset
        ds_series = []
        for i in idxs:
            df = dataframes[i]
            wl = df['wavelength_index'].to_numpy(dtype=float)
            mean_vals = df['mean'].to_numpy(dtype=float)
            ds_series.append((wl, mean_vals))

        for peak in map(float, peak_wavelengths):
            interpolated = []
            for wl, vals in ds_series:
                if wl.size > 0:
                    interpolated.append(np.interp(peak, wl, vals, left=np.nan, right=np.nan))
                else:
                    interpolated.append(np.nan)

            interpolated = np.array(interpolated, dtype=float)
            if np.all(np.isnan(interpolated)):
                group_result[peak] = np.nan
            else:
                first_val = interpolated[0]
                last_val = interpolated[-1]
                if last_val != 0 and not np.isnan(first_val) and not np.isnan(last_val):
                    drift = ((last_val - first_val) / last_val) * 100.0
                else:
                    drift = np.nan
                group_result[peak] = drift

        results[group_label] = group_result

    return results

def calculate_group_drift_min_max(dataframes, groups, dataset_tags, peak_wavelengths):
    """
    For each group and requested peak_wavelength, compute the percent drift
    between the minimum and maximum dataset values in that group:

        % Drift = ((Min Value - Max Value) / Max Value) * 100

    Uses raw 'mean' values at the given wavelength.
    """
    if not dataframes or not groups or not dataset_tags:
        return {}

    unique_groups_in_order = []
    for g in groups:
        if g not in unique_groups_in_order:
            unique_groups_in_order.append(g)

    idxs_by_group = {g: [i for i, gg in enumerate(groups) if gg == g] for g in unique_groups_in_order}
    group_labels = {g: dataset_tags[idxs[0]] if idxs else f"Group {g}" for g, idxs in idxs_by_group.items()}

    results = {}

    for g in unique_groups_in_order:
        idxs = idxs_by_group[g]
        if len(idxs) < 2:
            continue  # Need at least two datasets to compute drift

        group_label = group_labels[g]
        group_result = {}

        ds_series = []
        for i in idxs:
            df = dataframes[i]
            wl = df['wavelength_index'].to_numpy(dtype=float)
            mean_vals = df['mean'].to_numpy(dtype=float)
            ds_series.append((wl, mean_vals))

        for peak in map(float, peak_wavelengths):
            interpolated = []
            for wl, vals in ds_series:
                if wl.size > 0:
                    interpolated.append(np.interp(peak, wl, vals, left=np.nan, right=np.nan))
                else:
                    interpolated.append(np.nan)

            interpolated = np.array(interpolated, dtype=float)
            if np.all(np.isnan(interpolated)):
                group_result[peak] = np.nan
            else:
                max_val = np.nanmax(interpolated)
                min_val = np.nanmin(interpolated)
                if max_val != 0 and not np.isnan(max_val) and not np.isnan(min_val):
                    drift = ((min_val - max_val) / max_val) * 100.0
                else:
                    drift = np.nan
                group_result[peak] = drift

        results[group_label] = group_result

    return results