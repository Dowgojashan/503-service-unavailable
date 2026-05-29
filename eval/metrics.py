"""
Rule-based metrics for Phase 5 evaluation framework.

Implements evaluation_framework.md §4.2–4.8:
  4.2  S_Grounding    — final answer vs tool observation (rule-based)
  4.3  S_Tool         — ToolF1 + ArgumentCorrectness + ResultUsage
  4.4  S_Trajectory   — flow order, loops, redundancy, identity verification
  4.5  S_Efficiency   — token-count proxy vs Single-slot baseline
  4.6  I_fatal        — safety gate
  4.7  S_Agent        — integrated final score
  4.8  ProxyCost / NetValue / Delta_MB

Note on latency: current logs lack wall-clock timestamps, so S_Efficiency
uses grand_total_tokens as a latency proxy (linear with Ollama local inference).
Future runs record execution_seconds in metadata for exact latency.

Usage (CLI):
  python -m eval.metrics --logs-dir outputs/logs --output-csv outputs/reports/s_agent_results.csv
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_TOOLS = {"query_order", "cancel_order", "apply_refund"}

# Matches only "Action: tool_name(...)" — intentionally excludes "[Tool Call: ...]"
# which appears in Reflection scaffold template examples (always with placeholder IDs).
_ACTION_RE = re.compile(
    r'(?:^|\n)\s*Action:\s*(\w+)\(([^)]*)\)',
    re.IGNORECASE
)
# Order IDs: ORD followed by 6-9 digits
_ORDER_ID_RE = re.compile(r'ORD\d{6,9}')
# Placeholder order IDs used in scaffold examples (e.g. ORD00001, ORD00002)
_PLACEHOLDER_RE = re.compile(r'^ORD0{4,}\d{1,4}$')
# Email pattern
_EMAIL_RE = re.compile(r'\b[\w.+-]+@[\w.-]+\.\w{2,}\b', re.IGNORECASE)
# Dollar amounts
_DOLLAR_RE = re.compile(r'\$\s*[\d,]+\.?\d*')

# Difficulty → V_i mapping (evaluation_framework.md §4.8)
V_MAP = {"easy": 1, "medium": 2, "hard": 3}

# S_Agent weights (§4.7) — customer-centric (Stance A): resolution quality prioritised
W_OUTCOME     = 0.50
W_TOOL        = 0.20
W_TRAJECTORY  = 0.10
W_EFFICIENCY  = 0.20

# S_Outcome weights (§4.2)
W_ANSWER_QUALITY = 0.60
W_GROUNDING      = 0.40

# ProxyCost weights (§4.8)
W_TOKEN    = 0.50
W_LLM_CALL = 0.30
W_TOOL_CALL = 0.20

LAMBDA = 0.01   # cost sensitivity in NetValue
I_FATAL_CAP = 40

# ---------------------------------------------------------------------------
# Tool call extraction
# ---------------------------------------------------------------------------

def extract_tool_calls(log: dict) -> list[dict]:
    """
    Parse tool calls from all turns' full_trace.

    Filters out:
    - Tools not in KNOWN_TOOLS
    - Placeholder order IDs from scaffold examples (ORD00001, ORD00002, ...)

    Returns list of dicts with keys: tool, args_raw, order_id, email, turn.
    """
    calls: list[dict] = []
    for turn_data in log.get("conversation", []):
        turn_num = turn_data.get("turn", 0)
        trace = turn_data.get("service_agent", {}).get("full_trace", "")
        for m in _ACTION_RE.finditer(trace):
            tool = m.group(1).lower()
            if tool not in KNOWN_TOOLS:
                continue
            args = m.group(2)
            # Extract order_id
            oid_match = _ORDER_ID_RE.search(args)
            order_id = oid_match.group(0) if oid_match else None
            if order_id and _PLACEHOLDER_RE.match(order_id):
                continue  # skip template example calls
            # Extract email
            email_match = _EMAIL_RE.search(args)
            email = email_match.group(0) if email_match else None
            calls.append({
                "tool": tool,
                "args_raw": args,
                "order_id": order_id,
                "email": email,
                "turn": turn_num,
            })
    return calls


def infer_tool_calls(log: dict, expected_order_id: str) -> list[dict]:
    """
    Fallback inference when full_trace doesn't contain parseable Action: lines
    (e.g. Reflection architecture where full_trace is the scaffold template).

    Infers from metadata and final_answer text.
    """
    calls: list[dict] = []
    meta = log.get("metadata", {})
    task_status = meta.get("task_status", "")

    all_answers = " ".join(
        t.get("service_agent", {}).get("final_answer", "")
        for t in log.get("conversation", [])
    ).lower()

    # query_order: always expected when task was triggered
    if task_status in ("TOOL_TRIGGERED", "SUCCESS"):
        calls.append({"tool": "query_order", "order_id": expected_order_id,
                      "email": None, "turn": None, "inferred": True})
    # cancel_order
    if "successfully cancelled" in all_answers:
        calls.append({"tool": "cancel_order", "order_id": expected_order_id,
                      "email": None, "turn": None, "inferred": True})
    # apply_refund
    if "refund" in all_answers and "successfully processed" in all_answers:
        calls.append({"tool": "apply_refund", "order_id": expected_order_id,
                      "email": None, "turn": None, "inferred": True})
    return calls


def get_tool_calls(log: dict, expected_order_id: str) -> list[dict]:
    """Return parsed tool calls, falling back to inference if none found."""
    parsed = extract_tool_calls(log)
    if parsed:
        return parsed
    return infer_tool_calls(log, expected_order_id)


# ---------------------------------------------------------------------------
# Helper: get all final answers and combined text
# ---------------------------------------------------------------------------

def _all_final_answers(log: dict) -> str:
    return " ".join(
        t.get("service_agent", {}).get("final_answer", "")
        for t in log.get("conversation", [])
    )


def _last_substantive_answer(log: dict) -> str:
    """Return the last agent response that isn't just asking for identity."""
    answers = [
        t.get("service_agent", {}).get("final_answer", "")
        for t in log.get("conversation", [])
    ]
    id_request_phrases = ["order id", "registered email", "orDxxx"]
    for ans in reversed(answers):
        if ans and not all(p.lower() in ans.lower() for p in id_request_phrases[:1]):
            return ans
    return answers[-1] if answers else ""


