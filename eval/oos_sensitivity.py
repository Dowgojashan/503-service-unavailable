"""
OOS 敏感度分析：
  1. Weight Sensitivity — 969 種 weight 組合下 OOS S_Agent 排名穩定性
  2. ProSA (PSS)        — 跨 Persona 品質敏感度（judge score variance）

輸出：
  outputs/reports/oos_weight_sensitivity_ranks.csv
  outputs/reports/oos_weight_sensitivity_summary.txt
  outputs/reports/oos_pss_summary.txt
"""

from __future__ import annotations

import csv
import itertools
from collections import defaultdict
from pathlib import Path

INPUT_CSV   = Path("outputs/reports/oos_s_agent_results.csv")
OUT_DIR     = Path("outputs/reports")
AGENTS      = ["ReAct", "PlanExecute", "Reflection", "Single-slot"]
PERSONAS    = ["Polite", "Adversarial", "VIP"]
STEP        = 0.05
I_FATAL_CAP = 40


# ─────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────

def load_rows(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            try:
                rows.append({
                    "case_id":      rec["case_id"],
                    "agent_type":   rec["agent_type"],
                    "persona_type": rec["persona_type"],
                    "difficulty":   rec.get("difficulty", "medium"),
                    "s_outcome":    float(rec["s_outcome"]),
                    "s_tool":       float(rec["s_tool"]),
                    "s_trajectory": float(rec["s_trajectory"]),
                    "s_efficiency": float(rec["s_efficiency"]),
                    "i_fatal":      int(rec["i_fatal"]),
                    "judge_score":  float(rec["s_answer_quality"]),
                    "s_agent":      float(rec["s_agent"]),
                })
            except (ValueError, KeyError):
                pass
    return rows


# ─────────────────────────────────────────────────────────────
# 1. Weight Sensitivity
# ─────────────────────────────────────────────────────────────

def generate_weight_combos() -> list[tuple[float, float, float, float]]:
    n = round(1.0 / STEP)
    combos = []
    for a, b, c in itertools.product(range(1, n), repeat=3):
        d = n - a - b - c
        if d >= 1:
            combos.append((round(a*STEP,2), round(b*STEP,2),
                           round(c*STEP,2), round(d*STEP,2)))
    return combos


def compute_s_agent(row: dict, wo: float, wt: float, wtr: float, we: float) -> float:
    s_raw = wo*row["s_outcome"] + wt*row["s_tool"] + wtr*row["s_trajectory"] + we*row["s_efficiency"]
    return min(s_raw, I_FATAL_CAP) if row["i_fatal"] else s_raw


def agent_means(rows: list[dict], wo, wt, wtr, we) -> dict[str, float]:
    totals: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        totals[row["agent_type"]].append(compute_s_agent(row, wo, wt, wtr, we))
    return {a: sum(v)/len(v) for a, v in totals.items() if v}


def rank_agents(means: dict[str, float]) -> list[str]:
    return sorted(means, key=lambda a: means[a], reverse=True)


def run_weight_sensitivity(rows: list[dict]) -> None:
    combos = generate_weight_combos()
    print(f"\n[Weight Sensitivity] {len(combos)} combos × {len(rows)} OOS rows")

    baseline = (0.50, 0.20, 0.10, 0.20)
    baseline_means  = agent_means(rows, *baseline)
    baseline_order  = rank_agents(baseline_means)

    rank_counts: dict[str, dict[int, int]] = {a: {1:0,2:0,3:0,4:0} for a in AGENTS}
    upset_combos: list[tuple] = []
    score_records: list[dict] = []

    out_csv = OUT_DIR / "oos_weight_sensitivity_ranks.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["w_outcome","w_tool","w_trajectory","w_efficiency"] + \
                     [f"mean_{a.replace('-','_').replace(' ','_')}" for a in AGENTS] + \
                     ["rank1","rank2","rank3","rank4"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for wo, wt, wtr, we in combos:
            means = agent_means(rows, wo, wt, wtr, we)
            order = rank_agents(means)
            for pos, ag in enumerate(order, 1):
                rank_counts[ag][pos] += 1
            if order[0] != baseline_order[0]:
                upset_combos.append((wo, wt, wtr, we, order[0], means))
            row_out = {"w_outcome":wo,"w_tool":wt,"w_trajectory":wtr,"w_efficiency":we}
            for a in AGENTS:
                row_out[f"mean_{a.replace('-','_').replace(' ','_')}"] = round(means.get(a,0),2)
            row_out["rank1"] = order[0]; row_out["rank2"] = order[1]
            row_out["rank3"] = order[2]; row_out["rank4"] = order[3]
            writer.writerow(row_out)
            score_records.append({"wo":wo,"wt":wt,"wtr":wtr,"we":we,"means":means})

    total = len(combos)
    lines = []
    lines.append("="*72)
    lines.append("OOS S_Agent Weight Sensitivity Analysis")
    lines.append(f"  Input : {INPUT_CSV}  ({len(rows)} rows)")
    lines.append(f"  Sweep : step={STEP}, total combos={total}")
    lines.append(f"  Baseline weights: Outcome={baseline[0]} Tool={baseline[1]} Traj={baseline[2]} Eff={baseline[3]}")
    lines.append("="*72)

    lines.append("\n--- Baseline scores (current weights) ---")
    for a in baseline_order:
        lines.append(f"  #{baseline_order.index(a)+1}  {a:<14}  mean={baseline_means[a]:.2f}")

    lines.append("\n--- Rank Frequency (% of all weight combos) ---")
    lines.append(f"  {'Architecture':<14}  {'Rank 1':>8}  {'Rank 2':>8}  {'Rank 3':>8}  {'Rank 4':>8}")
    lines.append("  " + "-"*56)
    for a in AGENTS:
        r = rank_counts[a]
        lines.append(
            f"  {a:<14}  "
            f"{r[1]/total*100:>7.1f}%  {r[2]/total*100:>7.1f}%  "
            f"{r[3]/total*100:>7.1f}%  {r[4]/total*100:>7.1f}%"
        )

    lines.append(f"\n--- Top-1 Rank Stability ---")
    lines.append(f"  Baseline top-1: {baseline_order[0]}")
    lines.append(f"  Combos where top-1 differs: {len(upset_combos)} / {total} ({len(upset_combos)/total*100:.1f}%)")
    if upset_combos:
        challenger_counts: dict[str, int] = defaultdict(int)
        for *_, champ, _ in upset_combos:
            challenger_counts[champ] += 1
        lines.append("  Challengers:")
        for ag, cnt in sorted(challenger_counts.items(), key=lambda x: -x[1]):
            lines.append(f"    {ag}: {cnt} combos ({cnt/total*100:.1f}%)")
        lines.append("  Example upset combos:")
        for wo, wt, wtr, we, champ, means in upset_combos[:5]:
            lines.append(f"    Outcome={wo:.2f} Tool={wt:.2f} Traj={wtr:.2f} Eff={we:.2f} → {champ} ({means[champ]:.1f})")

    # Score range
    lines.append("\n--- Score Range Across All Weight Combos ---")
    agent_scores_all: dict[str, list[float]] = defaultdict(list)
    for rec in score_records:
        for a in AGENTS:
            agent_scores_all[a].append(rec["means"].get(a, 0.0))
    for a in baseline_order:
        s = agent_scores_all[a]
        lines.append(f"  {a:<14}  min={min(s):.1f}  mean={sum(s)/len(s):.1f}  max={max(s):.1f}  range={max(s)-min(s):.1f}")

    lines.append("\n" + "="*72)
    summary = "\n".join(lines)
    print(summary)
    out_txt = OUT_DIR / "oos_weight_sensitivity_summary.txt"
    out_txt.write_text(summary, encoding="utf-8")
    print(f"\nSaved: {out_csv}")
    print(f"Saved: {out_txt}")


# ─────────────────────────────────────────────────────────────
# 2. ProSA / PSS
# ─────────────────────────────────────────────────────────────

def run_pss(rows: list[dict]) -> None:
    print(f"\n[ProSA PSS] Computing cross-persona sensitivity …")

    # Build lookup: (agent, case_id, persona) → judge_score
    score_map: dict[tuple, float] = {}
    for r in rows:
        score_map[(r["agent_type"], r["case_id"], r["persona_type"])] = r["judge_score"]

    s_agent_map: dict[tuple, float] = {}
    for r in rows:
        s_agent_map[(r["agent_type"], r["case_id"], r["persona_type"])] = r["s_agent"]

    case_ids = sorted({r["case_id"] for r in rows})
    difficulty_map = {r["case_id"]: r["difficulty"] for r in rows}

    lines = []
    lines.append("="*72)
    lines.append("OOS ProSA — Prompt Sensitivity Score (PSS)")
    lines.append("  Metric: judge_score (s_answer_quality, 0-100) across 3 personas")
    lines.append("  PSS_i = mean(|score_P-score_A| + |score_P-score_V| + |score_A-score_V|) / 3")
    lines.append("="*72)

    # ── Per-architecture PSS ──
    lines.append("\n--- 1. Overall PSS by Architecture ---")
    lines.append(f"  {'Architecture':<14}  {'PSS mean':>9}  {'PSS max':>8}  {'PSS std':>8}  {'PSS>20 (%)':>12}")
    lines.append("  " + "-"*60)

    pss_by_agent: dict[str, list[float]] = {a: [] for a in AGENTS}

    for agent in AGENTS:
        for cid in case_ids:
            scores = [score_map.get((agent, cid, p)) for p in PERSONAS]
            if any(s is None for s in scores):
                continue
            p, a, v = scores
            pss_i = (abs(p-a) + abs(p-v) + abs(a-v)) / 3
            pss_by_agent[agent].append(pss_i)

    for agent in AGENTS:
        vals = pss_by_agent[agent]
        if not vals:
            continue
        mean_ = sum(vals)/len(vals)
        max_  = max(vals)
        std_  = (sum((x-mean_)**2 for x in vals)/len(vals))**0.5
        hi    = sum(1 for x in vals if x > 20)
        lines.append(f"  {agent:<14}  {mean_:>9.2f}  {max_:>8.2f}  {std_:>8.2f}  {hi:>5} ({hi/len(vals)*100:.0f}%)")

    # ── Pairwise delta ──
    lines.append("\n--- 2. Pairwise Persona Delta (mean |score_A − score_B|) ---")
    lines.append(f"  {'Architecture':<14}  {'Polite–Adv':>12}  {'Polite–VIP':>12}  {'Adv–VIP':>10}")
    lines.append("  " + "-"*54)
    pairs = [("Polite","Adversarial"), ("Polite","VIP"), ("Adversarial","VIP")]
    for agent in AGENTS:
        deltas = []
        for p1, p2 in pairs:
            diffs = []
            for cid in case_ids:
                s1 = score_map.get((agent, cid, p1))
                s2 = score_map.get((agent, cid, p2))
                if s1 is not None and s2 is not None:
                    diffs.append(abs(s1 - s2))
            deltas.append(sum(diffs)/len(diffs) if diffs else 0)
        lines.append(f"  {agent:<14}  {deltas[0]:>12.2f}  {deltas[1]:>12.2f}  {deltas[2]:>10.2f}")

    # ── PSS distribution ──
    lines.append("\n--- 3. PSS Distribution ---")
    lines.append(f"  {'Architecture':<14}  {'PSS≤10':>8}  {'10<PSS≤20':>12}  {'PSS>20':>8}")
    lines.append("  " + "-"*50)
    for agent in AGENTS:
        vals = pss_by_agent[agent]
        lo = sum(1 for x in vals if x <= 10)
        mid= sum(1 for x in vals if 10 < x <= 20)
        hi = sum(1 for x in vals if x > 20)
        n  = len(vals)
        lines.append(f"  {agent:<14}  {lo:>4}({lo/n*100:.0f}%)  {mid:>6}({mid/n*100:.0f}%)  {hi:>4}({hi/n*100:.0f}%)")

    # ── PSS by difficulty ──
    lines.append("\n--- 4. PSS by Difficulty (merged architectures) ---")
    lines.append(f"  {'Difficulty':<12}  {'n cases':>8}  {'PSS mean':>10}  {'Judge mean':>12}")
    lines.append("  " + "-"*48)
    diff_pss: dict[str, list[float]] = defaultdict(list)
    diff_judge: dict[str, list[float]] = defaultdict(list)
    for agent in AGENTS:
        for cid in case_ids:
            scores = [score_map.get((agent, cid, p)) for p in PERSONAS]
            if any(s is None for s in scores):
                continue
            p, a, v = scores
            pss_i = (abs(p-a) + abs(p-v) + abs(a-v)) / 3
            diff = difficulty_map.get(cid, "medium")
            diff_pss[diff].append(pss_i)
            diff_judge[diff].extend([p, a, v])
    for diff in ["easy","medium","hard"]:
        vals  = diff_pss[diff]
        jvals = diff_judge[diff]
        n = len(vals)
        lines.append(f"  {diff:<12}  {n:>8}  {sum(vals)/n:>10.2f}  {sum(jvals)/len(jvals):>12.2f}")

    # ── PSS by intent (merged architectures) ──
    intent_map = {r["case_id"]: r.get("difficulty","") for r in rows}
    # need actual intent — load from OOS fact sheets
    try:
        import json
        oos_fs = json.load(open("data/oos_fact_sheets.json", encoding="utf-8"))
        cid_intent = {cid: oos_fs[cid]["metadata"]["intent"] for cid in oos_fs}
    except Exception:
        cid_intent = {}

    if cid_intent:
        lines.append("\n--- 5. PSS by Intent (merged architectures) ---")
        lines.append(f"  {'Intent':<28}  {'n':>4}  {'PSS mean':>10}  {'Judge mean':>12}")
        lines.append("  " + "-"*60)
        intent_pss: dict[str, list[float]] = defaultdict(list)
        intent_judge: dict[str, list[float]] = defaultdict(list)
        for agent in AGENTS:
            for cid in case_ids:
                scores = [score_map.get((agent, cid, p)) for p in PERSONAS]
                if any(s is None for s in scores):
                    continue
                p, a, v = scores
                pss_i = (abs(p-a) + abs(p-v) + abs(a-v)) / 3
                intent = cid_intent.get(cid, "unknown")
                intent_pss[intent].append(pss_i)
                intent_judge[intent].extend([p, a, v])
        for intent in sorted(intent_pss, key=lambda x: -sum(intent_pss[x])/len(intent_pss[x])):
            vals  = intent_pss[intent]
            jvals = intent_judge[intent]
            n = len(vals)
            lines.append(f"  {intent:<28}  {n:>4}  {sum(vals)/n:>10.2f}  {sum(jvals)/len(jvals):>12.2f}")

    # ── Completion rate consistency ──
    lines.append("\n--- 6. Completion Rate Cross-Persona Consistency ---")
    lines.append(f"  {'Architecture':<14}  {'All 3 resolved':>15}  {'Mixed':>8}  {'All 3 PENDING':>15}")
    lines.append("  " + "-"*58)
    status_map_r: dict[tuple, str] = {}
    for r in rows:
        status_map_r[(r["agent_type"], r["case_id"], r["persona_type"])] = r.get("s_agent","0")
    # use s_agent > 50 as proxy for "resolved"
    for agent in AGENTS:
        all_res = mixed = all_fail = 0
        for cid in case_ids:
            resolved = []
            for p in PERSONAS:
                sa = s_agent_map.get((agent, cid, p))
                if sa is not None:
                    resolved.append(sa >= 50)
            if len(resolved) < 3:
                continue
            if all(resolved):
                all_res += 1
            elif not any(resolved):
                all_fail += 1
            else:
                mixed += 1
        n = len(case_ids)
        lines.append(f"  {agent:<14}  {all_res:>6}({all_res/n*100:.0f}%)  {mixed:>5}({mixed/n*100:.0f}%)  {all_fail:>6}({all_fail/n*100:.0f}%)")

    lines.append("\n" + "="*72)
    summary = "\n".join(lines)
    print(summary)
    out_txt = OUT_DIR / "oos_pss_summary.txt"
    out_txt.write_text(summary, encoding="utf-8")
    print(f"\nSaved: {out_txt}")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_rows(INPUT_CSV)
    print(f"Loaded {len(rows)} rows from {INPUT_CSV}")

    run_weight_sensitivity(rows)
    run_pss(rows)
