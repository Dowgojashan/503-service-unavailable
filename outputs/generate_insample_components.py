"""Generate in-sample S_Agent component breakdown (2×2 subplots)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

CSV = Path("outputs/reports/s_agent_results_full.csv")
OUT = Path("outputs/figures/fig_insample_components.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

ARCH_ORDER  = ["Single-slot", "ReAct", "Reflection", "PlanExecute"]
ARCH_COLORS = {
    "Single-slot": "#5B9BD5",
    "ReAct":        "#ED7D31",
    "Reflection":   "#A9D18E",
    "PlanExecute":  "#7030A0",
}

COMPONENTS = [
    ("s_outcome",     "S_Outcome",     "weight = 0.50"),
    ("s_tool",        "S_Tool",        "weight = 0.20"),
    ("s_trajectory",  "S_Trajectory",  "weight = 0.10"),
    ("s_efficiency",  "S_Efficiency",  "weight = 0.20"),
]

df = pd.read_csv(CSV)
arch_means = df.groupby("agent_type")[[c for c, _, _ in COMPONENTS]].mean().reindex(ARCH_ORDER)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

fig, axes = plt.subplots(2, 2, figsize=(11, 8))
fig.suptitle("In-Sample S_Agent Component Scores by Architecture",
             fontsize=13, fontweight="bold", y=1.01)

xs = np.arange(len(ARCH_ORDER))

for ax, (col, label, weight_note) in zip(axes.flat, COMPONENTS):
    vals  = arch_means[col].values
    colors = [ARCH_COLORS[a] for a in ARCH_ORDER]
    bars  = ax.bar(xs, vals, color=colors, edgecolor="white", linewidth=0.6, zorder=3, width=0.55)

    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.8,
                f"{val:.1f}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(xs)
    ax.set_xticklabels(ARCH_ORDER, fontsize=9)
    ax.set_ylabel("Score (0–100)", fontsize=9)
    ax.set_ylim(0, 115)
    ax.set_title(f"{label}  ({weight_note})", fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.35, zorder=0)

# shared legend
handles = [plt.Rectangle((0, 0), 1, 1, color=ARCH_COLORS[a]) for a in ARCH_ORDER]
fig.legend(handles, ARCH_ORDER, title="Architecture", title_fontsize=9,
           fontsize=9, loc="lower center", ncol=4,
           bbox_to_anchor=(0.5, -0.03), framealpha=0.85)

plt.tight_layout()
plt.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"Saved: {OUT}")
