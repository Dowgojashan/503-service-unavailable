# Evaluating LLM Agent Architectures for E-Commerce Customer Service: A Simulation-Based Benchmark

---

## 1. Methodologies

### 1.1 研究設計概述

本研究旨在系統性地比較四種基於大型語言模型（LLM）的客服 Agent 架構在電商情境下的表現，並檢驗其對訓練分布外（Out-of-Sample, OOS）意圖的泛化能力。我們採用全自動化的模擬對話框架（Simulation-Based Benchmark），以 LLM 驅動的顧客 Agent 取代人工測試員，對 CSR Agent 進行系統性壓測。

整體實驗設計為：

- **In-sample（域內）評估**：150 筆案例 × 4 種架構 × 3 種顧客 Persona = **1,800 場對話**
- **Out-of-sample（泛化）評估**：50 筆案例 × 4 種架構 × 3 種顧客 Persona = **600 場對話**

**案例數量設定依據**：In-sample 150 筆涵蓋 15 種意圖，每種意圖 10 筆（easy/medium/hard 各 3–4 筆），確保每個意圖的統計代表性與難度分布均衡。OOS 50 筆涵蓋 15 種意圖（9 種新意圖，6 種與 In-sample 重疊），每種意圖 3–4 筆，受限於新意圖案例生成的成本，規模設計為「足以觀察系統性趨勢，但不足以進行意圖層的精細統計推斷」，本研究在 §3.8 中已明確將 OOS 意圖層分析定位為探索性結論。

所有對話由程式全自動執行，每場對話結束後立即進行指標計算，確保評估一致性。

> 📊 **[Figure 0: fig0_experiment_flow.png — 完整實驗管道流程圖]**

---

### 1.2 模擬對話環境

#### 語言模型

所有 CSR Agent 與顧客 Agent 均使用相同底層模型：**llama3.1:8b**，透過本地部署的 Ollama（`http://localhost:11434`）進行推理，`temperature=0.0`，`max_tokens=1000`。

選用 llama3.1:8b 基於三點考量：（1）**可控性**——本地部署確保實驗完全可重現，不受 API 版本更新影響；（2）**代表性**——8B 參數量代表資源受限的實際部署場景（邊緣服務器、私有部署），四種架構的比較結論對此規模最具實用參考價值；（3）**壓力測試性**——輕量模型的指令遵循缺陷（meta-talk、格式污染等）能充分暴露各架構 Scaffold 設計的工程強健性差異，若使用更強模型（如 GPT-4o），Runner 補償機制的必要性大幅降低，架構間差距可能收窄而難以區分。

`temperature=0.0` 確保輸出的確定性，使不同架構之間的比較排除隨機性干擾。`max_tokens=1000` 足以涵蓋電商客服的完整回覆（含政策說明、操作步驟），同時防止模型進入無限生成循環，避免 Reflection 等多輪架構的 token 消耗因單輪輸出過長而失控。

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

為防止長對話導致 context overflow，BaseAgent 對所有架構一律截取最近 **8 輪**歷史（`history[-8:]`）注入提示，確保各架構在相同的記憶限制下競爭。8 輪的設定依據是：電商客服對話的中位輪次約為 4–6 輪（含身份驗證、問題確認、操作確認），8 輪提供足夠緩衝（可覆蓋 Adversarial Persona 的額外抵抗輪次），同時維持提示長度在 llama3.1:8b 的 8k context window 的安全範圍內。

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

Runner 執行一個原子循環（atomic loop，**最多 5 次迭代**，上限設定依據：電商客服任務最複雜的路徑為「查身份 → 查訂單 → 確認取消意圖 → 執行取消 → 確認退款 → 執行退款」，需要 5 步工具呼叫，再多的迭代在正常解決流程中無意義，只會累積 LOOP 懲罰），每次迭代：
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

若 Reflection 階段判斷需要工具，則以 `[Tool Call: tool_name(args)]` 語法標記，由 Runner 攔截執行。工具結果（observation）注入後 LLM 重新生成完整三段回覆（**最多 3 次迭代**；設定為 3 的理由是：第 1 次迭代完成工具呼叫、第 2 次迭代處理觀察結果並細化回覆、第 3 次作為邊緣情況的最後補救，超過 3 次代表 Scaffold 無法收斂，繼續迭代只會放大 token 消耗而非改善品質）。

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

**權重設定理由**：各子指標權重反映電商客服的業務優先順序。S_Outcome 佔 50% 是因為顧客需求是否得到解決直接決定服務品質的核心價值，符合客服 KPI 以「解決率（First Contact Resolution）」為首要指標的行業慣例。S_Tool 與 S_Efficiency 各佔 20%：工具呼叫正確性防止系統性錯誤（如誤退款、誤取消），對數據完整性至關重要；對話效率直接影響運營成本（每輪對話消耗客服資源）。S_Trajectory 僅佔 10% 因其測量的是推理路徑品質（冗餘步驟、循環次數），此維度與最終服務結果的相關性相對間接。四個權重在敏感度分析（969 種組合）中均已驗證排名穩健性。

$$S_{\text{Agent}} = \begin{cases} \min(S_{\text{raw}},\ 40) & \text{if } I_{\text{fatal}} = 1 \\ S_{\text{raw}} & \text{otherwise} \end{cases}$$

其中 $I_{\text{fatal}}$ 為嚴重違規指標（hallucination、未授權工具呼叫等），觸發時將分數強制封頂於 40 分。封頂值 40 的設定邏輯是：40 分對應 PENDING 狀態（任務未完成），即使 Agent 在語氣與效率上表現良好，只要存在嚴重違規，最終評分不應超過「未完成任務」的基準分——這體現了「不可信任的回覆比沒有回覆更危險」的業務判斷。

#### 子指標定義

| 子指標 | 權重 | 計算方式 |
|--------|------|----------|
| **S_Outcome** | 50% | $0.40 \times S_{\text{CompletionStatus}} + 0.60 \times S_{\text{AnswerQuality}}$（40/60 拆分理由：CompletionStatus 是二元程式化判定，缺乏對部分正確回覆的鑑別力；AnswerQuality 由 Judge 評估實際回覆品質，含解決度、完整性、語氣，具備連續鑑別力，故賦予較高權重）|
| **S_Tool** | 20% | 工具呼叫正確性（正確工具/正確參數/必要呼叫）的加權平均 |
| **S_Trajectory** | 10% | 對話效率（無冗餘工具呼叫、無死循環）的路徑品質分數 |
| **S_Efficiency** | 20% | 對話輪次效率分數（Turn-based penalty） |

