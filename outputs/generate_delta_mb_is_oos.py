"""ΔMB IS vs OOS grouped bar chart — PlanExecute is the only positive arch in both."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

IS_CSV  = Path("outputs/reports/s_agent_results_full.csv")
OOS_CSV = Path("outputs/reports/oos_s_agent_results.csv")
OUT     = Path("outputs/figures/fig_delta_mb_is_vs_oos.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

ARCH_ORDER = ["ReAct", "Reflection", "PlanExecute"]

def compute_dmb(csv_path):
    df = pd.read_csv(csv_path)
    ss = (df[df["agent_type"] == "Single-slot"]
          [["case_id", "persona_type", "net_value"]]
          .rename(columns={"net_value": "nv_ss"}))
    m  = df[df["agent_type"] != "Single-slot"].merge(ss, on=["case_id", "persona_type"])
    m["delta_mb"] = m["net_value"] - m["nv_ss"]
    return m.groupby("agent_type")["delta_mb"].mean().reindex(ARCH_ORDER)

is_dmb  = compute_dmb(IS_CSV)
oos_dmb = compute_dmb(OOS_CSV)

# ── colour logic: blue = positive, red = negative, independently per bar ──
def bar_colors(vals):
    return ["#2E86C1" if v >= 0 else "#C0392B" for v in vals]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

fig, ax = plt.subplots(figsize=(8, 5))

xs    = np.arange(len(ARCH_ORDER))
width = 0.32

bars_is  = ax.bar(xs - width / 2, is_dmb.values,  width,
                  color=bar_colors(is_dmb.values),
                  edgecolor="white", linewidth=0.8, zorder=3, alpha=0.90,
                  label="_nolegend_")
bars_oos = ax.bar(xs + width / 2, oos_dmb.values, width,
                  color=bar_colors(oos_dmb.values),
                  edgecolor="white", linewidth=0.8, zorder=3, alpha=0.65,
                  label="_nolegend_", hatch="////")

# value labels
for bar, val in zip(bars_is, is_dmb.values):
    offset = 0.006 if val >= 0 else -0.014
    va     = "bottom" if val >= 0 else "top"
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + offset,
            f"{val:+.3f}", ha="center", va=va, fontsize=9, fontweight="bold",
            color=bar.get_facecolor())

for bar, val in zip(bars_oos, oos_dmb.values):
    offset = 0.006 if val >= 0 else -0.014
    va     = "bottom" if val >= 0 else "top"
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + offset,
            f"{val:+.3f}", ha="center", va=va, fontsize=9, fontweight="bold",
            color=bar.get_facecolor())

# zero baseline
ax.axhline(0, color="#333333", linewidth=1.4, zorder=4)
ax.text(xs[-1] + width / 2 + 0.08, 0.005,
        "Single-slot baseline  (ΔMB = 0)",
        fontsize=8.5, color="#444444", va="bottom", ha="left")

# proxy legend for IS / OOS distinction
from matplotlib.patches import Patch
legend_handles = [
    Patch(facecolor="#888888", edgecolor="white", alpha=0.90, label="In-Sample (IS)"),
    Patch(facecolor="#888888", edgecolor="white", alpha=0.65, hatch="////", label="Out-of-Sample (OOS)"),
]
ax.legend(handles=legend_handles, fontsize=10, framealpha=0.85, loc="upper left")

ax.set_xticks(xs)
ax.set_xticklabels(ARCH_ORDER, fontsize=12)
ax.set_ylabel("ΔMB  (NetValue vs Single-slot)", fontsize=10)
ax.set_title("Marginal Benefit (ΔMB): In-Sample vs Out-of-Sample\nRelative to Single-slot Baseline",
             fontsize=11, fontweight="bold", pad=10)
ax.set_ylim(-0.32, 0.22)
ax.grid(axis="y", alpha=0.35, zorder=0)

plt.tight_layout()
plt.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"Saved: {OUT}")
