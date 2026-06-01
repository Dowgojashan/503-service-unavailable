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

- ✅ **2.4 完整 In-sample 測試集統計（150 筆）**：

    **Intent 分布（共 15 種）：**

    | Intent | 筆數 | Intent | 筆數 |
    |--------|------|--------|------|
    | check_payment_methods | 20 | track_refund | 9 |
    | delivery_period | 17 | place_order | 4 |
    | set_up_shipping_address | 15 | change_order | 2 |
    | cancel_order | 14 | get_invoice | 1 |
    | delivery_options | 13 | recover_password | 1 |
    | change_shipping_address | 12 | | |
    | check_refund_policy | 11 | | |
    | get_refund | 11 | | |
    | track_order | 10 | | |
    | payment_issue | 10 | | |

    **Category 分布：**

    | Category | 筆數 |
    |----------|------|
    | REFUND | 31 |
    | ORDER | 30 |
    | PAYMENT | 30 |
    | DELIVERY | 30 |
    | SHIPPING | 27 |
    | INVOICE / ACCOUNT | 2 |

    **難度分布：** easy = 50 / medium = 50 / hard = 50（完全平衡）

    **實驗規模：** 150 cases × 4 architectures × 3 personas = **1,800 筆對話**

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
    - `S_raw = 0.50 * S_Outcome + 0.20 * S_Tool + 0.10 * S_Trajectory + 0.20 * S_Efficiency`（立場 A，以客戶為中心）
    - I_fatal gate：觸發則 `S_Agent = min(S_raw, 40)`
    - 權重敏感度驗證：969 種合法 weight 組合下 PlanExecute 排名第一（100% 穩健）

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

## ✅ 階段六（6.3）：Phase 2 擴大實驗執行
**目標**：完成 150 筆 × 4 架構 × 3 Persona 的完整實驗。

- ✅ **6.3 Phase 2 實驗全數執行完畢**：
    - 總計 **1,800 筆**對話 log（150 cases × 4 architectures × 3 personas），全數儲存至 `outputs/logs/`
    - Judge 模型：`gemini-3.1-flash-lite`，1,800 筆全數評分完成（無缺漏）
    - 執行環境：本機（Single-slot/ReAct/PlanExecute/VIP 部分）+ Kaggle / Google Colab（Reflection 大批量）

---

## ✅ 階段七（7.1–7.3）：Phase 2 結果分析
**目標**：分析 1,800 筆實驗數據，輸出各 Persona 及跨 Persona 比較報告。

> 分析結果記錄於 `result.md`。評估指標簡化為 LLM-as-Judge（Fulfillment / Logic / Tone）+ 任務完成率 + Token 成本效益，捨棄 Phase 1 的 S_Agent 複合指標（因 Phase 2 規模下 rule-based grounding 資料無法逐筆維護）。

- ✅ **7.1 Polite Persona 四架構比較**（`result.md` §1）：
    - 完成率：ReAct 99.3% ≈ PlanExecute 98.7%，Reflection 48.7% 最差
    - 品質：ReAct 66.17 > PlanExecute 63.56 > Single-slot 59.00 > Reflection 54.73
    - 成本效益：PlanExecute 42.7 質量/萬 token 最高

- ✅ **7.2 Adversarial Persona 四架構比較**（`result.md` §2）：
    - 完成率：ReAct 100%（唯一零 PENDING），PlanExecute 97.3%
    - 品質：ReAct 70.20 大幅領先，PlanExecute 63.60
    - Single-slot 在 Adversarial 下品質崩跌 -8.4 分（最不穩定）

- ✅ **7.3 VIP Persona 四架構比較**（`result.md` §3）：
    - ReAct 品質達 72.98（三個 Persona 中所有架構的最高分）
    - PlanExecute 成本效益（42.21）≈ ReAct（42.32），幾乎並列

- ✅ **7.4 跨 Persona 比較**（`result.md` §4）：
    - ReAct 品質隨 Persona 複雜度單調遞增（Polite→Adv→VIP：66→70→73）
    - PlanExecute 跨 Persona 最穩定，品質波動 < 2 分
    - 全局建議：成本優先選 PlanExecute，品質優先選 ReAct

