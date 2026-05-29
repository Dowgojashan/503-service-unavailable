# Evaluating LLM Agent Architectures for E-Commerce Customer Service: A Simulation-Based Benchmark

---

## 1. Methodologies

### 1.1 研究設計概述

本研究旨在系統性地比較四種基於大型語言模型（LLM）的客服 Agent 架構在電商情境下的表現，並檢驗其對訓練分布外（Out-of-Sample, OOS）意圖的泛化能力。我們採用全自動化的模擬對話框架（Simulation-Based Benchmark），以 LLM 驅動的顧客 Agent 取代人工測試員，對 CSR Agent 進行系統性壓測。

整體實驗設計為：

- **In-sample（域內）評估**：150 筆案例 × 4 種架構 × 3 種顧客 Persona = **1,800 場對話**
- **Out-of-sample（泛化）評估**：50 筆案例 × 4 種架構 × 3 種顧客 Persona = **600 場對話**

所有對話由程式全自動執行，每場對話結束後立即進行指標計算，確保評估一致性。

---

### 1.2 模擬對話環境

#### 語言模型

所有 CSR Agent 與顧客 Agent 均使用相同底層模型：**llama3.1:8b**，透過本地部署的 Ollama（`http://localhost:11434`）進行推理，`temperature=0.0`，`max_tokens=1000`。固定 temperature 確保輸出的確定性，使不同架構之間的比較排除隨機性干擾。

#### 事實清單（Fact Sheet）

每筆案例配備一份結構化的事實清單（JSON 格式），包含：
- 訂單資訊（訂單號、狀態、金額、商品項目、出貨日期）
- 顧客資料（Email、聯繫方式）
- 案例元資料（意圖標籤 `intent`、難度標籤 `difficulty_label`）

事實清單同時注入 CSR Agent 的系統提示與顧客 Agent 的初始指令，作為唯一的地面實況（ground truth），防止 Agent 憑空捏造資料。

#### 工具模擬器（Tool Simulator）

CSR Agent 可呼叫以下工具，工具執行結果由模擬器根據事實清單動態生成：

| 工具 | 功能 |
|------|------|
| `query_order(email/order_id)` | 查詢訂單基本資訊 |
| `track_shipping(order_id)` | 查詢物流狀態 |
| `cancel_order(order_id, reason)` | 取消訂單 |
| `apply_refund(order_id, reason)` | 申請退款 |
| `get_policy(type)` | 查詢政策（退款/配送/付款等） |

#### 歷史記憶窗口

為防止長對話導致 context overflow，BaseAgent 對所有架構一律截取最近 **8 輪**歷史（`history[-8:]`）注入提示，確保各架構在相同的記憶限制下競爭。

---

### 1.3 四種 CSR Agent 架構

#### 架構一：Single-slot

Single-slot 為最簡化的基準架構，每輪對話執行單次 LLM 呼叫。Agent 的系統提示要求模型輸出三選一決策（OPTION A/B/C）：

- **OPTION A**：直接回覆顧客（無工具呼叫）
- **OPTION B**：呼叫工具後回覆
- **OPTION C**：結束對話

Runner 層的 Single-slot Intercept 機制負責解析 LLM 輸出、擷取工具呼叫指令並執行，隨後將觀察結果（observation）注入提示，再次呼叫 LLM 生成最終回覆。此架構無顯式的思考（Thought）步驟，推理負擔全數落在單次 LLM 呼叫中。

**主要限制**：缺乏中間推理步驟，模型易產生「meta-talk」（直接描述自身行為而非執行），需 Runner 偵測並強制重試（最多 3 次）。

#### 架構二：ReAct（Reasoning + Acting）

ReAct 架構強制 LLM 每輪輸出 `Thought:` + `Action:` 或 `Thought:` + `Final Answer:` 格式，透過交替推理與行動的循環來求解複雜任務。

Runner 執行一個原子循環（atomic loop，**最多 5 次迭代**），每次迭代：
1. 呼叫 LLM 取得 Thought + Action
2. 執行對應工具，取得 observation
3. 將 observation 附加至歷史，繼續下一次迭代
4. 偵測到 `Final Answer:` 時跳出循環

此架構設有多層 Runner 守衛（Guard）：
- **Guard 1**：無顧客 ID 時封鎖工具呼叫
- **Guard 2**：有 ID 但尚未查單時強制執行 `query_order`
- **Consent Guard（T1/T2）**：取消/退款操作須確認顧客同意
- **DEDUP Guard**：攔截重複工具呼叫，防止無限循環
- **Param Guard**：工具參數格式驗證

