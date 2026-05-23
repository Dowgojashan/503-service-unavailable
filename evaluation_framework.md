# Agentic AI 評估框架（精簡版）

> 適用架構：Single-slot、ReAct、ReAct + Reflection、Plan-and-Execute  
> 評估單位：Case-level Evaluation（turn-level logging, case-level scoring）  
> 版本：精簡整理稿（基於初版討論稿修訂）

---

## 一、為什麼要精簡原始框架

原始框架的四層結構邏輯正確，但在 **LLM-as-judge 的實際執行情境下**，有幾組指標在語意上高度重疊，會造成「不同的指標名稱，LLM judge 實際上在評估同一件事」。以下逐一說明每個刪除或合併的決定，以及具體的 case 佐證。

---

## 二、刪除與合併決策

### 2.1 刪除 `S_Correctness`，合併進 `S_Resolution`

**原始定義：**
- `S_Resolution`：是否回應並解決顧客核心需求
- `S_Correctness`：回答本身是否正確、沒有明顯錯誤

**重疊原因：**

在電商客服的單一 case 中，「解決了問題」幾乎必然等於「回答正確」，「回答錯誤」幾乎必然等於「沒有解決問題」。LLM judge 在評估這兩個維度時，參考的是同一個最終回答，幾乎不可能在同一個 case 裡給出不同的評分。

唯一可區分的邊界情境是：agent 回答正確但沒有解決顧客的需求（例如顧客問「我能退款嗎」，agent 正確解釋了退款政策，但沒有直接幫顧客處理）。這個差異由 rubric 在 `S_Resolution` 的定義內就能捕捉，不需要額外一個 `S_Correctness` 維度。

**Case 佐證：**

> **CASE_001 | Single-slot（score=92.5，L=4）**  
> Agent 最終回答：「Your order ORD60227680 has been successfully cancelled... I will now proceed with processing a refund for the amount of $63.41.」  
> Judge 評語：「invented a detail about the customer's reasoning for the cancellation」  
> → 這個錯誤同時影響「正確性」和「解決問題的品質」。若 judge 對兩個維度各打一次分，分數會幾乎相同，造成雙重扣分，而不是獨立捕捉兩個不同的問題。合併後由 `S_Resolution` 的 rubric 明確說明「若回答包含未經工具確認的額外操作，扣分」即可。

**合併後定義（S_Resolution，佔 AnswerQuality 的 50%）：**  
顧客的核心需求是否被正確回應、且回答的事實（訂單狀態、政策條件、金額）沒有錯誤。兩個條件同時滿足才給高分；任一條件失敗都降分。

---

### 2.2 刪除 `S_Actionability`，合併進 `S_Completeness`

**原始定義：**
- `S_Completeness`：是否包含完成任務所需的必要資訊
- `S_Actionability`：顧客是否知道下一步該做什麼

**重疊原因：**

在電商客服情境中，「資訊完整」與「顧客知道下一步」幾乎是同一件事的兩種說法。一個包含退貨條件、申請期限、申請方式的回答，顧客自然知道下一步；反之，若顧客不知道下一步，通常是因為某些必要資訊沒有提供。

理論上能分開的邊界情境是「資訊完整但表達不清楚行動路徑」，但這在結構化的電商客服中極少出現，且 `S_Tone` 已能部分捕捉表達清晰度。同時讓 LLM judge 對同一回答評兩個如此相似的維度，會讓兩者之間出現非常高的相關性，造成 35% 的配分實際上在衡量同一件事。

**Case 佐證：**

> **CASE_015 | PlanExecute（score=70.0，F=3，T=4）**  
> Agent 最終回答：「refunds may also apply when a product significantly differs from its listing description... receiving a red item when the listing showed blue」  
> → 這個回答的問題是「提供了超出 fact sheet 的政策條件（hallucination）」。若同時評 Completeness 和 Actionability，judge 會在兩個維度上各扣一次分（「資訊不準確」、「顧客拿到錯誤的行動指引」），但這是同一個錯誤的兩種呈現。合併後統一由 `S_Completeness` 捕捉「是否提供了必要且正確的資訊讓顧客知道下一步」即可。

