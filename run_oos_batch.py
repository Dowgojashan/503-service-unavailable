"""
OOS batch runner — runs all 50 OOS cases for one architecture × persona combination.

Usage:
  python run_oos_batch.py --agent Single-slot --persona Polite
  python run_oos_batch.py --agent ReAct --persona Adversarial
  python run_oos_batch.py --agent PlanExecute --persona VIP

Outputs:
  outputs/logs/outsample/{Persona}/{Agent}/log_OOS_xxx_{Agent}_{Persona}.json

Progress is checkpointed: already-completed logs are skipped automatically,
so the script can be safely re-run after an interruption.
"""

import argparse
import json
import traceback
from pathlib import Path

from src.core.runner import DialogueRunner

OOS_FACT_SHEETS = Path("data/oos_fact_sheets.json")
OUT_BASE        = Path("outputs/logs/outsample")

VALID_AGENTS   = ["ReAct", "PlanExecute", "Reflection", "Single-slot"]
VALID_PERSONAS = ["Polite", "Adversarial", "VIP"]


def log_path(out_dir: Path, case_id: str, agent: str, persona: str) -> Path:
    return out_dir / f"log_{case_id}_{agent}_{persona}.json"


def main(agent_type: str, persona_type: str, start: int = 1, end: int = 50):
    out_dir = OUT_BASE / persona_type / agent_type
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(OOS_FACT_SHEETS, encoding="utf-8") as f:
        all_fs = json.load(f)

    all_case_ids = sorted(all_fs.keys())  # OOS_001 … OOS_050
    case_ids = [c for c in all_case_ids if start <= int(c.split("_")[1]) <= end]
    total    = len(case_ids)

    runner = DialogueRunner(
        model_name="llama3.1:8b",
        fact_sheets_path=str(OOS_FACT_SHEETS),
    )

    passed = failed = skipped = 0

    print(f"\n{'='*65}")
    print(f"OOS Batch: {agent_type} × {persona_type}  ({total} cases)")
    print(f"Output dir: {out_dir}")
    print(f"{'='*65}\n")

    for i, case_id in enumerate(case_ids, 1):
        lp = log_path(out_dir, case_id, agent_type, persona_type)

        # ── checkpoint: skip if already done ──────────────────────────
        if lp.exists():
            skipped += 1
            print(f"[{i:>3}/{total}] SKIP  {case_id}  (log exists)")
            continue

        fact_sheet = all_fs[case_id]
        meta = fact_sheet["metadata"]
        print(f"[{i:>3}/{total}] RUN   {case_id}  "
              f"({meta['intent']} / {meta['difficulty_label']})", end="", flush=True)

        try:
            result = runner.run_conversation(
                case_id=case_id,
                fact_sheet=fact_sheet,
                agent_type=agent_type,
                persona_type=persona_type,
                dataset="outsample",
            )
            conv   = result.get("conversation", [])
            turns  = conv[-1]["turn"] if conv else 0
            status = result.get("metadata", {}).get("status", "?")
            print(f"  -> {status}  turns={turns}")
            passed += 1

        except Exception as e:
            print(f"  -> EXCEPTION: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*65}")
    print(f"DONE  {agent_type} × {persona_type}")
    print(f"  Ran: {passed}   Failed: {failed}   Skipped (already done): {skipped}")
    print(f"  Total: {passed+failed+skipped} / {total}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent",   required=True, choices=VALID_AGENTS)
    parser.add_argument("--persona", required=True, choices=VALID_PERSONAS)
    parser.add_argument("--start",   type=int, default=1,  help="First case number (inclusive, 1-50)")
    parser.add_argument("--end",     type=int, default=50, help="Last case number (inclusive, 1-50)")
    args = parser.parse_args()
    main(args.agent, args.persona, args.start, args.end)