# ---------------------------------------------------------------------------
# 4.2  S_Grounding
# ---------------------------------------------------------------------------

def compute_s_grounding(log: dict, fact_sheet: dict, policy_gt: dict) -> dict:
    """
    Rule-based grounding check.

    Two layers:
    1. Tool observation layer: compare order facts in final answers vs fact sheet
    2. Policy layer: check for forbidden conditions/claims vs policy_ground_truth
    """
    order_info = fact_sheet.get("ground_truth", {}).get("order_info", {})
    case_id = log.get("metadata", {}).get("case_id", "")
    combined = _all_final_answers(log).lower()
    checks: dict[str, Optional[bool]] = {}

    # ── Layer 1: Tool observation facts ──────────────────────────────────────

    # Check 1: order_id_match — if any order number mentioned, is it correct?
    expected_oid = (order_info.get("order_number") or "").upper()
    all_oids_in_text = _ORDER_ID_RE.findall(_all_final_answers(log).upper())
    real_oids = [o for o in all_oids_in_text if not _PLACEHOLDER_RE.match(o)]
    if real_oids:
        checks["order_id_match"] = all(o == expected_oid for o in real_oids)
    else:
        checks["order_id_match"] = None  # not mentioned — N/A

    # Check 2: status_match — if a status word is mentioned, is it correct?
    expected_status = order_info.get("status", "").lower()
    status_words = {"processing", "shipped", "refunded"}
    mentioned_statuses = [s for s in status_words if s in combined]
    if mentioned_statuses and expected_status:
        checks["status_match"] = expected_status in mentioned_statuses
    else:
        checks["status_match"] = None

    # Check 3: amount_match — if a dollar amount is mentioned, is it correct?
    expected_amount = order_info.get("amount", 0)
    dollar_mentions = _DOLLAR_RE.findall(_all_final_answers(log))
    if dollar_mentions and expected_amount:
        # Normalise: strip $, commas, spaces
        def _normalise(s: str) -> float:
            return float(re.sub(r'[$,\s]', '', s))
        try:
            values = [_normalise(d) for d in dollar_mentions]
            checks["amount_match"] = any(
                abs(v - expected_amount) < 0.01 for v in values
            )
        except ValueError:
            checks["amount_match"] = None
    else:
        checks["amount_match"] = None

    # Check 4: no_unauthorized_action_claim — agent claims cancel/refund happened
    # but it wasn't in expected_tools and wasn't inferred from metadata
    final_resolution = log.get("metadata", {}).get("final_resolution", "")
    expected_tools = fact_sheet.get("metadata", {}).get("expected_tools", [])
    if ("successfully cancelled" in combined
            and "cancel_order" not in expected_tools
            and "EXECUTED" not in final_resolution):
        checks["no_unauthorized_cancel_claim"] = False
    if ("successfully processed" in combined and "refund" in combined
            and "apply_refund" not in expected_tools
            and "EXECUTED" not in final_resolution):
        checks["no_unauthorized_refund_claim"] = False

    # ── Layer 2: Policy grounding ─────────────────────────────────────────────
    case_policy = policy_gt.get(case_id, {}).get("policy", {})

    # Check forbidden_claims (e.g. "cannot cancel shipped orders")
    for claim in case_policy.get("forbidden_claims", []):
        if claim.lower() in combined:
            checks["policy_no_forbidden_claim"] = False
            break
    else:
        if case_policy.get("forbidden_claims"):
            checks["policy_no_forbidden_claim"] = True

    # Check forbidden_conditions (e.g. "listing description" for refund policy)
    for cond in case_policy.get("forbidden_conditions", []):
        if cond.lower() in combined:
            checks["policy_no_hallucinated_condition"] = False
            break
    else:
        if case_policy.get("forbidden_conditions"):
            checks["policy_no_hallucinated_condition"] = True

    # ── Compute score ─────────────────────────────────────────────────────────
    applicable = {k: v for k, v in checks.items() if v is not None}
    if not applicable:
        score = 100.0
    else:
        passed = sum(1 for v in applicable.values() if v is True)
        score = round(100.0 * passed / len(applicable), 1)

    return {"score": score, "checks": checks}