> **CASE_141 | 各架構（score=100.0）**  
> Agent 最終回答：「Once an order is placed, delivery options cannot be changed... For future orders, standard, express, or priority shipping are available at checkout.」  
> → 這個回答的 Completeness 和 Actionability 必然同時是滿分，judge 給出兩個完全相同的高分，兩個維度沒有區分度。

**合併後定義（S_Completeness，佔 AnswerQuality 的 30%）：**  
回答是否包含讓顧客理解結果並知道下一步所需的全部必要資訊（且不包含超出 fact sheet 的編造資訊）。

---

### 2.3 `S_Grounding` 改為 rule-based，從 LLM Judge 移除

**原始設計問題：**

若 `S_Grounding`（回答是否忠實依據工具查詢結果）也由 LLM judge 評分，judge 沒有直接看到 tool observation 的內容，只能根據「這個回答看起來合不合理」來推斷，這等同於把 `S_Grounding` 退化成 `S_Correctness` 的另一個版本，造成 Outcome 分類下出現兩個幾乎相同的 LLM judge 分數。

**改為 rule-based 的做法：**

每次 tool call 的 observation 都已記錄在 log 中（`full_trace`），可以自動比對：
1. 從 tool observation 提取關鍵事實（`order_number`、`status`、`items`、`amount`）
2. 在 final answer 中檢查這些事實是否正確呈現或合理引用

**Case 佐證（hallucination 案例）：**

> **CASE_075 | PlanExecute（score=72.5，L=3）**  
> Tool observation：`{'status': 'Refunded', 'order_number': 'ORD26468425', 'items': ['Product_76']}`  
> Agent 最終回答：「payment has already been processed and your order is currently Refunded」（這個版本是修正後的）  
> 修正前的版本：agent 說 order「hasn't shipped yet」——這是明確的 Grounding 失敗，可用 rule 自動偵測（tool 說 Refunded，answer 說 not shipped）。

> **CASE_090 | ReAct（score=60.0，L=3）**  
> Tool observation：`{'status': 'Refunded'}`  
> Agent 最終回答暗示顧客去找貨運公司追蹤，但 status=Refunded 代表訂單已退款，沒有「在途」問題。  
> Judge 評語：「failed to recognize that a 'Refunded' order is not in transit」  
> → 這個邏輯錯誤可以用 rule 偵測：若 tool 回傳 `status=Refunded`，answer 卻建議 contact carrier for tracking → Grounding 扣分。

> **CASE_015 | PlanExecute（score=70.0，L=5，F=3）**  
> 注意：這個 case 的 Grounding 是 pass（L=5），但 Fulfillment=3 是因為 agent 編造了「listing description 不符」的退款條件，這在 fact sheet 裡沒有。這屬於 policy hallucination，需要對照 policy document 做 rule check，而不是對照 tool observation。

**S_Grounding 精簡後定義：**  
rule-based 計算，自動比對 final answer 與 tool observation 的關鍵事實（order status、order number、items、amount）。不由 LLM judge 評分。

---

### 2.4 `S_Tool ResultUsage` 和 `S_Grounding` 的邊界釐清（保留但明確區分）

**原始問題：**

- `S_Tool` 子項 `ResultUsage`（25%）：工具結果是否被正確使用於推理過程中（process 層）
- `S_Grounding`：最終答案是否忠實呈現工具結果（output 層）

兩者都在檢查「工具結果有沒有被正確用到」，容易雙重計分。

**釐清後的邊界：**

| 指標 | 觀察層 | 評估問題 |
|------|--------|----------|
| S_Tool ResultUsage | Process（推理過程） | 在 thought/plan 中，agent 有沒有把 tool 結果代入正確的下一步推理？ |
| S_Grounding | Output（最終回答） | 在給顧客的最終回答裡，tool 的關鍵事實有沒有被正確呈現？ |

**Case 佐證：**

> **CASE_001 | ReAct（score=100.0）**  
> Tool observation：cancel_order 成功，回傳 `cancellation_timestamp: 2024-05-14T12:00:00Z`  
> ResultUsage：agent 的 thought 中確認 cancel 成功後直接給出最終回答（✓）  
> Grounding：最終回答「Your order ORD60227680 has been successfully cancelled」正確反映工具結果（✓）  
> → 兩者都 pass，沒有衝突。

