"""ΔMB bar chart: IS only, Single-slot as zero baseline."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

IS_CSV = Path("outputs/reports/s_agent_results_full.csv")
OUT    = Path("outputs/figures/fig_delta_mb.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

ARCH_ORDER = ["ReAct", "Reflection", "PlanExecute"]

df  = pd.read_csv(IS_CSV)
ss  = (df[df["agent_type"] == "Single-slot"]
       [["case_id", "persona_type", "net_value"]]
       .rename(columns={"net_value": "nv_ss"}))
m   = df[df["agent_type"] != "Single-slot"].merge(ss, on=["case_id", "persona_type"])
m["delta_mb"] = m["net_value"] - m["nv_ss"]
is_dmb = m.groupby("agent_type")["delta_mb"].mean().reindex(ARCH_ORDER)

# ── plot ──────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

fig, ax = plt.subplots(figsize=(7, 5))
xs    = np.arange(len(ARCH_ORDER))
width = 0.45

bar_colors = ["#C0392B" if v < 0 else "#2E86C1" for v in is_dmb.values]
bars = ax.bar(xs, is_dmb.values, width, color=bar_colors,
              edgecolor="white", linewidth=0.6, zorder=3, alpha=0.88)

for bar, val in zip(bars, is_dmb.values):
    offset = 0.005 if val >= 0 else -0.013
    va     = "bottom" if val >= 0 else "top"
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + offset,
            f"{val:+.3f}", ha="center", va=va,
            fontsize=10, fontweight="bold",
            color=bar.get_facecolor())

ax.axhline(0, color="#333333", linewidth=1.4, zorder=4)
ax.text(xs[-1] + width / 2 + 0.05, 0.004,
        "Single-slot baseline  (ΔMB = 0)",
        fontsize=8.5, color="#444444", va="bottom", ha="left")

ax.set_xticks(xs)
ax.set_xticklabels(ARCH_ORDER, fontsize=12)
ax.set_ylabel("ΔMB  (NetValue vs Single-slot)", fontsize=10)
ax.set_title("In-Sample Marginal Benefit (ΔMB)\nRelative to Single-slot Baseline",
             fontsize=11, fontweight="bold", pad=10)
ax.set_ylim(-0.32, 0.22)
ax.grid(axis="y", alpha=0.35, zorder=0)

plt.tight_layout()
plt.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"Saved: {OUT}")
