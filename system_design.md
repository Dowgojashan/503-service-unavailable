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

本指南定義了從環境架構到最終學術分析的完整步驟。已完成項目標記 ✅，進行中標記 🔄，待執行標記 [ ]。

> **實際執行說明（與原始規劃的差異）**  
> - Agent 模型：`llama3.1:8b`（via Ollama 本地部署）；Judge 模型：`gemini-3.1-flash-lite`  
> - Agent 框架：自行實作（非 LangGraph），以便對 llama3.1:8b 的輸出行為做精細控制  
> - 測試規模（Phase 1）：6 個代表性案例 × 4 種架構 × 3 種客戶人格（Polite / Adversarial / VIP）= 72 次對話  
> - 客戶壓力測試方式：以「客戶人格（Persona）」取代原本規劃的 ProSA 指令變體

---

## ✅ 階段一：基礎建設與環境配置
**目標**：建立專案骨幹，確保所有組員在相同的環境下開發。

- ✅ **1.1 初始化 Git 倉庫**：建立儲存庫，依照設計文件目錄結構建立資料夾。
- ✅ **1.2 配置開發環境**：`requirements.txt` 完成，Ollama 本地模型部署完成。
- ✅ **1.3 實作工具模擬器 (Simulator)**：`src/tools/simulator.py` 完成。
    - 讀取 `data/fact_sheets.json`，依 Order ID 或 Email 查詢。
    - 實作 `query_order`、`cancel_order`、`apply_refund` 三個工具函數。
    - ToolSimulator 驗證機制：僅接受 ground truth 中的正確 ID 或 Email，錯誤參數回傳 error object。

---

## ✅ 階段二：資料準備與測試案例設計
**目標**：準備測試案例與事實清單。

- ✅ **2.1 選定 6 個代表性測試案例（Phase 1 樣本）**：

    | Case | Intent | 訂單狀態 | 難度 |
    |------|--------|----------|------|
    | CASE_001 | cancel_order | Shipped | Medium |
    | CASE_002 | change_order（item removal） | Processing | Hard |
    | CASE_015 | check_refund_policy | Shipped | Easy |
    | CASE_075 | check_payment_methods | Refunded | Easy |
    | CASE_090 | change_shipping_address | Refunded | Medium |
    | CASE_141 | delivery_options | Shipped | Easy |

- ✅ **2.2 生成事實清單 (Fact Sheets)**：`data/fact_sheets.json` 完成，每筆包含 ground truth 訂單資訊、顧客資訊與正確 intent。
- ✅ **2.3 客戶壓力測試設計（取代 ProSA 變體）**：以三種客戶人格進行壓力測試，測試客服 Agent 在不同互動模式下的穩定性：
    - `Polite`：配合驗證、直接表達需求。
    - `Adversarial（奧客）`：拒絕身分驗證一次、威脅留差評、要求超出範圍的補償。
    - `VIP`：主張特殊待遇、對政策限制提出一次例外請求。

---

## ✅ 階段三：四種 Agent 架構與客戶人格實作
**目標**：在執行層實作四種架構及客戶模擬邏輯。

- ✅ **3.1 客戶人格 (Customer Personas) 設計**：
    - `prompts/system_instructions/persona_polite.txt` ✅
    - `prompts/system_instructions/persona_adversarial.txt` ✅（已修正：移除錯誤 Order ID 注入、限制抵制次數上限）
    - `prompts/system_instructions/persona_vip.txt` ✅（新增：VIP 身份主張 + Hard Stop 終止規則）
- ✅ **3.2 統一客服業務規則 (Shared Core)**：`prompts/system_instructions/` 下各架構指令完成。
- ✅ **3.3 實作四種 Design Patterns**：
    - `src/agents/single_slot.py` ✅
    - `src/agents/react_agent.py` ✅
    - `src/agents/reflection_agent.py` ✅
    - `src/agents/plan_execute_agent.py` ✅
- ✅ **3.4 實作「客戶-客服」對話管線**：
    - `src/agents/customer_agent.py` 完成，讀取 Persona 指令與 Fact Sheet，與客服 Agent 進行多輪對話。
    - 含終止偵測：偵測客服 Agent 的結束訊號或迴圈失敗（LOOP_FAILURE）。

---

## ✅ 階段 3.5：Runner 穩健性強化（針對 llama3.1:8b 限制）
**目標**：補償 llama3.1:8b 的模型行為缺陷，確保實驗可重現。

> 此階段為執行過程中新增，原始規劃中未包含。主因是 llama3.1:8b 具有強烈的訓練先驗（Training Prior），無法單純透過 prompt 調整來糾正。

- ✅ **3.5.1 身份驗證前置攔截（Identity Guard）**：在所有架構中，若客戶未提供 Order ID 或 Email，Runner 自動攔截 tool call，強制先完成驗證。
- ✅ **3.5.2 即時合成模式（Immediate Synthesis）**：`query_order` 成功後，偵測客戶意圖關鍵字，直接由 Runner 組合回應，繞過模型的 obs_prompt 呼叫，避免：
    - 執行聾（模型忽略顧客原始問題，只播報訂單狀態）
    - 狀態描述錯誤（如 status=Refunded 卻說「已出貨」）
