"""Combined figure: S_Agent by persona (top) + component breakdown (bottom)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

CSV = Path("outputs/reports/s_agent_results_full.csv")
OUT = Path("outputs/figures/fig_insample_combined.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

ARCH_ORDER    = ["Single-slot", "ReAct", "Reflection", "PlanExecute"]
PERSONA_ORDER = ["Polite", "Adversarial", "VIP"]
ARCH_COLORS   = {
    "Single-slot": "#5B9BD5",
    "ReAct":        "#ED7D31",
    "Reflection":   "#A9D18E",
    "PlanExecute":  "#7030A0",
}
PERSONA_COLORS = {
    "Polite":      "#4472C4",
    "Adversarial": "#C00000",
    "VIP":         "#C9A227",
}
COMPONENTS = [
    ("s_outcome",    "S_Outcome",    "w=0.50"),
    ("s_tool",       "S_Tool",       "w=0.20"),
    ("s_trajectory", "S_Trajectory", "w=0.10"),
    ("s_efficiency", "S_Efficiency", "w=0.20"),
]

df = pd.read_csv(CSV)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

# ── layout: top row = 1 wide axis; bottom row = 4 equal axes ──────────────
fig = plt.figure(figsize=(14, 10))
gs  = fig.add_gridspec(2, 4, hspace=0.45, wspace=0.35,
                        height_ratios=[1.1, 1])
ax_top  = fig.add_subplot(gs[0, :])          # spans all 4 columns
ax_bot  = [fig.add_subplot(gs[1, i]) for i in range(4)]

# ── TOP: S_Agent by architecture × persona ────────────────────────────────
means = (df.groupby(["agent_type", "persona_type"])["s_agent"]
           .mean().reset_index())

n_arch = len(ARCH_ORDER)
width  = 0.22
offsets = np.array([-1, 0, 1]) * width

for j, persona in enumerate(PERSONA_ORDER):
    vals = [
        means.loc[(means["agent_type"] == a) & (means["persona_type"] == persona),
                  "s_agent"].values[0]
        for a in ARCH_ORDER
    ]
    xs   = np.arange(n_arch) + offsets[j]
    bars = ax_top.bar(xs, vals, width=width * 0.92,
                      color=PERSONA_COLORS[persona], label=persona,
                      edgecolor="white", linewidth=0.6, zorder=3)
    for bar, val in zip(bars, vals):
        ax_top.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.5,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=8)

ax_top.set_xticks(np.arange(n_arch))
ax_top.set_xticklabels(ARCH_ORDER, fontsize=10)
ax_top.set_ylabel("S_Agent Score (0–100)", fontsize=10)
ax_top.set_ylim(0, 105)
ax_top.set_title("(a)  S_Agent Score by Architecture and Persona  (1,800 Conversations)",
                 fontsize=11, fontweight="bold")
ax_top.grid(axis="y", alpha=0.35, zorder=0)
ax_top.legend(fontsize=9, title="Persona", title_fontsize=9,
              loc="lower right", framealpha=0.85)

# ── BOTTOM: component breakdown ───────────────────────────────────────────
arch_comp = df.groupby("agent_type")[[c for c, _, _ in COMPONENTS]].mean().reindex(ARCH_ORDER)
xs = np.arange(n_arch)

for ax, (col, label, wnote) in zip(ax_bot, COMPONENTS):
    vals   = arch_comp[col].values
    colors = [ARCH_COLORS[a] for a in ARCH_ORDER]
    bars   = ax.bar(xs, vals, color=colors, edgecolor="white",
                    linewidth=0.6, zorder=3, width=0.55)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.8,
                f"{val:.1f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels(ARCH_ORDER, fontsize=8, rotation=12, ha="right")
    ax.set_ylabel("Score (0–100)", fontsize=8)
    ax.set_ylim(0, 115)
    ax.set_title(f"(b)  {label}  ({wnote})", fontsize=10, fontweight="bold")
    ax.grid(axis="y", alpha=0.35, zorder=0)

# shared arch legend for bottom row
handles = [plt.Rectangle((0, 0), 1, 1, color=ARCH_COLORS[a]) for a in ARCH_ORDER]
fig.legend(handles, ARCH_ORDER, title="Architecture", title_fontsize=9,
           fontsize=9, loc="lower center", ncol=4,
           bbox_to_anchor=(0.5, -0.02), framealpha=0.85)

plt.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"Saved: {OUT}")
