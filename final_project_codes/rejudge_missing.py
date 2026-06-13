"""
補評腳本：針對 outsample logs 中 judge 欄位缺失的筆數重新呼叫 LLM Judge，
並將結果寫回原 log 檔。
"""

import json
import time
from pathlib import Path

from eval.llm_judge import judge_single_case, JUDGE_MODEL

OOS_FACT_SHEETS = Path("data/oos_fact_sheets.json")
OUTSAMPLE_DIR   = Path("outputs/logs/outsample")
DELAY           = 2.0  # seconds between API calls


def has_judge(log: dict) -> bool:
    j = log.get("judge")
    return isinstance(j, dict) and j.get("final_score_0_100") is not None


def find_missing(base: Path) -> list[Path]:
    missing = []
    for lp in sorted(base.rglob("log_*.json")):
        with open(lp, encoding="utf-8") as f:
            d = json.load(f)
        if not has_judge(d):
            missing.append(lp)
    return missing


def main():
    missing = find_missing(OUTSAMPLE_DIR)
    print(f"Judge 缺分筆數：{len(missing)}\n")

    for i, lp in enumerate(missing, 1):
        with open(lp, encoding="utf-8") as f:
            log = json.load(f)
        meta    = log.get("metadata", {})
        case_id = meta.get("case_id", "?")
        agent   = meta.get("agent_type", "?")
        persona = meta.get("persona_type", "?")

        print(f"[{i:>2}/{len(missing)}] {case_id} | {agent} | {persona} … ", end="", flush=True)

        try:
            result = judge_single_case(lp, OOS_FACT_SHEETS, verbose=False)

            # 只保留需要的欄位寫回 log
            judge_entry = {
                "model":             JUDGE_MODEL,
                "scores":            result.get("scores", {}),
                "final_score_0_100": result.get("final_score_0_100"),
                "reasoning":         result.get("reasoning", {}),
                "evidence":          result.get("evidence", {}),
            }
            log["judge"] = judge_entry

            with open(lp, "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=2)

            s = result.get("scores", {})
            score = result.get("final_score_0_100", "?")
            print(f"R={s.get('s_resolution','?')} C={s.get('s_completeness','?')} T={s.get('s_tone','?')} → {score}/100")

        except Exception as e:
            print(f"ERROR: {e}")

        if i < len(missing):
            time.sleep(DELAY)

    print("\n補評完成。")


if __name__ == "__main__":
    main()