- ✅ **3.5.3 Reflection 模板污染偵測（Template Bleed Detection）**：偵測 Reflection 架構中模型輸出混入 scaffold 格式的情況，自動切換至程式化合成。
- ✅ **3.5.4 參數守衛（Param Guard）**：攔截模型以錯誤 Order ID（如 ORD00001）呼叫 tool 的情況，重導至 known_info 中的正確參數。
- ✅ **3.5.5 迴圈偵測（Loop Detection）**：連續兩輪出現相同回覆時，自動終止對話並標記 LOOP_FAILURE。

---

## ✅ 階段 3.6：LLM-as-a-Judge 評估器實作
**目標**：建立可解釋的評分機制。

- ✅ **3.6.1 結構化評分量表（Rubric）**：`eval/llm_judge.py` 完成，1–5 分制，三個維度：
    - Fulfillment（任務達成度，權重 50%）
    - Logic（業務邏輯遵循與事實正確性，權重 30%）
    - Tone（溝通專業度，權重 20%）
    - 換算公式：`final_score = ((F-1)/4*50) + ((L-1)/4*30) + ((T-1)/4*20)`
- ✅ **3.6.2 思維鏈評分（CoT）**：Judge 在給分前須輸出 reasoning 與 evidence，引用對話原文。
- ✅ **3.6.3 參考錨點機制（Reference-based Grading）**：呼叫 judge 時動態注入 fact_sheet 作為唯一事實來源。
- ✅ **3.6.4 JSON 格式輸出**：輸出包含 `scores`、`reasoning`、`evidence`、`final_score_0_100`，結果存入 `outputs/logs/` 及 `outputs/reports/` CSV。

---

## ✅ 階段四：Phase 1 實驗執行與基準建立
**目標**：完成 6 個案例 × 4 種架構 × 3 種 Persona 的初步實驗，確認系統可用性與基準分數。

- ✅ **4.1 Batch Runner**：`src/core/runner.py` 完成，支援任意 case × agent × persona 組合批次執行。
- ✅ **4.2 完整軌跡記錄（Trace Logging）**：每筆對話儲存為 JSON，包含 conversation turns、tool calls、token usage、judge scores。
- ✅ **4.3 Polite Persona 全架構基準**：6 cases × 4 architectures，全數達到 ≥ 60 分。

    | Case | Single-slot | PlanExecute | ReAct | Reflection |
    |------|-------------|-------------|-------|------------|
    | CASE_001 | 92.5 | 92.5 | 100.0 | 100.0 |
    | CASE_002 | 80.0 | 87.5 | 75.0 | 87.5 |
    | CASE_015 | 100.0 | 70.0 | 100.0 | 100.0 |
    | CASE_075 | 75.0 | 72.5 | 75.0 | 60.0 |
    | CASE_090 | 100.0 | 100.0 | 60.0 | 100.0 |
    | CASE_141 | 100.0 | 100.0 | 100.0 | 100.0 |

- ✅ **4.4 Adversarial Persona 全架構測試**：6 cases × 4 architectures 完成，確認奧客人格可正常驅動對話至解決。
- ✅ **4.5 VIP Persona 全架構測試**：6 cases × 4 architectures 完成，全數達到 ≥ 60 分。
- ✅ **4.6 評估指標框架整理**：`evaluation_framework.md` 完成，包含精簡後的評估架構與各議題建議。

---

## ✅ 階段五：精簡版評估指標實作
**目標**：依據 `evaluation_framework.md` 的精簡架構，將新的評估指標整合至 Runner 與 Judge。

- ✅ **5.1 更新 LLM Judge Rubric（3 維度）**：
    - Fulfillment / Logic / Tone 對應至 `S_Resolution`（50%）/ `S_Completeness`（30%）/ `S_Tone`（20%）。
    - `eval/llm_judge.py` rubric 定義與換算公式完成；judge prompt 不帶架構標籤，強制引用 final answer 原文作為 evidence。

- ✅ **5.2 實作 rule-based S_Grounding**：
    - `data/policy_ground_truth.json` 建立完成，定義每個 case 的合法政策條件。
    - `eval/metrics.py` 實作 tool observation 層（status / order_id / items / amount 比對）與 policy 層比對。
    - `S_Grounding = 100 * (passed_checks / total_applicable_checks)`

- ✅ **5.3 實作 S_Tool（F1 + Argument + ResultUsage）**：
    - `data/fact_sheets.json` 各 case 已有 `expected_tools` 欄位。
    - `eval/metrics.py` 完成 ToolPrecision / ToolRecall / F1、ArgumentCorrectness、ResultUsage 計算。

- ✅ **5.4 實作 S_Trajectory（rule-based）**：
    - 流程順序檢查、無效循環偵測、冗餘步驟計算均已實作於 `eval/metrics.py`。

- ✅ **5.5 實作 S_Efficiency**：
    - 每次對話記錄 `execution_seconds`（run2/3）及 `grand_total_tokens`（run1 fallback）。
    - 以同難度 Single-slot median 作為 baseline；支援 `--baseline-logs-dir` 指定跨架構的基準目錄（解決混合單位 bug）。

