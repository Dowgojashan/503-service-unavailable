"""
Quick smoke-test: run 2 OOS cases through the DialogueRunner and verify output.

Cases  : OOS_001 (Returns / hard), OOS_028 (Refund / hard)
Agent  : ReAct
Persona: standard
"""

import json
from pathlib import Path
from src.core.runner import DialogueRunner

OOS_FACT_SHEETS = Path("data/oos_fact_sheets.json")
FACT_SHEETS_PATH = str(OOS_FACT_SHEETS)   # passed to judge

TEST_CASES  = ["OOS_001", "OOS_028"]
AGENT_TYPE  = "ReAct"
PERSONA     = "Polite"

def main():
    with open(OOS_FACT_SHEETS, encoding="utf-8") as f:
        all_fs = json.load(f)

    runner = DialogueRunner(model_name="llama3.1:8b", fact_sheets_path=str(OOS_FACT_SHEETS))

    for case_id in TEST_CASES:
        fact_sheet = all_fs[case_id]
        print(f"\n{'='*60}")
        print(f"Running {case_id} | intent={fact_sheet['metadata']['intent']} | diff={fact_sheet['metadata']['difficulty_label']}")
        print(f"Instruction: {fact_sheet['agent_input'][:100]}...")
        print(f"{'='*60}")

        result = runner.run_conversation(
            case_id=case_id,
            fact_sheet=fact_sheet,
            agent_type=AGENT_TYPE,
            persona_type=PERSONA,
            dataset="outsample",
        )

        # Brief summary
        summary = result.get("summary", {})
        print(f"\n--- Result ---")
        print(f"  Status          : {summary.get('status')}")
        print(f"  Final resolution: {summary.get('final_resolution')}")
        print(f"  Turns           : {summary.get('total_turns')}")
        print(f"  Exec seconds    : {summary.get('execution_seconds')}")
        usage = result.get("usage_summary", {})
        print(f"  Total tokens    : {usage.get('grand_total_tokens')}")
        judge = result.get("judge")
        if judge:
            print(f"  Judge scores    : {judge.get('scores')}")
        else:
            print(f"  Judge          : not available")

    print("\n\nAll test cases finished.")

if __name__ == "__main__":
    main()