**S_CompletionStatus** 根據對話結果標籤判定，各分值設計反映結果的業務影響程度：

| 結果標籤 | 分數 | 設定理由 |
|----------|------|---------|
| `SUCCESS` | 100 | 顧客需求完整解決，對話正常結束 |
| `INFO_PROVIDED` | 80 | 提供了所需資訊但無可執行操作（如政策查詢），顧客目標達成但缺乏主動服務感 |
| `PENDING` | 40 | 對話未完成，顧客需求懸而未決，低於及格線但非完全失敗（有部分進展） |
| `FAILED_INCOMPLETE` | 20 | 對話中斷或 Agent 明確表示無法處理，顧客體驗差但至少提供了明確終止信號 |
| `LOOP_FAILURE` | 0 | 迭代循環耗盡仍無輸出，系統性失敗，對業務零貢獻 |

---

### 1.6 LLM-as-Judge

**S_AnswerQuality** 由獨立的 LLM 評審（Judge）評估，與 CSR Agent 使用不同模型以避免自我評估偏差：

- **Judge 模型**：`gemini-2.0-flash-lite`，`temperature=0.1`，`max_output_tokens=2048`
  - 選用 Gemini 系列而非與 CSR Agent 相同的 llama3.1:8b，是為了避免**自我偏好偏誤（self-preference bias）**——同一模型擔任評審與被評對象時，往往對自身輸出風格給出較高分數（Panickssery et al., 2024）。Flash-lite 版本在自然語言理解與指令遵循能力上遠強於 llama3.1:8b，足以支持三維度 CoT 評分，且 API 成本合理（2,400 次呼叫）。
  - `temperature=0.1` 而非 0.0：評分涉及自然語言推理（CoT 步驟），輕微的隨機性有助於避免完全固定的評分模式（如固定輸出 3/5），同時 0.1 仍足夠低以確保跨案例的評分一致性。
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

---

## 2. Results

### 2.1 In-Sample 評估結果（域內，1,800 場對話）

#### 2.1.1 任務完成率

任務完成率以「有效解決率」衡量，即對話最終狀態為 `SUCCESS`、`INFO_PROVIDED` 或 `REFUSAL` 的比例（`PENDING` 與 `LOOP_FAILURE` 均視為未完成）。

> 📊 **[Figure 2: fig2_insample_performance.png — 完成率（左圖）]**

| 架構 | Polite | Adversarial | VIP | 三 Persona 均值 |
|------|--------|-------------|-----|----------------|
| **ReAct** | **99.3%** | **100%** | 98.0% | **99.1%** |
| **PlanExecute** | 98.7% | 97.3% | **98.7%** | 98.2% |
| Single-slot | 56.0% | 55.3% | 67.3% | 59.5% |
| Reflection | 48.7% | 72.7% | 74.7% | 65.4% |

ReAct 與 PlanExecute 在所有 Persona 下均達到 97% 以上的完成率，遠高於另外兩種架構。Single-slot 因缺乏顯式推理步驟，約 40–44% 的案例停在 PENDING（未完成）。Reflection 完成率最低，且在 Polite Persona 下僅 48.7%，主因是其三段式 scaffold 在 llama3.1:8b 上容易產生 Template Bleed 與 REFUSAL（共 16 筆）。

值得注意的是，Reflection 的完成率在 Adversarial 與 VIP Persona 下顯著回升（+24pp 至 +26pp），推測是因攻擊性對話的情境較為直接，反而觸發了更多 Programmatic Synthesis 路徑。

#### 2.1.2 對話品質（LLM-as-Judge）

> 📊 **[Figure 2: fig2_insample_performance.png — Judge 均分（右圖）]**

| 架構 | Polite | Adversarial | VIP | 三 Persona 均值 |
|------|--------|-------------|-----|----------------|
| **ReAct** | **66.17** | **70.20** | **72.98** | **69.78** |
| PlanExecute | 63.56 | 63.60 | 65.50 | 64.22 |
| Single-slot | 59.00 | 50.60 | 62.73 | 57.44 |
| Reflection | 54.73 | 63.05 | 64.43 | 60.74 |

ReAct 品質在所有 Persona 下均最高，且呈現單調遞增趨勢（Polite → Adversarial → VIP：66 → 70 → 73）。此趨勢與直覺相反——對抗性與高要求的顧客互動反而激發了 ReAct 更精確的推理與回覆。

PlanExecute 跨 Persona 品質最穩定，三個 Persona 均分差距不超過 2 分，反映 Immediate Synthesis 機制的輸出一致性。Single-slot 在 Adversarial 下品質下跌最多（-8.4 分），顯示單次決策架構在高壓環境下容易崩解。

#### 2.1.3 Token 成本與效益

> 📊 **[Figure 6: fig6_cost_efficiency.png — 成本效益散點圖]**

**各架構 × Persona 平均 Token 用量（In-Sample）：**

| 架構 | Polite | Adversarial | VIP | 三 Persona 均值 | 相對倍數（均值）|
|------|--------|-------------|-----|----------------|----------------|
| **PlanExecute** | **14,803** | 20,745 | 15,448 | **16,999** | **1.0×** |
| ReAct | 19,113 | 25,884 | **17,497** | 20,831 | 1.2× |
| Single-slot | 24,057 | 26,135 | 22,067 | 24,086 | 1.4× |
| Reflection | 84,551 | 69,474 | 71,290 | **75,105** | **4.4×** |

**Polite Persona 效益（S_Agent / 萬 Token）：**

| 架構 | Polite 效益（分/萬 Token）|
|------|--------------------------|
| **PlanExecute** | **42.7** |
| ReAct | 34.7 |
| Single-slot | 23.7 |
| Reflection | 6.1 |

PlanExecute 的 Immediate Synthesis 機制在完成工具呼叫後直接組裝回覆，避免後續 LLM 推理的 token 消耗，使其成為四種架構中成本最低者。Reflection 的三段式多輪結構三 Persona 均值達 75,105 token，是 PlanExecute 的 4.4 倍，但品質卻最低，在成本效益上表現最差。