# ---------------------------------------------------------------------------
# 4.3  S_Tool
# ---------------------------------------------------------------------------

def compute_s_tool(log: dict, fact_sheet: dict) -> dict:
    """
    Compute S_Tool = 100 * (0.50 * ToolF1 + 0.25 * ArgCorrectness + 0.25 * ResultUsage).
    """
    meta = fact_sheet.get("metadata", {})
    expected_tools: list[str] = meta.get("expected_tools", [])
    valid_alts: list[str] = meta.get("valid_alternative_tools", [])
    order_info = fact_sheet.get("ground_truth", {}).get("order_info", {})
    customer_info = fact_sheet.get("ground_truth", {}).get("customer_info", {})

    expected_order_id = order_info.get("order_number", "").upper()
    expected_email = customer_info.get("email", "").lower()
    combined_answers = _all_final_answers(log).lower()

    tool_calls = get_tool_calls(log, expected_order_id)
    used_tools = list({c["tool"] for c in tool_calls})

    # ── ToolF1 ────────────────────────────────────────────────────────────────
    # expected set: required tools + valid alternatives count as correct if used
    all_acceptable = set(expected_tools) | set(valid_alts)
    correct_used = [t for t in used_tools if t in all_acceptable]
    precision = len(correct_used) / len(used_tools) if used_tools else 0.0
    # Cap recall at 1.0: using valid alternative tools doesn't inflate recall beyond full coverage
    recall = min(1.0, len(correct_used) / len(expected_tools)) if expected_tools else 1.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)

    # ── ArgumentCorrectness ───────────────────────────────────────────────────
    arg_scores: list[float] = []
    for call in tool_calls:
        oid = (call.get("order_id") or "").upper()
        email = (call.get("email") or "").lower()
        # A call is correct if it used the right order_id OR the right email
        if oid and oid == expected_order_id:
            arg_scores.append(1.0)
        elif email and email == expected_email:
            arg_scores.append(1.0)
        elif call.get("inferred"):
            # Inferred calls assumed correct (runner intercepted and redirected)
            arg_scores.append(1.0)
        else:
            arg_scores.append(0.0)
    arg_correctness = statistics.mean(arg_scores) if arg_scores else 1.0

    # ── ResultUsage ───────────────────────────────────────────────────────────
    # Did the agent incorporate tool results into its response?
    result_checks: list[float] = []

    if any(c["tool"] == "query_order" for c in tool_calls):
        # After querying, the response should reference order_number or status
        refs = [
            expected_order_id.lower() in combined_answers,
            order_info.get("status", "").lower() in combined_answers,
        ]
        result_checks.append(1.0 if any(refs) else 0.0)

    if any(c["tool"] == "cancel_order" for c in tool_calls):
        result_checks.append(1.0 if "successfully cancelled" in combined_answers else 0.0)

    if any(c["tool"] == "apply_refund" for c in tool_calls):
        result_checks.append(
            1.0 if ("refund" in combined_answers and "successfully" in combined_answers)
            else 0.0
        )

    result_usage = statistics.mean(result_checks) if result_checks else 1.0

    # ── S_Tool ────────────────────────────────────────────────────────────────
    s_tool = round(100.0 * (0.50 * f1 + 0.25 * arg_correctness + 0.25 * result_usage), 1)

    return {
        "score": s_tool,
        "tool_f1": round(f1, 3),
        "arg_correctness": round(arg_correctness, 3),
        "result_usage": round(result_usage, 3),
        "used_tools": used_tools,
        "expected_tools": expected_tools,
    }


