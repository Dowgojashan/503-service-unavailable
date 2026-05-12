# 電商 AI Agent 成本效益分析實驗系統設計文件

本文件整理了專案的技術棧、垂直系統架構以及檔案目錄結構，旨在建立一個具備學術嚴謹性（基於 ProSA 框架）且可高度擴展的 AI Agent 測試環境。

---

## 🛠 1. 技術棧與開發工具 (Technology Stack)

系統核心採用 **Python** 進行開發，利用其強大的 AI 生態系達成自動化實驗。

| 層級 | 推薦技術 / API |
| :--- | :--- |
| **核心語言** | **Python 3.10+** |
| **LLM 模型** | **gemma3-27b-it** |
| **Agent 框架** | **LangGraph** (推薦，適合實作有狀態的 Reflection 與 P&E) 或 LangChain |
| **資料處理** | **Pandas** (CSV 處理), **JSON** (事實清單管理) |
| **API 異步處理** | **asyncio** (加速 150 筆批次測試) |
| **指標統計** | **NumPy** (計算 PSS), **Matplotlib/Seaborn** (權衡矩陣視覺化) |

---

## 🏗 2. 垂直系統架構 (Vertical Architecture)

實驗系統分為五層，資料由上而下流動，確保「事實（Ground Truth）」與「執行邏輯」解耦。

1.  **資料層 (Data Layer)**：儲存 150 筆測試案例的 Fact Sheets 與 ProSA 四維度提示詞變體。
2.  **調度層 (Orchestration Layer)**：Batch Runner 自動遍歷測試案例；Agent Factory 根據實驗設定生產指定架構（如 ReAct）。
3.  **執行層 (Agent Execution Layer)**：實作四種設計模式（Single-slot, ReAct, Reflection, P&E），進行推理與決策。
4.  **模擬層 (Simulation Layer)**：本地 Tool API Simulator 根據 Agent 請求，從 Fact Sheets 檢索並回傳真實數據。
5.  **評估層 (Evaluation Layer)**：包含主觀評分（LLM-as-a-Judge）與客觀數據統計（Token 成本、延遲、邏輯正確率）。

---

## 📁 3. 專案目錄結構 (Folder Structure)

