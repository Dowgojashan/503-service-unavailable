"""
LLM-as-a-Judge evaluator for customer service agent conversations.

Implements system_design.md §3.6.1–3.6.4:
  3.6.1  Structured scoring rubrics (1–5 per dimension)
  3.6.2  Chain-of-Thought prompting: evidence → reasoning → score
  3.6.3  Reference-based grounding via fact_sheets.json
  3.6.4  JSON output + 0–100 mapping + CSV export

Judge model : gemini-3.1-flash-lite  (Google AI Studio / Gemini API)
Note        : deliberately different from the evaluated model (llama3.1:8b)
              to avoid self-evaluation bias (player-referee problem)

Weights (→ S_Judge, weight 0.7 in the overall framework):
  Fulfillment  50%  — did the agent resolve the customer's core problem?
  Logic        30%  — SOP compliance + zero hallucination vs. fact sheet
  Tone         20%  — professional, concise, empathetic

Score mapping: dimension 1–5  →  (score-1)/4 × 100  →  weighted average
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JUDGE_MODEL = "gemini-3.1-flash-lite"

DIMENSION_WEIGHTS = {"fulfillment": 0.50, "logic": 0.30, "tone": 0.20}

# ---------------------------------------------------------------------------
# Scoring rubric (injected verbatim into the judge prompt)
# ---------------------------------------------------------------------------

RUBRIC = """
=== SCORING RUBRIC ===

[Fulfillment] Task Achievement — Did the agent resolve the customer's core problem?
  5 = Core problem fully resolved; correct tool action executed
      (e.g. order cancelled, refund applied, info provided accurately)
  4 = Problem largely resolved with a minor gap or unnecessary detour
  3 = Topic addressed but the key request was left unanswered or incomplete
  2 = Only tangential help given; customer's actual need was ignored
  1 = Problem not addressed, refused without valid reason, or situation worsened

[Logic] Business Logic & Hallucination — Did the agent follow SOPs and stay factual?
  5 = All SOP steps followed correctly (identity verification → action);
      every factual claim matches the fact sheet exactly; no invented information
  4 = Minor phrasing deviation; no harmful factual errors
  3 = One hallucinated fact OR one critical SOP step skipped
      (e.g. acted before verifying identity; invented a refund reason)
  2 = Multiple hallucinated facts OR significant policy violation
  1 = Dangerous hallucination (fabricated amounts/dates) or completely wrong procedure

[Tone] Communication Professionalism — Was the agent professional and concise?
  5 = Professional, empathetic, concise, and clear throughout
  4 = Mostly professional; minor verbosity or slight coldness
  3 = Acceptable but inconsistent (e.g. robotic repetition, slightly off-topic)
  2 = Unprofessional, excessively verbose, or unnecessarily repeated itself
  1 = Rude, confusing, dismissive, or actively frustrated the customer
""".strip()

# ---------------------------------------------------------------------------
# Judge prompt template
# ---------------------------------------------------------------------------

JUDGE_PROMPT_TEMPLATE = """\
You are an expert evaluator for customer service AI systems.
Your task: score the conversation below using the FACT SHEET as the SOLE source of truth for order-specific facts.