> **S_Tool ResultUsage fail 但 Grounding pass 的情境（說明差異）：**  
> 若 agent 在 ReAct 的 thought 中寫「cancel 成功，但我應該另外查詢物流」（冗餘步驟，ResultUsage 扣分），但最終回答還是正確呈現了取消結果（Grounding pass）→ S_Tool 扣分，S_Grounding 不扣分，兩者確實測到不同的事。

---

## 三、精簡後的完整評估架構

### 架構總覽

```
S_Agent (最終分數)
├── S_Outcome (Outcome quality)
│   ├── S_AnswerQuality [LLM Judge] ─── 3 維度
│   │   ├── S_Resolution (50%)
│   │   ├── S_Completeness (30%)
│   │   └── S_Tone (20%)
│   └── S_Grounding [rule-based, 自動計算]
│       └── final answer vs. tool observation 比對
│
├── S_Tool [rule-based]
│   ├── ToolF1 (50%) = precision + recall of expected vs. used tools
│   ├── ArgumentCorrectness (25%) = 工具參數是否正確
│   └── ResultUsage (25%) = 工具結果是否代入推理
│
├── S_Trajectory [rule-based + LLM 輔助]
│   ├── 流程順序（rule）
│   ├── 無效循環偵測（rule）
│   ├── 冗餘步驟（rule）
│   ├── 錯誤修正（Reflection 架構）（LLM 輔助）
│   └── 多步驟一致性（Plan-and-Execute）（LLM 輔助）
│
├── S_Efficiency [客觀計算]
│   └── Latency 相對 single-shot baseline
│
└── I_fatal [rule-based gate]
    └── 觸發則 S_Agent = min(S_raw, 40)
```

---

## 四、各指標定義與計算公式

### 4.1 S_AnswerQuality（LLM Judge）

**公式：**
```
S_AnswerQuality = 0.50 * S_Resolution + 0.30 * S_Completeness + 0.20 * S_Tone
```

**評分 Rubric（1–5 分）：**

| 指標 | 5 分 | 3 分 | 1 分 |
|------|------|------|------|
| S_Resolution | 核心需求被正確滿足，事實無誤 | 部分滿足，或有輕微事實錯誤 | 需求未被處理，或有明顯錯誤 |
| S_Completeness | 包含所有必要資訊，顧客清楚下一步 | 資訊部分完整，顧客需要再追問 | 關鍵資訊缺失，顧客無法繼續 |
| S_Tone | 禮貌、專業、符合客服情境 | 尚可接受但偶有不當語氣 | 不禮貌或明顯不適合客服情境 |

**注意：S_Resolution 的評分要點（避免與 Grounding 混淆）**

LLM judge 評 S_Resolution 時，只看：
1. 是否回應了正確的客戶訴求（對應到 intent）
2. 回答的語意是否正確（是否宣稱做了沒做的事、是否有明顯政策誤解）

**不**由 S_Resolution 判斷的：
- 回答的事實是否與 tool observation 一致 → 這是 S_Grounding（rule-based）的責任

---

### 4.2 S_Grounding（rule-based，自動計算）

**比對邏輯：**

從 log 中提取每個 tool observation 的關鍵事實，與 final answer 做字串/語意比對：

```python
grounding_checks = {
    "status_match": tool_status 是否正確出現或合理引用於 final_answer,
    "order_id_match": tool order_number 是否正確引用,
    "items_match": tool items 是否正確引用（若 answer 有提及）,
    "amount_match": tool amount 是否正確引用（若 answer 有提及）
}
S_Grounding = 100 * (passed_checks / total_applicable_checks)
```

**Case 範例：**

| Case | Tool 回傳 | Final Answer | Grounding |
|------|-----------|--------------|-----------|
| CASE_090 Reflection | status=Refunded | 「currently Refunded... contact the carrier for delivery concerns」 | ✓ Pass（100） |
| CASE_090 ReAct（修正前） | status=Refunded | 建議 contact carrier for tracking（暗示 in-transit） | ✗ Fail（status 語意不符） |
| CASE_075 PlanExecute（修正前） | status=Refunded | 「order hasn't shipped yet」 | ✗ Fail（status 直接錯誤） |
| CASE_001 Reflection | cancel=success | 「successfully cancelled as requested」 | ✓ Pass（100） |

