import numpy as np
import matplotlib.pyplot as plt
from itertools import cycle
from tkinter import messagebox


def plot_parameter(figure, dataframes, groups, group_tags, param):
    x_pts, means, cvs, mins, maxs, errors, tags = [], [], [], [], [], [], []
    for df, grp, tag in zip(dataframes, groups, group_tags):
        r = df[df["Order Parameter"] == param]
        if not r.empty:
            mean = float(r["Mean"].iloc[0])
            cv = float(r["%CV"].iloc[0])
            mn = float(r["Min"].iloc[0])
            mx = float(r["Max"].iloc[0])
            err = abs(mean * (cv / 100.0))
            x_pts.append(grp)
            means.append(mean)
            cvs.append(cv)
            mins.append(mn)
            maxs.append(mx)
            errors.append(err)
            tags.append(tag)

    figure.clf()
    ax1 = figure.add_subplot(121)
    ax2 = figure.add_subplot(122)

    unique_groups = sorted(set(x_pts))
    if not unique_groups:
        messagebox.showwarning("No Data", f"No entries for '{param}' found.")
        return

    color_cycle = cycle(plt.cm.tab10.colors)
    gcols = {g: next(color_cycle) for g in unique_groups}
    tagmap = {g: next((t for i, t in enumerate(tags) if x_pts[i] == g), str(g)) for g in unique_groups}

    jitter = 0.15
    for g in unique_groups:
        idxs = [i for i, v in enumerate(x_pts) if v == g]
        offs = np.linspace(-jitter, jitter, len(idxs)) if len(idxs) > 1 else [0.0]
        xj = [g + o for o in offs]
        ax1.errorbar(xj, np.array(means)[idxs], yerr=np.array(errors)[idxs], fmt="o", color="blue", capsize=5)
        ax1.scatter(xj, np.array(maxs)[idxs], color="green", marker="^")
        ax1.scatter(xj, np.array(mins)[idxs], color="red", marker="v")
        ax2.scatter(xj, np.array(cvs)[idxs], color=gcols[g], label=tagmap[g])

    pname = param.lower()
    ylabel = "Amps (A)" if "current" in pname else ("Volts (V)" if "voltage" in pname else "Value")
    ax1.set_ylabel(ylabel)
    ax2.set_ylabel("CV (%)")
    ax1.set_xticks(unique_groups)
    ax1.set_xticklabels([tagmap[g] for g in unique_groups])
    ax2.set_xticks(unique_groups)
    ax2.set_xticklabels([tagmap[g] for g in unique_groups])

    ax1.scatter([], [], color="blue", marker="o", label="Mean (±Error)")
    ax1.scatter([], [], color="green", marker="^", label="Max")
    ax1.scatter([], [], color="red", marker="v", label="Min")
    ax1.legend(loc="upper left", bbox_to_anchor=(1.05, 1))
    ax2.legend(loc="upper left", bbox_to_anchor=(1.05, 1))

    ax1.set_title(param)
    ax2.set_title(f"{param} – CV%")
    figure.tight_layout(rect=[0, 0, 0.92, 1])