{rubric}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUSINESS RULES  (this system's authoritative policies — override any generic CS assumptions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Identity verification SOP: The agent MUST ask for the customer's Order ID (ORDxxx format)
   OR registered email before taking any action. Providing either one is sufficient.
   Skipping this step before executing a tool is a Logic violation.

2. Cancellation policy: Orders in ANY status — including "Shipped" — MAY be cancelled upon
   customer request. Offering to cancel a shipped order is CORRECT behaviour, not a violation.

3. Return / refund policy: The 30-day return window applies to returns for damaged goods,
   incorrect items, or quality issues AFTER delivery. It is separate from pre-delivery
   cancellations and does NOT block a cancellation request.

4. Item removal: The system does NOT support removing individual items from an order.
   Full cancellation is the only option available. Informing the customer of this limitation
   and offering full cancellation is CORRECT.

5. Address change: Shipping addresses CANNOT be changed once an order is placed.
   Telling the customer this limitation is CORRECT.

6. Delivery options: Delivery options (standard / express / priority) CANNOT be changed
   after an order is placed. Telling the customer this is CORRECT.

7. Refund reasons: If `refund_info.refund_status` in the fact sheet is "N/A", the reason
   for the order's refunded status is UNKNOWN. The agent MUST NOT invent a reason
   (e.g. "refunded due to a damaged item"). Inventing a reason IS a Logic violation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANTI-HALLUCINATION RULE  (critical — read carefully)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The fact sheet tells you everything that is KNOWN about this specific order.
If the service agent states an order-specific fact that is NOT in the fact sheet, that is a hallucination.

Examples of hallucinations to penalise under [Logic]:
• Inventing a REASON for a refund (e.g. "refunded due to a damaged item") when the fact sheet only shows refund_status: "N/A"
• Stating a wrong order amount, wrong item name, or wrong order number
• Claiming an action was taken (cancel/refund) when the tool call trace shows it was NOT executed

General business policy (e.g. "30-day return window", "contact support for investigations") is NOT in the fact sheet on purpose — the agent is allowed to cite standard policy. Only penalise order-specific invented facts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FACT SHEET  (ground truth for this case)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```json
{fact_sheet}
```

CUSTOMER INTENT: {intent}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSATION TRANSCRIPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{conversation}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EVALUATION — follow these steps in order
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1 — Evidence extraction
  For each dimension list the key quotes or actions that are POSITIVE (✓) or NEGATIVE (✗).

Step 2 — Fact verification
  Compare every order-specific claim by the agent against the fact sheet.
  Flag any discrepancy.

Step 3 — Score derivation
  State the score (1–5) for each dimension and a one-sentence justification.

Step 4 — Output JSON
  After completing Steps 1–3, output ONLY the JSON block below with no additional text after it.

```json
{{
  "case_id": "{case_id}",
  "agent_type": "{agent_type}",
  "evidence": {{
    "fulfillment": ["<quote or action>"],
    "logic": ["<fact check result>"],
    "tone": ["<tone observation>"]
  }},
  "reasoning": {{
    "fulfillment": "<one-sentence justification>",
    "logic": "<one-sentence justification>",
    "tone": "<one-sentence justification>"
  }},
  "scores": {{
    "fulfillment": <integer 1-5>,
    "logic": <integer 1-5>,
    "tone": <integer 1-5>
  }},
  "final_score_0_100": <number>
}}
```

final_score_0_100 formula (compute yourself):
  dim_100 = (score - 1) / 4 × 100
  final = fulfillment_100 × 0.50  +  logic_100 × 0.30  +  tone_100 × 0.20
""".strip()


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_log(log_path: str | Path) -> dict:
    with open(log_path, encoding="utf-8") as f:
        return json.load(f)


def load_fact_sheet(fact_sheets_path: str | Path, case_id: str) -> dict:
    with open(fact_sheets_path, encoding="utf-8") as f:
        all_sheets = json.load(f)
    return all_sheets.get(case_id, {})


def format_conversation(log: dict) -> str:
    lines: list[str] = []
    for turn in log.get("conversation", []):
        t = turn["turn"]
        cust = turn.get("customer", {}).get("content", "")
        agent = turn.get("service_agent", {}).get("final_answer", "")
        lines.append(f"[Turn {t}] Customer : {cust}")
        lines.append(f"[Turn {t}] Agent    : {agent}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON extraction (handles markdown fences from model output)
# ---------------------------------------------------------------------------

def extract_json_from_response(text: str) -> dict:
    # 1. ```json ... ``` block
    m = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if m:
        return json.loads(m.group(1))
    # 2. Last standalone {...} block
    m = re.search(r"(\{[\s\S]*\})\s*$", text)
    if m:
        return json.loads(m.group(1))
    raise ValueError(f"No JSON found in model response (first 500 chars):\n{text[:500]}")


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_final_score(scores: dict) -> float:
    """Map 1–5 per dimension → weighted 0–100."""
    total = 0.0
    for dim, weight in DIMENSION_WEIGHTS.items():
        raw = scores.get(dim, 1)
        total += ((raw - 1) / 4 * 100) * weight
    return round(total, 1)


# ---------------------------------------------------------------------------
# Judge API call
# ---------------------------------------------------------------------------

def call_judge(prompt: str, model_name: str = JUDGE_MODEL) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )
    raw_text = response.text
    result = extract_json_from_response(raw_text)
    result["_raw_response"] = raw_text
    return result


# ---------------------------------------------------------------------------
# Single-case evaluation
# ---------------------------------------------------------------------------

def judge_single_case(
    log_path: str | Path,
    fact_sheets_path: str | Path,
    model_name: str = JUDGE_MODEL,
    verbose: bool = True,
) -> dict:
    log = load_log(log_path)
    meta = log.get("metadata", {})
    case_id = meta.get("case_id", "UNKNOWN")
    agent_type = meta.get("agent_type", "UNKNOWN")

    # intent from fact sheet (more reliable than log metadata)
    fact_sheet = load_fact_sheet(fact_sheets_path, case_id)
    intent = fact_sheet.get("metadata", {}).get("intent", "unknown")

    conversation_str = format_conversation(log)

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        rubric=RUBRIC,
        fact_sheet=json.dumps(fact_sheet, ensure_ascii=False, indent=2),
        intent=intent,
        conversation=conversation_str,
        case_id=case_id,
        agent_type=agent_type,
    )

    if verbose:
        print(f"  Judging {case_id} / {agent_type} …")

    result = call_judge(prompt, model_name)

    # Always recompute final score with our formula (model may differ)
    if "scores" in result:
        result["final_score_0_100"] = compute_final_score(result["scores"])

    result["case_id"] = case_id
    result["agent_type"] = agent_type
    result["run_status"] = meta.get("status", "UNKNOWN")
    result["persona_type"] = meta.get("persona_type", "UNKNOWN")

    return result


# ---------------------------------------------------------------------------
# Batch evaluation
# ---------------------------------------------------------------------------

def judge_batch(
    logs_dir: str | Path,
    fact_sheets_path: str | Path,
    output_csv: str | Path,
    model_name: str = JUDGE_MODEL,
    delay_seconds: float = 1.5,
) -> list[dict]:
    logs_dir = Path(logs_dir)
    log_files = sorted(logs_dir.glob("log_*.json"))

    print(f"Found {len(log_files)} log file(s). Judge model: {model_name}")
    results: list[dict] = []

    for i, log_path in enumerate(log_files):
        try:
            result = judge_single_case(log_path, fact_sheets_path, model_name)
            results.append(result)
            scores = result.get("scores", {})
            print(
                f"  [{i+1}/{len(log_files)}] {result['case_id']:10s} | {result['agent_type']:12s} "
                f"| F={scores.get('fulfillment','?')} "
                f"L={scores.get('logic','?')} "
                f"T={scores.get('tone','?')} "
                f"→ {result.get('final_score_0_100','?'):5}/100"
            )
        except Exception as exc:
            print(f"  ERROR on {log_path.name}: {exc}")
            results.append({"case_id": log_path.stem, "agent_type": "?", "error": str(exc)})

        if i < len(log_files) - 1:
            time.sleep(delay_seconds)

    save_results_csv(results, output_csv)
    print(f"\nResults saved → {output_csv}")
    return results


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def save_results_csv(results: list[dict], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "case_id", "agent_type", "persona_type", "run_status",
        "score_fulfillment", "score_logic", "score_tone", "final_score_0_100",
        "reasoning_fulfillment", "reasoning_logic", "reasoning_tone",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            if "error" in r:
                writer.writerow({
                    "case_id": r.get("case_id", ""),
                    "run_status": f"ERROR: {r['error']}",
                })
                continue
            scores = r.get("scores", {})
            reasoning = r.get("reasoning", {})
            writer.writerow({
                "case_id": r.get("case_id"),
                "agent_type": r.get("agent_type"),
                "persona_type": r.get("persona_type"),
                "run_status": r.get("run_status"),
                "score_fulfillment": scores.get("fulfillment"),
                "score_logic": scores.get("logic"),
                "score_tone": scores.get("tone"),
                "final_score_0_100": r.get("final_score_0_100"),
                "reasoning_fulfillment": reasoning.get("fulfillment"),
                "reasoning_logic": reasoning.get("logic"),
                "reasoning_tone": reasoning.get("tone"),
            })


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM-as-a-Judge evaluator (§3.6)")
    parser.add_argument(
        "--mode", choices=["single", "batch"], default="batch",
        help="Evaluate one log file or all logs in a directory",
    )
    parser.add_argument("--log", help="Path to a single log JSON (required for --mode single)")
    parser.add_argument("--logs-dir", default="outputs/logs", help="Directory of log files")
    parser.add_argument("--fact-sheets", default="data/fact_sheets.json")
    parser.add_argument("--output-csv", default="outputs/judge_results.csv")
    parser.add_argument(
        "--model", default=JUDGE_MODEL,
        help="Judge model name (e.g. gemini-3.1-flash-lite or gemini-2.5-flash)",
    )
    parser.add_argument(
        "--delay", type=float, default=1.5,
        help="Seconds to wait between API calls (batch mode)",
    )
    args = parser.parse_args()

    if args.mode == "single":
        if not args.log:
            parser.error("--log is required when using --mode single")
        result = judge_single_case(args.log, args.fact_sheets, args.model)
        # Print without the raw response to keep output clean
        display = {k: v for k, v in result.items() if k != "_raw_response"}
        print(json.dumps(display, ensure_ascii=False, indent=2))
    else:
        judge_batch(args.logs_dir, args.fact_sheets, args.output_csv, args.model, args.delay)
