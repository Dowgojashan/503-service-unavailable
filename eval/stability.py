"""
Phase 6: Stability validation and reliability analysis.

§6.1  Multi-run aggregation   — mean ± SD of S_Agent per (case × agent × persona)
§6.2  Judge reliability       — sample 60-75 range cases for human review; Spearman ρ
§6.4  I_fatal cap sensitivity — compare ranking stability under 4 cap settings

Usage:
  python -m eval.stability --aggregate
  python -m eval.stability --sensitivity  --results-csv outputs/reports/s_agent_results.csv
  python -m eval.stability --judge-check  --results-csv outputs/reports/s_agent_results.csv
  python -m eval.stability --spearman     --reviewed-csv outputs/reports/judge_checklist.csv
  python -m eval.stability --all
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Optional

from eval.metrics import (
    _get_agent_cost_value,
    evaluate_log,
    extract_tool_calls,
)

# ---------------------------------------------------------------------------
# Constants (evaluation_framework.md §6.3)
# ---------------------------------------------------------------------------

SD_STABLE     = 10.0   # SD ≤ 10  → stable
SD_BORDERLINE = 20.0   # 10 < SD ≤ 20 → borderline; SD > 20 → unstable

# I_fatal cap settings for §6.4 sensitivity analysis
CAP_SETTINGS: dict[str, int] = {
    "hard_zero": 0,
    "cap_30":   30,
    "cap_40":   40,   # current default
    "severity": 40,   # placeholder — same as cap_40 when no severity levels defined
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_run_id(stem: str) -> tuple[str, int]:
    """
    Extract base name and run_id from a log filename stem.

    'log_CASE_001_Single-slot_Polite'       → ('log_CASE_001_Single-slot_Polite', 1)
    'log_CASE_001_Single-slot_Polite_run2'  → ('log_CASE_001_Single-slot_Polite', 2)
    """
    m = re.search(r'_run(\d+)$', stem)
    if m:
        return stem[:m.start()], int(m.group(1))
    return stem, 1


def _load_support_files(fact_sheets_path: str | Path, policy_gt_path: str | Path):
    with open(fact_sheets_path, encoding="utf-8") as f:
        fact_sheets = json.load(f)
    with open(policy_gt_path, encoding="utf-8") as f:
        policy_gt = json.load(f)
    return fact_sheets, policy_gt


def _stability_label(sd: float) -> str:
    if sd <= SD_STABLE:
        return "stable"
    if sd <= SD_BORDERLINE:
        return "borderline"
    return "unstable"


def _apply_cap(s_raw: float, i_fatal: int, cap: int) -> float:
    return min(s_raw, cap) if i_fatal else s_raw


# ---------------------------------------------------------------------------
# §6.1  Multi-run stability aggregation
# ---------------------------------------------------------------------------

def aggregate_runs(
    logs_dir: str | Path,
    fact_sheets_path: str | Path,
    policy_gt_path: str | Path,
    output_csv: str | Path,
    only_cases: Optional[list[str]] = None,
    baseline_logs_dir: Optional[str | Path] = None,
) -> list[dict]:
    """
    Scan all log files under logs_dir (recursive), group by (case_id, agent_type, persona_type),
    evaluate each run, then compute mean ± SD for S_Agent and sub-metrics.

    Naming convention:
      log_CASE_001_Single-slot_Polite.json        → run 1 (baseline, no suffix)
      log_CASE_001_Single-slot_Polite_run2.json   → run 2
      log_CASE_001_Single-slot_Polite_run3.json   → run 3

    If baseline_logs_dir is provided, Single-slot efficiency baselines are sourced
    from that directory instead of logs_dir (needed when logs_dir contains no Single-slot logs).
    """
    logs_dir = Path(logs_dir)
    fact_sheets, policy_gt = _load_support_files(fact_sheets_path, policy_gt_path)

    log_files = sorted(logs_dir.rglob("log_*.json"))
    print(f"Found {len(log_files)} log file(s) under {logs_dir}")

    # Load all logs and parse run IDs
    entries: list[tuple[str, int, Path, dict]] = []
    for lf in log_files:
        base_stem, run_id = _parse_run_id(lf.stem)
        try:
            with open(lf, encoding="utf-8") as f:
                log = json.load(f)
            entries.append((base_stem, run_id, lf, log))
        except Exception as e:
            print(f"  SKIP {lf.name}: {e}")

    # Group by (case_id, agent_type, persona_type)
    groups: dict[tuple, list[tuple[int, Path, dict]]] = defaultdict(list)
    for base_stem, run_id, lf, log in entries:
        meta = log.get("metadata", {})
        key = (meta.get("case_id"), meta.get("agent_type"), meta.get("persona_type"))
        if None in key:
            continue
        if only_cases and key[0] not in only_cases:
            continue
        groups[key].append((run_id, lf, log))

    # Global normalisation maxima for ProxyCost
    all_tokens    = [log.get("usage_summary", {}).get("grand_total_tokens", 0) or 0
                     for _, _, _, log in entries]
    all_turns     = [len(log.get("conversation", [])) for _, _, _, log in entries]
    all_tools     = [len(extract_tool_calls(log)) for _, _, _, log in entries]
    max_tokens    = max(all_tokens, default=1) or 1
    max_llm_calls = max(all_turns, default=1) or 1
    max_tool_calls = max(all_tools, default=1) or 1

    # Load baseline source logs (may be a different directory for non-Single-slot evaluations)
    if baseline_logs_dir is not None:
        baseline_path = Path(baseline_logs_dir)
        baseline_entries: list[tuple[str, int, Path, dict]] = []
        for lf in sorted(baseline_path.rglob("log_*.json")):
            _, run_id = _parse_run_id(lf.stem)
            try:
                with open(lf, encoding="utf-8") as f:
                    log = json.load(f)
                baseline_entries.append(("", run_id, lf, log))
            except Exception:
                pass
    else:
        baseline_entries = entries

    # Single-slot baselines by difficulty — separated by unit to avoid mixing seconds and tokens.
    ss_seconds_by_diff: dict[str, list[float]] = {}
    ss_tokens_by_diff:  dict[str, list[float]] = {}
    for _, _, _, log in baseline_entries:
        if log.get("metadata", {}).get("agent_type") != "Single-slot":
            continue
        cid  = log.get("metadata", {}).get("case_id", "")
        fs   = fact_sheets.get(cid, {})
        diff = fs.get("metadata", {}).get("difficulty_label", "medium")
        secs = log.get("metadata", {}).get("execution_seconds")
        if secs and secs > 0:
            ss_seconds_by_diff.setdefault(diff, []).append(float(secs))
        else:
            tokens = log.get("usage_summary", {}).get("grand_total_tokens", 1) or 1
            ss_tokens_by_diff.setdefault(diff, []).append(float(tokens))

    baseline_seconds_map = {d: statistics.median(v) for d, v in ss_seconds_by_diff.items() if v}
    baseline_tokens_map  = {d: statistics.median(v) for d, v in ss_tokens_by_diff.items()  if v}

    # Evaluate and aggregate
    results: list[dict] = []
    for key, runs in sorted(groups.items()):
        case_id, agent_type, persona_type = key
        fs = fact_sheets.get(case_id, {})
        if not fs:
            continue
        diff = fs.get("metadata", {}).get("difficulty_label", "medium")

        run_metrics: list[dict] = []
        for run_id, lf, log in sorted(runs, key=lambda x: x[0]):
            try:
                # Choose matching-unit baseline for this specific log
                _secs = log.get("metadata", {}).get("execution_seconds")
                if _secs and _secs > 0:
                    baseline = baseline_seconds_map.get(diff, 1.0)
                else:
                    baseline = baseline_tokens_map.get(diff, float(max_tokens))
                m = evaluate_log(
                    log, fs, policy_gt,
                    baseline, max_tokens, max_llm_calls, max_tool_calls,
                )
                m["_run_id"]   = run_id
                m["_log_path"] = str(lf)
                run_metrics.append(m)
            except Exception as e:
                print(f"  ERROR {lf.name} run {run_id}: {e}")

        if not run_metrics:
            continue

        def _mean(field: str) -> Optional[float]:
            vals = [r[field] for r in run_metrics if r.get(field) is not None]
            return round(statistics.mean(vals), 2) if vals else None

        def _sd(field: str) -> float:
            vals = [r[field] for r in run_metrics if r.get(field) is not None]
            return round(statistics.stdev(vals), 2) if len(vals) >= 2 else 0.0

        n          = len(run_metrics)
        mean_sa    = _mean("s_agent")
        sd_sa      = _sd("s_agent")
        i_fatal_ct = sum(r["i_fatal"] for r in run_metrics)

        row = {
            "case_id":      case_id,
            "agent_type":   agent_type,
            "persona_type": persona_type,
            "difficulty":   run_metrics[0].get("difficulty"),
            "v_i":          run_metrics[0].get("v_i"),
            "n_runs":       n,
            # S_Agent
            "mean_s_agent":    mean_sa,
            "sd_s_agent":      sd_sa,
            "min_s_agent":     min(r["s_agent"] for r in run_metrics),
            "max_s_agent":     max(r["s_agent"] for r in run_metrics),
            "stability_label": _stability_label(sd_sa),
            # Sub-metrics
            "mean_s_outcome":    _mean("s_outcome"),    "sd_s_outcome":    _sd("s_outcome"),
            "mean_s_tool":       _mean("s_tool"),       "sd_s_tool":       _sd("s_tool"),
            "mean_s_trajectory": _mean("s_trajectory"), "sd_s_trajectory": _sd("s_trajectory"),
            "mean_s_efficiency": _mean("s_efficiency"), "sd_s_efficiency": _sd("s_efficiency"),
            # I_fatal
            "i_fatal_count": i_fatal_ct,
            "i_fatal_rate":  round(i_fatal_ct / n, 3),
            # Economic
            "mean_net_value":  _mean("net_value"),  "sd_net_value":  _sd("net_value"),
            "mean_proxy_cost": _mean("proxy_cost"),
            # Run info
            "run_ids": ",".join(str(r["_run_id"]) for r in run_metrics),
        }

        sym = "OK" if sd_sa <= SD_STABLE else ("~" if sd_sa <= SD_BORDERLINE else "!!")
        print(
            f"  {case_id:10s} | {agent_type:12s} | {persona_type:12s} "
            f"| n={n} | S_Agent={mean_sa:6.1f} +/- {sd_sa:4.1f} [{sym}]"
        )
        results.append(row)

    _save_stability_csv(results, output_csv)
    print(f"\nSaved {len(results)} rows → {output_csv}")
    return results


def _save_stability_csv(results: list[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id", "agent_type", "persona_type", "difficulty", "v_i", "n_runs",
        "mean_s_agent", "sd_s_agent", "min_s_agent", "max_s_agent", "stability_label",
        "mean_s_outcome",    "sd_s_outcome",
        "mean_s_tool",       "sd_s_tool",
        "mean_s_trajectory", "sd_s_trajectory",
        "mean_s_efficiency", "sd_s_efficiency",
        "i_fatal_count", "i_fatal_rate",
        "mean_net_value", "sd_net_value", "mean_proxy_cost",
        "run_ids",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


# ---------------------------------------------------------------------------
# §6.4  I_fatal cap sensitivity analysis
# ---------------------------------------------------------------------------

def run_sensitivity(
    results_csv: str | Path,
    output_csv: str | Path,
    caps: Optional[dict[str, int]] = None,
) -> list[dict]:
    """
    For each row in results_csv, recompute S_Agent under multiple I_fatal cap settings
    and compare per-architecture ranking stability.

    Cap settings (evaluation_framework.md §6.4):
      hard_zero : S_Agent = 0 if I_fatal triggered
      cap_30    : S_Agent = min(S_raw, 30) if I_fatal triggered
      cap_40    : S_Agent = min(S_raw, 40) — current default
      severity  : reserved for severity-graded penalties (maps to cap_40 when not further defined)
    """
    if caps is None:
        caps = CAP_SETTINGS

    with open(results_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No data in results CSV.")
        return []

    output_rows: list[dict] = []
    for row in rows:
        try:
            s_raw   = float(row.get("s_raw") or 0)
            i_fatal = int(float(row.get("i_fatal") or 0))
        except ValueError:
            continue

        out: dict = {
            "case_id":      row.get("case_id"),
            "agent_type":   row.get("agent_type"),
            "persona_type": row.get("persona_type"),
            "difficulty":   row.get("difficulty"),
            "s_raw":        round(s_raw, 2),
            "i_fatal":      i_fatal,
        }
        for cap_name, cap_val in caps.items():
            out[f"s_agent_{cap_name}"] = round(_apply_cap(s_raw, i_fatal, cap_val), 2)
        output_rows.append(out)

    # Per-architecture mean under each cap
    arch_means: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in output_rows:
        for cap_name in caps:
            arch_means[r["agent_type"]][cap_name].append(r[f"s_agent_{cap_name}"])

    print("\nPer-architecture mean S_Agent under each I_fatal cap setting:")
    col_w = 13
    header = f"  {'Architecture':14s}" + "".join(f"  {n:>{col_w}s}" for n in caps)
    print(header)
    print("  " + "-" * (14 + (col_w + 2) * len(caps)))
    for arch in sorted(arch_means):
        line = f"  {arch:14s}"
        for cap_name in caps:
            vals = arch_means[arch][cap_name]
            mean = statistics.mean(vals) if vals else 0.0
            line += f"  {mean:>{col_w}.1f}"
        print(line)

    # Ranking per cap setting
    print("\n  Ranking (1=best) per cap setting:")
    rankings: dict[str, list[str]] = {}
    for cap_name in caps:
        arch_score = {
            arch: statistics.mean(arch_means[arch][cap_name])
            for arch in arch_means
        }
        ranked = sorted(arch_score, key=lambda a: arch_score[a], reverse=True)
        rankings[cap_name] = ranked
        print(f"    {cap_name:12s}: {' > '.join(ranked)}")

    # Ranking consistency check
    ref = rankings[list(caps.keys())[0]]
    consistent = all(rankings[n] == ref for n in caps)
    print(f"\n  Ranking consistent across all cap settings: {'YES' if consistent else 'NO -- inspect differences'}")

    # Save
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        ["case_id", "agent_type", "persona_type", "difficulty", "s_raw", "i_fatal"]
        + [f"s_agent_{n}" for n in caps]
    )
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"\n  Saved {len(output_rows)} rows → {output_csv}")
    return output_rows


# ---------------------------------------------------------------------------
# §6.2  Judge reliability checklist
# ---------------------------------------------------------------------------

def generate_judge_checklist(
    results_csv: str | Path,
    logs_dir: str | Path,
    output_csv: str | Path,
    score_range: tuple[float, float] = (60.0, 75.0),
    sample_rate: float = 1.0,
) -> list[dict]:
    """
    Identify cases whose S_Agent falls in the gray zone [score_range] and
    sample `sample_rate` of them for human annotation.

    Deduplicates by (case_id, agent_type, persona_type): keeps the entry
    closest to the midpoint of score_range per unique combination (avoids
    reviewing run2/run3 duplicates of the same case).

    Output CSV contains conversation excerpts for annotators to fill in
    human_score_0_100 and human_notes columns.
    """
    logs_dir = Path(logs_dir)

    with open(results_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    lo, hi = score_range
    midpoint = (lo + hi) / 2

    gray_zone_raw = []
    for r in rows:
        try:
            sa = float(r.get("s_agent") or 0)
            if lo <= sa <= hi:
                gray_zone_raw.append(r)
        except ValueError:
            pass

    # Deduplicate: keep one entry per (case_id, agent_type, persona_type)
    # — the one closest to the gray-zone midpoint
    seen: dict[tuple, dict] = {}
    for r in gray_zone_raw:
        key = (r.get("case_id"), r.get("agent_type"), r.get("persona_type"))
        sa = float(r.get("s_agent") or 0)
        if key not in seen or abs(sa - midpoint) < abs(float(seen[key].get("s_agent", 0)) - midpoint):
            seen[key] = r
    gray_zone = sorted(seen.values(), key=lambda r: abs(float(r.get("s_agent", 0)) - midpoint))

    n_sample = max(1, round(len(gray_zone) * sample_rate))
    sampled = gray_zone[:n_sample]

    print(f"\n  Cases in {lo}–{hi} S_Agent range: {len(gray_zone_raw)} rows → {len(gray_zone)} unique (case x arch x persona)")
    print(f"  Sampled {len(sampled)} for human review (rate={sample_rate:.0%})")

    checklist: list[dict] = []
    for r in sampled:
        cid     = r.get("case_id", "")
        agent   = r.get("agent_type", "")
        persona = r.get("persona_type", "")
        sa      = r.get("s_agent", "")

        # Locate corresponding log file
        pattern = f"log_{cid}_{agent}_{persona}.json"
        matches = list(logs_dir.rglob(pattern))
        log_path = str(matches[0]) if matches else "NOT_FOUND"

        last_answer = ""
        if matches:
            try:
                with open(matches[0], encoding="utf-8") as f:
                    log = json.load(f)
                convs = log.get("conversation", [])
                if convs:
                    last_answer = convs[-1].get("service_agent", {}).get("final_answer", "")[:600]
            except Exception:
                pass

        row_out = {
            "case_id":      cid,
            "agent_type":   agent,
            "persona_type": persona,
            "s_agent":      sa,
            "s_answer_quality":   r.get("s_answer_quality"),
            "s_grounding":        r.get("s_grounding"),
            "judge_s_resolution": r.get("judge_s_resolution"),
            "judge_s_completeness": r.get("judge_s_completeness"),
            "judge_s_tone":       r.get("judge_s_tone"),
            "log_path":           log_path,
            "last_agent_answer_excerpt": last_answer,
            "human_score_0_100": "",   # annotator fills this in
            "human_notes":       "",   # annotator fills this in
        }
        print(f"    {cid:10s} | {agent:12s} | {persona:12s} | S_Agent={sa}")
        checklist.append(row_out)

    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id", "agent_type", "persona_type", "s_agent",
        "s_answer_quality", "s_grounding",
        "judge_s_resolution", "judge_s_completeness", "judge_s_tone",
        "log_path", "last_agent_answer_excerpt",
        "human_score_0_100", "human_notes",
    ]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(checklist)
    print(f"  Saved {len(checklist)} rows → {output_csv}")
    return checklist


# ---------------------------------------------------------------------------
# §6.2  Spearman ρ (after human annotation)
# ---------------------------------------------------------------------------

def _rank_with_ties(values: list[float]) -> list[float]:
    """Assign average rank to tied values (1-indexed)."""
    n = len(values)
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and values[indexed[j]] == values[indexed[j + 1]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg_rank
        i = j + 1
    return ranks


def compute_spearman(
    reviewed_csv: str | Path,
    human_col: str = "human_score_0_100",
    judge_col: str = "s_agent",
) -> float:
    """
    Compute Spearman rank correlation between automated judge scores and human scores
    from a completed review checklist.

    Target: ρ ≥ 0.75 to validate LLM judge reliability (evaluation_framework.md §6.2).
    """
    pairs: list[tuple[float, float]] = []
    with open(reviewed_csv, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                h = float(r[human_col])
                j = float(r[judge_col])
                pairs.append((h, j))
            except (ValueError, KeyError):
                pass

    if len(pairs) < 2:
        print("  Not enough annotated rows to compute Spearman ρ (need ≥ 2).")
        return float("nan")

    humans = [p[0] for p in pairs]
    judges = [p[1] for p in pairs]
    rh = _rank_with_ties(humans)
    rj = _rank_with_ties(judges)
    n  = len(pairs)

    mean_rh = statistics.mean(rh)
    mean_rj = statistics.mean(rj)
    num = sum((rh[i] - mean_rh) * (rj[i] - mean_rj) for i in range(n))
    den = (
        sum((rh[i] - mean_rh) ** 2 for i in range(n)) *
        sum((rj[i] - mean_rj) ** 2 for i in range(n))
    ) ** 0.5
    rho = round(num / den, 4) if den else 0.0

    target_met = rho >= 0.75
    verdict = "PASS" if target_met else "FAIL -- increase sample or review rubric"
    print(f"\n  Spearman rho = {rho:.3f}  (n={n}, target >= 0.75)  [{verdict}]")
    return rho


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_PHASE1_CASES = ["CASE_001", "CASE_002", "CASE_015", "CASE_075", "CASE_090", "CASE_141"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 6: Stability validation, judge reliability, cap sensitivity"
    )
    parser.add_argument("--aggregate",   action="store_true",
                        help="§6.1 Aggregate multi-run logs → stability_report.csv")
    parser.add_argument("--sensitivity", action="store_true",
                        help="§6.4 I_fatal cap sensitivity → sensitivity_report.csv")
    parser.add_argument("--judge-check", action="store_true",
                        help="§6.2 Generate judge checklist → judge_checklist.csv")
    parser.add_argument("--spearman",    action="store_true",
                        help="§6.2 Compute Spearman ρ from completed checklist")
    parser.add_argument("--all",         action="store_true",
                        help="Run aggregate + sensitivity + judge-check")

    parser.add_argument("--logs-dir",          default="outputs/logs")
    parser.add_argument("--baseline-logs-dir", default=None,
                        help="Directory with Single-slot baseline logs (use when logs-dir has none)")
    parser.add_argument("--results-csv",  default="outputs/reports/s_agent_results.csv",
                        help="Existing per-run results CSV (for sensitivity / judge-check)")
    parser.add_argument("--reviewed-csv", default="outputs/reports/judge_checklist.csv",
                        help="Completed checklist CSV with human_score_0_100 filled in")
    parser.add_argument("--output-dir",   default="outputs/reports")
    parser.add_argument("--fact-sheets",  default="data/fact_sheets.json")
    parser.add_argument("--policy-gt",    default="data/policy_ground_truth.json")
    parser.add_argument("--cases", nargs="*", default=_PHASE1_CASES)
    parser.add_argument(
        "--sample-rate", type=float, default=1.0,
        help="Fraction of gray-zone cases to sample for judge checklist (default: 1.0 = all)"
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if args.aggregate or args.all:
        print("=== §6.1 Multi-run Stability Aggregation ===")
        aggregate_runs(
            logs_dir=args.logs_dir,
            fact_sheets_path=args.fact_sheets,
            policy_gt_path=args.policy_gt,
            output_csv=output_dir / "stability_report.csv",
            only_cases=args.cases,
            baseline_logs_dir=args.baseline_logs_dir,
        )

    if args.sensitivity or args.all:
        print("\n=== §6.4 I_fatal Cap Sensitivity Analysis ===")
        run_sensitivity(
            results_csv=args.results_csv,
            output_csv=output_dir / "sensitivity_report.csv",
        )

    if args.judge_check or args.all:
        print("\n=== §6.2 Judge Reliability Checklist ===")
        generate_judge_checklist(
            results_csv=args.results_csv,
            logs_dir=args.logs_dir,
            output_csv=output_dir / "judge_checklist.csv",
            sample_rate=args.sample_rate,
        )

    if args.spearman:
        print("\n=== §6.2 Spearman ρ Computation ===")
        compute_spearman(reviewed_csv=args.reviewed_csv)

    if not any([args.aggregate, args.sensitivity, args.judge_check, args.spearman, args.all]):
        parser.print_help()