**跨 Persona token 差異的關鍵觀察：**

- **Adversarial 對 PlanExecute 和 ReAct 衝擊最大**：Adversarial 顧客第一次拒絕提供 ID，強迫 Agent 多跑一輪驗證流程。有 Guard 機制的兩種架構對此反應敏感——PlanExecute Adversarial 較 Polite 多出 40%（+5,942 token），ReAct 多出 35%（+6,771 token）。

- **VIP 對 ReAct 反而最省**：ReAct VIP（17,497）低於 Polite（19,113）。VIP 顧客的表達結構清晰、目標明確，Guard 鏈可提前收斂，與 §2.1.2 中 ReAct 品質在 VIP 下最高的發現相互呼應——更少 token 換到更高品質，是 ReAct 在 VIP 情境下的雙重優勢。

- **Reflection 呈現反向趨勢**：Adversarial（69,474）與 VIP（71,290）均低於 Polite（84,551）。推測原因是 Adversarial/VIP 對話下更頻繁觸發 Programmatic Synthesis 早期終止路徑，跳過了部分多輪反思迭代，反而減少了 token 消耗。

---

#### 2.1.4 ProxyCost / NetValue / Delta_MB（In-Sample）

本研究以 **ProxyCost**（正規化成本指標）、**NetValue**（成本調整後淨價值）與 **Delta_MB**（相對 Single-slot 的邊際效益）三個指標，評估各架構的成本效益。

$$\text{ProxyCost} = 100 \times (0.5 \times \text{TokenNorm} + 0.3 \times \text{LLMCallNorm} + 0.2 \times \text{ToolCallNorm})$$

$$\text{NetValue}(a,i) = V_i \times \frac{S_{\text{Agent}}(a,i)}{100} - 0.01 \times \text{ProxyCost}(a,i)$$

$$\Delta_{\text{MB}}(a,i) = \text{NetValue}(a,i) - \text{NetValue}(\text{Single-slot}, i)$$

正規化使用全部 1,944 筆 log 的**全域 max**（tokens=241,655, LLM calls=6, tool calls=4），確保跨架構比較基準一致。

| 架構 | ProxyCost（均值）| NetValue（均值）| Delta_MB（均值）| Delta_MB > 0 比例 |
|------|----------------|----------------|----------------|-----------------|
| **PlanExecute** | **20.83** | **1.429** | **+0.162** | **72.9%** |
| Single-slot | 28.70 | 1.247 | 0.000（基準）| — |
| ReAct | 30.30 | 1.202 | -0.059 | 38.9% |
| Reflection | 33.90 | 0.938 | -0.267 | 28.6% |

**Delta_MB 按難度分層：**

| 架構 | Easy | Medium | Hard |
|------|------|--------|------|
| **PlanExecute** | +0.057 | +0.222 | **+0.228** |
| Single-slot | 0.000 | 0.000 | 0.000 |
| ReAct | -0.107 | -0.035 | -0.026 |
| Reflection | -0.117 | -0.231 | **-0.501** |

**PlanExecute 是唯一在所有難度下 Delta_MB 均為正值的架構**，在 Hard 任務中優勢最顯著（+0.228）。ReAct 的負值幅度極小（-0.059），顯示其品質優勢幾乎能抵銷額外的迭代成本；Reflection 的 Hard 任務 Delta_MB 達 -0.501，是成本效益最差的組合。

---

#### 2.1.5 S_Agent 綜合評分

> 📊 **[Figure 1: fig1_s_agent_overview.png — 左側 In-Sample 部分]**

S_Agent 加權公式為：$S_{\text{raw}} = 0.50 \times S_{\text{Outcome}} + 0.20 \times S_{\text{Tool}} + 0.10 \times S_{\text{Trajectory}} + 0.20 \times S_{\text{Efficiency}}$

**各架構子分項均值（In-Sample，1,800 場對話）：**

| 架構 | S_Outcome | S_Tool | S_Trajectory | S_Efficiency | **S_Agent** |
|------|-----------|--------|--------------|--------------|-------------|
| **PlanExecute** | 79.0 | **72.8** | **99.4** | 97.0 | **83.07** |
| Single-slot | 74.4 | 71.7 | **99.9** | 85.2 | 78.53 |
| ReAct | **81.8** | 47.7 | 63.1 | **98.0** | 76.37 |
| Reflection | 75.2 | 67.8 | **100.0** | 23.6 | 65.80 |

PlanExecute 以 S_Agent = **83.07** 奪冠，但其勝出並非靠單一維度壓倒性優勢，而是各維度均衡表現——在沒有弱點的情況下積分最高。具體而言，ReAct 雖然 S_Outcome 最高（81.8），但 S_Tool 僅 47.7（工具呼叫錯誤率高）且 S_Trajectory 只有 63.1（reason-act 循環產生過多冗餘步驟），拉低了整體得分。Reflection 的 S_Efficiency 僅 23.6，反映其 token 暴增帶來的嚴重效率懲罰。

**S_Agent 跨 Persona 穩定性：**

| 架構 | Polite | Adversarial | VIP | 波動幅度 |
|------|--------|-------------|-----|---------|
| **PlanExecute** | **82.77** | **82.40** | **84.05** | **1.65** |
| Single-slot | 78.69 | 76.71 | 80.18 | 3.47 |
| ReAct | 76.20 | 74.92 | 77.99 | 3.07 |
| Reflection | 64.62 | 65.78 | 66.99 | 2.37 |

PlanExecute 的跨 Persona 波動僅 1.65 分（最穩定），與 PSS 分析結論相互呼應。

---

#### 2.1.6 權重敏感度分析

針對 S_Agent 公式的四個子指標權重進行全量掃描（步長 0.05，每個權重 ≥ 0.05，969 種合法組合）：

| 架構 | Rank 1 頻率 | Rank 2 頻率 |
|------|------------|------------|
| **PlanExecute** | **100%** | 0% |
| Single-slot | 0% | **87%** |
| ReAct | 0% | 13% |
| Reflection | 0% | 0% |

**PlanExecute 在所有 969 種權重組合下均排名第一，結論對指標設計假設完全穩健。** 即使將 S_Trajectory 權重提高至 0.85（遠超實際使用的 0.10），PlanExecute 仍維持第一，顯示其排名不依賴任何特定的權重設定。

