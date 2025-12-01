import tkinter as tk
from tkinter import ttk
from tracemalloc import start
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

class NumberBarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Number Line Bar Generator")
        self.root.geometry("1500x975")
        self.secondary_ranges = []  # store tuples with all widget variables
        self.create_widgets()

    def create_widgets(self):
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 18))
        style.configure("TButton", font=("Segoe UI", 18))
        style.configure("TEntry", font=("Segoe UI", 18))
        style.configure("TCheckbutton", font=("Segoe UI", 16))

        frame = ttk.LabelFrame(self.root, text="Input Parameters", padding=15)
        frame.pack(padx=20, pady=20, fill="x")

        # Primary range
        ttk.Label(frame, text="Primary Start:").grid(row=0, column=0, sticky="e", padx=10, pady=8)
        self.start_var = tk.DoubleVar(value=0)
        ttk.Entry(frame, textvariable=self.start_var, width=12).grid(row=0, column=1, padx=8)

        ttk.Label(frame, text="Primary End:").grid(row=0, column=2, sticky="e", padx=10, pady=8)
        self.end_var = tk.DoubleVar(value=10)
        ttk.Entry(frame, textvariable=self.end_var, width=12).grid(row=0, column=3, padx=8)

        # Unit label and tick spacing
        ttk.Label(frame, text="Unit Label:").grid(row=1, column=0, sticky="e", padx=10, pady=8)
        self.unit_var = tk.StringVar(value="kHz")
        ttk.Entry(frame, textvariable=self.unit_var, width=12).grid(row=1, column=1, padx=8)

        ttk.Label(frame, text="Tick Interval:").grid(row=1, column=2, sticky="e", padx=10, pady=8)
        self.tick_interval_var = tk.DoubleVar(value=1)
        ttk.Entry(frame, textvariable=self.tick_interval_var, width=12).grid(row=1, column=3, padx=8)

        # Secondary bar section
        self.sec_frame = ttk.LabelFrame(self.root, text="Secondary Ranges", padding=15)
        self.sec_frame.pack(padx=20, pady=10, fill="x")

        add_btn = ttk.Button(self.sec_frame, text="Add Secondary Bar", command=self.add_secondary_bar)
        add_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Create button
        ttk.Button(self.root, text="Create Number Bar", command=self.create_bar).pack(pady=20)

        # Plot area
        self.fig, self.ax = plt.subplots(figsize=(15, 3))
        self.ax.set_aspect(3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(padx=15, pady=15, fill="both", expand=True)

    def add_secondary_bar(self):
        """Add a new secondary range input row with checkbox toggle, label text, and delete button."""
        row = len(self.secondary_ranges) + 1
        start_var = tk.DoubleVar(value=2 * row)
        end_var = tk.DoubleVar(value=4 * row)
        visible_var = tk.BooleanVar(value=True)
        label_var = tk.StringVar(value=f"Bar {row}")

        frame = ttk.Frame(self.sec_frame)
        frame.grid(row=row, column=0, columnspan=8, sticky="w", pady=5)

        ttk.Checkbutton(frame, text=f"Show Bar {row}", variable=visible_var).grid(row=0, column=0, padx=5)
        ttk.Label(frame, text="Start:").grid(row=0, column=1, padx=5)
        ttk.Entry(frame, textvariable=start_var, width=10).grid(row=0, column=2, padx=5)
        ttk.Label(frame, text="End:").grid(row=0, column=3, padx=5)
        ttk.Entry(frame, textvariable=end_var, width=10).grid(row=0, column=4, padx=5)
        ttk.Label(frame, text="Label:").grid(row=0, column=5, padx=5)
        ttk.Entry(frame, textvariable=label_var, width=12).grid(row=0, column=6, padx=5)

        # Add delete button (same size as label entry, no symbol)
        del_btn = ttk.Button(frame, text="Delete", width=12, command=lambda f=frame: self.delete_secondary_bar(f))
        del_btn.grid(row=0, column=7, padx=8)

        self.secondary_ranges.append((frame, start_var, end_var, visible_var, label_var))

    def delete_secondary_bar(self, frame):
        """Remove a secondary bar row from GUI and internal list."""
        # Find the matching tuple
        self.secondary_ranges = [entry for entry in self.secondary_ranges if entry[0] != frame]
        # Destroy the GUI frame
        frame.destroy()
        # Repack rows neatly
        for idx, (f, *_rest) in enumerate(self.secondary_ranges, start=1):
            f.grid(row=idx, column=0, columnspan=8, sticky="w", pady=5)

    def create_bar(self):
        start = self.start_var.get()
        end = self.end_var.get()
        unit = self.unit_var.get()
        tick_interval = self.tick_interval_var.get()

        self.ax.clear()

        total_height = (end - start) / 25.0
        visible_width = end - start
        rounding = max(0.05, min(visible_width * 0.02, (end - start) / 10.0))
        y_center = 0

        # Primary bar
        primary_bar = patches.FancyBboxPatch(
            (start, y_center - total_height / 2),
            end - start,
            total_height,
            boxstyle=f"round,pad=0.02,rounding_size={rounding}",
            facecolor="lightgray",
            edgecolor="gray",
            zorder=1
        )
        self.ax.add_patch(primary_bar)

        # Visible bars
        visible_bars = []
        for _, s_var, e_var, vis_var, label_var in self.secondary_ranges:
            if vis_var.get():
                s, e = sorted((s_var.get(), e_var.get()))
                visible_bars.append((s, e, label_var.get()))

        num_bars = len(visible_bars)
        if num_bars == 0:
            self.canvas.draw()
            return

        row_height = total_height / num_bars
        bar_height = row_height * 0.8  # spacing between bars

        # Muted color palette
        color_palette = [
            (0.5, 0.7, 1.0),
            (0.4, 0.8, 0.9),
            (0.6, 0.6, 1.0),
            (0.5, 0.8, 0.8),
            (0.7, 0.7, 0.9),
            (0.6, 0.7, 0.85)
        ]

        # --- Overlap computation ---
        overlap_segments = []
        if len(visible_bars) > 1:
            segments = self.find_overlap_regions([(s, e) for s, e, _ in visible_bars])
            max_overlap = max(segments["overlaps"]) if segments["overlaps"] else 0
            for (seg_start, seg_end), overlap in zip(segments["segments"], segments["overlaps"]):
                if overlap == max_overlap and max_overlap > 1:
                    overlap_segments.append((seg_start, seg_end))
                    overlap_bar = patches.FancyBboxPatch(
                        (seg_start, y_center - total_height / 2),
                        seg_end - seg_start,
                        total_height,
                        boxstyle=f"round,pad=0.02,rounding_size={rounding}",
                        facecolor=(0.1, 0.2, 0.5),
                        edgecolor="none",
                        alpha=0.4,
                        zorder=0
                    )
                    self.ax.add_patch(overlap_bar)

        # --- Draw stacked secondary bars ---
        for i, (s, e, label_text) in enumerate(visible_bars):
            color = color_palette[i % len(color_palette)]
            bottom = y_center - total_height / 2 + i * row_height + (row_height - bar_height) / 2

            secondary_bar = patches.FancyBboxPatch(
                (s, bottom),
                e - s,
                bar_height,
                boxstyle=f"round,pad=0.02,rounding_size={rounding}",
                facecolor=color,
                edgecolor=color,
                alpha=0.5,
                zorder=2
            )
            self.ax.add_patch(secondary_bar)

            # Label centered in each bar
            x_mid = (s + e) / 2
            y_mid = bottom + bar_height / 2
            self.ax.text(
                x_mid,
                y_mid,
                label_text,
                ha="center",
                va="center",
                fontsize=12,
                color="black",
                weight="bold",
                zorder=3
            )

        # Dashed overlap lines (bounded to primary bar height)
        for seg_start, seg_end in overlap_segments:
            self.ax.vlines(
                x=[seg_start, seg_end],
                ymin=y_center - total_height / 2,
                ymax=y_center + total_height / 2,
                colors="gray",
                linestyles="--",
                linewidth=1.5,
                alpha=0.8,
                zorder=4
            )

        # Axis formatting
        self.ax.set_xlim(start - tick_interval, end + tick_interval)
        self.ax.set_ylim(-total_height * 1.5, total_height * 1.5)
        self.ax.set_yticks([])

        ticks = [x for x in self.frange(start, end, tick_interval)]
        tick_labels = [f"{x:g}" for x in ticks]
        self.ax.set_xticks(ticks)
        self.ax.set_xticklabels(tick_labels)

        baseline_y = -total_height * 0.55
        self.ax.spines['bottom'].set_visible(True)
        self.ax.spines['bottom'].set_position(('data', baseline_y))
        for s in ('top', 'left', 'right'):
            self.ax.spines[s].set_visible(False)
        self.ax.xaxis.set_ticks_position('bottom')
        self.ax.tick_params(axis='x', which='both', pad=2, labelsize=14)

        # Unit label
        if unit.strip():
            self.ax.text(
                0.5, 0.15, unit,
                ha='center', va='top',
                transform=self.ax.transAxes, fontsize=16
            )

        self.ax.margins(y=0)
        self.ax.grid(False)
        self.fig.subplots_adjust(bottom=0.18, top=0.95)
        self.canvas.draw()

    def find_overlap_regions(self, bars):
        points = []
        for s, e in bars:
            points.append((s, 1))
            points.append((e, -1))
        points.sort()
        segments, overlaps, active, last_x = [], [], 0, None
        for x, change in points:
            if last_x is not None and x != last_x:
                segments.append((last_x, x))
                overlaps.append(active)
            active += change
            last_x = x
        return {"segments": segments, "overlaps": overlaps}

    def frange(self, start, end, step):
        x = start
        while x <= end:
            yield round(x, 5)
            x += step

if __name__ == "__main__":
    root = tk.Tk()
    app = NumberBarGUI(root)
    root.mainloop()