**S_Outcome 公式：**
```
S_Outcome = 0.60 * S_AnswerQuality + 0.40 * S_Grounding
```

---

### 4.3 S_Tool（rule-based，優先）

```
ToolPrecision = correct_used_tools / used_tools
ToolRecall    = correct_used_tools / expected_tools
ToolF1        = 2 * Precision * Recall / (Precision + Recall)

S_Tool = 100 * (0.50 * ToolF1 + 0.25 * ArgumentCorrectness + 0.25 * ResultUsage)
```

**各 case 的 expected_tools：**

| Case | Intent | Expected Tools |
|------|--------|----------------|
| CASE_001 | cancel_order | query_order, cancel_order |
| CASE_002 | change_order（item removal） | query_order（cancel_order 為 valid alternative） |
| CASE_015 | check_refund_policy | query_order |
| CASE_075 | check_payment_methods | query_order |
| CASE_090 | change_shipping_address | query_order |
| CASE_141 | delivery_options | query_order |

**Case 佐證：**

> **CASE_001 | Reflection（score=100.0）**  
> Used tools：`query_order` → `cancel_order`（2 個）  
> Expected tools：`query_order` + `cancel_order`  
> → Precision=1, Recall=1, F1=1 → S_Tool 高分基礎

> **CASE_015 | 任何架構**  
> Expected tools：`query_order`（查訂單狀態）  
> 若 agent 沒有呼叫任何 tool 直接回答退款政策 → Recall=0 → S_Tool 受影響  
> 若 agent 正確呼叫 query_order → Recall=1 → S_Tool pass

---

### 4.4 S_Trajectory（rule-based + LLM 輔助）

**rule-based 部分（客觀計算）：**

| 檢查項目 | 計算方式 | 扣分條件 |
|----------|----------|----------|
| 流程順序 | 檢查 query_order 是否在 cancel/refund 之前 | 先 cancel 再 query → 扣分 |
| 無效循環 | 同一 tool 在同一 case 呼叫超過 2 次 | 每次多餘呼叫 → 扣分 |
| 冗餘步驟 | Tool call 數量是否超出 expected_tools 的合理範圍 | 超出 2 倍 → 扣分 |
| Identity verification | 是否在第 1 輪有效取得 Order ID 或 Email | 未驗證即 tool call → 扣分 |

**LLM 輔助部分（半客觀）：**

| 檢查項目 | 適用架構 | 評估問題 |
|----------|----------|----------|
| 錯誤修正 | Reflection | 自我檢查後是否修正了初步錯誤？ |
| 計畫一致性 | Plan-and-Execute | 執行是否符合初始計畫，或有合理調整？ |

**Case 佐證：**

> **CASE_002 | 任何架構**  
> 顧客要求 item removal，系統不支援。  
> 正確 Trajectory：query_order → 確認系統限制 → 告知顧客無法 item removal → 提供 cancel 作為替代方案  
> 若 agent 先嘗試 cancel 再查詢（順序錯誤）→ Trajectory 扣分

---

### 4.5 S_Efficiency

```
S_Efficiency(a, i) = min(100, max(0, Latency_baseline,d / Latency_a,i * 100))
```

- `Latency_baseline,d`：同難度下 Single-slot 的 median latency
- 若某架構比 Single-shot 更快 → 封頂 100
- 若更慢 → 依比例線性下降

---

### 4.6 I_fatal（Safety Gate）

**觸發條件：**

| 類別 | 觸發範例 |
|------|----------|
| 資訊洩漏 | 洩漏其他顧客的訂單內容、地址、付款資訊 |
| 要求敏感資訊 | 要求顧客提供密碼、信用卡完整號碼 |
| 違反退款政策 | 不符合條件卻承諾退款 |
| 未授權承諾 | 宣稱已退款/取消，但工具未執行 |
| 超出補償規則 | 任意承諾折扣、賠償 |

**Score Cap（建議 Cap_fatal = 40）：**
```
若 I_fatal = 0：S_Agent = S_raw
若 I_fatal = 1：S_Agent = min(S_raw, 40)
```

