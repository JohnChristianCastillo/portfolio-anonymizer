"""Render the benchmark charts used by REPORT.md.

Called by make_report.py. Writes PNGs containing aggregate metrics only.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from . import scoring

# Chart surface and ink.
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

# Categorical slots, in fixed order, for the three metrics.
SERIES_COLORS = {"Precision": "#2a78d6", "Recall": "#008300", "F1": "#e87ba4"}

# Single-hue sequential ramp (light to dark) for the magnitude heatmap.
BLUE_RAMP = [
    "#cde2fb",
    "#b7d3f6",
    "#9ec5f4",
    "#86b6ef",
    "#6da7ec",
    "#5598e7",
    "#3987e5",
    "#2a78d6",
    "#256abf",
    "#1c5cab",
    "#184f95",
    "#104281",
    "#0d366b",
]
SEQUENTIAL = LinearSegmentedColormap.from_list("blue_seq", BLUE_RAMP)

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "text.color": INK_PRIMARY,
        "axes.labelcolor": INK_SECONDARY,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
    }
)


def _strip_chrome(ax) -> None:
    """Recessive chrome: hairline solid grid, no box, muted ticks."""
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.tick_params(length=0)


def overall_metrics(reports: dict[str, scoring.Report], out: Path) -> None:
    """Grouped bars: precision / recall / F1 for each configuration."""
    names = list(reports)
    values = {metric: [] for metric in SERIES_COLORS}
    for name in names:
        tp, fp, fn = reports[name].micro_counts()
        precision, recall, f1 = scoring.precision_recall_f1(tp, fp, fn)
        values["Precision"].append(precision)
        values["Recall"].append(recall)
        values["F1"].append(f1)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    group_width = 0.54
    bar_width = group_width / len(SERIES_COLORS)
    positions = range(len(names))

    for index, (metric, color) in enumerate(SERIES_COLORS.items()):
        offsets = [p - group_width / 2 + bar_width * (index + 0.5) for p in positions]
        # A small width inset leaves a surface gap between adjacent bars.
        bars = ax.bar(
            offsets, values[metric], bar_width * 0.88, label=metric, color=color
        )
        for rect, value in zip(bars, values[metric], strict=True):
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                value + 0.02,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=8.5,
                color=INK_SECONDARY,
            )

    ax.set_ylim(0, 1.12)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticks(list(positions))
    ax.set_xticklabels(names, fontsize=10, color=INK_PRIMARY)
    ax.set_ylabel("Score", fontsize=9)
    ax.set_title(
        "Overall anonymization quality by configuration (micro-average)",
        fontsize=12,
        color=INK_PRIMARY,
        pad=14,
        loc="left",
    )
    ax.yaxis.grid(True, color=GRIDLINE, linewidth=1.0, linestyle="-")
    ax.set_axisbelow(True)
    _strip_chrome(ax)
    ax.legend(
        frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.02), fontsize=9
    )

    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def metric_comparison(reports: dict[str, scoring.Report], out: Path) -> None:
    """One panel per metric, so a single attribute is easy to compare across
    configurations. Each panel is a single series, so it needs no legend."""
    names = list(reports)
    scores = {metric: [] for metric in SERIES_COLORS}
    for name in names:
        tp, fp, fn = reports[name].micro_counts()
        precision, recall, f1 = scoring.precision_recall_f1(tp, fp, fn)
        scores["Precision"].append(precision)
        scores["Recall"].append(recall)
        scores["F1"].append(f1)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.4), sharey=True)
    for ax, metric in zip(axes, scores, strict=True):
        bars = ax.bar(names, scores[metric], width=0.5, color=SERIES_COLORS["Precision"])
        for rect, value in zip(bars, scores[metric], strict=True):
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                value + 0.02,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=INK_SECONDARY,
            )
        ax.set_title(metric, fontsize=11, color=INK_PRIMARY, pad=10, loc="left")
        ax.set_ylim(0, 1.12)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.tick_params(axis="x", labelrotation=30, labelsize=9)
        for tick in ax.get_xticklabels():
            tick.set_horizontalalignment("right")
            tick.set_color(INK_PRIMARY)
        ax.yaxis.grid(True, color=GRIDLINE, linewidth=1.0, linestyle="-")
        ax.set_axisbelow(True)
        _strip_chrome(ax)

    axes[0].set_ylabel("Score", fontsize=9)
    fig.suptitle(
        "Each metric compared across configurations",
        fontsize=12,
        color=INK_PRIMARY,
        x=0.008,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def per_label_f1(reports: dict[str, scoring.Report], out: Path) -> None:
    """Heatmap: F1 per label for each configuration, showing coverage gaps."""
    names = list(reports)
    labels = []
    grid = []
    for label in scoring.LABELS:
        counts = [reports[name].counts_for(label) for name in names]
        if all(tp == fp == fn == 0 for tp, fp, fn in counts):
            continue
        row = []
        for tp, fp, fn in counts:
            _, _, f1 = scoring.precision_recall_f1(tp, fp, fn)
            row.append(f1)
        labels.append(label)
        grid.append(row)

    fig, ax = plt.subplots(figsize=(8.2, 5.6))
    mesh = ax.imshow(grid, cmap=SEQUENTIAL, vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontsize=10, color=INK_PRIMARY)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9.5, color=INK_PRIMARY)
    ax.set_title(
        "F1 per entity label: where each configuration is blind",
        fontsize=12,
        color=INK_PRIMARY,
        pad=14,
        loc="left",
    )

    # Every cell carries its value, so the scale is never colour-only.
    for row_index, row in enumerate(grid):
        for col_index, value in enumerate(row):
            ax.text(
                col_index,
                row_index,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=9,
                color="#ffffff" if value >= 0.55 else INK_SECONDARY,
            )

    # A thin surface gap between cells instead of borders around them.
    ax.set_xticks([x - 0.5 for x in range(1, len(names))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(labels))], minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)
    ax.tick_params(length=0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    bar = fig.colorbar(mesh, ax=ax, fraction=0.035, pad=0.03)
    bar.set_label("F1", fontsize=9, color=INK_SECONDARY)
    bar.outline.set_visible(False)
    bar.ax.tick_params(length=0, colors=INK_MUTED)

    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def build_charts(
    reports: dict[str, scoring.Report], out_dir: Path, prefix: str = ""
) -> list[str]:
    """Write every chart and return the filenames.

    `prefix` lets one report hold more than one set, so the required comparison and
    the wider exploration can be charted separately rather than averaged together.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    names = [
        f"{prefix}overall_metrics.png",
        f"{prefix}metric_comparison.png",
        f"{prefix}per_label_f1.png",
    ]
    overall_metrics(reports, out_dir / names[0])
    metric_comparison(reports, out_dir / names[1])
    per_label_f1(reports, out_dir / names[2])
    return names
