"""
S_Agent weight sensitivity analysis.

Sweeps all valid combinations of (W_OUTCOME, W_TOOL, W_TRAJECTORY, W_EFFICIENCY)
summing to 1.0, step 0.05, each weight >= 0.05.

For each combination:
  - Recomputes S_Agent per row (with I_FATAL cap)
  - Averages per architecture
  - Records architecture ranking (1st to 4th)

Outputs:
  outputs/reports/weight_sensitivity_ranks.csv   — one row per weight combo
  outputs/reports/weight_sensitivity_summary.txt — rank stability + key findings
"""

from __future__ import annotations

import csv
import itertools
from pathlib import Path
from collections import defaultdict

INPUT_CSV  = Path("outputs/reports/s_agent_results_full.csv")
OUT_CSV    = Path("outputs/reports/weight_sensitivity_ranks.csv")
OUT_TXT    = Path("outputs/reports/weight_sensitivity_summary.txt")

I_FATAL_CAP = 40
STEP        = 0.05
AGENTS      = ["ReAct", "PlanExecute", "Reflection", "Single-slot"]


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_data(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            try:
                rows.append({
                    "agent_type":   rec["agent_type"],
                    "s_outcome":    float(rec["s_outcome"]),
                    "s_tool":       float(rec["s_tool"]),
                    "s_trajectory": float(rec["s_trajectory"]),
                    "s_efficiency": float(rec["s_efficiency"]),
                    "i_fatal":      int(rec["i_fatal"]),
                })
            except (ValueError, KeyError):
                pass  # skip rows with missing numeric values
    return rows


# ---------------------------------------------------------------------------
# Weight grid
# ---------------------------------------------------------------------------

def generate_weight_combos() -> list[tuple[float, float, float, float]]:
    """All (w1, w2, w3, w4) with wi>=STEP, sum=1, step=STEP."""
    n = round(1.0 / STEP)
    combos = []
    for a, b, c in itertools.product(range(1, n), repeat=3):
        d = n - a - b - c
        if d >= 1:
            combos.append((
                round(a * STEP, 2),
                round(b * STEP, 2),
                round(c * STEP, 2),
                round(d * STEP, 2),
            ))
    return combos


# ---------------------------------------------------------------------------
# Compute S_Agent for one weight combo
# ---------------------------------------------------------------------------

def compute_s_agent(row: dict, wo: float, wt: float, wtr: float, we: float) -> float:
    s_raw = (
        wo  * row["s_outcome"]
      + wt  * row["s_tool"]
      + wtr * row["s_trajectory"]
      + we  * row["s_efficiency"]
    )
    return min(s_raw, I_FATAL_CAP) if row["i_fatal"] else s_raw


def agent_means(rows: list[dict], wo: float, wt: float, wtr: float, we: float) -> dict[str, float]:
    totals: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        score = compute_s_agent(row, wo, wt, wtr, we)
        totals[row["agent_type"]].append(score)
    return {a: (sum(v) / len(v) if v else 0.0) for a, v in totals.items()}


def rank_agents(means: dict[str, float]) -> list[str]:
    """Return agents sorted best-first."""
    return sorted(means, key=lambda a: means[a], reverse=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    rows = load_data(INPUT_CSV)
    print(f"Loaded {len(rows)} rows from {INPUT_CSV}")
    for a in AGENTS:
        n = sum(1 for r in rows if r["agent_type"] == a)
        print(f"  {a}: {n} rows")

    combos = generate_weight_combos()
    print(f"\nWeight combinations to test: {len(combos)}")

    # Track rank counts: rank_counts[agent][rank] = count
    rank_counts: dict[str, dict[int, int]] = {a: {1: 0, 2: 0, 3: 0, 4: 0} for a in AGENTS}

    # Track when ranking order differs from baseline
    baseline_combo = (0.35, 0.25, 0.20, 0.20)
    baseline_means = agent_means(rows, *baseline_combo)
    baseline_order = rank_agents(baseline_means)

    upset_combos: list[tuple] = []   # combos where top-1 differs from baseline

    # Mean score per architecture per combo (for sensitivity quantification)
    score_records: list[dict] = []

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "w_outcome", "w_tool", "w_trajectory", "w_efficiency",
        ] + [f"mean_{a.replace('-','_').replace(' ','_')}" for a in AGENTS] + [
            "rank1", "rank2", "rank3", "rank4",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for wo, wt, wtr, we in combos:
            means = agent_means(rows, wo, wt, wtr, we)
            order = rank_agents(means)

            for rank_pos, agent in enumerate(order, start=1):
                rank_counts[agent][rank_pos] += 1

            if order[0] != baseline_order[0]:
                upset_combos.append((wo, wt, wtr, we, order[0], means))

            row_out = {
                "w_outcome":    wo,
                "w_tool":       wt,
                "w_trajectory": wtr,
                "w_efficiency": we,
            }
            for a in AGENTS:
                key = f"mean_{a.replace('-','_').replace(' ','_')}"
                row_out[key] = round(means.get(a, 0.0), 2)
            row_out["rank1"] = order[0]
            row_out["rank2"] = order[1]
            row_out["rank3"] = order[2]
            row_out["rank4"] = order[3]
            writer.writerow(row_out)
            score_records.append({"wo": wo, "wt": wt, "wtr": wtr, "we": we, "means": means})

    total = len(combos)

    # ---------------------------------------------------------------------------
    # Build summary text
    # ---------------------------------------------------------------------------

    lines = []
    lines.append("=" * 72)
    lines.append("S_Agent Weight Sensitivity Analysis")
    n_per_arch = len(rows) // len(AGENTS)
    lines.append(f"  Input : {INPUT_CSV}  ({len(rows)} rows, 4 architectures x {n_per_arch} cases)")
    lines.append(f"  Sweep : step={STEP}, min_weight={STEP}, total combos={total}")
    lines.append(f"  Baseline weights: Outcome={baseline_combo[0]} Tool={baseline_combo[1]} "
                 f"Traj={baseline_combo[2]} Eff={baseline_combo[3]}")
    lines.append("=" * 72)

    # Baseline scores
    lines.append("\n--- Baseline scores (current published weights) ---")
    for a in baseline_order:
        lines.append(f"  #{baseline_order.index(a)+1}  {a:<14}  mean={baseline_means[a]:.2f}")

    # Rank stability table
    lines.append("\n--- Rank Frequency (% of all weight combos) ---")
    header = f"  {'Architecture':<14}  {'Rank 1':>8}  {'Rank 2':>8}  {'Rank 3':>8}  {'Rank 4':>8}"
    lines.append(header)
    lines.append("  " + "-" * 56)
    for a in AGENTS:
        r = rank_counts[a]
        lines.append(
            f"  {a:<14}  "
            f"{r[1]/total*100:>7.1f}%  "
            f"{r[2]/total*100:>7.1f}%  "
            f"{r[3]/total*100:>7.1f}%  "
            f"{r[4]/total*100:>7.1f}%"
        )

    # Upset analysis
    lines.append(f"\n--- Top-1 Rank Stability ---")
    lines.append(f"  Baseline top-1: {baseline_order[0]}")
    lines.append(f"  Weight combos where top-1 differs: {len(upset_combos)} / {total} "
                 f"({len(upset_combos)/total*100:.1f}%)")
    if upset_combos:
        # Show the challengers
        challenger_counts: dict[str, int] = defaultdict(int)
        for *_, champ, _ in upset_combos:
            challenger_counts[champ] += 1
        lines.append("  Challengers:")
        for arch, cnt in sorted(challenger_counts.items(), key=lambda x: -x[1]):
            lines.append(f"    {arch}: {cnt} combos ({cnt/total*100:.1f}%)")
        # Show a few extreme examples
        lines.append("  Example upset combos (wo / wt / wtr / we → winner):")
        for wo, wt, wtr, we, champ, means in upset_combos[:5]:
            lines.append(
                f"    Outcome={wo:.2f} Tool={wt:.2f} Traj={wtr:.2f} Eff={we:.2f}  "
                f"→  {champ}  (mean={means[champ]:.1f})"
            )
    else:
        lines.append("  Top-1 is stable across ALL weight combinations.")

    # Score range per architecture
    lines.append("\n--- Score Range Across All Weight Combos (min / mean / max) ---")
    agent_scores_all: dict[str, list[float]] = defaultdict(list)
    for rec in score_records:
        for a in AGENTS:
            agent_scores_all[a].append(rec["means"].get(a, 0.0))
    for a in baseline_order:
        scores = agent_scores_all[a]
        lines.append(
            f"  {a:<14}  min={min(scores):.1f}  mean={sum(scores)/len(scores):.1f}  max={max(scores):.1f}  "
            f"range={max(scores)-min(scores):.1f}"
        )

    # Which weight drives the biggest spread?
    lines.append("\n--- Weight Impact on Score Gap (ReAct vs Single-slot) ---")
    lines.append("  (Shows how gap changes as each weight increases, others averaged)")
    for w_name, w_idx in [("W_OUTCOME", 0), ("W_TOOL", 1), ("W_TRAJECTORY", 2), ("W_EFFICIENCY", 3)]:
        buckets: dict[float, list[float]] = defaultdict(list)
        for rec in score_records:
            w_vals = (rec["wo"], rec["wt"], rec["wtr"], rec["we"])
            gap = rec["means"].get("ReAct", 0) - rec["means"].get("Single-slot", 0)
            buckets[w_vals[w_idx]].append(gap)
        lines.append(f"  {w_name}:")
        for wv in sorted(buckets):
            avg_gap = sum(buckets[wv]) / len(buckets[wv])
            lines.append(f"    {wv:.2f} → avg gap = {avg_gap:+.2f}")

    lines.append("\n" + "=" * 72)
    lines.append(f"Output CSV : {OUT_CSV}")
    lines.append("=" * 72)

    summary_text = "\n".join(lines)
    print(summary_text)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(f"\nSaved: {OUT_CSV}")
    print(f"Saved: {OUT_TXT}")


if __name__ == "__main__":
    main()