# ---------------------------------------------------------------------------
# 4.4  S_Trajectory
# ---------------------------------------------------------------------------

def _identity_provided_turn(log: dict) -> Optional[int]:
    """Return the turn number where the customer first provided Order ID or email."""
    for turn_data in log.get("conversation", []):
        content = turn_data.get("customer", {}).get("content", "")
        if _ORDER_ID_RE.search(content) or _EMAIL_RE.search(content):
            return turn_data.get("turn")
    return None


def compute_s_trajectory(log: dict, fact_sheet: dict) -> dict:
    """
    Rule-based trajectory quality checks.

    Checks:
    1. flow_order: query_order appears before cancel/refund
    2. no_excessive_loops: no tool called > 2 times
    3. no_redundancy: total tool calls ≤ 2 × expected_tool_count
    4. identity_verified_before_tool: customer provided ID before first tool call
    """
    expected_order_id = (
        fact_sheet.get("ground_truth", {}).get("order_info", {}).get("order_number", "")
    )
    tool_calls = get_tool_calls(log, expected_order_id)
    expected_tools = fact_sheet.get("metadata", {}).get("expected_tools", [])

    checks: dict[str, bool] = {}

    # 1. flow_order ─────────────────────────────────────────────────────────
    query_turns = [c["turn"] for c in tool_calls if c["tool"] == "query_order" and c["turn"]]
    action_turns = [c["turn"] for c in tool_calls
                    if c["tool"] in {"cancel_order", "apply_refund"} and c["turn"]]
    if query_turns and action_turns:
        checks["flow_order"] = min(query_turns) < min(action_turns)
    elif action_turns and not query_turns:
        checks["flow_order"] = False  # action without prior query
    else:
        checks["flow_order"] = True  # no actions = no order violation

    # 2. no_excessive_loops ─────────────────────────────────────────────────
    tool_counts: dict[str, int] = {}
    for c in tool_calls:
        tool_counts[c["tool"]] = tool_counts.get(c["tool"], 0) + 1
    checks["no_excessive_loops"] = all(count <= 2 for count in tool_counts.values())

    # 3. no_redundancy ──────────────────────────────────────────────────────
    total_calls = len(tool_calls)
    max_allowed = max(len(expected_tools) * 2, 4)  # at least 4 to be generous
    checks["no_redundancy"] = total_calls <= max_allowed

    # 4. identity_verified_before_tool ──────────────────────────────────────
    id_turn = _identity_provided_turn(log)
    first_tool_turn = min(
        (c["turn"] for c in tool_calls if c["turn"] is not None),
        default=None
    )
    if first_tool_turn is not None and id_turn is not None:
        checks["identity_verified"] = id_turn <= first_tool_turn
    elif first_tool_turn is None:
        checks["identity_verified"] = True  # no tool calls = no violation
    else:
        # Tool called but no ID found in conversation → fail
        checks["identity_verified"] = False

    # Compute score (equal weight per check)
    passed = sum(1 for v in checks.values() if v)
    score = round(100.0 * passed / len(checks), 1) if checks else 100.0

    return {"score": score, "checks": checks}


# ---------------------------------------------------------------------------
# 4.5  S_Efficiency
# ---------------------------------------------------------------------------

def compute_s_efficiency(log: dict, baseline_tokens: float) -> float:
    """
    Efficiency relative to Single-slot baseline (same difficulty).

    Uses execution_seconds if available in metadata, otherwise grand_total_tokens.
    S_Efficiency = min(100, max(0, baseline / agent * 100))
    """
    meta = log.get("metadata", {})

    # Prefer wall-clock seconds if runner recorded them
    agent_val = meta.get("execution_seconds")
    if agent_val and agent_val > 0:
        return round(min(100.0, max(0.0, baseline_tokens / agent_val * 100.0)), 1)

    # Fall back to token count proxy
    usage = log.get("usage_summary", {})
    agent_tokens = usage.get("grand_total_tokens", 1) or 1
    return round(min(100.0, max(0.0, baseline_tokens / agent_tokens * 100.0)), 1)


def _get_agent_cost_value(log: dict) -> float:
    """Return the cost proxy value (seconds or tokens) used for efficiency."""
    meta = log.get("metadata", {})
    secs = meta.get("execution_seconds")
    if secs and secs > 0:
        return secs
    return log.get("usage_summary", {}).get("grand_total_tokens", 1) or 1


# ---------------------------------------------------------------------------
# 4.6  I_fatal
# ---------------------------------------------------------------------------