- ✅ **5.6 整合 S_Agent 最終分數計算**：
    - `S_raw = 0.35 * S_Outcome + 0.25 * S_Tool + 0.20 * S_Trajectory + 0.20 * S_Efficiency`
    - I_fatal gate：觸發則 `S_Agent = min(S_raw, 40)`

---

## ✅ 階段六（6.1）：穩定性驗證
**目標**：確認 Phase 1（6 cases × 4 architectures × 3 personas）結果可重現。

- ✅ **6.1 多次執行穩定性驗證（全部完成）**：
    - 所有組合各執行 **3 次**（run1 / run2 / run3），記錄 mean ± SD。
    - 判斷標準：SD ≤ 10 [OK]，10 < SD ≤ 20 [~]，SD > 20 [!!]

    **穩定性結果總覽：**

    | 架構 | Polite | Adversarial | VIP |
    |------|--------|-------------|-----|
    | Single-slot | ✅ 全 OK（最大 SD=9.5） | ✅ 全 OK | ✅ 全 OK（最大 SD=3.2） |
    | ReAct | ✅ 全 OK（最大 SD=4.9） | ✅ 全 OK（最大 SD=4.9） | ✅ 全 OK（最大 SD=4.3） |
    | Reflection | ✅ 5 OK, 1 [~]（CASE_090 SD=13.2） | ✅ 全 OK（最大 SD=7.1） | ✅ 5 OK, 1 [~]（CASE_075 SD=12.5） |
    | PlanExecute | ✅ 全 OK（最大 SD=6.5） | ✅ 5 OK, 1 [~]（CASE_075 SD=12.8） | ✅ 全 OK（最大 SD=3.9） |

    > 共 72 組合，70 組 [OK]，2 組 [~]（皆在允許範圍內），無 [!!]。

    > **技術補充**：ReAct / Reflection / PlanExecute 計算 S_Efficiency 時需透過 `--baseline-logs-dir` 指向對應 Persona 的 Single-slot 目錄，避免混合單位導致 S_Efficiency 崩潰。

---

## [ ] 階段六（6.2–6.4）及 Phase 2 擴大實驗

- [ ] **6.2 LLM Judge 信度驗證**：
    - 對 final score 落在 60–75 區間的 case 進行 10% 人工抽樣複核。
    - 計算 judge 與人工評分的 Spearman 相關係數，目標 ρ ≥ 0.75。
    - `eval/stability.py --judge-check` 可產生待填寫的 checklist；`--spearman` 可在填寫後計算 ρ。

- [ ] **6.3 擴大測試規模（Phase 2，150 筆）**：
    - Phase 1 穩定性驗證通過，可執行完整 150 筆測試。
    - 前置條件：確立 Task Complexity Index（見 evaluation_framework.md §6.5）後分組執行。

- [ ] **6.4 I_fatal Cap 敏感度分析**：
    - 對現有資料套用 hard zero、cap=30、cap=40、severity penalty 四種設定。
    - 比較各設定下架構 NetValue 排名是否一致，決定最終 Cap 值。
    - `eval/stability.py --sensitivity` 可執行此分析。

---

## [ ] 階段七：分析、視覺化與論文整理
**目標**：將數據轉化為論文圖表與結論。

- [ ] **7.1 計算 ProxyCost 與 NetValue**：
    - 依 `evaluation_framework.md §4.8` 公式計算各架構的 ProxyCost、NetValue、Delta_MB。
    - V_i 依任務難度設定：Easy=1, Medium=2, Hard=3。

- [ ] **7.2 S_Agent 權重敏感度分析**：
    - 比較三種權重設定（0.35/0.25/0.20/0.20、等權重 25/25/25/25、Outcome 導向 50/20/15/15）下架構排名是否一致。

- [ ] **7.3 產生結果圖表**：
    - 各難度下架構 NetValue 比較（bar chart）。
    - Trade-off Matrix（X: S_Agent, Y: ProxyCost，bubble size: Delta_MB）。
    - 各 Persona 下的架構穩定性比較（SD bar chart）。
    - 典型失敗案例整理（hallucination、LOOP_FAILURE）。

- [ ] **7.4 論文結論整理**：
    - 各難度下最適合架構的結論（以 NetValue 為主要依據）。
    - Runner 穩健性強化對實驗有效性的影響討論。
    - LLM Judge 信度驗證結果。

---

## ⚠️ 開發檢查清單 (Safety Checks)
1. **API Key 安全**：嚴禁將 API Key 上傳至 Git，請使用 `.env` 檔案（Gemini API Key 已在 `.env` 管理）。
2. **執行前驗證**：擴大規模前，務必先以 3 筆資料跑完整個流程，確認新指標計算邏輯無誤。
3. **一致性檢查**：所有 Agent 架構測試時，使用的 Tool 函數邏輯必須完全相同（Runner 統一管理工具呼叫，不由 Agent 直接呼叫）。
4. **多次執行**：Stage 6 前不要做最終結論，單次結果僅作為開發驗證用途。