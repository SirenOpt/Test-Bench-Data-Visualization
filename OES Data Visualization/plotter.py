import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

def plot_oes_data(dataframes, groups, group_tags, wavelengths):
    if not dataframes:
        raise ValueError("No dataframes provided")

    wl_sorted = sorted(wavelengths)
    xpos = np.arange(len(wl_sorted))
    colors = plt.cm.tab10.colors
    tags = sorted(set(group_tags))
    cmap = {tag: colors[i % len(colors)] for i, tag in enumerate(tags)}

    grps = sorted(set(groups))
    offsets = np.linspace(-0.3, 0.3, len(grps)) if len(grps) > 1 else [0.0]
    g_off = dict(zip(grps, offsets))
    rng = np.random.default_rng(42)
    jitter = 0.05

    # ---- Main figure (OES intensity + CV%)
    main_fig = Figure(figsize=(10, 8), dpi=100)
    ax1, ax2 = main_fig.subplots(1, 2)

    plotted_tags = set()
    for df, g, t in zip(dataframes, groups, group_tags):
        sub = df[df["wavelength_index"].isin(wl_sorted)].sort_values("wavelength_index")
        if sub.empty:
            continue

        j = rng.uniform(-jitter, jitter, len(sub))
        base = g_off[g]
        sub["x"] = [xpos[wl_sorted.index(w)] + base + j[i] for i, w in enumerate(sub["wavelength_index"])]
        label = t if t not in plotted_tags else None
        plotted_tags.add(t)

        ax1.errorbar(sub["x"], sub["mean"], yerr=sub["std_dev"], fmt="o",
                     color=cmap[t], capsize=4, markersize=4, label=label)
        ax2.plot(sub["x"], sub["cv_percent"], "o", color=cmap[t], markersize=4, label=label)

    for ax in (ax1, ax2):
        ax.legend(title="Data Set", fontsize=8, bbox_to_anchor=(1.05, 1), loc="upper left")
        ax.set_xticks(xpos)
        ax.set_xticklabels([str(w) for w in wl_sorted])
        ax.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("OES Intensity (Mean ± Std Dev)")
    ax1.set_title("OES Intensity vs Wavelength")
    ax2.set_ylabel("CV (%)")
    ax2.set_title("CV% vs Wavelength")
    main_fig.tight_layout()

    return main_fig