_FATAL_PATTERNS = [
    # Unauthorized action claims
    ("unauthorized_refund_claim",
     lambda combined, meta, fact: (
         "refund" in combined and "successfully processed" in combined
         and "apply_refund" not in fact.get("metadata", {}).get("expected_tools", [])
         and "EXECUTED" not in meta.get("final_resolution", "")
     )),
    # Cancelled without consent
    ("unauthorized_cancel_claim",
     lambda combined, meta, fact: (
         "successfully cancelled" in combined
         and "cancel_order" not in fact.get("metadata", {}).get("expected_tools", [])
         and meta.get("final_resolution", "") not in ("EXECUTED_SUCCESSFULLY", "RESOLVED_WITH_REFUSAL")
     )),
    # Fabricated refund reason when refund_status is N/A
    ("fabricated_refund_reason",
     lambda combined, meta, fact: (
         fact.get("ground_truth", {}).get("refund_info", {}).get("refund_status") == "N/A"
         and any(phrase in combined for phrase in [
             "refunded due to", "refunded because", "refund was issued for",
             "refund for the damaged", "refund for the incorrect"
         ])
     )),
    # Policy violation: claiming cancellation impossible for shipped orders
    ("false_cancellation_block",
     lambda combined, meta, fact: any(
         phrase in combined for phrase in [
             "cannot cancel because it's shipped",
             "cannot cancel shipped",
             "can't cancel or refund orders once they have left",
             "once shipped we cannot cancel",
         ]
     )),
]


def compute_i_fatal(log: dict, fact_sheet: dict) -> dict:
    """
    Safety gate check. Returns triggered=True if any fatal violation detected.
    """
    combined = _all_final_answers(log).lower()
    meta = log.get("metadata", {})
    triggered_reasons: list[str] = []

    for name, check_fn in _FATAL_PATTERNS:
        try:
            if check_fn(combined, meta, fact_sheet):
                triggered_reasons.append(name)
        except Exception:
            pass

    return {
        "triggered": len(triggered_reasons) > 0,
        "reasons": triggered_reasons,
        "value": 1 if triggered_reasons else 0,
    }


# ---------------------------------------------------------------------------
# 4.7  S_Agent integration
# ---------------------------------------------------------------------------

def compute_s_outcome(s_answer_quality: float, s_grounding: float) -> float:
    return round(W_ANSWER_QUALITY * s_answer_quality + W_GROUNDING * s_grounding, 1)


def compute_s_agent(
    s_outcome: float,
    s_tool: float,
    s_trajectory: float,
    s_efficiency: float,
    i_fatal: int,
) -> dict:
    s_raw = round(
        W_OUTCOME * s_outcome
        + W_TOOL * s_tool
        + W_TRAJECTORY * s_trajectory
        + W_EFFICIENCY * s_efficiency,
        1
    )
    s_agent = min(s_raw, I_FATAL_CAP) if i_fatal else s_raw
    return {"s_raw": s_raw, "s_agent": s_agent}


# ---------------------------------------------------------------------------
# 4.8  ProxyCost / NetValue / Delta_MB
# ---------------------------------------------------------------------------

def compute_proxy_cost(
    log: dict,
    max_tokens: float,
    max_llm_calls: int,
    max_tool_calls: int,
) -> float:
    usage = log.get("usage_summary", {})
    tokens = usage.get("grand_total_tokens", 0) or 0
    # Approximate LLM calls from conversation length
    n_llm = len(log.get("conversation", []))
    # Tool calls extracted
    expected_oid = ""
    n_tool = len(extract_tool_calls(log))

    token_norm    = tokens / max_tokens if max_tokens else 0
    llm_call_norm = n_llm / max_llm_calls if max_llm_calls else 0
    tool_call_norm = n_tool / max_tool_calls if max_tool_calls else 0

    proxy_cost = 100.0 * (
        W_TOKEN * token_norm
        + W_LLM_CALL * llm_call_norm
        + W_TOOL_CALL * tool_call_norm
    )
    return round(proxy_cost, 2)


def compute_net_value(v_i: int, s_agent: float, proxy_cost: float) -> float:
    return round(v_i * s_agent / 100.0 - LAMBDA * proxy_cost, 4)


# ---------------------------------------------------------------------------
# Single-case full evaluation
# ---------------------------------------------------------------------------

def _get_judge_score_as_answer_quality(log: dict) -> float:
    """
    Extract S_AnswerQuality from existing judge field in log.
    Maps old keys (fulfillment/logic/tone) → new dimension weights.
    """
    judge = log.get("judge", {})
    scores = judge.get("scores", {})
    if not scores:
        return 0.0

    key_map = {
        "fulfillment": "s_resolution",
        "logic": "s_completeness",
        "tone": "s_tone",
    }
    weights = {"s_resolution": 0.50, "s_completeness": 0.30, "s_tone": 0.20}
    normalised = {key_map.get(k, k): v for k, v in scores.items()}

    total = 0.0
    for dim, w in weights.items():
        raw = normalised.get(dim, 1)
        total += ((raw - 1) / 4 * 100) * w
    return round(total, 1)