- ✅ **7.5 Synthesis 介入率分析**（`analysis_synthesis.py`）：
    - PlanExecute 的 runner-level synthesis 介入率約 96%
    - 介入組 vs 純 LLM 組的品質與完成率差異已量化

- ✅ **7.6 敏感度分析（PSS）**（`result.md` §5）：
    - 借用 ProSA 的 PromptSensiScore 框架，以三種 Persona 作為 prompt 變體
    - PlanExecute PSS 均值最低（17.96，最穩健），Reflection 最高（28.70）
    - ReAct 完成率一致性最高（98% 案例三 Persona 均解決）

- ✅ **7.7 ProSA 任務分層分析**（`result.md` §6）：
    - PSS by Intent：`cancel_order`、`check_refund_policy` 最敏感；`change_shipping_address` 最穩健
    - PSS by Difficulty：簡單案例（difficulty=1）PSS 反而最高（反直覺）——能解決的案例才有分化空間
    - PSS vs 品質相關性：ReAct r = -0.293（最強負相關），Reflection r = -0.008（幾乎無關）

---

## 🔄 階段八：Out-of-Sample 驗證與延伸分析
**目標**：驗證系統在未見案例上的泛化能力，補強研究主張。

- ✅ **8.1 Out-of-Sample 測試集建立（50 筆）**：
    - 來源：獨立建立的 OOS 案例集（`data/oos_fact_sheets.json`），非從 in-sample case bank 抽取
    - 案例 ID：OOS_001 – OOS_050，儲存於 `data/oos_fact_sheets.json`

    **OOS Intent 分布（共 15 種，9 種為 in-sample 未出現的新意圖）：**

    | Intent | 筆數 | 是否為新意圖 |
    |--------|------|------------|
    | track_return | 10 | ✅ 新 |
    | track_order | 9 | 重疊 |
    | get_refund | 8 | 重疊 |
    | payment_issue | 4 | 重疊 |
    | cancel_order | 4 | 重疊 |
    | product_inquiry | 3 | ✅ 新 |
    | missing_item | 2 | ✅ 新 |
    | installation_request | 2 | ✅ 新 |
    | check_payment_methods | 2 | 重疊 |
    | return_request | 1 | ✅ 新 |
    | fraud_dispute | 1 | ✅ 新 |
    | exchange_request | 1 | ✅ 新 |
    | change_order | 1 | 重疊 |
    | cancel_return | 1 | ✅ 新 |
    | check_warranty | 1 | ✅ 新 |

    **OOS Category 分布：**

    | Category | 筆數 | 備註 |
    |----------|------|------|
    | ORDER | 17 | 與 in-sample 重疊 |
    | RETURNS | 15 | ✅ in-sample 無此 category |
    | REFUND | 8 | 與 in-sample 重疊 |
    | PAYMENT | 6 | 與 in-sample 重疊 |
    | PRODUCT | 4 | ✅ in-sample 無此 category |

    **OOS 難度分布：** easy = 15 / medium = 17 / hard = 18（接近平衡）

    **泛化測試設計說明：**
    - 6 個重疊 intent：測試相同任務類型的 OOS 泛化
    - 9 個全新 intent：測試架構面對未見任務類型的處理能力
    - RETURNS / PRODUCT 兩個全新 category：測試跨領域泛化

- ✅ **8.2 Out-of-Sample 實驗執行**：
    - 執行 50 cases × 4 architectures × 3 personas = **600 筆**（全數完成）
    - Log 儲存路徑：`outputs/logs/outsample/{Persona}/{Agent}/`
    - 執行環境：本機（Single-slot / PlanExecute）+ Google Colab + Kaggle（Reflection × Adversarial）
    - 批次執行腳本：`run_oos_batch.py`（含 `--start` / `--end` 參數，支援分段執行與 checkpoint 續跑）
    - **Judge 補評**：15 筆因 Gemini 503 錯誤缺評分，透過 `rejudge_missing.py` 全數補齊；600 筆 judge 分數完整無缺漏