---

#### 2.1.7 ProSA 敏感度分析（In-Sample PSS）

> 📊 **[Figure 4: fig4_pss_violin.png — In-Sample PSS 分布]**
> 📊 **[Figure 5: fig5_intent_pss_heatmap.png — Intent × 架構 PSS 熱力圖]**

**整體 PSS 比較：**

| 架構 | PSS 均值 | PSS 標準差 | 高敏感案例（PSS > 20） |
|------|---------|----------|----------------------|
| **PlanExecute** | **17.96** | 17.80 | 52 筆（35%）|
| ReAct | 20.27 | 17.54 | 69 筆（46%）|
| Single-slot | 25.08 | 19.71 | 70 筆（47%）|
| Reflection | 28.70 | 16.69 | 97 筆（65%）|

PlanExecute PSS 最低（17.96），Reflection 最高（28.70）。Reflection 有近三分之二的案例（65%）屬高敏感，意即相同問題在不同 Persona 下輸出品質差異顯著。

**按 Intent 分層（節選）：**

敏感度最高的意圖為 `cancel_order`（PSS = 29.97）與 `check_refund_policy`（PSS = 29.92），這類任務有明確可執行動作，但成功與否高度依賴顧客的表達清晰度。最穩健的意圖為 `change_shipping_address`（PSS = 13.58），因其有固定政策回應，Synthesis 模板可完整覆蓋。

**反直覺發現**：難度 1（簡單案例）的 PSS（24.93）高於難度 3（困難案例，PSS = 22.50）。與 ProSA 原論文（困難任務敏感度較高）的結論相反，本研究中簡單案例反而存在更大的跨 Persona 品質分化空間——困難案例在三個 Persona 下往往一致失敗，差距自然縮小。

**完成率跨 Persona 一致性：**

| 架構 | 三 Persona 全解決 | 混合（部分解決）| 三 Persona 全失敗 |
|------|-------------------|----------------|-----------------|
| **ReAct** | **147（98%）** | 3（2%）| 0（0%）|
| **PlanExecute** | 143（95%）| 7（5%）| 0（0%）|
| Single-slot | 60（40%）| 53（35%）| 37（**25%**）|
| Reflection | 49（33%）| 94（**63%**）| 7（5%）|

ReAct 是完成率一致性最高的架構（98% 的案例在三個 Persona 下均能解決），而 Single-slot 有 25% 的案例在所有 Persona 下均失敗，顯示其對特定類型問題存在系統性缺陷。

---

### 2.2 Out-of-Sample 泛化評估結果（OOS，600 場對話）

OOS 資料集涵蓋 15 種意圖，其中 9 種為 In-sample 訓練分布外的新意圖（`track_return`、`missing_item`、`fraud_dispute`、`installation_request`、`product_inquiry` 等）。OOS 日誌完整記錄了 token 與執行秒數，以下分析同時涵蓋兩項指標。

#### 2.2.1 任務完成率（OOS）

> 📊 **[Figure 3: fig3_oos_performance.png — OOS 完成率（左圖）]**

| 架構 | Polite | Adversarial | VIP | OOS 均值 |
|------|--------|-------------|-----|---------|
| **PlanExecute** | **98%** | 92% | **98%** | **96%** |
| Reflection | 56% | 86% | **98%** | 80% |
| ReAct | 58% | 74% | 96% | 76% |
| Single-slot | 44% | 46% | 52% | 47% |

PlanExecute 在 OOS 下仍維持接近 96% 的完成率，是四種架構中泛化最穩健者。然而，**ReAct 完成率出現嚴重崩跌**：In-sample 下幾近 100% 的完成率，OOS Polite Persona 下降至 58%，主要原因是面對分布外意圖時，reason-act 循環無法在 5 次迭代內收斂，觸發大量 LOOP\_FAILURE（21/50 筆）。

值得關注的是，Reflection 在 VIP Persona 下完成率回升至 98%——VIP 顧客的表達結構清晰，觸發了更多早期終止路徑，減少了無效迭代。

#### 2.2.2 對話品質（LLM-as-Judge，OOS）

> 📊 **[Figure 3: fig3_oos_performance.png — OOS Judge 均分（右圖）]**

| 架構 | Polite | Adversarial | VIP | OOS 均值 |
|------|--------|-------------|-----|---------|
| ReAct | **36.2** | **31.9** | 37.8 | **35.3** |
| Reflection | 32.7 | 29.4 | **38.4** | 33.5 |
| Single-slot | 32.4 | 23.3 | 35.4 | 30.4 |
| PlanExecute | 29.4 | 22.1 | 30.4 | 27.3 |

**四種架構 Judge 均分全面崩跌**，OOS 均分集中在 22–38 分，對比 In-sample 的 51–73 分，差距達 20–35 分。這一系統性崩跌反映了 agent 的工具集（query\_order、cancel\_order、apply\_refund 等）無法對應新意圖（track\_return、fraud\_dispute 等），導致 agent 只能輸出通用模板回覆，解析度（s\_resolution）在所有架構下均接近最低分段（均值 1.7–2.3/5）。

**PlanExecute 在 OOS 下呈現悖論現象**：完成率最高（96%）但 Judge 均分最低（27.3）。Immediate Synthesis 機制以「I can help you with your concern」類的通用模板結束對話，Runner 計為 SUCCESS，但 Judge 評定顧客需求完全未被實際回應。此為 Synthesis 機制在分布外情境下的系統性侷限。

語氣（s\_tone）是 OOS 下唯一未大幅下滑的維度，Reflection 在 VIP Persona 下 s\_tone 達 4.46（所有 OOS 組合最高），顯示多輪反思在語氣調整上仍有效用，但無法補償任務解決能力的缺失。

#### 2.2.3 Token 成本與效益（OOS）

**各架構 × Persona 平均 Token 用量（OOS）：**

| 架構 | Polite | Adversarial | VIP | 三 Persona 均值 | 效益（S_Agent / 萬 Token）|
|------|--------|-------------|-----|----------------|--------------------------|
| **PlanExecute** | **18,825** | 25,303 | 19,537 | **21,222** | **34.5** |
| **ReAct** | 19,390 | 28,166 | **16,545** | 21,367 | 30.7 |
| Single-slot | 28,761 | 30,282 | 30,526 | 29,856 | 23.4 |
| Reflection | 148,091 | 51,261 | **19,431** | **72,928** | 8.3 |

