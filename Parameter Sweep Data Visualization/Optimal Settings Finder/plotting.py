# plotting.py
import numpy as np
from matplotlib import cm
import numpy.ma as ma


def build_grid_from_map(mapping):
    """
    mapping: dict[(power,freq)] -> value
    Returns:
      powers_sorted, freqs_sorted, grid (2D array shape (len(powers), len(freqs))) with np.nan where missing
    """
    if not mapping:
        return [], [], np.array([[]])
    powers = sorted({k[0] for k in mapping.keys() if k[0] is not None})
    freqs  = sorted({k[1] for k in mapping.keys() if k[1] is not None})
    if not powers or not freqs:
        return powers, freqs, np.full((len(powers), len(freqs)), np.nan)

    grid = np.full((len(powers), len(freqs)), np.nan)
    pidx = {p: i for i, p in enumerate(powers)}
    fidx = {f: i for i, f in enumerate(freqs)}

    for (p, f), v in mapping.items():
        if p in pidx and f in fidx:
            grid[pidx[p], fidx[f]] = v

    return powers, freqs, grid


def clear_plot_gui(gui):
    """Clear the current plot, uncheck all boxes, and reset to placeholder text."""
    # Uncheck electrical
    for var in gui.elec_check_vars.values():
        var.set(0)
    # Uncheck OES
    for var in gui.oes_check_vars.values():
        var.set(0)

    # Full reset of figure and axes
    gui.fig.clf()
    gui.ax = gui.fig.add_subplot(111)

    gui.ax.text(
        0.5, 0.5,
        "Plot cleared.\nClick 'Process Data', select parameters,\nthen 'Find Optimal Range' to plot.",
        ha="center", va="center", fontsize=12
    )

    gui.canvas.draw()


def update_heatmap_gui(gui):
    """
    Build and plot the heatmap based on the current checkbox selections.
    Assumes gui.electrical_normalized and gui.oes_normalized have been
    populated by process_data().
    """
    combined_map = {}
    any_selected = False

    # Electrical selections
    for (op, stat), var in gui.elec_check_vars.items():
        if var.get():
            any_selected = True
            mapping = gui.electrical_normalized.get((op, stat), {})
            for k, v in mapping.items():
                combined_map[k] = combined_map.get(k, 0.0) + float(v)

    # OES selections
    for (wl, stat), var in gui.oes_check_vars.items():
        if var.get():
            any_selected = True
            mapping = gui.oes_normalized.get((wl, stat), {})
            for k, v in mapping.items():
                combined_map[k] = combined_map.get(k, 0.0) + float(v)

    # Completely reset the figure and axes (no old colorbars, no old axes)
    gui.fig.clf()
    gui.ax = gui.fig.add_subplot(111)

    if not any_selected:
        gui.ax.text(
            0.5, 0.5,
            "No parameters selected.\nCheck boxes on the right, then click 'Find Optimal Range'.",
            ha="center", va="center", fontsize=12
        )
        gui.canvas.draw()
        return

    # Build grid
    powers, freqs, grid = build_grid_from_map(combined_map)

    if grid.size == 0 or grid.shape[0] == 0 or grid.shape[1] == 0:
        gui.ax.text(
            0.5, 0.5,
            "No overlapping power/frequency data to display.",
            ha="center", va="center"
        )
        gui.canvas.draw()
        return

    # Normalize combined grid
    grid_numeric = np.nan_to_num(grid, nan=0.0)
    maxv = np.nanmax(grid_numeric)
    if maxv == 0 or np.isnan(maxv):
        norm_grid = grid_numeric
    else:
        norm_grid = grid_numeric / maxv

    mask = np.isnan(grid)
    masked = ma.array(norm_grid, mask=mask)
    cmap = cm.get_cmap('BuGn')

    # Plot heatmap
    im = gui.ax.imshow(
        masked,
        origin='lower',
        aspect='auto',
        interpolation='nearest',
        cmap=cmap,
        extent=[min(freqs), max(freqs), min(powers), max(powers)]
    )

    # Ticks only at existing values
    gui.ax.set_xticks(freqs)
    gui.ax.set_yticks(powers)

    # Axis labels and title
    gui.ax.set_xlabel("Frequency (kHz)")
    gui.ax.set_ylabel("Power (U)")
    gui.ax.set_title("Optimal Range Color Map")

    # Single colorbar
    gui.fig.colorbar(im, ax=gui.ax, orientation='vertical', label='Normalized value')

    gui.canvas.draw()