- ✅ **8.3 Out-of-Sample 結果比較**（結果記錄於 `result.md` OOS 章節）：

    **OOS S_Agent 排名：**

    | 架構 | Polite | Adversarial | VIP | 整體 | vs In-sample |
    |------|--------|-------------|-----|------|-------------|
    | PlanExecute | 73.8 | 71.4 | 74.4 | **73.2** | ▲+1.2 |
    | Single-slot | 69.6 | 68.6 | 71.6 | **70.0** | ▼-5.5 |
    | ReAct | 68.3 | 64.6 | 64.6 | **65.8** | ▼-7.9 |
    | Reflection | 53.3 | 61.1 | 68.0 | **60.8** | ▼-7.9 |

    - **架構排名一致**：PlanExecute 在 OOS 仍排名第一，且是唯一 S_Agent 不降反升的架構
    - **泛化失敗確認**：LLM Judge 分數全面崩跌（OOS 範圍 22–38 vs In-sample 51–73），肇因為 9 個未見 intent
    - **PE Synthesis 悖論**：PlanExecute Immediate Synthesis 對新 intent 生成通用模板回應 → completion rate 最高（98%）但 Judge 最低
    - **ReAct LOOP 爆炸**：OOS Polite 下 LOOP_FAILURE 率 42%（21/50），新 intent 導致 Reason-Act 循環不收斂

    **OOS 權重敏感度分析（969 種合法組合）：**
    - PlanExecute 排名第一的比例：99.9%（968/969）；唯一例外在 W_Trajectory=0.85 時 Single-slot 勝出

    **OOS ProSA PSS 分析（跨 Persona 穩定性）：**

    | 架構 | PSS 均值 | 穩定性排名 |
    |------|---------|----------|
    | ReAct | 17.20 | 最穩定 |
    | PlanExecute | 18.33 | 第二 |
    | Reflection | 20.13 | 第三 |
    | Single-slot | 20.87 | 最不穩定 |

- [ ] **8.4 ProSA 四變體實驗（選擇性）**：
    - `data/prosa_variants.json` 已備妥 150 cases × 4 變體（simple_input / emotional_support / role_player / output_requirement）
    - 若執行：選 2 個架構（建議 ReAct + PlanExecute）× 50 cases × 4 variants = 400 筆
    - 計算原版 instruction-level PSS，與 persona-level PSS 對照

---

## 🔄 階段九：視覺化與論文整理
**目標**：將數據轉化為可發表的圖表與論文結論。

- [ ] **9.1 產生結果圖表**：
    - 三 Persona 下四架構完成率與 Judge 分比較（grouped bar chart）
    - PSS 分布圖（各架構 violin/box plot）
    - Intent 分層 PSS 熱力圖（架構 × intent）
    - 成本效益散點圖（X: Token，Y: Judge，bubble: 完成率）

- [ ] **9.2 LLM Judge 信度驗證**：
    - 對 final score 落在 60–75 區間的 case 進行 10% 人工抽樣複核
    - 計算 Spearman ρ（目標 ≥ 0.75）

- ✅ **9.3 論文方法論部分撰寫**（`final_project.md` §1 Methodologies）：
    - §1.1 Research Design Overview（1,800 in-sample + 600 OOS）
    - §1.2 Simulated Dialogue Environment（llama3.1:8b、Fact Sheet、Tool Simulator、history[-8:]）
    - §1.3 四種 CSR Agent 架構（Single-slot OPTION A/B/C、ReAct max 5 iter、Reflection 3-phase、PlanExecute Immediate Synthesis）
    - §1.4 三種顧客 Persona（Polite / Adversarial / VIP 及行為約束）
    - §1.5 S_Agent 指標與公式（sub-score 表、I_fatal cap）
    - §1.6 LLM-as-Judge（Gemini 盲測、3 維度、4-step CoT）
    - §1.7 實驗設計（in-sample 150 cases、OOS 50 cases、checkpoint-resume）
    - §1.8 權重敏感度分析（969 種合法組合）

- [ ] **9.4 論文 Results 章節（`final_project.md` §2）**：
    - In-sample 四架構全 Persona 定量結果表
    - OOS 泛化結果（S_Agent、Judge、LOOP率）
    - 權重敏感度與 ProSA PSS 摘要

- [ ] **9.5 論文 Analysis and Discussion（`final_project.md` §3）**：
    - 各 Persona 下最適架構建議（ReAct vs PlanExecute 取捨原則）
    - PE Synthesis 悖論分析（高完成率 vs 低 Judge 的解釋）
    - PSS / ProSA 分析對架構選擇的啟示
    - 對未來研究的建議（公平 prompt 控制、更大規模模型測試）

