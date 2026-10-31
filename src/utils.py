"""Small shared helpers: plotting style and figure saving."""
from pathlib import Path

import matplotlib.pyplot as plt

from src import config

# Chart colours (validated categorical palette, light mode). Series colours are
# assigned in this fixed order; text never uses a series colour.
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID_COLOR = "#e4e3df"
SURFACE = "#fcfcfb"


def set_plot_style() -> None:
    """Apply one consistent, minimal Matplotlib style to every figure."""
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlecolor": TEXT_PRIMARY,
        "axes.labelcolor": TEXT_SECONDARY,
        "axes.edgecolor": GRID_COLOR,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID_COLOR,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "xtick.color": TEXT_SECONDARY,
        "ytick.color": TEXT_SECONDARY,
        "legend.frameon": False,
        "lines.linewidth": 2,
    })


def save_fig(fig, name: str) -> Path:
    """Save a figure to results/<name>.png and return the path."""
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.RESULTS_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    return path
