"""
analysis_synthesis.py

分析每個案例中 runner programmatic synthesis 的介入程度。
比較「純 LLM 處理」vs「Synthesis 介入」兩組的完成率與品質。

偵測邏輯：
- PlanExecute: full_trace 含 Action: 但 final_answer 不含 Action: → 代表 runner 攔截後
  用 synthesis 生成回應，而非再呼叫一次 LLM
- ReAct: full_trace 含 Action: 且 final_answer 含已知 synthesis 模板短語
- Reflection: final_answer 含已知 synthesis 模板短語
- Single-slot: 永遠視為純 LLM（無 synthesis 機制）

輸出：
- 每個架構 × persona 的介入率
- 純 LLM 組 vs Synthesis 組的 Judge 分與完成率比較
"""

import os
import json
from collections import defaultdict

# ── Synthesis 偵測模板短語 ──────────────────────────────────────────────
# 這些短語是 runner 程式碼裡寫死的模板，出現在 final_answer 就代表 synthesis 介入
SYNTHESIS_PHRASES = [
    # PE / ReAct DEDUP synthesis
    "successfully cancelled as requested. is there anything else",
    "refund for order",
    "i've verified your order",
    "i can help with tracking, cancellation, or refund requests",
    "unfortunately, our system doesn't support changing the shipping address",
    "we accept major credit/debit cards",
    "our standard policy allows returns within 30 days",
    "once an order has been placed, delivery options cannot be changed",
    "for password resets, please use the 'forgot password' link",
    "is already cancelled",
    "is already refunded",
    "no further cancellation is needed",
    "has already been refunded",
    # PE IMMEDIATE SYNTHESIS (address / policy)
    "shipping addresses cannot be changed once an order is placed",
    "i wasn't able to cancel your order at this time",
    "i wasn't able to process a refund",
    # Reflection synthesis
    "i completely understand. unfortunately, removing individual items is a hard",
    "i understand this isn't the outcome you were hoping for",
]


def detect_synthesis_in_turn(turn: dict, agent_type: str) -> bool:
    """
    判斷單一對話 turn 裡是否有 synthesis 介入。
    回傳 True = synthesis 介入，False = 純 LLM。
    """
    sa = turn.get("service_agent", {})
    final_answer = (sa.get("final_answer") or "").lower()
    full_trace = (sa.get("full_trace") or "").lower()

    if agent_type == "Single-slot":
        return False  # Single-slot 沒有 synthesis

    # 方法一：final_answer 包含已知 synthesis 模板短語
    for phrase in SYNTHESIS_PHRASES:
        if phrase in final_answer:
            return True

    # 方法二（PlanExecute 專屬）：
    # full_trace 有 Action:（LLM 試圖呼叫工具），
    # 但 final_answer 沒有 Action:（runner 攔截後 synthesis 生成回應）
    if agent_type == "PlanExecute":
        if "action:" in full_trace and "action:" not in final_answer:
            # 還需要確認 final_answer 不是空的（才算真的 synthesis 替換）
            if len(final_answer.strip()) > 20:
                return True

    return False


def analyze_case(log_path: str, agent_type: str) -> dict:
    """
    分析單一 case log，回傳：
    - synthesis_turns: 有 synthesis 介入的 turn 數
    - total_turns: 總 turn 數
    - synthesis_rate: 介入比率
    - is_synthesis_assisted: 只要有一個 turn 被介入就算 True
    - final_resolution, judge_score, tokens
    """
    with open(log_path, encoding="utf-8") as f:
        data = json.load(f)

    conversation = data.get("conversation", [])
    meta = data.get("metadata", {})
    usage = data.get("usage_summary", {})
    judge = data.get("judge", {})

    synthesis_turns = 0
    total_turns = 0

    for turn in conversation:
        sa = turn.get("service_agent", {})
        # 只計算有 service_agent 回應的 turn
        if sa.get("final_answer") or sa.get("full_trace"):
            total_turns += 1
            if detect_synthesis_in_turn(turn, agent_type):
                synthesis_turns += 1

    is_synthesis_assisted = synthesis_turns > 0
    synthesis_rate = synthesis_turns / total_turns if total_turns > 0 else 0.0

    return {
        "case_id": meta.get("case_id", ""),
        "agent_type": agent_type,
        "persona_type": meta.get("persona_type", ""),
        "synthesis_turns": synthesis_turns,
        "total_turns": total_turns,
        "synthesis_rate": synthesis_rate,
        "is_synthesis_assisted": is_synthesis_assisted,
        "final_resolution": meta.get("final_resolution", "UNKNOWN"),
        "status": meta.get("status", "UNKNOWN"),
        "judge_score": judge.get("final_score_0_100"),
        "tokens": usage.get("grand_total_tokens", 0),
    }