**與 In-sample 對比的關鍵變化：**

- **PlanExecute token 上升（14,803 → 18,825 Polite）**：In-sample 的 Immediate Synthesis 介入率約 96%，而 OOS 新意圖找不到對應模板，Synthesis 觸發失敗後仍須走一次後置 LLM 呼叫，使每場對話的 LLM 呼叫次數增加，token 成本因此提高。

- **Reflection Polite 暴衝至 148,091（是 In-sample 的 1.75 倍）**：OOS 新意圖下 Reflection 無法在前幾輪收斂，多次迭代全程執行三段式結構，且 Template Bleed 偵測後的 Programmatic Synthesis 在新意圖情境下觸發更晚，造成 token 極度膨脹。

- **Reflection VIP 驟降至 19,431（是 In-sample 的 0.27 倍）**：VIP 顧客表達清晰，觸發早期終止路徑，使 Reflection 在 VIP 下的多輪迭代大幅縮短，與完成率 98% 的結果一致。Reflection 的跨 Persona token 方差（σ ≈ 55,000）是四種架構中最高，反映其對對話結構的極度敏感性。

- **ReAct VIP 仍最省（16,545）**：與 In-sample 趨勢一致，VIP 的結構化對話讓 ReAct Guard 鏈快速收斂，即使在 OOS 下仍維持此優勢。

- **效益排名維持**：PlanExecute（34.5）> ReAct（30.7）> Single-slot（23.4）> Reflection（8.3），與 In-sample 排名完全相同，顯示成本效益的相對格局在分布外情境下具穩健性。

---

#### 2.2.4 ProxyCost / NetValue / Delta_MB（OOS）

使用與 In-sample 相同的公式，OOS 正規化以全部 600 筆 log 的全域 max（tokens=230,342, LLM calls=6, tool calls=4）為分母。

| 架構 | ProxyCost（均值）| NetValue（均值）| Delta_MB（均值）| Delta_MB > 0 比例 |
|------|----------------|----------------|----------------|-----------------|
| **PlanExecute** | **22.01** | **0.512** | **+0.125** | **78.0%** |
| Single-slot | 31.28 | 0.387 | 0.000（基準）| — |
| ReAct | 29.51 | 0.363 | -0.023 | 41.3% |
| Reflection | 33.40 | 0.274 | -0.113 | 46.7% |

**Delta_MB 按難度分層（OOS）：**

| 架構 | Easy | Medium | Hard |
|------|------|--------|------|
| **PlanExecute** | +0.129 | +0.094 | **+0.151** |
| Single-slot | 0.000 | 0.000 | 0.000 |
| ReAct | -0.033 | -0.017 | -0.021 |
| Reflection | -0.121 | -0.078 | -0.139 |

**三項關鍵跨集比較：**

1. **PlanExecute 雙集均正值**：In-sample +0.162 → OOS +0.125，跌幅僅 0.037，Immediate Synthesis 的低成本優勢在分布外情境下高度保留，Delta_MB > 0 比例甚至從 72.9% 上升至 78.0%（因 OOS 中 Synthesis 的低 ProxyCost 與 Single-slot 高 ProxyCost 拉大了差距）。

2. **ReAct OOS 負值縮小（-0.059 → -0.023）**：LOOP_FAILURE 案例提前終止反而節省後續 token，使 OOS ProxyCost 相對降低。

3. **所有架構 NetValue 絕對值均大幅下滑**（0.94–1.43 → 0.27–0.51），因 OOS S_Agent 系統性崩跌，即使 ProxyCost 相近，品質損失使成本調整後價值縮水約 60%。

---

#### 2.2.5 OOS S_Agent 與泛化落差

> 📊 **[Figure 7: fig7_generalization_gap.png — S_Agent 跌幅比較]**

| 架構 | OOS S_Agent | In-sample S_Agent | 泛化跌幅 |
|------|------------|------------------|---------|
| **PlanExecute** | **73.2** | 83.07 | -9.9 |
| Single-slot | 70.0 | 78.53 | -8.5 |
| ReAct | 65.8 | 76.37 | **-10.6** |
| Reflection | 60.8 | 65.80 | -5.0 |

**三個關鍵觀察：**

1. **排名維持**：PlanExecute 在 OOS 下仍為第一，四種架構的整體排名順序未變。
2. **排名逆轉（局部）**：In-sample 下 ReAct（76.37）高於 Single-slot（78.53 → 調整後：ReAct 76.37 < Single-slot 78.53，故 In-sample 已是 PE > SS > ReAct），但 OOS 下 Single-slot（70.0）超越 ReAct（65.8）。Single-slot 缺乏迭代機制，遇到無法處理的意圖直接輸出通用回覆並結束，反而避免了 LOOP 懲罰。
3. **Reflection 跌幅最小（-5.0）**：In-sample 基礎分本就最低，下跌空間有限；部分 OOS 案例反而因反思機制提前觸發終止而獲得較高 S_Outcome。

**OOS S_Agent 子分項（均值）：**

| 架構 | S_Outcome | S_Tool | S_Trajectory | S_Efficiency | **S_Agent（OOS）** |
|------|-----------|--------|--------------|-------------|-----------------|
| **PlanExecute** | 56 | **78** | **99** | **99** | **73.2** |
| Single-slot | 53 | 75 | **100** | 91 | 70.0 |
| ReAct | **57** | 54 | 66 | **99** | 65.8 |
| Reflection | 56 | 74 | **100** | 40 | 60.8 |

S_Trajectory 是 OOS 下差異最顯著的子分項：ReAct 從 In-sample 的 63.1 進一步惡化至 OOS 均值 66（Adversarial Persona 下僅 50），而 PlanExecute 則維持接近 99，反映 Synthesis 機制的路徑確定性在分布外仍然穩定。

#### 2.2.6 OOS 權重敏感度分析

對 OOS 600 筆數據重複 969 種權重組合掃描：

| 架構 | Rank 1 頻率 | Rank 2 頻率 |
|------|------------|------------|
| **PlanExecute** | **99.9%** | 0.1% |
| Single-slot | 0.1% | **94.6%** |
| ReAct | 0.0% | 5.3% |
| Reflection | 0.0% | 0.0% |

