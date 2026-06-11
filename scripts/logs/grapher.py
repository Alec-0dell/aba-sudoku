"""
plot_results.py  —  Sudoku benchmark visualizations
Expects results CSV in the same directory. Produces four figures:
  1. Clustered bar chart: correct % grouped by solver, difficulties side by side
  2. 2x2 subplots: avg solve time ± std dev, one subplot per difficulty
  3. Line chart: avg time vs difficulty (no Prolog) with std dev shading
  4. NN cell accuracy ± std dev by difficulty
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
COLORS = {
    "python": "#4a2377",
    "prolog": "#8cc5e3",
    "clingo": "#f55f74",
    "nn":     "#0d7d87",
}

DIFFICULTY_ORDER = ["Easy", "Medium", "Hard", "Diabolical"]
SOLVER_ORDER     = ["python", "prolog", "clingo", "nn"]
SOLVER_LABELS    = {"python": "Python", "prolog": "Prolog", "clingo": "Clingo", "nn": "Neural Net"}

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
CSV_PATH = os.path.join(os.path.dirname(__file__), "results_20260605_132244.csv")
df = pd.read_csv(CSV_PATH)
df["difficulty"] = pd.Categorical(df["difficulty"], categories=DIFFICULTY_ORDER, ordered=True)
df["se_ms"] = df["std_dev_ms"] / np.sqrt(df["attempted"])

# ---------------------------------------------------------------------------
# Shared style
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
})

BAR_WIDTH   = 0.18
X_DIFF      = np.arange(len(DIFFICULTY_ORDER))   # 4 difficulty positions
X_SOLVER    = np.arange(len(SOLVER_ORDER))        # 4 solver positions


# ---------------------------------------------------------------------------
# Figure 1: Clustered bar — grouped by solver, difficulties side by side, NN last
# ---------------------------------------------------------------------------
fig1, ax1 = plt.subplots(figsize=(9, 5))

for i, difficulty in enumerate(DIFFICULTY_ORDER):
    sub = df[df["difficulty"] == difficulty].set_index("solver").reindex(SOLVER_ORDER)
    offset = (i - 1.5) * BAR_WIDTH
    ax1.bar(
        X_SOLVER + offset,
        sub["correct_pct"],
        width=BAR_WIDTH,
        color=[COLORS[s] for s in SOLVER_ORDER],
        label=difficulty if i == 0 else "_nolegend_",
        zorder=3,
    )

# Difficulty legend via patch handles
from matplotlib.patches import Patch
difficulty_colors = ["#999999", "#777777", "#555555", "#333333"]
legend_handles = [
    Patch(facecolor=difficulty_colors[i], label=d)
    for i, d in enumerate(DIFFICULTY_ORDER)
]
# Solver color legend
solver_handles = [
    Patch(facecolor=COLORS[s], label=SOLVER_LABELS[s]) for s in SOLVER_ORDER
]
ax1.legend(handles=solver_handles, loc="upper right", title="Solver", title_fontsize=8,
           frameon=True, facecolor="white", edgecolor="black", framealpha=1, fancybox=False)

# Secondary legend for difficulty shading
ax1.set_xticks(X_SOLVER)
ax1.set_xticklabels([SOLVER_LABELS[s] for s in SOLVER_ORDER])
ax1.set_xlabel("Solver")
ax1.set_ylabel("Correct (%)")
ax1.set_title("Solver Accuracy by Difficulty", fontweight="bold", pad=12)
ax1.set_ylim(0, 120)
ax1.yaxis.set_major_formatter(mticker.PercentFormatter())

# Annotate difficulty labels on bars for the NN group (only solver with variation)
nn_idx = SOLVER_ORDER.index("nn")
for i, difficulty in enumerate(DIFFICULTY_ORDER):
    sub = df[(df["difficulty"] == difficulty) & (df["solver"] == "nn")]
    val = sub["correct_pct"].values[0]
    xpos = nn_idx + (i - 1.5) * BAR_WIDTH
    ax1.text(xpos, val + 2, difficulty[0], ha="center", va="bottom", fontsize=7, color="#333333")

fig1.tight_layout()
fig1.savefig(os.path.join(os.path.dirname(__file__), "fig1_accuracy.png"), dpi=150)


# ---------------------------------------------------------------------------
# Figure 2: Grouped bar chart — avg time ± std dev, grouped by difficulty
# ---------------------------------------------------------------------------
fig2, ax2 = plt.subplots(figsize=(10, 5))

for i, solver in enumerate(SOLVER_ORDER):
    sub = df[df["solver"] == solver].set_index("difficulty").reindex(DIFFICULTY_ORDER)
    offset = (i - 1.5) * BAR_WIDTH
    ax2.bar(
        X_DIFF + offset,
        sub["avg_time_ms"],
        yerr=sub["std_dev_ms"],
        width=BAR_WIDTH,
        color=COLORS[solver],
        label=SOLVER_LABELS[solver],
        capsize=3,
        error_kw={"linewidth": 1.1, "ecolor": "#555555"},
        zorder=3,
    )

ax2.set_xticks(X_DIFF)
ax2.set_xticklabels(DIFFICULTY_ORDER)
ax2.set_xlabel("Difficulty")
ax2.set_ylabel("Avg Time (ms)")
ax2.set_title("Average Solve Time ± Std Dev by Difficulty", fontweight="bold", pad=12)
ax2.legend(loc="upper right", bbox_to_anchor=(1.08, 1),
           frameon=True, facecolor="white", edgecolor="black", framealpha=1, fancybox=False)

fig2.tight_layout()
fig2.savefig(os.path.join(os.path.dirname(__file__), "fig2_time_by_difficulty.png"), dpi=150, bbox_inches="tight")


# ---------------------------------------------------------------------------
# Figure 3: Line chart — avg time vs difficulty, no Prolog, std dev shading
# ---------------------------------------------------------------------------
LINE_SOLVERS = ["clingo", "nn", "python"]

fig3, ax3 = plt.subplots(figsize=(9, 5))

for solver in LINE_SOLVERS:
    sub = df[df["solver"] == solver].set_index("difficulty").reindex(DIFFICULTY_ORDER)
    y   = sub["avg_time_ms"].values
    sd  = sub["std_dev_ms"].values
    color = COLORS[solver]

    ax3.plot(X_DIFF, y, marker="o", color=color, label=SOLVER_LABELS[solver], linewidth=2, zorder=3)
    ax3.fill_between(X_DIFF, y - sd, y + sd, color=color, alpha=0.18, zorder=2)

ax3.set_xticks(X_DIFF)
ax3.set_xticklabels(DIFFICULTY_ORDER)
ax3.set_xlabel("Difficulty")
ax3.set_ylabel("Avg Time (ms)")
ax3.set_title("Solve Time Across Difficulty (± Std Dev)", fontweight="bold", pad=12)
ax3.legend(frameon=True, facecolor="white", edgecolor="black", framealpha=1, fancybox=False)

fig3.tight_layout()
fig3.savefig(os.path.join(os.path.dirname(__file__), "fig3_time_line.png"), dpi=150)


# ---------------------------------------------------------------------------
# Figure 4: NN cell accuracy ± std dev by difficulty
# ---------------------------------------------------------------------------
nn_df = df[df["solver"] == "nn"].set_index("difficulty").reindex(DIFFICULTY_ORDER).reset_index()

fig4, ax4 = plt.subplots(figsize=(7, 4.5))

ax4.bar(
    X_DIFF,
    nn_df["avg_cell_accuracy_pct"],
    yerr=nn_df["std_cell_accuracy_pct"],
    color=COLORS["nn"],
    width=0.5,
    capsize=5,
    error_kw={"linewidth": 1.3, "ecolor": "#555555"},
    zorder=3,
)

ax4.set_xticks(X_DIFF)
ax4.set_xticklabels(DIFFICULTY_ORDER)
ax4.set_xlabel("Difficulty")
ax4.set_ylabel("Cell Accuracy (%)")
ax4.set_title("Neural Net: Cell Accuracy ± Std Dev by Difficulty", fontweight="bold", pad=12)
ax4.set_ylim(0, 110)
ax4.yaxis.set_major_formatter(mticker.PercentFormatter())

for i, row in nn_df.iterrows():
    ax4.text(
        X_DIFF[i], row["avg_cell_accuracy_pct"] + row["std_cell_accuracy_pct"] + 1.5,
        f"{row['avg_cell_accuracy_pct']:.1f}%",
        ha="center", va="bottom", fontsize=9, color="#333333",
    )

fig4.tight_layout()
fig4.savefig(os.path.join(os.path.dirname(__file__), "fig4_nn_cell_accuracy.png"), dpi=150)

print("Saved: fig1_accuracy.png, fig2_time_by_difficulty.png, fig3_time_line.png, fig4_nn_cell_accuracy.png")