def analyze_all(base_dir: str = "outputs/logs") -> list:
    """分析所有可用的 log 檔案。"""
    archs = ["Single-slot", "ReAct", "Reflection", "PlanExecute"]
    personas = ["Polite", "Adversarial", "VIP"]
    results = []

    for persona in personas:
        for arch in archs:
            d = os.path.join(base_dir, persona, arch)
            if not os.path.exists(d):
                continue
            files = sorted([
                f for f in os.listdir(d)
                if f.endswith(".json") and "_run2" not in f and "_run3" not in f
            ])
            for fn in files:
                r = analyze_case(os.path.join(d, fn), arch)
                results.append(r)

    return results


def print_report(results: list):
    """印出分析報告。"""
    from collections import Counter

    archs = ["Single-slot", "ReAct", "Reflection", "PlanExecute"]
    personas = ["Polite", "Adversarial", "VIP"]

    print("=" * 70)
    print("SYNTHESIS 介入率分析")
    print("=" * 70)

    # ── Part 1: 每個架構 × Persona 的介入率 ────────────────────────────
    print("\n【Part 1】各架構 × Persona 的 Synthesis 介入率")
    print(f"{'':20} {'Polite':>10} {'Adversarial':>12} {'VIP':>8}")
    print("-" * 52)

    for arch in archs:
        row = []
        for persona in personas:
            subset = [r for r in results if r["agent_type"] == arch and r["persona_type"] == persona]
            if not subset:
                row.append("  N/A")
                continue
            assisted = sum(1 for r in subset if r["is_synthesis_assisted"])
            row.append(f"{assisted/len(subset)*100:>8.1f}%")
        print(f"{arch:<20} {row[0]:>10} {row[1]:>12} {row[2]:>8}")

    # ── Part 2: 純 LLM vs Synthesis 的完成率與品質 ─────────────────────
    print("\n【Part 2】純 LLM 組 vs Synthesis 介入組：完成率 & Judge 分")
    print(f"{'架構':<14} {'組別':<12} {'n':>5} {'完成率':>8} {'Judge /100':>11} {'Tokens':>8}")
    print("-" * 62)

    resolved_labels = {"EXECUTED_SUCCESSFULLY", "INFO_PROVIDED", "RESOLVED_WITH_REFUSAL"}

    for arch in archs:
        for assisted_flag, label in [(False, "純 LLM"), (True, "Synthesis")]:
            subset = [
                r for r in results
                if r["agent_type"] == arch and r["is_synthesis_assisted"] == assisted_flag
            ]
            if not subset:
                print(f"{arch:<14} {label:<12} {'—':>5}")
                continue
            n = len(subset)
            resolved = sum(1 for r in subset if r["final_resolution"] in resolved_labels)
            judge_scores = [r["judge_score"] for r in subset if r["judge_score"] is not None]
            tokens = [r["tokens"] for r in subset if r["tokens"]]
            j_mean = sum(judge_scores) / len(judge_scores) if judge_scores else None
            t_mean = sum(tokens) / len(tokens) if tokens else None
            print(
                f"{arch:<14} {label:<12} {n:>5} "
                f"{resolved/n*100:>7.1f}% "
                f"{j_mean:>10.2f}" if j_mean else f"{arch:<14} {label:<12} {n:>5} "
                f"{resolved/n*100:>7.1f}%        N/A",
                f" {t_mean:>7.0f}" if t_mean else ""
            )

    # ── Part 3: PlanExecute 深度分析（介入比最高的架構）──────────────
    print("\n【Part 3】PlanExecute — 每筆案例平均 Synthesis 介入 turn 比率")
    pe_results = [r for r in results if r["agent_type"] == "PlanExecute"]
    if pe_results:
        rates = [r["synthesis_rate"] for r in pe_results]
        print(f"  平均介入比率（每 turn）: {sum(rates)/len(rates)*100:.1f}%")
        print(f"  完全無介入案例 (synthesis_rate=0): {sum(1 for r in pe_results if r['synthesis_rate']==0)} / {len(pe_results)}")
        print(f"  全程被介入案例 (synthesis_rate=1): {sum(1 for r in pe_results if r['synthesis_rate']==1)} / {len(pe_results)}")

    # ── Part 4: ReAct 深度分析 ─────────────────────────────────────────
    print("\n【Part 4】ReAct — Synthesis 介入 vs 純 LLM 品質比較（合併所有 Persona）")
    react_results = [r for r in results if r["agent_type"] == "ReAct"]
    for assisted_flag, label in [(False, "純 LLM"), (True, "Synthesis")]:
        subset = [r for r in react_results if r["is_synthesis_assisted"] == assisted_flag]
        if not subset:
            continue
        j_scores = [r["judge_score"] for r in subset if r["judge_score"] is not None]
        resolved = sum(1 for r in subset if r["final_resolution"] in resolved_labels)
        j_mean = sum(j_scores) / len(j_scores) if j_scores else None
        print(
            f"  {label}: n={len(subset)}, 完成率={resolved/len(subset)*100:.1f}%"
            + (f", Judge={j_mean:.2f}/100" if j_mean else "")
        )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("讀取所有 log 檔案...")
    results = analyze_all()
    print(f"共分析 {len(results)} 筆案例\n")
    print_report(results)