唯一翻轉條件：W\_Trajectory = 0.85（其餘各 0.05）時 Single-slot 以 S\_Agent = 95.7 勝出，但此權重設定在實際評估中毫無合理依據。**OOS 下 PlanExecute 的排名穩健性（99.9%）與 In-sample（100%）幾乎相同**，確認研究結論不依賴特定權重選擇。

---

#### 2.2.7 OOS ProSA 敏感度分析（OOS PSS）

**整體 PSS（OOS）：**

| 架構 | PSS 均值 | PSS 標準差 | 高敏感案例（PSS > 20） |
|------|---------|----------|----------------------|
| **ReAct** | **17.20** | 12.78 | 10（20%）|
| PlanExecute | 18.33 | 15.89 | 12（24%）|
| Reflection | 20.13 | 14.09 | 18（36%）|
| Single-slot | 20.87 | 18.33 | 18（36%）|

OOS 下品質穩定性排名出現反轉：**ReAct 取代 PlanExecute 成為最穩健架構**（PSS 17.20 vs PlanExecute In-sample 17.96）。此轉變源於 OOS 壓縮了所有架構的 Judge 分數範圍（22–38 分），而 ReAct 的跨 Persona 分差在這個壓縮空間中是最小的。

**PSS by Intent（OOS，節選）：**

| Intent | 類型 | PSS 均值 | 說明 |
|--------|------|---------|------|
| cancel_order | 重疊意圖 | **39.90** | 部分 Persona 下偶有成功（均分 56.41），造成大幅落差 |
| payment_issue | 重疊意圖 | 26.56 | 有部分工具可用但結果不穩定 |
| track_order | 重疊意圖 | 15.83 | 重疊意圖中相對穩定 |
| track_return | 新意圖 | 12.83 | 三個 Persona 下均一致低分（均分 18.67）|
| installation_request | 新意圖 | 8.75 | 全架構均無法處理 |
| check_warranty | 新意圖 | **5.83** | PSS 最低，三個 Persona 下分數趨同於最低分 |

重疊意圖（如 `cancel_order`）的 PSS 顯著高於純新意圖（如 `check_warranty`）。這是因為重疊意圖偶有成功案例（特別是在 Polite Persona 下），造成跨 Persona 的大幅分化；而純新意圖無論哪個 Persona，所有架構均一致失敗，三個 Persona 分數趨同於最低分段，差距自然縮小。

**S_Agent 完成一致性（OOS，以 S_Agent ≥ 50 為解決標準）：**

| 架構 | 三 Persona 全解決 | 混合（部分解決）| 三 Persona 全失敗 |
|------|-------------------|----------------|-----------------|
| **PlanExecute** | **49（98%）** | 1（2%）| 0（0%）|
| ReAct | 45（90%）| 5（10%）| 0（0%）|
| Single-slot | 45（90%）| 5（10%）| 0（0%）|
| Reflection | 26（**52%**）| 24（**48%**）| 0（0%）|

OOS 下四種架構均無「三 Persona 全失敗」案例（對比 In-sample Single-slot 有 25% 全失敗），說明 OOS 的主要問題是「品質差」而非「完全無法完成」。PlanExecute 以 98% 的完成一致性領先，Reflection 則有近一半案例處於混合狀態（某些 Persona 成功、某些失敗）。

---

## 3. Analysis and Discussion

### 3.1 PlanExecute 的雙面性：Immediate Synthesis 的能力邊界

PlanExecute 在 In-sample 下以 S_Agent = 83.07 奪冠，關鍵在於 **Immediate Synthesis** 機制的兩項效果：其一，`query_order` 成功後由 Runner 直接組裝回覆，跳過後續 LLM 呼叫，將 llama3.1:8b 在工具觀察解讀上的幻覺風險降至最低；其二，固定模板使 S_Trajectory 達到 99.4（第二高），推理路徑幾乎無冗餘。從這個角度看，PlanExecute 的成功本質上是一種**以確定性換取品質**的工程策略，而非模型推理能力的直接體現。

然而，同一機制在 OOS 下揭示了其能力邊界。Synthesis 模板的設計覆蓋範圍是有限且封閉的（`track_order`、`cancel_order`、`get_refund` 等既有意圖），當顧客意圖為 `track_return`、`fraud_dispute` 或 `installation_request` 時，Runner 找不到對應模板，只能輸出「I can help you with your tracking/cancellation/refund concern」類的通用回覆並結束對話——Runner 計為 SUCCESS，Judge 則評定需求完全未被回應。這導致 OOS 下 PlanExecute 呈現**完成率最高（96%）但 Judge 均分最低（27.3）的系統性悖論**。

此悖論揭示了一個重要的評估設計啟示：**任務完成率（completion rate）與回覆品質（answer quality）在分布外情境下可能嚴重解耦**，單用完成率衡量泛化能力會產生誤導性結論。Immediate Synthesis 的「覆蓋半徑」決定了 PlanExecute 能泛化到多遠，而這個半徑完全取決於人工設計的模板集合，而非模型的通用推理能力。

---

### 3.2 ReAct 的雙刃劍效應：迭代推理的情境依賴性

ReAct 在 In-sample 下展現了最高的 S_Outcome（81.8），且品質呈現一個反直覺的**單調遞增**趨勢：Polite（66.17）→ Adversarial（70.20）→ VIP（72.98）。這說明 ReAct 的 Thought + Action 迭代框架在面對更複雜的對話壓力時，反而激發了更精確的推理——對抗性顧客的抵制行為與 VIP 顧客的明確期待，提供了更豐富的推理信號，讓 ReAct 的每一輪 Thought 步驟能做出更有針對性的判斷。

然而，相同的迭代機制在 OOS 下成為最大的弱點。面對分布外意圖（`track_return`、`missing_item` 等），Agent 的工具呼叫清單中不存在對應的操作，ReAct 進入「思考 → 嘗試工具 → 無效觀察 → 再思考」的死循環，直到達到 5 次迭代上限才終止。OOS Polite Persona 下的 LOOP\_FAILURE 率高達 42%（21/50 筆），是 In-sample 的數十倍。

