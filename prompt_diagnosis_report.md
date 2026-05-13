# Prompt診斷報告

## 概述
本報告基於CASE_001（Polite Persona）的實驗結果，分析各Agent的Prompt設計、邏輯框架、表現問題及改善建議。實驗涉及四種Agent架構：Single-slot、ReAct、Reflection及Plan-and-Execute。共同規則（Common Rules）適用於所有Agent。

## 共同規則（Common Rules）分析
### 設計邏輯
- **身份驗證優先**：強調在執行敏感操作前必須取得Order ID或Email。
- **工具使用**：僅使用模擬器工具，不得虛構數據。
- **風格**：簡潔、有禮，完整驗證後直接解決問題。
- **上下文記憶**：每次回應前掃描完整對話歷史，避免重複問題。

### 問題
- 規則本身合理，但Agent在實際執行中未能完全遵循，特別是工具調用方面。

### 改善建議
- 強化規則的強制性，加入更嚴格的檢查機制。

## Persona Polite分析
### 設計邏輯
- **角色設定**：禮貌合作的客戶，不主動洩露敏感信息。
- **互動規則**：僅在Agent明確要求時提供信息，遵守Fact Sheet。
- **對話流程**：開場陳述問題，過程中配合，中場結束。

### 問題
- Persona表現良好，成功測試Agent的驗證能力。
- 但在某些情況下，對話過於冗長（如ReAct的多次道別）。

### 改善建議
- 加入結束對話的明確信號，減少不必要的互動。

## Agent架構分析

### 1. Single-slot Agent
#### Prompt設計
- 無特定Scaffold，主要依賴Common Rules。
- 從Log顯示，有Thought和Final Answer結構，類似簡化版ReAct。

#### 邏輯框架
- 直接分析對話，決定是否需要詢問信息或提供答案。
- 允許基於"內部知識"直接回答，而非總是調用工具。

#### 表現問題
- **成功案例**：在CASE_001中成功完成任務（TOOL_TRIGGERED, EXECUTED_SUCCESSFULLY）。
- Turn 1：正確詢問Order ID。
- Turn 2：直接告知無法取消，因為已發貨（雖然Log顯示無實際工具調用，但Metadata標記為TOOL_TRIGGERED，可能代碼層處理）。

#### 發生問題
- 可能過度依賴假設數據，而非實際工具。

#### 改善建議
- 明確區分何時需要工具，何時可直接回答。
- 加入工具調用驗證。

### 2. ReAct Agent
#### Prompt設計
- **結構**：每Turn必須包含Thought、Action、Final Answer。
- **Action規則**：需要數據時必須調用工具，格式為`Action: tool_name(parameter="value")`。
- **嚴格約束**：禁止預測工具結果，必須等待Observation。

#### 邏輯框架
- Thought：分析歷史和意圖。
- Action：調用工具。
- Final Answer：基於Observation回答或詢問信息。

#### 表現問題
- **失敗案例**：FAILED_INCOMPLETE, NO_TOOL, PENDING。
- Turn 1：正確詢問ID。
- Turn 2：Thought提到需要檢查狀態，但直接Final Answer，違反"ACTION MANDATORY"規則。假裝已檢查，告知無法取消。
- 隨後Turns：繼續閒聊，無實際解決。

#### 發生問題
- 未遵循Action規則，導致無工具調用，無法取得真實數據。
- 對話冗長，未能有效結束。

#### 改善建議
- 強化Action的強制性，加入自動檢查機制。
- 限制Final Answer的條件，確保有Observation才回答。
- 加入對話結束邏輯。

### 3. Reflection Agent
#### Prompt設計
- **結構**：Initial Draft → Reflection → Final Response。
- **Reflection規則**：檢查PII規則和政策，必須解釋Observation。
- **工具調用**：格式為`[Tool Call: tool_name(args)]`。

#### 邏輯框架
- Initial Draft：初步回應。
- Reflection：事實檢查，決定是否需要工具。
- Final Response：修正輸出。

#### 表現問題
- **失敗案例**：FAILED_INCOMPLETE, NO_TOOL, PENDING。
- Turn 1：正確詢問ID。
- Turn 2：Reflection提到Observation，但Final Response為"let me look that up"，無實際工具調用。
- Turn 4：用戶確認取消，Agent又詢問ID，顯示上下文記憶問題。
- 隨後重複類似行為。

#### 發生問題
- 雖然Prompt要求使用Observation，但實際無工具調用，假裝有數據。
- 上下文記憶不足，重複詢問已知信息。
- 對話循環，未能解決問題。

#### 改善建議
- 確保Reflection階段必須驗證工具調用。
- 改善上下文掃描，記住已提供的信息。
- 加入循環檢測，避免重複問題。

### 4. Plan-and-Execute Agent
#### Prompt設計
- **角色**：Strategic Planner，只輸出計劃，不執行工具。
- **規則**：安全優先，步驟化分解任務。
- **輸出格式**：編號列表計劃。

#### 邏輯框架
- 分析請求，輸出順序步驟。
- Executor負責執行。

#### 表現問題
- CASE_001無Log，但推測類似問題：計劃階段可能過於籠統，導致執行失敗。

#### 發生問題
- 可能計劃不夠具體，無法有效指導執行。

#### 改善建議
- 加入計劃驗證機制。
- 確保步驟與可用工具對應。

## 總體問題與改善建議
### 主要問題
1. **工具調用失敗**：ReAct和Reflection未正確調用工具，導致無數據依據。
2. **假裝數據**：Agent假裝有Observation，但實際無。
3. **上下文記憶**：Reflection在Turn 4又詢問ID。
4. **對話效率**：ReAct和Reflection對話過長，未及時結束。

### 改善方向
1. **強化Prompt強制性**：加入更嚴格的格式檢查和錯誤處理。
2. **工具整合**：確保所有Agent在需要數據時必須調用工具。
3. **上下文管理**：改善記憶機制，避免重複。
4. **結束邏輯**：加入明確的對話結束條件。
5. **測試與驗證**：增加自動檢查工具調用和Observation的機制。

### 結論
Single-slot表現最佳，但可能因簡化設計。ReAct和Reflection邏輯先進，但執行不力。建議重點改善工具調用和上下文處理，以提升整體效能。</content>
<parameter name="filePath">c:\Users\dowgojashan\Documents\GitHub\503-service-unavailable\prompt_diagnosis_report.md