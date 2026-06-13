"""Generate in-sample S_Agent bar chart (architecture × persona)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

CSV = Path("outputs/reports/s_agent_results_full.csv")
OUT = Path("outputs/figures/fig_insample_sagent.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

ARCH_ORDER    = ["Single-slot", "ReAct", "Reflection", "PlanExecute"]
PERSONA_ORDER = ["Polite", "Adversarial", "VIP"]
PERSONA_COLORS = {
    "Polite":      "#4472C4",
    "Adversarial": "#C00000",
    "VIP":         "#C9A227",
}

df = pd.read_csv(CSV)
means = (
    df.groupby(["agent_type", "persona_type"])["s_agent"]
    .mean()
    .reset_index()
)

fig, ax = plt.subplots(figsize=(8, 5))
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})
ax.grid(axis="y", alpha=0.35, zorder=0)

n_arch = len(ARCH_ORDER)
n_p    = len(PERSONA_ORDER)
width  = 0.22
offsets = np.array([-1, 0, 1]) * width

for j, persona in enumerate(PERSONA_ORDER):
    vals = [
        means.loc[(means["agent_type"] == a) & (means["persona_type"] == persona), "s_agent"].values[0]
        for a in ARCH_ORDER
    ]
    xs = np.arange(n_arch) + offsets[j]
    bars = ax.bar(xs, vals, width=width * 0.92,
                  color=PERSONA_COLORS[persona], label=persona,
                  edgecolor="white", linewidth=0.6, zorder=3)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.6,
                f"{val:.1f}", ha="center", va="bottom", fontsize=8)


ax.set_xticks(np.arange(n_arch))
ax.set_xticklabels(ARCH_ORDER, fontsize=10)
ax.set_ylabel("S_Agent Score (0–100)", fontsize=10)
ax.set_ylim(0, 105)
ax.set_title("In-Sample S_Agent Performance by Architecture and Persona\n(1,800 Conversations)",
             fontsize=11, fontweight="bold", pad=10)
ax.legend(fontsize=9, title="Persona", title_fontsize=9,
          loc="lower right", framealpha=0.85)

plt.tight_layout()
plt.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"Saved: {OUT}")