---

## ⚠️ 開發檢查清單 (Safety Checks)
1. **API Key 安全**：嚴禁將 API Key 上傳至 Git，請使用 `.env` 檔案（Gemini API Key 已在 `.env` 管理）。
2. **執行前驗證**：擴大規模前，務必先以 3 筆資料跑完整個流程，確認新指標計算邏輯無誤。

---

## 附錄 A：四種 Agent 架構設計細節

> 對應實作：`src/agents/`、`src/core/runner.py`、`prompts/system_instructions/`

所有架構共用相同的 **底層 LLM**（`llama3.1:8b`，Ollama 本機運行）與相同的 **system instruction 基底**（`common.txt`，定義身分驗證規則、可用工具白名單、Anti-hallucination 規則）。各架構的差異在於推理框架（scaffold）以及 runner 如何與 agent 互動。

---

### A.1 Single-slot

**設計理念**：每個 turn 只做一次 LLM 呼叫，但帶完整的對話歷史（full context window）。作為 baseline，代表「不帶任何推理框架的 zero-shot 表現」。

**Prompt 結構**（`single_slot.py`）：

每次 `run()` 呼叫，直接組裝一個包含三個 OPTION 的 decision prompt，要求 LLM 選擇唯一一個輸出：

```
OPTION A — 已有 Order ID/Email 且需查詢訂單 → 輸出 Action: query_order(...) 後停止
OPTION B — 尚未拿到 Order ID/Email → 向顧客詢問
OPTION C — 已收到 Observation，需要 follow-up action → 輸出下一個 Action 後停止
```

**Tool 執行機制**：

由 `runner.py` 的「Single-slot Intercept」層處理：
1. LLM 輸出 `Action: tool_name(args)` 格式
2. runner 截取該行，呼叫 `ToolSimulator` 執行，取得 observation
3. 將 `Observation: {...}` 注入回下一輪的 user prompt

**歷史管理**：`BaseAgent._call_llm()` 保留最近 8 筆對話記錄（`history[-8:]`），超出後自動截斷，避免 context overflow。

**主要限制**：
- 沒有 Thought 步驟，LLM 直接決策，容易在複雜情境下跳步（例如先 cancel 再 query）
- 對 llama3.1:8b 而言，OPTION 選擇容易輸出多餘的 meta-talk（觸發 runner 的 meta-talk guard 重試）
- 不具備計畫能力，每個 turn 是獨立決策

---

### A.2 ReAct（Reason + Act）

**設計理念**：強制 LLM 在每個 turn 先輸出 `Thought:`（內部推理），再輸出 `Action:` 或 `Final Answer:`。推理過程對顧客不可見，但記錄在 `full_trace` 中供評估。

**Scaffold 規則**（`react_scaffold.txt`）：

每個 turn 的輸出結構必須是以下兩種之一：
```
Thought: [內部推理]
Action: tool_name(param="value")    ← 輸出後立刻停止

— 或 —

Thought: [內部推理]
Final Answer: [給顧客的回覆]
```

**三步決策協議**（Decision Protocol）：
1. 對話歷史中是否有 Order ID/Email？→ 否：詢問；是：Step 2
2. 本對話是否已有 query_order 的 Observation？→ 否：必須先呼叫 query_order；是：Step 3
3. 顧客明確要求什麼？→ 根據 intent 決定對應 action（cancel/refund/track）或 Final Answer

**Runner 互動（Atomic Loop）**：

Runner 的 `while ... react_iter < 5` 循環處理一個 turn 內的多次 tool call：
1. 偵測 `Action:` → 執行工具 → 注入 `Observation:` → 繼續循環
2. 偵測 `Final Answer:` → 跳出循環，輸出給顧客
3. 達到上限（5 次）→ 強制結束，避免無限循環

**主要 Guards（runner.py 實作）**：
- **Guard 1**：顧客尚未提供任何 ID → 阻止所有 tool call
- **Guard 2**：有 ID 但未執行 query_order → 強制第一個 action 為 query_order
- **Consent Guard T1**：顧客從未在對話中提到取消/退款相關字眼 → 阻止 cancel_order / apply_refund
- **Consent Guard T2**：顧客目前訊息有拒絕信號 → 阻止 action tool
- **DEDUP Guard**：同一 turn 同一工具只能呼叫一次；重複呼叫時依 intent 做 programmatic synthesis