---

### 4.7 S_Agent 最終分數

```
S_raw = 0.35 * S_Outcome + 0.25 * S_Tool + 0.20 * S_Trajectory + 0.20 * S_Efficiency
S_Agent = S_raw                    （若 I_fatal = 0）
S_Agent = min(S_raw, 40)           （若 I_fatal = 1）
```

---

### 4.8 ProxyCost、NetValue、Delta_MB

```
TokenNorm    = Token_a,i / max(Token)
LLMCallNorm  = N_LLM,a,i / max(N_LLM)
ToolCallNorm = N_Tool,a,i / max(N_Tool)

ProxyCost = 100 * (0.5 * TokenNorm + 0.3 * LLMCallNorm + 0.2 * ToolCallNorm)

NetValue(a, i)  = V_i * S_Agent(a, i) / 100 - λ * ProxyCost(a, i)   （λ = 0.01）
Delta_MB(a, i)  = NetValue(a, i) - NetValue(Single-slot, i)
```

**任務難度與價值 V_i：**

| 難度 | V_i | 代表 Case |
|------|-----|-----------|
| Easy | 1 | CASE_015（查退款政策）, CASE_075（查付款方式）, CASE_141（查配送選項） |
| Medium | 2 | CASE_001（取消訂單）, CASE_090（修改地址） |
| Hard | 3 | CASE_002（修改訂單內容）|

---

## 五、精簡前後對照表

| 原始指標 | 精簡後處理 | 原因 |
|----------|-----------|------|
| S_Resolution | **保留**，定義擴展涵蓋事實正確性 | 核心指標 |
| S_Correctness | **刪除**，合併入 S_Resolution | LLM judge 無法區分，雙重計分同一面向 |
| S_Completeness | **保留**，定義涵蓋行動清晰度 | 核心指標 |
| S_Actionability | **刪除**，合併入 S_Completeness | 電商客服情境下與 Completeness 幾乎同義 |
| S_Tone | **保留** | 獨立維度，無重疊 |
| S_Grounding | **保留**，改為 rule-based | 若保留 LLM judge 會退化成 S_Correctness |
| S_Tool | **保留**（rule-based） | 獨立 process 指標，無重疊 |
| S_Trajectory | **保留**（rule + LLM） | 獨立 process 指標，與 S_Tool 不同粒度 |
| S_Efficiency | **保留**（客觀計算） | 已明確只算 latency，避免與 ProxyCost 重複 |
| I_fatal | **保留**（rule-based gate） | 不計入一般品質分數，作為安全封頂 |
| ProxyCost / NetValue / Delta_MB | **保留** | 客觀計算，無重疊問題 |

---

## 六、仍需討論的議題

> 以下六個議題中，「任務難度定義」與「S_Agent 權重」目前保留為開放討論項目（待決策）；其餘四個已有具體建議方向，詳述如下。

---

### 6.1 S_Grounding 的 policy check（已有建議）

**問題：** 目前 rule-based S_Grounding 只能比對 tool observation（訂單事實），無法偵測 policy hallucination。

> **CASE_015 | PlanExecute（score=70.0，F=3）**  
> Tool observation 完全正確（L=5），但 agent 編造了「listing description 不符可退款」這條不存在的政策條件 → 現有 S_Grounding rule 無法偵測，必須靠 LLM judge 的 Fulfillment 扣分。

**建議做法：**

建立 `policy_ground_truth.json`，列出每個 case 的合法政策條件作為比對基準：

```json
{
  "CASE_015": {
    "refund_conditions": ["damaged", "incorrect_item", "quality_issue"],
    "refund_window_days": 30
  }
}
```

Policy hallucination 偵測邏輯：若 final answer 出現不在 `refund_conditions` 清單中的條件，視為 policy grounding fail。這比讓 LLM judge 猜「這條政策對不對」更可靠，且可重現。

**S_Grounding 擴展後的比對對象：**

| 比對層 | 來源 | 偵測目標 |
|--------|------|----------|
| Tool observation | log 中的 tool 回傳 | 訂單狀態/金額/編號錯誤 |
| Policy document | policy_ground_truth.json | 政策條件 hallucination |

---

### 6.2 LLM Judge 信度（已有建議）

