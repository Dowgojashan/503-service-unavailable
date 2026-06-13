"""IS vs OOS S_Agent grouped bar chart (averaged across all personas)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

IS_CSV  = Path("outputs/reports/s_agent_results_full.csv")
OOS_CSV = Path("outputs/reports/oos_s_agent_results.csv")
OUT     = Path("outputs/figures/fig_is_vs_oos_sagent.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

ARCH_ORDER = ["Single-slot", "ReAct", "Reflection", "PlanExecute"]

is_means  = pd.read_csv(IS_CSV).groupby("agent_type")["s_agent"].mean().reindex(ARCH_ORDER)
oos_means = pd.read_csv(OOS_CSV).groupby("agent_type")["s_agent"].mean().reindex(ARCH_ORDER)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

fig, ax = plt.subplots(figsize=(8, 5))

xs    = np.arange(len(ARCH_ORDER))
width = 0.32
IS_COLOR  = "#2E86C1"
OOS_COLOR = "#E67E22"

bars_is  = ax.bar(xs - width / 2, is_means.values,  width, label="In-Sample (IS)",
                  color=IS_COLOR,  edgecolor="white", linewidth=0.6, zorder=3, alpha=0.88)
bars_oos = ax.bar(xs + width / 2, oos_means.values, width, label="Out-of-Sample (OOS)",
                  color=OOS_COLOR, edgecolor="white", linewidth=0.6, zorder=3, alpha=0.88)

for bar, val in zip(bars_is, is_means.values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6,
            f"{val:.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold",
            color=IS_COLOR)

for bar, val in zip(bars_oos, oos_means.values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6,
            f"{val:.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold",
            color=OOS_COLOR)

ax.set_xticks(xs)
ax.set_xticklabels(ARCH_ORDER, fontsize=11)
ax.set_ylabel("S_Agent Score (0–100)", fontsize=10)
ax.set_ylim(0, 105)
ax.set_title("S_Agent Score: In-Sample vs Out-of-Sample\n(Averaged Across All Personas)",
             fontsize=11, fontweight="bold", pad=10)
ax.grid(axis="y", alpha=0.35, zorder=0)
ax.legend(fontsize=10, framealpha=0.85, loc="lower right")

plt.tight_layout()
plt.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"Saved: {OUT}")