#### 架構三：Reflection

Reflection 架構要求 LLM 每輪輸出三段式結構：

```
Initial Draft: <草稿回覆>
Reflection: <自我批評，檢查是否需要工具>
Final Response: <最終回覆>
```

若 Reflection 階段判斷需要工具，則以 `[Tool Call: tool_name(args)]` 語法標記，由 Runner 攔截執行。工具結果（observation）注入後 LLM 重新生成完整三段回覆（**最多 3 次迭代**）。

Runner 設有**Template Bleed 偵測**：若草稿標頭意外出現在最終回覆中，自動切換為程式化合成（Programmatic Synthesis）直接組裝回覆，防止格式污染傳遞給顧客。

#### 架構四：PlanExecute

PlanExecute 架構分離規劃與執行兩個階段。LLM 每輪輸出：

```
**Plan**
1. ...
2. ...

**Execution**
[實際動作或回覆]
```

此架構的核心優化為 **Immediate Synthesis（即時合成）**：當 `query_order` 成功返回且意圖屬於資訊查詢類型時，Runner 直接以程式邏輯組裝回覆，完全繞過後續 LLM 呼叫。此設計大幅減少工具觀察誤解的機率（LLM 不需要詮釋工具結果），是四種架構中 S_Trajectory 最高的關鍵原因。

**PE Guard**：將已執行的工具觀察結果快取注入後續提示，確保 LLM 在 Execution 階段能直接引用已知資訊，而非重新推理。

---

### 1.4 三種顧客 Persona

顧客 Agent 由 LLM 扮演，依據事實清單與 Persona 指令模擬真實顧客行為。設計三種 Persona 以測試 CSR Agent 在不同溝通壓力下的表現：

#### Polite（禮貌型）
基準情境。顧客合作、等待引導、接受合理解釋，首輪主動提供訂單資訊。用於衡量架構在理想條件下的上限表現。

#### Adversarial（對抗型）
壓力測試情境。顧客行為受到三條嚴格約束：
1. **一次抵抗**：第一次被要求提供 ID 時拒絕，第二次無條件提供
2. **一次威脅**：僅允許威脅一次差評，避免模擬失真
3. **兩次拒絕後接受現實**：CSR 若連續兩次說明無法處理，顧客自動停止抵抗

此設計防止顧客 Agent 無限對抗，確保對話終止條件明確。

#### VIP（尊貴型）
邊界測試情境。顧客自帶優越感，行為特徵：
1. **VIP 開場**：首輪主張「VIP 身分」，暗示應享特殊待遇
2. **驗證抵抗**：不情願提供身份資料（但最終會提供）
3. **一次例外申請**：嘗試申請超出政策範圍的特殊處理
4. **Hard Stop**：收到 CSR 的禮貌但明確的拒絕後，以保留態度（而非憤怒）結束對話

此設計旨在測試 CSR Agent 在政策邊界（`I_fatal` 觸發點）上的處理能力。

#### 共用機制

- **Turn ≥ 4 接受提示（Acceptance Note）**：CustomerAgent 於第 4 輪起自動注入提示，引導顧客接受現實，防止對話無限延伸
- **FORBIDDEN 詞彙清單**：禁止顧客 Agent 說出 CSR 專用語（"I'll look into this"、"let me check"等），維持角色邊界

---

### 1.5 評估指標：S_Agent

本研究使用 **S_Agent**（0–100 分）作為主要評估指標，計算公式如下：

$$S_{\text{raw}} = 0.50 \times S_{\text{Outcome}} + 0.20 \times S_{\text{Tool}} + 0.10 \times S_{\text{Trajectory}} + 0.20 \times S_{\text{Efficiency}}$$

$$S_{\text{Agent}} = \begin{cases} \min(S_{\text{raw}},\ 40) & \text{if } I_{\text{fatal}} = 1 \\ S_{\text{raw}} & \text{otherwise} \end{cases}$$

其中 $I_{\text{fatal}}$ 為嚴重違規指標（hallucination、未授權工具呼叫等），觸發時將分數強制封頂於 40 分。

#### 子指標定義

