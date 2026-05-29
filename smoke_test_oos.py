"""
Smoke test: run all 12 combinations (4 architectures × 3 personas) with OOS data.

Uses 2 cases:
  OOS_013  RETURNS / exchange_request / easy
  OOS_020  ORDER   / track_order       / medium

Each combination must complete without exception for PASS.
Results are summarised in a table at the end.
"""

import json
import traceback
from pathlib import Path
from src.core.runner import DialogueRunner

OOS_FACT_SHEETS = Path("data/oos_fact_sheets.json")

AGENT_TYPES  = ["ReAct", "PlanExecute", "Reflection", "Single-slot"]
PERSONA_TYPES = ["Polite", "Adversarial", "VIP"]
SMOKE_CASES  = ["OOS_013", "OOS_020"]      # easy + medium

def main():
    with open(OOS_FACT_SHEETS, encoding="utf-8") as f:
        all_fs = json.load(f)

    runner = DialogueRunner(
        model_name="llama3.1:8b",
        fact_sheets_path=str(OOS_FACT_SHEETS),
    )

    results = {}   # (agent, persona, case_id) → {"status", "resolution", "turns", "error"}

    total = len(AGENT_TYPES) * len(PERSONA_TYPES) * len(SMOKE_CASES)
    done  = 0

    for agent_type in AGENT_TYPES:
        for persona_type in PERSONA_TYPES:
            for case_id in SMOKE_CASES:
                done += 1
                key = (agent_type, persona_type, case_id)
                fact_sheet = all_fs[case_id]
                meta = fact_sheet["metadata"]

                print(f"\n{'='*65}")
                print(f"[{done}/{total}]  {agent_type} | {persona_type} | {case_id}"
                      f"  ({meta['intent']} / {meta['difficulty_label']})")
                print(f"{'='*65}")

                try:
                    result = runner.run_conversation(
                        case_id=case_id,
                        fact_sheet=fact_sheet,
                        agent_type=agent_type,
                        persona_type=persona_type,
                        dataset="outsample",
                    )
                    summary = result.get("metadata", {})
                    conv    = result.get("conversation", [])
                    turns   = conv[-1]["turn"] if conv else 0
                    results[key] = {
                        "status":     summary.get("status", "?"),
                        "resolution": summary.get("final_resolution", "?"),
                        "turns":      turns,
                        "error":      None,
                    }
                    print(f"  → PASS  status={results[key]['status']}"
                          f"  resolution={results[key]['resolution']}"
                          f"  turns={turns}")

                except Exception as e:
                    results[key] = {
                        "status":     "EXCEPTION",
                        "resolution": "N/A",
                        "turns":      0,
                        "error":      str(e),
                    }
                    print(f"  → FAIL  {e}")
                    traceback.print_exc()

    # ── Summary table ──────────────────────────────────────────────────────────
    print("\n\n" + "="*80)
    print("SMOKE TEST SUMMARY  (4 architectures × 3 personas × 2 cases = 24 runs)")
    print("="*80)
    header = f"{'Agent':<14} {'Persona':<12} {'Case':<10} {'Status':<18} {'Resolution':<26} {'Turns'}"
    print(header)
    print("-"*80)

    passes = fails = 0
    for agent_type in AGENT_TYPES:
        for persona_type in PERSONA_TYPES:
            for case_id in SMOKE_CASES:
                key = (agent_type, persona_type, case_id)
                r = results.get(key, {})
                ok  = r.get("error") is None
                tag = "PASS" if ok else "FAIL"
                if ok: passes += 1
                else:   fails += 1
                print(f"[{tag}] {agent_type:<14} {persona_type:<12} {case_id:<10}"
                      f" {r.get('status','?'):<18} {r.get('resolution','?'):<26} {r.get('turns','?')}")

    print("-"*80)
    print(f"TOTAL: {passes} PASS  {fails} FAIL  out of {total} runs")
    if fails == 0:
        print("All combinations PASSED — ready for full 600-run batch.")
    else:
        print("Some combinations FAILED — fix before launching full batch.")

if __name__ == "__main__":
    main()
