"""
Phase 7 cost and marginal benefit analysis (evaluation_framework.md §4.8).

Loads all run-1 logs across all architectures and personas in a single batch so
that ProxyCost normalization denominators (max_tokens, max_llm_calls,
max_tool_calls) are globally consistent — eliminating the cross-batch problem
described in §4.8.

Computes:
  - ProxyCost  : 100*(0.5*TokenNorm + 0.3*LLMCallNorm + 0.2*ToolCallNorm)
  - NetValue   : V_i * S_Agent/100 - λ*ProxyCost
  - Delta_MB   : NetValue(arch) - NetValue(Single-slot)  [for the same case+persona]

Usage:
  python -m eval.cost_analysis \\
    --logs-dir outputs/logs \\
    --fact-sheets data/fact_sheets.json \\
    --policy-gt data/policy_ground_truth.json \\
    --output-dir outputs/reports
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Optional

from eval.metrics import (
    extract_tool_calls,
    compute_s_grounding,
    compute_s_tool,
    compute_s_trajectory,
    compute_s_efficiency,
    compute_i_fatal,
    compute_s_outcome,
    compute_s_agent,
    compute_proxy_cost,
    compute_net_value,
    _get_judge_score_as_answer_quality,
    V_MAP,
)

ARCHITECTURES = ["Single-slot", "ReAct", "Reflection", "PlanExecute"]
PERSONAS = ["Polite", "Adversarial", "VIP"]
PHASE1_CASES = ["CASE_001", "CASE_002", "CASE_015", "CASE_075", "CASE_090", "CASE_141"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_run1(path: Path) -> bool:
    """True if the file is a run-1 log (no _run2 / _run3 suffix)."""
    stem = path.stem
    return not (stem.endswith("_run2") or stem.endswith("_run3"))


def _load_run1_logs(logs_dir: Path) -> dict[Path, dict]:
    logs: dict[Path, dict] = {}
    for lf in sorted(logs_dir.rglob("log_*.json")):
        if not _is_run1(lf):
            continue
        try:
            with open(lf, encoding="utf-8") as f:
                logs[lf] = json.load(f)
        except Exception as e:
            print(f"  SKIP {lf.name}: {e}")
    return logs


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyse(
    logs_dir: str | Path,
    fact_sheets_path: str | Path,
    policy_gt_path: str | Path,
    output_dir: str | Path,
    only_cases: Optional[list[str]] = None,
) -> list[dict]:
    logs_dir = Path(logs_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(fact_sheets_path, encoding="utf-8") as f:
        all_fact_sheets: dict = json.load(f)
    with open(policy_gt_path, encoding="utf-8") as f:
        policy_gt: dict = json.load(f)

    # ── Load all run-1 logs globally ──────────────────────────────────────
    logs_by_file = _load_run1_logs(logs_dir)
    print(f"Loaded {len(logs_by_file)} run-1 log file(s) from {logs_dir}")

    if only_cases:
        logs_by_file = {
            lf: log for lf, log in logs_by_file.items()
            if log.get("metadata", {}).get("case_id", "") in only_cases
        }
        print(f"  Filtered to {len(logs_by_file)} logs for: {only_cases}")

    # ── Single-slot baselines for S_Efficiency (by difficulty) ───────────
    ss_tokens_by_diff: dict[str, list[float]] = {}
    ss_seconds_by_diff: dict[str, list[float]] = {}
    for lf, log in logs_by_file.items():
        if log.get("metadata", {}).get("agent_type", "") != "Single-slot":
            continue
        case_id = log.get("metadata", {}).get("case_id", "")
        fs = all_fact_sheets.get(case_id, {})
        diff = fs.get("metadata", {}).get("difficulty_label", "medium")
        secs = log.get("metadata", {}).get("execution_seconds")
        if secs and secs > 0:
            ss_seconds_by_diff.setdefault(diff, []).append(float(secs))
        else:
            tokens = log.get("usage_summary", {}).get("grand_total_tokens", 1) or 1
            ss_tokens_by_diff.setdefault(diff, []).append(float(tokens))

    baseline_tokens_map = {d: statistics.median(v) for d, v in ss_tokens_by_diff.items() if v}
    baseline_seconds_map = {d: statistics.median(v) for d, v in ss_seconds_by_diff.items() if v}
    print(f"  S_Efficiency baselines (tokens):  {baseline_tokens_map}")
    print(f"  S_Efficiency baselines (seconds): {baseline_seconds_map}")

    # ── Global max for ProxyCost normalization ────────────────────────────
    all_tokens    = [log.get("usage_summary", {}).get("grand_total_tokens", 0) or 0
                     for log in logs_by_file.values()]
    all_turns     = [len(log.get("conversation", [])) for log in logs_by_file.values()]
    all_tool_cnts = [len(extract_tool_calls(log)) for log in logs_by_file.values()]
    max_tokens    = max(all_tokens, default=1) or 1
    max_llm_calls = max(all_turns,  default=1) or 1
    max_tool_calls = max(all_tool_cnts, default=1) or 1
    print(f"  Global max -> tokens={max_tokens}, llm_calls={max_llm_calls}, tool_calls={max_tool_calls}")

    # ── Evaluate each log ─────────────────────────────────────────────────
    results: list[dict] = []
    for lf, log in logs_by_file.items():
        meta = log.get("metadata", {})
        case_id    = meta.get("case_id", "")
        agent_type = meta.get("agent_type", "")
        persona    = meta.get("persona_type", "")

        fs = all_fact_sheets.get(case_id, {})
        if not fs:
            print(f"  SKIP {lf.name}: no fact sheet for {case_id}")
            continue

        diff = fs.get("metadata", {}).get("difficulty_label", "medium")
        v_i  = fs.get("metadata", {}).get("v_i", V_MAP.get(diff, 2))

        # S_Efficiency: match units (seconds vs tokens)
        _secs = meta.get("execution_seconds")
        if _secs and _secs > 0:
            baseline_cost = baseline_seconds_map.get(diff, 1.0)
        else:
            baseline_cost = baseline_tokens_map.get(diff, float(max_tokens))

        s_answer_quality = _get_judge_score_as_answer_quality(log)
        grounding  = compute_s_grounding(log, fs, policy_gt)
        tool_m     = compute_s_tool(log, fs)
        traj       = compute_s_trajectory(log, fs)
        s_eff      = compute_s_efficiency(log, baseline_cost)
        fatal      = compute_i_fatal(log, fs)
        s_outcome  = compute_s_outcome(s_answer_quality, grounding["score"])
        ag_scores  = compute_s_agent(s_outcome, tool_m["score"], traj["score"], s_eff, fatal["value"])

        proxy_cost = compute_proxy_cost(log, max_tokens, max_llm_calls, max_tool_calls)
        net_value  = compute_net_value(v_i, ag_scores["s_agent"], proxy_cost)

        results.append({
            "case_id":      case_id,
            "agent_type":   agent_type,
            "persona_type": persona,
            "difficulty":   diff,
            "v_i":          v_i,
            "s_agent":      ag_scores["s_agent"],
            "s_efficiency": s_eff,
            "total_tokens": log.get("usage_summary", {}).get("grand_total_tokens", 0) or 0,
            "n_llm_calls":  len(log.get("conversation", [])),
            "n_tool_calls": len(extract_tool_calls(log)),
            "proxy_cost":   proxy_cost,
            "net_value":    net_value,
            "delta_mb":     None,   # filled below
        })

    # ── Delta_MB: NetValue(arch) − NetValue(Single-slot) ─────────────────
    ss_nv: dict[tuple[str, str], float] = {
        (r["case_id"], r["persona_type"]): r["net_value"]
        for r in results if r["agent_type"] == "Single-slot"
    }
    for r in results:
        ss_base = ss_nv.get((r["case_id"], r["persona_type"]))
        if ss_base is not None:
            r["delta_mb"] = round(r["net_value"] - ss_base, 4)

    # ── Save detail CSV ───────────────────────────────────────────────────
    detail_csv = output_dir / "cost_analysis.csv"
    fieldnames = [
        "case_id", "agent_type", "persona_type", "difficulty", "v_i",
        "s_agent", "s_efficiency",
        "total_tokens", "n_llm_calls", "n_tool_calls",
        "proxy_cost", "net_value", "delta_mb",
    ]
    with open(detail_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(
            sorted(results, key=lambda r: (r["case_id"], r["agent_type"], r["persona_type"]))
        )
    print(f"\nSaved {len(results)} rows -> {detail_csv}")

    # ── Print summary ─────────────────────────────────────────────────────
    _print_summary(results)

    return results


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def _print_summary(results: list[dict]) -> None:
    print("\n=== ProxyCost / NetValue / Delta_MB - averaged across 6 cases x 3 personas ===")
    print(f"{'Architecture':<14} {'n':>4} {'ProxyCost':>10} {'NetValue':>10} {'D_MB (avg)':>12}")
    print("-" * 54)

    arch_data: dict[str, dict[str, list[float]]] = {}
    for r in results:
        a = r["agent_type"]
        arch_data.setdefault(a, {"proxy_cost": [], "net_value": [], "delta_mb": []})
        arch_data[a]["proxy_cost"].append(r["proxy_cost"])
        arch_data[a]["net_value"].append(r["net_value"])
        if r["delta_mb"] is not None:
            arch_data[a]["delta_mb"].append(r["delta_mb"])

    for arch in ARCHITECTURES:
        d = arch_data.get(arch)
        if not d or not d["proxy_cost"]:
            continue
        n = len(d["proxy_cost"])
        avg_pc  = statistics.mean(d["proxy_cost"])
        avg_nv  = statistics.mean(d["net_value"])
        avg_dmb = statistics.mean(d["delta_mb"]) if d["delta_mb"] else float("nan")
        dmb_str = f"{avg_dmb:+.4f}" if d["delta_mb"] else "   -"
        print(f"{arch:<14} {n:>4} {avg_pc:>10.2f} {avg_nv:>10.4f} {dmb_str:>12}")

    print("\n=== Delta_MB detail - NetValue(arch) - NetValue(Single-slot) per case x persona ===")
    print(f"{'Arch':<14} {'Case':<10} {'Polite':>10} {'Adversarial':>12} {'VIP':>8}")
    print("-" * 58)

    by_ca: dict[tuple[str, str], dict[str, Optional[float]]] = {}
    for r in results:
        key = (r["agent_type"], r["case_id"])
        by_ca.setdefault(key, {})
        by_ca[key][r["persona_type"]] = r["delta_mb"]

    for arch in ["ReAct", "Reflection", "PlanExecute"]:
        for case_id in PHASE1_CASES:
            d = by_ca.get((arch, case_id), {})
            p   = f"{d['Polite']:+.4f}"      if d.get("Polite")      is not None else "  N/A"
            adv = f"{d['Adversarial']:+.4f}"  if d.get("Adversarial") is not None else "  N/A"
            v   = f"{d['VIP']:+.4f}"          if d.get("VIP")         is not None else "  N/A"
            print(f"{arch:<14} {case_id:<10} {p:>10} {adv:>12} {v:>8}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 7 cost & marginal benefit analysis")
    parser.add_argument("--logs-dir",     default="outputs/logs")
    parser.add_argument("--fact-sheets",  default="data/fact_sheets.json")
    parser.add_argument("--policy-gt",    default="data/policy_ground_truth.json")
    parser.add_argument("--output-dir",   default="outputs/reports")
    parser.add_argument(
        "--cases", nargs="*", default=PHASE1_CASES,
        help="Case IDs to include (default: Phase 1 selection)"
    )
    args = parser.parse_args()

    analyse(
        logs_dir=args.logs_dir,
        fact_sheets_path=args.fact_sheets,
        policy_gt_path=args.policy_gt,
        output_dir=args.output_dir,
        only_cases=args.cases,
    )