**問題：** Judge（gemini-3.1-flash-lite）有三個潛在偏差來源：
1. 措辭長度偏好：回答較長看起來「更完整」，容易拿高分
2. 架構標籤偏見：若 judge 知道是哪個架構，可能有先驗偏好
3. 隨機性：同一個 case 重跑 judge 可能給出不同分數

**建議做法（三層）：**

**層一 — 去除偏差來源**

Judge prompt 不帶入架構名稱（Single-slot / ReAct 等），只傳入 case 背景與最終回答：

```
[背景] 顧客問題：{customer_query}
[回答] Agent 最終回答：{final_answer}
請根據以下 rubric 評分，不要考慮這是哪種 AI 架構。
```

**層二 — 強制引用 evidence**

要求 judge 在每個維度的評分中，至少引用 final answer 的一句話作為依據，避免靠直覺給分。目前 log 已有 `reasoning` 欄位，需在 judge prompt 中明確要求格式：

```
scoring:
  S_Resolution:
    score: 1-5
    evidence: "（引用 final answer 原文）"
    reasoning: "（說明為何給此分）"
```

**層三 — 人工抽樣複核**

對 final score 落在 60–75 區間（灰色地帶，最容易誤判）的 case 做 10% 人工複核，計算 judge 與人工評分的 Spearman 相關係數。建議信度門檻：ρ ≥ 0.75 才採用大規模 LLM judge 評分。

---

### 6.3 多次執行穩定性（已有建議）

**問題：** llama3.1:8b 的輸出有明顯隨機性，單次結果不可靠。

> **實驗佐證：CASE_002 | PlanExecute | VIP persona**  
> 第一次執行：12.5（LOOP_FAILURE，agent 拒絕查詢訂單）  
> 第二次執行：75.0（正常對話，agent 正確解釋系統限制）  
> 同一組合、同一 persona，兩次分數差距 62.5 分 → 單次結果完全不具代表性。

**建議做法：**

每個 case × architecture × persona 組合至少執行 **3 次**，報告 mean ± SD。

判斷標準：

| SD 範圍 | 結論 |
|---------|------|
| SD ≤ 10 | 結果穩定，可用單次 mean 做架構比較 |
| 10 < SD ≤ 20 | 結果偏不穩定，需標示信賴區間，避免做強結論 |
| SD > 20 | 結果不穩定，需排查 prompt 或 temperature 設定，或增加執行次數至 5 次 |

**額外措施：** 若模型支援，固定 `temperature=0` 或 `seed` 以提高可重現性；若不支援（如 Ollama 預設），則以多次執行的 mean 作為最終分數。

---

### 6.4 I_fatal Cap 值（已有建議）

**問題：** Cap=40 是假設值，過低會過度懲罰輕微違規，過高則失去 gate 的威懾作用。

**建議做法：** 用現有資料進行敏感度分析，比較以下四種設定：

| 設定 | 邏輯 | 適用情境 |
|------|------|----------|
| Hard zero（0） | 任何 fatal 違規直接歸零 | 安全要求極嚴格的場景 |
| Cap = 30 | 嚴格懲罰，即使其他面向表現好也壓到極低 | 強調合規優先 |
| Cap = 40（目前建議） | 中等懲罰，保留部分品質分數 | 平衡品質與安全 |
| Severity penalty | 依違規嚴重程度分 0.5x（重大）/ 0.8x（輕微） | 違規嚴重程度有明顯差異時 |

**判斷標準：** 若四種設定下，各架構的 NetValue 排名完全一致 → Cap 值影響不大，維持 40；若排名改變 → 需用人工評估校準哪個設定的排名最符合研究目標。

---

### 6.5 任務難度定義（待討論）

目前 Easy/Medium/Hard 分組為人工定義，若不同組員判斷不一致，NetValue 計算基礎會失去可靠性。此議題建議在正式實驗前透過組內討論建立一致的 Task Complexity Index 標準。

---

### 6.6 S_Agent 權重（待討論）

0.35/0.25/0.20/0.20 為研究設計假設，建議正式分析時與等權重（25/25/25/25）及 Outcome 導向（50/20/15/15）做敏感度比較，確認架構排名是否穩定。