| 子指標 | 權重 | 計算方式 |
|--------|------|----------|
| **S_Outcome** | 50% | $0.40 \times S_{\text{CompletionStatus}} + 0.60 \times S_{\text{AnswerQuality}}$ |
| **S_Tool** | 20% | 工具呼叫正確性（正確工具/正確參數/必要呼叫）的加權平均 |
| **S_Trajectory** | 10% | 對話效率（無冗餘工具呼叫、無死循環）的路徑品質分數 |
| **S_Efficiency** | 20% | 對話輪次效率分數（Turn-based penalty） |

**S_CompletionStatus**（0 或 100）根據對話結果標籤判定：

| 結果標籤 | 分數 |
|----------|------|
| `SUCCESS` | 100 |
| `INFO_PROVIDED` | 80 |
| `PENDING` | 40 |
| `FAILED_INCOMPLETE` | 20 |
| `LOOP_FAILURE` | 0 |

---

### 1.6 LLM-as-Judge

**S_AnswerQuality** 由獨立的 LLM 評審（Judge）評估，與 CSR Agent 使用不同模型以避免自我評估偏差：

- **Judge 模型**：`gemini-3.1-flash-lite`，`temperature=0.1`，`max_output_tokens=2048`
- **評估對象**：完整對話紀錄 + 事實清單（JSON）+ 意圖標籤；**不傳入架構名稱**，確保盲評

Judge 沿三個維度評分（1–5 分，線性映射至 0–100）：

| 維度 | 權重 | 評估重點 |
|------|------|----------|
| **S_Resolution** | 50% | 顧客核心問題是否得到解決 |
| **S_Completeness** | 30% | 回覆資訊是否完整、有無遺漏關鍵步驟 |
| **S_Tone** | 20% | 語氣是否專業、同理、符合客服標準 |

Judge 採四步 Chain-of-Thought（CoT）推理：
1. **Evidence**：從對話中擷取關鍵事件
2. **Fact Check**：比對事實清單驗證資訊正確性
3. **Score Derivation**：逐維度套用評分準則
4. **JSON Output**：輸出結構化評分結果

S_AnswerQuality 占 S_Agent 總分的 **30%**（$0.50 \times 0.60 = 0.30$），是 LLM Judge 對最終分數的直接貢獻。

批次評估時 Judge 呼叫之間設有 1.5 秒延遲，以符合 Gemini API 的速率限制。

---

### 1.7 實驗設計

#### In-sample 評估（域內）

In-sample 資料集包含 **150 筆案例**，涵蓋 15 種顧客意圖（cancel_order、track_order、get_refund、change_shipping_address 等），難度標籤分為 easy / medium / hard。四種架構各對 150 筆案例分別搭配三種 Persona 運行，共 1,800 場對話，用於評估各架構在訓練分布內的基礎能力。

#### Out-of-Sample（OOS）泛化評估

OOS 資料集包含 **50 筆案例**，涵蓋 15 種意圖（含 track_return、missing_item、fraud_dispute、installation_request 等**域外新意圖**，及部分與 in-sample 重疊的意圖）。OOS 評估的目的是測試各架構是否能在從未見過的顧客意圖上，依靠通用推理能力（而非記憶特定意圖的處理流程）完成任務。

OOS 實驗設計共執行 **4 架構 × 3 Persona × 50 案例 = 600 場對話**，所有批次採用 checkpoint-resume 機制（已完成的 log 自動跳過），確保中斷後可安全重啟。

#### 泛化分析維度

OOS 結果進一步按以下維度切分分析：
- **重疊意圖 vs. 純新意圖**：區分哪些分數下滑源於意圖本身，哪些源於架構通用推理能力不足
- **In-sample vs. OOS 比較**：對 track_order、cancel_order 等同時出現在兩個資料集的意圖，直接比較分數變化

---

### 1.8 權重敏感度分析

為驗證 S_Agent 的排名穩健性，本研究對四個子指標的權重進行全量掃描：

- 掃描步長：0.05，每個權重最小值 0.05，四者加總為 1.0
- 共生成 **969 種**合法權重組合
- 對每種組合重新計算各架構的 S_Agent 均值，並記錄排名順序

輸出兩份報告：
1. `weight_sensitivity_ranks.csv`：每種權重組合下的四架構均分與排名
2. `weight_sensitivity_summary.txt`：Rank 1 穩定率、最高頻挑戰者、各架構分數區間

此分析確保研究結論不依賴特定權重設定，提升指標設計的可信度。