```text
ecommerce-agent-eval/
├── data/                  # 1. 資料層 (Data Layer)
│   ├── raw_bitext.csv           # 原始資料
│   ├── selected_samples_150.csv # 篩選後的 150 筆測試集
│   └── fact_sheets.json         # 產生的自動化事實清單 (Ground Truth)
│
├── prompts/               # 提示詞管理 (Prompts Management)
│   ├── prosa_templates.yaml     # ProSA 四種語氣模板 (Simple, Role, etc.)
│   └── system_instructions/     # 各架構的核心指令 (Shared Core)
│       ├── common.txt           # 共享業務邏輯
│       ├── react_scaffold.txt   # ReAct 專用格式指令
│       └── reflection_scaffold.txt
│
├── src/                   # 核心程式碼 (Source Code)
│   ├── agents/            # 3. 執行層 (Agent Execution Layer)
│   │   ├── __init__.py
│   │   ├── base.py              # Agent 基底類別
│   │   ├── single_slot.py       # 單次呼叫模式
│   │   ├── react_agent.py       # ReAct 模式
│   │   ├── reflection_agent.py  # 反思模式
│   │   └── plan_execute_agent.py# 規劃與執行模式
│   │
│   ├── tools/             # 4. 模擬層 (Simulation Layer)
│   │   └── simulator.py         # 對接 Fact Sheets 的工具模擬器
│   │
│   └── core/              # 2. 調度層 (Orchestration Layer)
│       ├── factory.py           # Agent 生成工廠
│       └── runner.py            # 批次自動化執行主程式
│
├── eval/                  # 5. 評估層 (Evaluation Layer)
│   ├── llm_judge.py             # GPT-4o 裁判評分邏輯
│   ├── metrics.py               # 成本 (Token) 與延遲統計
│   └── prosa_analyzer.py        # PSS (提示詞敏感度) 指標計算
│
├── outputs/               # 實驗輸出紀錄
│   ├── logs/                    # 每一筆對話的完整 Trace (JSON)
│   └── reports/                 # 統計圖表、PSS 報告、Trade-off 矩陣
│
├── requirements.txt       # 套件依賴清單
└── main.py                # 系統啟動入口


# 🚀 電商 AI Agent 實驗開發全流程指南

本指南定義了從環境架構到最終學術分析的完整步驟，請團隊成員依照階段執行。

---

## 📅 階段一：基礎建設與環境配置 (Week 1)
**目標**：建立專案骨幹，確保所有組員在相同的環境下開發。

- [ ] **1.1 初始化 Git 倉庫**：建立 `ecommerce-agent-eval` 儲存庫，並依照設計文件的目錄結構建立資料夾。
- [ ] **1.2 配置開發環境**：撰寫 `requirements.txt`（包含 `langchain`, `langgraph`, `openai`, `pandas`, `tiktoken` 等）。
- [ ] **1.3 實作工具模擬器 (Simulator)**：撰寫 `src/tools/simulator.py`。
    - 確保能讀取 `data/fact_sheets.json`。
    - 實作 `query_order`, `track_shipping`, `apply_refund` 等模擬函數。

---

## 🧪 階段二：資料預處理與 ProSA 指令變體生成
**目標**：準備好具備學術嚴謹性的 150 筆「多維度指令」。

- [ ] **2.1 資料抽樣**：執行 Python 腳本從 Bitext 挑選 150 筆平衡難度與領域的資料。
- [ ] **2.2 生成事實清單 (Fact Sheets)**：確保每一筆案例都有對應的正確資訊。
- [ ] **2.3 產生 ProSA 任務變體 (Task Variants)**：
    *針對同一項任務，利用 ProSA 框架產生四種「輸入指令」變體，測試客服 Agent 的穩定性：*
    - `Simple Input`: 「我想查詢訂單 ORD123 的狀態。」
    - `Emotional Support`: 「這件衣服是我明天要穿的，真的很急，請幫我查 ORD123。」
    - `Role Player`: 「身為你們的 VIP 會員，我要求立即確認 ORD123 的物流。」
    - `Output Requirement`: 「請查詢 ORD123 並以表格形式回覆我。」

---

## 🤖 階段三：四種 Agent 架構與「客戶人格」模擬實作
**目標**：在執行層中，不僅實作四種架構，還要實作「模擬客戶」的行為邏輯。

- [ ] **3.1 客戶人格 (Customer Personas) 指令設計**：
    *這部分是在模擬與客服對話的「那個人」，用於壓力測試：*
    - `Polite Customer`: 語氣客氣，會主動配合提供 Email 或單號。
    - `Adversarial Customer (奧客)`：語氣惡劣、不耐煩，甚至會故意提供錯誤資訊或拒絕核對身分。
- [ ] **3.2 統一客服業務規則 (Shared Core)**：在 `prompts/system_instructions/common.txt` 定義所有模式通用的客服規則。
- [ ] **3.3 實作四種 Design Patterns**：
    - Single-slot, ReAct, Reflection, Plan-and-Execute。
- [ ] **3.4 實作「客戶-客服」對話管線**：
    - 讓「客戶 Agent」讀取 Personas，與「客服 Agent」進行多輪對話，直到問題解決或失敗。

---

## 🏃 階段四：自動化實驗執行 (Week 3)
**目標**：大規模跑完測試，收集原始數據。

- [ ] **4.1 開發 Batch Runner**：在 `src/core/runner.py` 撰寫異步執行腳本。
    - 需遍歷：150 筆案例 × 4 種架構 × 4 種 ProSA 變體 = 2,400 次測試（若預算有限可先縮減樣本）。
- [ ] **4.2 紀錄完整軌跡 (Trace Logging)**：
    - 每一筆測試結果存為 JSON，放在 `outputs/logs/`。
    - 必須紀錄：Input, Thought steps, Tool calls, Final response, Token Usage。

---

## 📊 階段五：評估、分析與視覺化 (Week 4)
**目標**：將數據轉化為論文與簡報中的圖表。

- [ ] **5.1 執行 LLM-as-a-Judge**：
    - 執行 `eval/llm_judge.py`。
    - 使用 gemma3-27b-it 讀取 Log 與 Fact Sheet，給出 0-100 的品質分 ($S_{Judge}$)。
- [ ] **5.2 計算硬數據指標**：
    - 計算各模式的平均 Token 成本 ($C$) 與延遲 ($L$)。
    - 統計邏輯達成率 ($A_{logic}$)：例如「是否正確核對了 Email」。
- [ ] **5.3 ProSA 敏感度分析**：
    - 執行 `eval/prosa_analyzer.py` 計算 PSS 分數。
- [ ] **5.4 產生結果圖表**：
    - 繪製 **Trade-off Matrix** (X: 品質, Y: 成本, 氣泡大小: PSS)。
    - 整理失敗案例（如 Over-reflection 截圖）。

---

## ⚠️ 開發檢查清單 (Safety Checks)
1. **API Key 安全**：嚴禁將 API Key 上傳至 Git，請使用 `.env` 檔案。
2. **Token 監控**：執行 150 筆大樣本前，務必先用 3 筆資料跑完整個流程，確認計費與邏輯無誤。
3. **一致性檢查**：所有 Agent 在測試時，使用的工具（Tools）邏輯必須完全相同。