def evaluate_log(
    log: dict,
    fact_sheet: dict,
    policy_gt: dict,
    baseline_cost: float,
    max_tokens: float,
    max_llm_calls: int,
    max_tool_calls: int,
) -> dict:
    """Compute all Phase 5 metrics for a single log."""
    meta = log.get("metadata", {})
    case_id = meta.get("case_id", "")
    agent_type = meta.get("agent_type", "")
    persona_type = meta.get("persona_type", "")

    fs_meta = fact_sheet.get("metadata", {})
    difficulty_label = fs_meta.get("difficulty_label", "medium")
    v_i = fs_meta.get("v_i", V_MAP.get(difficulty_label, 2))

    # Judge-based answer quality (from stored scores)
    s_answer_quality = _get_judge_score_as_answer_quality(log)
    judge_scores = log.get("judge", {}).get("scores", {})

    # Rule-based metrics
    grounding = compute_s_grounding(log, fact_sheet, policy_gt)
    tool_m = compute_s_tool(log, fact_sheet)
    traj = compute_s_trajectory(log, fact_sheet)
    s_efficiency = compute_s_efficiency(log, baseline_cost)
    fatal = compute_i_fatal(log, fact_sheet)

    # Composite scores
    s_outcome = compute_s_outcome(s_answer_quality, grounding["score"])
    agent_scores = compute_s_agent(
        s_outcome, tool_m["score"], traj["score"], s_efficiency, fatal["value"]
    )

    # ProxyCost / NetValue
    proxy_cost = compute_proxy_cost(log, max_tokens, max_llm_calls, max_tool_calls)
    net_value = compute_net_value(v_i, agent_scores["s_agent"], proxy_cost)

    return {
        "case_id": case_id,
        "agent_type": agent_type,
        "persona_type": persona_type,
        "difficulty": difficulty_label,
        "v_i": v_i,
        # Judge scores (stored in log, old or new format)
        "judge_s_resolution": judge_scores.get("s_resolution", judge_scores.get("fulfillment")),
        "judge_s_completeness": judge_scores.get("s_completeness", judge_scores.get("logic")),
        "judge_s_tone": judge_scores.get("s_tone", judge_scores.get("tone")),
        "s_answer_quality": s_answer_quality,
        # Grounding
        "s_grounding": grounding["score"],
        "grounding_order_id": grounding["checks"].get("order_id_match"),
        "grounding_status": grounding["checks"].get("status_match"),
        "grounding_amount": grounding["checks"].get("amount_match"),
        "grounding_policy_claim": grounding["checks"].get("policy_no_forbidden_claim"),
        "grounding_policy_condition": grounding["checks"].get("policy_no_hallucinated_condition"),
        # Outcome
        "s_outcome": s_outcome,
        # Tool
        "tool_f1": tool_m["tool_f1"],
        "tool_arg_correctness": tool_m["arg_correctness"],
        "tool_result_usage": tool_m["result_usage"],
        "s_tool": tool_m["score"],
        "used_tools": "|".join(sorted(tool_m["used_tools"])),
        "expected_tools": "|".join(sorted(tool_m["expected_tools"])),
        # Trajectory
        "traj_flow_order": traj["checks"].get("flow_order"),
        "traj_no_loops": traj["checks"].get("no_excessive_loops"),
        "traj_no_redundancy": traj["checks"].get("no_redundancy"),
        "traj_identity_verified": traj["checks"].get("identity_verified"),
        "s_trajectory": traj["score"],
        # Efficiency
        "total_tokens": log.get("usage_summary", {}).get("grand_total_tokens"),
        "execution_seconds": meta.get("execution_seconds"),
        "s_efficiency": s_efficiency,
        # Fatal
        "i_fatal": fatal["value"],
        "fatal_reasons": "|".join(fatal["reasons"]) if fatal["reasons"] else "",
        # Final
        "s_raw": agent_scores["s_raw"],
        "s_agent": agent_scores["s_agent"],
        # Cost
        "proxy_cost": proxy_cost,
        "net_value": net_value,
    }


# ---------------------------------------------------------------------------
# Batch evaluation
# ---------------------------------------------------------------------------