---

### A.3 Reflection（ReAct + Self-Reflection）

**設計理念**：在 ReAct 的基礎上增加自我審視步驟。LLM 輸出「初稿 → 反思 → 最終回覆」三階段，讓模型有機會在給顧客答案之前自我修正。

**Scaffold 結構**（`reflection_scaffold.txt`）：

```
Initial Draft: [第一版回覆草稿]
Reflection: [審視草稿：有沒有錯誤？邏輯是否完整？]
Final Response: [修正後的最終回覆]
```

**Tool Call 格式**（與 ReAct 不同）：

Reflection 使用 `[Tool Call: tool_name(param)]` 格式（方括號），而非 `Action:` 格式：
```
[Tool Call: query_order(oos001@example.com)]
```

**Runner 互動（Reflection Atomic Loop）**：

`while agent_type == "Reflection" and reflection_iter < 3:` 循環：
1. 偵測 `[Tool Call: ...]` → 執行工具 → 注入 observation → `service_agent.run(obs_prompt)` → 繼續循環
2. 偵測 `Final Response:` → 提取文字，清除所有 `Initial Draft:` / `Reflection:` 標題後輸出
3. 若回應不完整（無 Tool Call 也無 Final Response）→ 最多重試 3 次

**Programmatic Synthesis（Template Bleed 補救）**：

當 llama3.1:8b 把 scaffold 範例直接輸出（template bleed，如輸出 `Turn 1 (Customer:...` 之類的範例文字），runner 偵測後跳過 LLM，改用規則直接組裝回應（同 PlanExecute 的 synthesis 邏輯）。

**主要限制**：
- 三階段輸出消耗較多 tokens，在 8192-token context 限制下容易 overflow
- Reflection 的自我修正有時會帶入幻覺（auditing 一個沒有問題的回答，反而引入新錯誤）

---

### A.4 Plan-and-Execute

**設計理念**：將「規劃」與「執行」明確分離。LLM 先輸出完整計畫（Plan），再在 Execution 階段逐步執行，確保每一步行動有明確依據。

**Scaffold 結構**（`plan_execute_scaffold.txt`）：

```
**Plan**
1. [步驟 1]
2. [步驟 2]
...

**Execution**
Action: tool_name(param="value")    ← 輸出後停止

— 或 —

Final Response: [給顧客的訊息]
```

**Immediate Synthesis 機制**：

PlanExecute 是唯一架構使用「Immediate Synthesis」——在 `query_order` 成功後，runner **直接根據 observation 資料組裝回應，不再呼叫 LLM**。這補償了 llama3.1:8b 在取得 observation 後仍會產生幻覺（narrating order data, topic pivoting）的問題。

觸發條件（`runner.py` 第 1205 行區域）：
- 顧客意圖為資訊查詢（非 transactional）→ 根據 intent keywords 選擇對應的預設回覆模板
- 顧客意圖為 cancel/refund → 執行對應工具，合成結果文字

**PlanExecute Guard**（`runner.py`）：

若 query_order 已成功，LLM 再次嘗試呼叫 query_order → runner 注入 cached observation，跳過重複查詢。

**為何 PlanExecute 在 S_Agent 排名最高**：

Plan 步驟強迫 LLM 在行動前先宣告意圖，降低了跳步和幻覺的機率；Immediate Synthesis 確保 observation 後的回應準確；PlanExecute S_Trajectory 得分最高（99.4），反映推理軌跡的高度一致性。

---

## 附錄 B：三種顧客 Persona 設計細節

> 對應實作：`src/agents/customer_agent.py`、`prompts/system_instructions/persona_*.txt`

顧客 Simulator 統一由 `CustomerAgent`（繼承 `BaseAgent`）實作，使用相同的 llama3.1:8b。三種 persona 的差異完全由不同的 `persona_instruction`（system prompt）控制，核心邏輯（不洩漏 ID、提供 email 優先、堅持目標但接受現實）由 `customer_agent.py` 的共用規則統一管理。

---

### B.1 Polite（禮貌合作型）

**設計目標**：模擬標準電商客服情境的典型顧客，提供穩定、可控的基準測試環境。