值得關注的是，VIP Persona 下 ReAct 的 OOS 完成率大幅回升至 96%。VIP 顧客的表達結構清晰、目標明確，即使面對新意圖，對話的上下文信號也足以讓 ReAct 較早找到一個可收斂的輸出路徑（`Final Answer`），而非陷入工具探索循環。這說明 ReAct 的 LOOP 問題本質上是**推理收斂性（convergence）的失敗**，而收斂性高度依賴對話上下文的結構化程度——對話越結構化，ReAct 越容易找到出口。

---

### 3.3 Simple is Robust：結構簡單性作為意外的泛化優勢

Single-slot 在 In-sample 下完成率僅 59.5%（四者最低），但在 OOS 下卻以 S_Agent = 70.0 超越 ReAct（65.8），成為第二名。這個「排名逆轉」揭示了一個反直覺的泛化規律：**面對未知意圖，架構複雜度可能是負資產。**

Single-slot 的邏輯是：若無法從單次 LLM 呼叫中產生有效工具呼叫，則直接輸出通用回覆並結束對話。這個「快速失敗」（fail fast）的特性在 OOS 下反而成為優勢——它不會觸發 LOOP\_FAILURE 懲罰，也不會因為反覆嘗試而產生高 S\_Trajectory 懲罰，S\_Efficiency 也因此維持在 91。相比之下，ReAct 的迭代設計在面對無解問題時必然陷入多輪無效循環，累積的懲罰使 S\_Agent 被壓低至 65.8。

這一發現對實際部署有直接啟示：在工具覆蓋範圍不確定的場景下，「少做一點但做得快」的架構設計，比「多做幾次嘗試找到答案」更能維持整體評分。然而，Single-slot 在 OOS 下的 Judge 均分（30.4）仍顯著低於 In-sample（57.4），顯示「快速失敗」只是減少了懲罰，並非真正提升了回覆品質。

---

### 3.4 PSS 排名反轉的統計解釋：分數壓縮效應

In-sample 下 PSS 最低者為 PlanExecute（17.96），OOS 下則由 ReAct（17.20）取代。這個排名反轉並非架構本身的穩定性發生了根本改變，而是源於一個統計層面的效應：**分數範圍（score range）的壓縮。**

PSS 是以各 Persona 之間的 Judge 分數**絕對差距**衡量，其數值天然受分數分布範圍的影響。In-sample 下 Judge 均分範圍為 51–73 分，跨 Persona 的分化空間較大；OOS 下分數被壓縮至 22–38 分，即使架構間的相對穩定性格局未變，絕對 PSS 也會因分數壓縮而縮小。在這個壓縮後的空間中，ReAct 的跨 Persona 分差最小（因為它在所有三個 Persona 下均處於中等低分段），因此 PSS 自然最低。

這一發現對 PSS 指標的使用方法有方法論啟示：**跨資料集（In-sample vs OOS）的 PSS 絕對值不可直接比較**，相對排名才具有跨集穩定的解釋意義。若需進行跨集比較，應考慮對 PSS 進行分數範圍標準化（如 normalized PSS = PSS / score\_range），以消除絕對分數空間的干擾。

---

### 3.5 難度—敏感度悖論：PSS 的概念重新詮釋

ProSA 原論文（Zhuo et al., EMNLP 2024）在數學推理任務上發現困難案例的 PSS 較高，因為困難任務對 prompt 寫法更敏感。然而，本研究在 In-sample 觀察到相反趨勢：**難度 1（簡單）的 PSS（24.93）反而高於難度 3（困難，PSS = 22.50）**，OOS 下更加顯著（easy = 19.11，hard = 17.96）。

這個反轉現象可以用一個概念框架來解釋：**PSS 衡量的不是「任務有多難」，而是「任務的成功是否對表達風格敏感」**。困難案例（如複雜退款流程）在三個 Persona 下往往一致失敗，三組分數均集中在低分段，差距縮小；而簡單案例（如查詢訂單狀態）有能力被解決，Polite Persona 下可能完美作答（100 分），Adversarial Persona 下可能因一次抵抗而失敗（0–30 分），跨 Persona 分差因此更大。

換言之，高 PSS 不代表任務困難，而代表**存在可分化的成功空間**。這一詮釋對 PSS 的應用有實際意義：PSS 高的意圖（如 `cancel_order` PSS = 29.97）應優先進行 Persona 泛化強化，因為這些意圖有成功潛力但表現不穩定，最具改善空間；PSS 低的新意圖（`check_warranty` PSS = 5.83）則代表全面失敗，需要的不是穩定性強化，而是工具集擴展。

---

### 3.6 顧客 Persona 作為推理壓力源：架構間的差異化反應

不同架構面對三種 Persona 的反應模式存在顯著差異，揭示了各架構的底層設計假設：

**ReAct 從壓力中獲益**。Adversarial 顧客的抵抗行為（拒絕提供 ID 一次）和 VIP 顧客的明確期待，提供了額外的對話信號，讓每輪 Thought 步驟有更多可推理的材料。這與 ReAct 原始設計的哲學一致——推理需要觀察，更豐富的觀察帶來更精確的推理。

**PlanExecute 對 Persona 幾乎免疫**。三個 Persona 下 S_Agent 波動僅 1.65 分（最低），根本原因是 Immediate Synthesis 的模板輸出與顧客語氣無關——無論顧客是禮貌、攻擊或強勢，Runner 輸出的是相同的規則合成文字。這是設計上的穩定性，但也解釋了為何在 OOS 下 PlanExecute 的語氣（s\_tone）評分偏低：固定模板無法針對 VIP 的尊貴語境調整措辭。

**Single-slot 在 Adversarial 下最脆弱**。品質跌幅最大（-8.4 分），因為單次 LLM 呼叫沒有緩衝機制——Adversarial 顧客的攻擊性語言直接注入提示，模型在無推理步驟的情況下只能反應式回覆，語氣控制崩潰。

**Reflection 的 VIP 異常優秀**（OOS 完成率 98%，Judge 均分 38.4）值得單獨解釋。VIP 對話的結構化特性（清晰目標、明確期待）使 Reflection 的 Initial Draft → Reflection → Final Response 流程能夠收斂：初稿已接近正確，反思步驟只需微調語氣，三段式結構恰好契合 VIP 期待細緻、全面回覆的需求。這說明 Reflection 並非普遍低效，而是**高度情境依賴**——在結構清晰的對話中，多輪反思有其價值。