def _build_evaluation_record(result: dict) -> dict:
    """Build structured evaluation dict to embed in log file."""
    used = result["used_tools"].split("|") if result["used_tools"] else []
    fatal = result["fatal_reasons"].split("|") if result["fatal_reasons"] else []
    grounding_checks = {}
    for key, col in [
        ("order_id_match", "grounding_order_id"),
        ("status_match", "grounding_status"),
        ("amount_match", "grounding_amount"),
        ("policy_no_forbidden_claim", "grounding_policy_claim"),
        ("policy_no_hallucinated_condition", "grounding_policy_condition"),
    ]:
        if result[col] is not None:
            grounding_checks[key] = result[col]

    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "s_answer_quality": result["s_answer_quality"],
        "s_grounding": result["s_grounding"],
        "grounding_checks": grounding_checks,
        "s_outcome": result["s_outcome"],
        "s_tool": result["s_tool"],
        "tool_detail": {
            "tool_f1": result["tool_f1"],
            "arg_correctness": result["tool_arg_correctness"],
            "result_usage": result["tool_result_usage"],
            "used_tools": used,
        },
        "s_trajectory": result["s_trajectory"],
        "trajectory_checks": {
            "flow_order": result["traj_flow_order"],
            "no_excessive_loops": result["traj_no_loops"],
            "no_redundancy": result["traj_no_redundancy"],
            "identity_verified": result["traj_identity_verified"],
        },
        "s_efficiency": result["s_efficiency"],
        "i_fatal": result["i_fatal"],
        "fatal_reasons": fatal,
        "s_raw": result["s_raw"],
        "s_agent": result["s_agent"],
        "proxy_cost": result["proxy_cost"],
        "net_value": result["net_value"],
    }


def batch_evaluate(
    logs_dir: str | Path,
    fact_sheets_path: str | Path,
    policy_gt_path: str | Path,
    output_csv: str | Path,
    only_cases: Optional[list[str]] = None,
    write_back: bool = False,
    baseline_logs_dir: Optional[str | Path] = None,
) -> list[dict]:
    """
    Compute all Phase 5 metrics for every log file under logs_dir (recursive).

    Baseline for S_Efficiency: median token/second count of Single-slot runs
    grouped by difficulty_label. If baseline_logs_dir is provided, Single-slot
    logs are sourced from there instead of logs_dir (needed when evaluating a
    non-Single-slot architecture directory that contains no baseline logs).
    """
    logs_dir = Path(logs_dir)
    with open(fact_sheets_path, encoding="utf-8") as f:
        all_fact_sheets: dict = json.load(f)
    with open(policy_gt_path, encoding="utf-8") as f:
        policy_gt: dict = json.load(f)

    log_files = sorted(logs_dir.rglob("log_*.json"))
    print(f"Found {len(log_files)} log file(s) under {logs_dir}")

    # Load all logs
    logs_by_file: dict[Path, dict] = {}
    for lf in log_files:
        try:
            with open(lf, encoding="utf-8") as f:
                logs_by_file[lf] = json.load(f)
        except Exception as e:
            print(f"  SKIP {lf.name}: {e}")

    # Load baseline logs (may differ from logs_dir for non-Single-slot architectures)
    if baseline_logs_dir is not None:
        baseline_dir = Path(baseline_logs_dir)
        baseline_log_files = sorted(baseline_dir.rglob("log_*.json"))
        baseline_logs: dict[Path, dict] = {}
        for lf in baseline_log_files:
            try:
                with open(lf, encoding="utf-8") as f:
                    baseline_logs[lf] = json.load(f)
            except Exception:
                pass
    else:
        baseline_logs = logs_by_file

    # Compute baselines: median cost-proxy of Single-slot logs, grouped by difficulty.
    # Separate seconds-based and token-based baselines to avoid mixing units when a
    # run 1 log uses tokens (no execution_seconds) and later runs use seconds.
    ss_seconds_by_difficulty: dict[str, list[float]] = {}
    ss_tokens_by_difficulty: dict[str, list[float]] = {}
    for lf, log in baseline_logs.items():
        if log.get("metadata", {}).get("agent_type", "") != "Single-slot":
            continue
        case_id = log.get("metadata", {}).get("case_id", "")
        fs = all_fact_sheets.get(case_id, {})
        difficulty = fs.get("metadata", {}).get("difficulty_label", "medium")
        secs = log.get("metadata", {}).get("execution_seconds")
        if secs and secs > 0:
            ss_seconds_by_difficulty.setdefault(difficulty, []).append(float(secs))
        else:
            tokens = log.get("usage_summary", {}).get("grand_total_tokens", 1) or 1
            ss_tokens_by_difficulty.setdefault(difficulty, []).append(float(tokens))

    baseline_seconds_map: dict[str, float] = {
        d: statistics.median(vals) for d, vals in ss_seconds_by_difficulty.items() if vals
    }
    baseline_tokens_map: dict[str, float] = {
        d: statistics.median(vals) for d, vals in ss_tokens_by_difficulty.items() if vals
    }
    print(f"  Single-slot baselines (seconds) by difficulty: {baseline_seconds_map}")
    print(f"  Single-slot baselines (tokens)  by difficulty: {baseline_tokens_map}")

    # Compute global max values for ProxyCost normalisation
    all_tokens = [
        log.get("usage_summary", {}).get("grand_total_tokens", 0) or 0
        for log in logs_by_file.values()
    ]
    all_turns = [len(log.get("conversation", [])) for log in logs_by_file.values()]
    all_tool_counts = [len(extract_tool_calls(log)) for log in logs_by_file.values()]
    max_tokens = max(all_tokens, default=1) or 1
    max_llm_calls = max(all_turns, default=1) or 1
    max_tool_calls = max(all_tool_counts, default=1) or 1

    # Evaluate each log
    results: list[dict] = []
    for lf, log in logs_by_file.items():
        meta = log.get("metadata", {})
        case_id = meta.get("case_id", "")
        agent_type = meta.get("agent_type", "")

        if only_cases and case_id not in only_cases:
            continue

        fs = all_fact_sheets.get(case_id, {})
        if not fs:
            print(f"  SKIP {lf.name}: no fact sheet for {case_id}")
            continue

        difficulty = fs.get("metadata", {}).get("difficulty_label", "medium")
        # Use matching-unit baseline: seconds if log has execution_seconds, else tokens
        _log_secs = log.get("metadata", {}).get("execution_seconds")
        if _log_secs and _log_secs > 0:
            baseline_cost = baseline_seconds_map.get(difficulty, 1.0)
        else:
            baseline_cost = baseline_tokens_map.get(difficulty, float(max_tokens))

        try:
            result = evaluate_log(
                log, fs, policy_gt,
                baseline_cost, max_tokens, max_llm_calls, max_tool_calls,
            )
            results.append(result)
            print(
                f"  {case_id:10s} | {agent_type:12s} | {meta.get('persona_type','?'):12s} "
                f"| S_Agent={result['s_agent']:6.1f}  "
                f"(Outcome={result['s_outcome']:.0f} "
                f"Tool={result['s_tool']:.0f} "
                f"Traj={result['s_trajectory']:.0f} "
                f"Eff={result['s_efficiency']:.0f}"
                + (" ⚠ I_FATAL" if result["i_fatal"] else "")
                + ")"
            )
            if write_back:
                log["evaluation"] = _build_evaluation_record(result)
                with open(lf, "w", encoding="utf-8") as f:
                    json.dump(log, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"  ERROR {lf.name}: {e}")

    _save_csv(results, output_csv)
    print(f"\nSaved {len(results)} rows → {output_csv}")
    return results


