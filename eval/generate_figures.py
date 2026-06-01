"""
Figure generation script for the e-commerce CSR agent evaluation paper.

Produces 8 figures saved to outputs/figures/:
  fig0_experiment_flow.png      — Experiment pipeline flowchart
  fig1_s_agent_overview.png     — S_Agent in-sample vs OOS grouped bar
  fig2_insample_performance.png — In-sample completion rate + judge score
  fig3_oos_performance.png      — OOS completion rate + judge score
  fig4_pss_violin.png           — PSS distribution violin/box by architecture
  fig5_intent_pss_heatmap.png   — PSS heatmap: architecture × intent (in-sample)
  fig6_cost_efficiency.png      — Cost-efficiency scatter
  fig7_generalization_gap.png   — In-sample vs OOS delta

Usage:
  python eval/generate_figures.py
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

# ── paths ──────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
OUT_DIR     = ROOT / "outputs" / "figures"
INSAMPLE_CSV = ROOT / "outputs" / "reports" / "s_agent_results_full.csv"
OOS_CSV      = ROOT / "outputs" / "reports" / "oos_s_agent_results.csv"
FS_PATH      = ROOT / "data" / "fact_sheets.json"
OOS_FS_PATH  = ROOT / "data" / "oos_fact_sheets.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── style ──────────────────────────────────────────────────────────────────
ARCH_ORDER    = ["Single-slot", "ReAct", "Reflection", "PlanExecute"]
PERSONA_ORDER = ["Polite", "Adversarial", "VIP"]
ARCH_COLORS   = {
    "Single-slot": "#5B9BD5",
    "ReAct":        "#ED7D31",
    "Reflection":   "#A9D18E",
    "PlanExecute":  "#7030A0",
}
PERSONA_COLORS = {
    "Polite":       "#4472C4",
    "Adversarial":  "#C00000",
    "VIP":          "#C9A227",
}

plt.rcParams.update({
    "font.family":     "DejaVu Sans",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "axes.grid.axis":     "y",
    "grid.alpha":         0.4,
    "figure.dpi":         150,
})


# ── helpers ────────────────────────────────────────────────────────────────
def load_insample() -> pd.DataFrame:
    df = pd.read_csv(INSAMPLE_CSV)
    # average across multiple runs per combo
    grp = df.groupby(["case_id", "agent_type", "persona_type"]).agg(
        difficulty=("difficulty", "first"),
        s_answer_quality=("s_answer_quality", "mean"),
        s_agent=("s_agent", "mean"),
        traj_no_loops=("traj_no_loops", "mean"),   # mean → completion rate proxy
        total_tokens=("total_tokens", "mean"),
        i_fatal=("i_fatal", "mean"),
    ).reset_index()
    grp["completed"] = grp["traj_no_loops"]        # already 0/1 mean
    return grp


def load_oos() -> pd.DataFrame:
    df = pd.read_csv(OOS_CSV)
    df["completed"] = df["traj_no_loops"].astype(float)
    return df


def compute_pss(df: pd.DataFrame, score_col: str = "s_answer_quality") -> pd.DataFrame:
    """PSS_i = mean(|P-A|, |P-V|, |A-V|) per (case_id, agent_type)."""
    pivot = df.pivot_table(
        index=["case_id", "agent_type"],
        columns="persona_type",
        values=score_col,
        aggfunc="mean",
    ).reset_index()
    pivot.columns.name = None
    for col in PERSONA_ORDER:
        if col not in pivot.columns:
            pivot[col] = np.nan
    pivot["PSS"] = (
        (pivot["Polite"] - pivot["Adversarial"]).abs()
        + (pivot["Polite"] - pivot["VIP"]).abs()
        + (pivot["Adversarial"] - pivot["VIP"]).abs()
    ) / 3
    return pivot.dropna(subset=["PSS"])


def grouped_bar(ax, data: pd.DataFrame, x_col: str, hue_col: str, y_col: str,
                x_order, hue_order, colors: dict, ylabel: str, title: str,
                ylim=None):
    n_x   = len(x_order)
    n_hue = len(hue_order)
    width = 0.65 / n_hue
    offsets = np.linspace(-(n_hue - 1) / 2, (n_hue - 1) / 2, n_hue) * width

    for j, hue in enumerate(hue_order):
        vals = []
        for xi, x in enumerate(x_order):
            sub = data[(data[x_col] == x) & (data[hue_col] == hue)]
            vals.append(sub[y_col].mean() if not sub.empty else 0)
        xs = np.arange(n_x) + offsets[j]
        bars = ax.bar(xs, vals, width=width * 0.9, color=colors[hue],
                      label=hue, edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + (ylim[1] * 0.01 if ylim else 0.5),
                        f"{val:.1f}", ha="center", va="bottom", fontsize=7)

    ax.set_xticks(np.arange(n_x))
    ax.set_xticklabels(x_order, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=10, fontweight="bold")
    if ylim:
        ax.set_ylim(*ylim)
    ax.legend(fontsize=8, title=hue_col, title_fontsize=8)


# ═══════════════════════════════════════════════════════════════════════════
# Fig 1 — S_Agent overview: in-sample vs OOS
# ═══════════════════════════════════════════════════════════════════════════
def fig1_s_agent_overview():
    ins = load_insample()
    oos = load_oos()

    ins_mean = ins.groupby("agent_type")["s_agent"].mean().reindex(ARCH_ORDER)
    oos_mean = oos.groupby("agent_type")["s_agent"].mean().reindex(ARCH_ORDER)

    ins_persona = ins.groupby(["agent_type", "persona_type"])["s_agent"].mean().unstack()
    oos_persona = oos.groupby(["agent_type", "persona_type"])["s_agent"].mean().unstack()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("S_Agent Score: In-Sample vs Out-of-Sample", fontsize=13, fontweight="bold")

    for ax, data, title in [
        (axes[0], ins.groupby(["agent_type", "persona_type"])["s_agent"].mean().reset_index(), "In-Sample (1,800 dialogues)"),
        (axes[1], oos.groupby(["agent_type", "persona_type"])["s_agent"].mean().reset_index(), "OOS (600 dialogues)"),
    ]:
        grouped_bar(ax, data, "agent_type", "persona_type", "s_agent",
                    ARCH_ORDER, PERSONA_ORDER, PERSONA_COLORS,
                    "S_Agent Score", title, ylim=(0, 105))

    plt.tight_layout()
    path = OUT_DIR / "fig1_s_agent_overview.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 2 — In-sample: completion rate + judge score
# ═══════════════════════════════════════════════════════════════════════════
def fig2_insample_performance():
    ins = load_insample()
    agg = ins.groupby(["agent_type", "persona_type"]).agg(
        completion_rate=("completed", "mean"),
        judge_score=("s_answer_quality", "mean"),
    ).reset_index()
    agg["completion_pct"] = agg["completion_rate"] * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("In-Sample Performance by Architecture × Persona", fontsize=13, fontweight="bold")

    grouped_bar(ax1, agg, "agent_type", "persona_type", "completion_pct",
                ARCH_ORDER, PERSONA_ORDER, PERSONA_COLORS,
                "Completion Rate (%)", "Completion Rate", ylim=(0, 110))

    grouped_bar(ax2, agg, "agent_type", "persona_type", "judge_score",
                ARCH_ORDER, PERSONA_ORDER, PERSONA_COLORS,
                "LLM Judge Score (0–100)", "LLM Judge Score (S_AnswerQuality)", ylim=(0, 100))

    plt.tight_layout()
    path = OUT_DIR / "fig2_insample_performance.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 3 — OOS: completion rate + judge score
# ═══════════════════════════════════════════════════════════════════════════
def fig3_oos_performance():
    oos = load_oos()
    agg = oos.groupby(["agent_type", "persona_type"]).agg(
        completion_rate=("completed", "mean"),
        judge_score=("s_answer_quality", "mean"),
    ).reset_index()
    agg["completion_pct"] = agg["completion_rate"] * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("OOS Performance by Architecture × Persona", fontsize=13, fontweight="bold")

    grouped_bar(ax1, agg, "agent_type", "persona_type", "completion_pct",
                ARCH_ORDER, PERSONA_ORDER, PERSONA_COLORS,
                "Completion Rate (%)", "Completion Rate", ylim=(0, 110))

    grouped_bar(ax2, agg, "agent_type", "persona_type", "judge_score",
                ARCH_ORDER, PERSONA_ORDER, PERSONA_COLORS,
                "LLM Judge Score (0–100)", "LLM Judge Score (S_AnswerQuality)", ylim=(0, 100))

    plt.tight_layout()
    path = OUT_DIR / "fig3_oos_performance.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 4 — PSS violin + box by architecture (in-sample)
# ═══════════════════════════════════════════════════════════════════════════
def fig4_pss_violin():
    ins = load_insample()
    pss = compute_pss(ins)

    fig, ax = plt.subplots(figsize=(9, 5))
    data_list = [pss[pss["agent_type"] == a]["PSS"].dropna().values for a in ARCH_ORDER]
    colors    = [ARCH_COLORS[a] for a in ARCH_ORDER]

    parts = ax.violinplot(data_list, positions=range(len(ARCH_ORDER)),
                          showmedians=False, showextrema=False, widths=0.6)
    for pc, color in zip(parts["bodies"], colors):
        pc.set_facecolor(color)
        pc.set_alpha(0.55)
        pc.set_edgecolor("black")
        pc.set_linewidth(0.8)

    bp = ax.boxplot(data_list, positions=range(len(ARCH_ORDER)),
                    widths=0.18, patch_artist=True,
                    medianprops=dict(color="black", linewidth=2),
                    whiskerprops=dict(linewidth=1.2),
                    capprops=dict(linewidth=1.2),
                    flierprops=dict(marker="o", markersize=3, alpha=0.5))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)

    # annotate medians
    for i, vals in enumerate(data_list):
        med = np.median(vals)
        ax.text(i, med + 1.5, f"{med:.1f}", ha="center", va="bottom",
                fontsize=9, fontweight="bold")

    ax.set_xticks(range(len(ARCH_ORDER)))
    ax.set_xticklabels(ARCH_ORDER, fontsize=10)
    ax.set_ylabel("PSS (Persona Sensitivity Score)", fontsize=10)
    ax.set_title("ProSA PSS Distribution by Architecture (In-Sample)", fontsize=12, fontweight="bold")
    ax.set_ylim(0, None)

    legend_handles = [mpatches.Patch(color=ARCH_COLORS[a], label=a, alpha=0.7) for a in ARCH_ORDER]
    ax.legend(handles=legend_handles, fontsize=9, loc="upper right")

    plt.tight_layout()
    path = OUT_DIR / "fig4_pss_violin.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 5 — Intent PSS heatmap: architecture × intent (in-sample)
# ═══════════════════════════════════════════════════════════════════════════
def fig5_intent_pss_heatmap():
    ins = load_insample()
    with open(FS_PATH, encoding="utf-8") as f:
        fs = json.load(f)

    intent_map = {k: v["metadata"]["intent"] for k, v in fs.items()}
    ins["intent"] = ins["case_id"].map(intent_map)
    pss = compute_pss(ins)
    pss["intent"] = pss["case_id"].map(intent_map)

    heat = pss.groupby(["intent", "agent_type"])["PSS"].mean().unstack()
    heat = heat.reindex(columns=ARCH_ORDER)

    # sort intents by mean PSS (descending)
    heat["_mean"] = heat.mean(axis=1)
    heat = heat.sort_values("_mean", ascending=False).drop(columns="_mean")

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(
        heat, ax=ax, annot=True, fmt=".1f", cmap="YlOrRd",
        linewidths=0.5, linecolor="white",
        cbar_kws={"label": "Mean PSS", "shrink": 0.8},
        annot_kws={"size": 9},
    )
    ax.set_title("ProSA PSS Heatmap: Intent × Architecture (In-Sample)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Architecture", fontsize=10)
    ax.set_ylabel("Intent", fontsize=10)
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=8, rotation=0)

    plt.tight_layout()
    path = OUT_DIR / "fig5_intent_pss_heatmap.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 6 — Cost-efficiency scatter (in-sample)
# ═══════════════════════════════════════════════════════════════════════════
def fig6_cost_efficiency():
    ins = load_insample()
    agg = ins.groupby(["agent_type", "persona_type"]).agg(
        tokens=("total_tokens", "mean"),
        judge=("s_answer_quality", "mean"),
        completion=("completed", "mean"),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(10, 6.5))

    for persona in PERSONA_ORDER:
        sub = agg[agg["persona_type"] == persona]
        for _, row in sub.iterrows():
            arch    = row["agent_type"]
            color   = ARCH_COLORS[arch]
            pcolor  = PERSONA_COLORS[persona]
            size    = 120 + row["completion"] * 400   # bubble ~ completion rate
            ax.scatter(row["tokens"], row["judge"],
                       s=size, color=color, edgecolors=pcolor,
                       linewidth=2.2, alpha=0.82, zorder=3)
            ax.annotate(
                f"{arch[:4]}-{persona[:3]}",
                (row["tokens"], row["judge"]),
                textcoords="offset points", xytext=(6, 4),
                fontsize=7.5, color="gray",
            )

    # legend: architecture patches
    arch_handles = [mpatches.Patch(color=ARCH_COLORS[a], label=a, alpha=0.8) for a in ARCH_ORDER]
    persona_handles = [
        mpatches.Patch(facecolor="white", edgecolor=PERSONA_COLORS[p],
                       linewidth=2, label=p) for p in PERSONA_ORDER
    ]
    size_handles = [
        plt.scatter([], [], s=120 + r * 400, color="gray", alpha=0.5, label=f"{int(r*100)}%")
        for r in [0.5, 0.8, 1.0]
    ]

    leg1 = ax.legend(handles=arch_handles, title="Architecture", loc="lower right",
                     fontsize=8, title_fontsize=9, framealpha=0.9)
    leg2 = ax.legend(handles=persona_handles, title="Persona (edge color)", loc="lower center",
                     fontsize=8, title_fontsize=9, framealpha=0.9)
    leg3 = ax.legend(handles=size_handles, title="Completion Rate", loc="upper left",
                     fontsize=8, title_fontsize=9, framealpha=0.9, scatterpoints=1)
    ax.add_artist(leg1)
    ax.add_artist(leg2)

    ax.set_xlabel("Mean Token Count per Dialogue", fontsize=10)
    ax.set_ylabel("LLM Judge Score (S_AnswerQuality)", fontsize=10)
    ax.set_title("Cost-Efficiency Trade-off: Tokens vs Quality (In-Sample)", fontsize=12, fontweight="bold")

    plt.tight_layout()
    path = OUT_DIR / "fig6_cost_efficiency.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 7 — In-sample vs OOS S_Agent delta (additional insight)
# ═══════════════════════════════════════════════════════════════════════════
def fig7_insample_oos_delta():
    ins = load_insample()
    oos = load_oos()

    ins_m = ins.groupby("agent_type")["s_agent"].mean().reindex(ARCH_ORDER)
    oos_m = oos.groupby("agent_type")["s_agent"].mean().reindex(ARCH_ORDER)
    delta = oos_m - ins_m

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("In-Sample vs OOS: S_Agent Comparison & Generalization Gap",
                 fontsize=12, fontweight="bold")

    # Left: side-by-side bars for in-sample and OOS
    ax = axes[0]
    x = np.arange(len(ARCH_ORDER))
    w = 0.35
    b1 = ax.bar(x - w/2, ins_m.values, w, label="In-Sample", color="#4472C4", alpha=0.85)
    b2 = ax.bar(x + w/2, oos_m.values, w, label="OOS", color="#ED7D31", alpha=0.85)
    for bar, val in zip(list(b1) + list(b2), list(ins_m.values) + list(oos_m.values)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{val:.1f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(ARCH_ORDER, fontsize=9)
    ax.set_ylabel("Mean S_Agent Score", fontsize=9)
    ax.set_title("Overall S_Agent Comparison", fontsize=10, fontweight="bold")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=9)

    # Right: delta bar (OOS - In-sample)
    ax2 = axes[1]
    bar_colors = ["#C00000" if d < 0 else "#70AD47" for d in delta.values]
    bars = ax2.bar(ARCH_ORDER, delta.values, color=bar_colors, alpha=0.85, edgecolor="white")
    for bar, val in zip(bars, delta.values):
        ypos = bar.get_height() + 0.2 if val >= 0 else bar.get_height() - 1.5
        ax2.text(bar.get_x() + bar.get_width()/2, ypos,
                 f"{val:+.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_ylabel("S_Agent Delta (OOS - In-Sample)", fontsize=9)
    ax2.set_title("Generalization Gap by Architecture", fontsize=10, fontweight="bold")
    ax2.tick_params(axis="x", labelsize=9)

    plt.tight_layout()
    path = OUT_DIR / "fig7_generalization_gap.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 0 — Experiment pipeline flowchart
# ═══════════════════════════════════════════════════════════════════════════
def fig0_experiment_flow():
    fig, ax = plt.subplots(figsize=(14, 11))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 11)
    ax.axis("off")
    fig.patch.set_facecolor("#FAFAFA")

    def box(ax, x, y, w, h, text, facecolor, edgecolor="#333333",
            fontsize=9, bold=False, radius=0.3, text_color="black"):
        fancy = mpatches.FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle=f"round,pad={radius}", linewidth=1.2,
            facecolor=facecolor, edgecolor=edgecolor, zorder=3,
        )
        ax.add_patch(fancy)
        ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
                fontweight="bold" if bold else "normal",
                color=text_color, zorder=4, wrap=True,
                multialignment="center")

    def arrow(ax, x1, y1, x2, y2, label=""):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#555555",
                                   lw=1.4, connectionstyle="arc3,rad=0.0"),
                    zorder=2)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx + 0.12, my, label, fontsize=7.5, color="#666666",
                    va="center", zorder=5)

    # ── Title ──────────────────────────────────────────────────────────────
    ax.text(7, 10.55, "Experiment Pipeline Overview", ha="center", va="center",
            fontsize=14, fontweight="bold", color="#1A1A1A")

    # ── Row 1: Datasets ─────────────────────────────────────────────────────
    box(ax, 3.5, 9.7, 4.2, 0.85,
        "In-Sample Dataset\n150 cases × 15 intents\n(easy / medium / hard)",
        "#D6E4F7", "#2E75B6", fontsize=8.5)
    box(ax, 10.5, 9.7, 4.2, 0.85,
        "OOS Dataset\n50 cases × 15 intents\n(9 new + 6 overlap intents)",
        "#FCE4D6", "#C55A11", fontsize=8.5)

    # arrows down to Simulation
    arrow(ax, 3.5, 9.27, 3.5, 8.65)
    arrow(ax, 10.5, 9.27, 10.5, 8.65)

    # ── Row 2: Simulation block ──────────────────────────────────────────────
    box(ax, 7, 8.25, 12.5, 0.75,
        "Simulation Engine   ·   llama3.1:8b (Ollama)   ·   temperature=0.0   ·   history=8 turns",
        "#EEF2FF", "#5B5EA6", fontsize=8.5, bold=True)
    arrow(ax, 3.5, 8.65, 5.0, 8.63)
    arrow(ax, 10.5, 8.65, 9.0, 8.63)

    # ── Row 3: Architectures × Personas ─────────────────────────────────────
    arch_x = [2.0, 4.8, 7.5, 10.2]
    arch_names = ["Single-slot\n(1 LLM call / turn)",
                  "ReAct\n(max 5 iter / turn)",
                  "Reflection\n(max 3 iter / turn)",
                  "PlanExecute\n(+ Imm. Synthesis)"]
    arch_colors = ["#5B9BD5", "#ED7D31", "#A9D18E", "#7030A0"]
    arch_text_colors = ["white", "white", "black", "white"]

    for x, name, fc, tc in zip(arch_x, arch_names, arch_colors, arch_text_colors):
        arrow(ax, 7, 7.87, x, 7.45)
        box(ax, x, 7.1, 2.55, 0.65, name, fc, fc, fontsize=7.5,
            text_color=tc, radius=0.2)

    persona_x = [12.2, 13.0, 13.8]   # collapsed to right
    persona_names = ["Polite", "Adver-\nsarial", "VIP"]
    persona_colors = ["#4472C4", "#C00000", "#C9A227"]
    box(ax, 12.8, 7.1, 2.2, 0.65,
        "× 3 Personas\nPolite / Adversarial / VIP",
        "#FFF2CC", "#C9A227", fontsize=7.5, radius=0.2)
    arrow(ax, 7, 7.87, 12.8, 7.45)

    # combination label
    ax.text(7, 6.58, "4 architectures × 3 personas × (150 + 50) cases  =  2,400 dialogues",
            ha="center", va="center", fontsize=8, color="#444444",
            style="italic")

    # ── Row 4: Dialogue Logs ────────────────────────────────────────────────
    arrow(ax, 7, 6.35, 7, 5.85)
    box(ax, 7, 5.6, 5.0, 0.65,
        "Dialogue Logs  (JSON)",
        "#F2F2F2", "#888888", fontsize=8.5)

    # ── Row 5: Two evaluation branches ─────────────────────────────────────
    # Left: programmatic metrics
    arrow(ax, 4.8, 5.27, 3.2, 4.7)
    box(ax, 3.0, 4.4, 3.8, 0.65,
        "Programmatic Metrics\nS_Tool · S_Trajectory · S_Efficiency\n+ S_CompletionStatus",
        "#E2F0D9", "#548235", fontsize=7.5)

    # Right: LLM Judge
    arrow(ax, 9.2, 5.27, 10.8, 4.7)
    box(ax, 11.0, 4.4, 3.8, 0.65,
        "LLM-as-Judge\nGemini 2.0 Flash-lite (blind)\nS_Resolution · S_Completeness · S_Tone",
        "#FCE4D6", "#C55A11", fontsize=7.5)

    # Judge → S_AnswerQuality
    arrow(ax, 11.0, 4.07, 11.0, 3.55)
    box(ax, 11.0, 3.3, 3.2, 0.45,
        "S_AnswerQuality  (0–100)", "#FCE4D6", "#C55A11", fontsize=7.5)

    # merge into S_Outcome
    arrow(ax, 3.0, 4.07, 3.0, 3.55)
    box(ax, 3.0, 3.3, 3.2, 0.45,
        "S_CompletionStatus  (0/20/40/80/100)", "#E2F0D9", "#548235", fontsize=7.5)

    arrow(ax, 3.0, 3.07, 5.5, 2.65)
    arrow(ax, 11.0, 3.07, 8.5, 2.65)
    box(ax, 7, 2.4, 5.5, 0.65,
        "S_Outcome = 0.40 × S_CompletionStatus + 0.60 × S_AnswerQuality",
        "#FFF2CC", "#BF8F00", fontsize=8)

    # ── Row 6: S_Agent ──────────────────────────────────────────────────────
    arrow(ax, 7, 2.07, 7, 1.6)
    box(ax, 7, 1.3, 9.5, 0.65,
        "S_Agent = 0.50·S_Outcome + 0.20·S_Tool + 0.10·S_Trajectory + 0.20·S_Efficiency"
        "   [cap @ 40 if I_fatal]",
        "#E8D5F5", "#7030A0", fontsize=8.5, bold=True)

    # ── Row 7: Analysis outputs ─────────────────────────────────────────────
    arrow(ax, 7, 0.97, 7, 0.55)
    analysis_x = [2.0, 5.0, 8.5, 12.0]
    analysis_labels = [
        "Arch. Comparison\n(in-sample / OOS)",
        "Generalization Gap\n(ΔS_Agent)",
        "Weight Sensitivity\n(969 combos)",
        "ProSA PSS\n(Persona × Intent)",
    ]
    analysis_colors = ["#D6E4F7", "#FCE4D6", "#E2F0D9", "#FFF2CC"]
    for x, lbl, fc in zip(analysis_x, analysis_labels, analysis_colors):
        arrow(ax, 7, 0.55, x, 0.2)
        box(ax, x, 0.05, 2.6, 0.35, lbl, fc, "#888888", fontsize=7, radius=0.15)

    plt.tight_layout(pad=0.3)
    path = OUT_DIR / "fig0_experiment_flow.png"
    plt.savefig(path, bbox_inches="tight", dpi=180)
    plt.close()
    print(f"Saved {path}")


# ── main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating figures...")
    fig0_experiment_flow()
    fig1_s_agent_overview()
    fig2_insample_performance()
    fig3_oos_performance()
    fig4_pss_violin()
    fig5_intent_pss_heatmap()
    fig6_cost_efficiency()
    fig7_insample_oos_delta()
    print(f"\nAll figures saved to {OUT_DIR}")