**關鍵行為規則**：
- 開場不提供 Order ID 或 Email，只描述問題類型
- 被詢問後立刻提供 Email（或 Order ID）
- 對 agent 的每個回覆給予合理的善意解讀
- 問題解決後真誠道謝，禮貌結束

**對話終止條件**：
- 問題已解決 → 感謝語 + 再見
- agent 重複說明同一限制兩次 → 接受現實，禮貌結束

**Stress Test 價值**：提供「最佳情境」基準，測試 agent 在無干擾下的純技術表現。

---

### B.2 Adversarial（不合作對抗型）

**設計目標**：測試 agent 在高壓、對抗性對話下的穩定性與合規性。

**關鍵行為規則**：
- **抵抗驗證（僅一次）**：agent 第一次要求 ID 時，顧客拒絕（「你不是應該查得到嗎？」）；但第二次必須提供，不能無限拒絕
- **威脅行為（限範圍內）**：可以威脅負面評論或要求退款，但只能要求系統支援的操作（cancel/refund），不能要求折扣或補償
- **每個限制只抱怨一次**：agent 重複說明限制兩次後，Adversarial 顧客接受現實，以不滿的語氣結束（「我再考慮要不要留負評」）

**設計約束**：
- Adversarial 不能無限升級——設有「只抵抗一次、只威脅一次、接受現實」的明確規則，確保對話在 6 turn 內可以結束
- 這使得 agent 必須在高壓下仍保持流程正確，而不是因顧客讓步而「假過關」

**對 S_Agent 的影響**：Adversarial persona 下 S_Efficiency 普遍較低（turn 數較多），但 S_Tone 評分差異最能反映架構間的差距。

---

### B.3 VIP（高期待 VIP 型）

**設計目標**：測試 agent 在面對「有正當資格感但非惡意」顧客時的處理能力。

**關鍵行為規則**：
- **VIP 開場**：第一句提及自己的 VIP 身分，期待優先且順暢的服務
- **身分驗證的輕微不適**：表示「我以為 VIP 資料應該已經在系統裡了」，但仍提供 Email
- **VIP 特例申請（僅一次）**：若 agent 說某事無法做，VIP 顧客引用自己的身分請求特例（「我是長期 VIP 顧客，這能不能為我通融？」）；若 agent 再次拒絕，接受
- **平靜結束**：問題解決 → 「好，這才是我期待的服務水準。謝謝。」；未解決 → 「我很失望，需要重新考慮 VIP 方案的價值。」
- **Hard Stop**：說完結語後，若 agent 再傳訊息，VIP 只回「Goodbye.」並完全停止

**設計細節**：VIP persona 的「特例申請」設計用來測試 agent 是否會因身分壓力而違反系統規則（例如在不符合條件時仍承諾退款）。這是 I_fatal 違規的潛在觸發點。

---

### B.4 CustomerAgent 共用控制機制

無論哪種 persona，`customer_agent.py` 都套用以下共用規則：

| 規則 | 實作 |
|------|------|
| 第一句不洩漏 ID | `persona.txt` + customer agent prompt |
| 被問到才提供 Email | `customer_agent.py` prompt 明確指示 |
| 不憑空捏造訂單事實 | `system_instruction` 注入 fact sheet 的 items/amount/email |
| turn ≥ 4 後接受現實 | `customer_agent.py` 第 95–104 行的 acceptance_note 機制 |
| 不說 CSR 用語 | 兩份 prompt 的 FORBIDDEN PHRASES 清單 |
| 終止信號 | 目標達成或限制被說明兩次後，說再見並停止 |

**Fact Sheet 注入格式**：

```
WHAT YOU KNOW ABOUT YOUR ORDER:
Your order contains EXACTLY 1 item(s): Product_44.
The total order amount is $63.41.
Your name is John Smith and your registered email is case001@example.com.
Provide email only when the agent explicitly asks for it.
```

這確保顧客不會憑空說出「keep most of the items」（當只有 1 件商品時），也不會報錯誤的訂單金額。
3. **一致性檢查**：所有 Agent 架構測試時，使用的 Tool 函數邏輯必須完全相同（Runner 統一管理工具呼叫，不由 Agent 直接呼叫）。
4. **多次執行**：Stage 6 前不要做最終結論，單次結果僅作為開發驗證用途。