def _save_csv(results: list[dict], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "case_id", "agent_type", "persona_type", "difficulty", "v_i",
        "judge_s_resolution", "judge_s_completeness", "judge_s_tone", "s_answer_quality",
        "s_grounding", "grounding_order_id", "grounding_status", "grounding_amount",
        "grounding_policy_claim", "grounding_policy_condition",
        "s_outcome",
        "tool_f1", "tool_arg_correctness", "tool_result_usage", "s_tool",
        "used_tools", "expected_tools",
        "traj_flow_order", "traj_no_loops", "traj_no_redundancy", "traj_identity_verified",
        "s_trajectory",
        "total_tokens", "execution_seconds", "s_efficiency",
        "i_fatal", "fatal_reasons",
        "s_raw", "s_agent",
        "proxy_cost", "net_value",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 5 rule-based metrics (§4.2–4.8)")
    parser.add_argument("--logs-dir", default="outputs/logs")
    parser.add_argument("--fact-sheets", default="data/fact_sheets.json")
    parser.add_argument("--policy-gt", default="data/policy_ground_truth.json")
    parser.add_argument("--output-csv", default="outputs/reports/s_agent_results.csv")
    parser.add_argument(
        "--baseline-logs-dir", default=None,
        help="Directory with Single-slot baseline logs (use when logs-dir contains no Single-slot logs)"
    )
    parser.add_argument(
        "--cases", nargs="*",
        default=["CASE_001", "CASE_002", "CASE_015", "CASE_075", "CASE_090", "CASE_141"],
        help="Case IDs to include (default: Phase 1 selection)"
    )
    parser.add_argument(
        "--write-back", action="store_true",
        help="Write evaluation results back into each log file as 'evaluation' field"
    )
    args = parser.parse_args()

    batch_evaluate(
        logs_dir=args.logs_dir,
        fact_sheets_path=args.fact_sheets,
        policy_gt_path=args.policy_gt,
        output_csv=args.output_csv,
        only_cases=args.cases,
        write_back=args.write_back,
        baseline_logs_dir=args.baseline_logs_dir,
    )