---

### 3.7 評估框架的設計反思

#### Runner 補償機制對評估公平性的影響

本研究的一個核心設計決策是對所有架構統一施加 Runner 層的補償機制（身份驗證前置攔截、Immediate Synthesis、Template Bleed 偵測等），以補償 llama3.1:8b 的訓練先驗缺陷。這些補償機制確保了實驗可重現性，但同時也引入了一個公平性問題：**各架構受益於 Runner 補償的程度不均等。**

最顯著的例子是 PlanExecute 的 Immediate Synthesis：PlanExecute 的高 S_Trajectory（99.4）與高完成率，有相當大比例歸功於 Runner 直接繞過 LLM 合成回覆（In-sample 介入率約 96%），而非架構本身的推理能力。若移除此機制，PlanExecute 的 S_Agent 預期大幅下滑，而 ReAct 的相對排名可能上升。在分析結論時，應將 S_Trajectory 與完成率視為「系統級（system-level）」指標，而非純粹的「架構級（architecture-level）」指標。

#### LLM-as-Judge 的有效性

本研究採用不同模型（Gemini gemini-3.1-flash-lite）作為 Judge，並在評分提示中**隱藏架構名稱**（盲評），以降低模型自我偏好偏誤。Judge 的三維度評分（S_Resolution、S_Completeness、S_Tone）在 In-sample 下顯示出合理的鑑別力——四種架構的 Judge 均分差距達 10–15 分，與完成率趨勢一致。

然而，OOS 下 Judge 均分的全面崩跌（22–38 分）揭示了一個潛在的 **地板效應（floor effect）**：當所有架構的回覆品質均很差時，Judge 在最低分段的鑑別力有限——s\_resolution 均值集中在 1.7–2.3/5，各架構差距縮小。這意味著 OOS Judge 分數的架構間比較（如 ReAct 36 vs PlanExecute 27）在統計上的意義可能不如 In-sample 比較穩健。

#### 顧客 Persona 模擬的生態效度

以 LLM 模擬顧客而非招募真實用戶，是本研究在可重現性與成本上的核心取捨。三種 Persona 的行為規則設計（一次抵抗、兩次接受現實等）確保了對話的可控性與可比性，但也必然無法完整再現真實顧客行為的多樣性——真實的 Adversarial 顧客可能持續對抗超過預設的輪次限制，真實的 VIP 顧客可能提出本研究 Fact Sheet 中未涵蓋的特殊要求。這一設計取捨使本研究的結論適用範圍主要限於「受控模擬情境下的架構比較」，在推廣至真實部署時需額外的人工評估驗證。

---

### 3.8 研究限制

**模型特異性（Model Specificity）**  
本研究使用 llama3.1:8b 作為 Agent 的底層模型。多項 Runner 補償機制（Param Guard、Template Bleed 偵測）是針對 llama3.1:8b 的特定行為缺陷而設計，在規模更大或對齊更完善的模型（如 Llama-3.3-70b、GPT-4o）上，同等的 Scaffold 設計可能無需這些補償即可穩定運行，進而改變四種架構的相對表現。

**工具集覆蓋範圍的先天限制**  
OOS 資料集中 9 種新意圖（`track_return`、`installation_request`、`fraud_dispute` 等）的全面失敗，部分原因是這些意圖在現有工具集（`query_order`、`cancel_order`、`apply_refund`、`get_policy` 等）下**無對應操作**。這是實驗設計的刻意選擇（測試架構的通用推理能力），但也意味著 OOS 的「泛化失敗」無法完全區分「架構推理能力不足」與「工具覆蓋範圍不足」兩種原因。

**OOS 規模限制**  
OOS 資料集僅 50 筆案例，涵蓋 15 種意圖，其中部分意圖的案例數極少（`check_warranty` 僅 1 筆、`return_request` 4 筆）。在如此小樣本下，PSS by Intent 的估計具有較高的抽樣方差，本研究的 OOS 意圖層分析宜視為探索性結論，而非具有統計顯著性的確定性發現。

**單一 Judge 模型**  
所有 2,400 筆評估（1,800 In-sample + 600 OOS）均使用同一 Judge 模型（Gemini gemini-3.1-flash-lite）。不同 Judge 模型（如 GPT-4o 或人工評估者）對相同對話的評分可能存在系統性差異，本研究未進行多 Judge 交叉驗證。

---

### 3.9 未來研究方向

**擴展至更強的底層模型**  
以 Llama-3.3-70b 或其他規模更大的模型替換 llama3.1:8b，可測試在無需 Runner 補償的條件下，四種架構的本質性能差異是否與本研究結論一致。若 PlanExecute 的優勢消失（因不再需要 Synthesis 補償），則可確認其 In-sample 排名主要來自工程設計而非架構設計。

**擴展 OOS 工具集**  
在保留現有評估架構的前提下，為 `track_return`、`fraud_dispute` 等新意圖設計對應工具函數，可將 OOS 評估從「工具缺失下的泛化」轉為「新工具適應下的泛化」，更直接測試架構的學習遷移能力。

**Instruction-level ProSA 驗證**  
本研究以顧客 Persona 作為 PSS 計算的 prompt 變體，概念上等價於 ProSA 的指令寫法敏感性，但切入點不同。未來可對 ReAct 與 PlanExecute 兩種代表架構，同時進行 Persona-level PSS（本研究方法）與 Instruction-level PSS（ProSA 原始方法）的雙軌比較，以驗證兩種 PSS 框架的結論是否一致。

**人工評估驗證（Human Evaluation）**  
對 Judge 分數落在 60–75 區間（高不確定性區段）的案例進行 10% 人工抽樣複核，計算 Spearman ρ（目標 ≥ 0.75），以驗證 LLM-as-Judge 的評分信度，為後續研究提供方法論基準。

**混合架構設計**  
本研究結果顯示各架構的優勢互補：PlanExecute 的 S_Trajectory 穩定性、ReAct 的 S_Outcome 品質、Single-slot 的 OOS 避難特性。未來可探索「動態架構路由（Dynamic Architecture Routing）」——依據顧客意圖的置信度選擇合適的架構，在已知意圖時啟動 PlanExecute，在意圖不確定時退回 Single-slot，以兼顧精確性與泛化穩健性。
