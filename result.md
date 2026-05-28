# Experiment Results — LLM Agent Architecture Evaluation

Model: llama3.1:8b (Ollama)  
Judge: gemini-3.1-flash-lite (LLM-as-Judge, auxiliary metric)  
Date: 2026-05-28

---

## Polite Persona — 四架構比較

### 1. 任務完成率

| 架構 | 已解決率 | EXECUTED | INFO | REFUSAL | PENDING (未解決) |
|------|---------|---------|------|---------|-----------------|
| Single-slot | 56.0% | 32 | 52 | 0 | 66 (44%) |
| ReAct | **99.3%** | 14 | 135 | 1 | 0 |
| Reflection | 48.7% | 73 | 0 | 16 | 61 (41%) |
| PlanExecute | **98.7%** | 9 | 139 | 1 | 1 |

- ReAct / PlanExecute 幾乎不留 PENDING，解決率接近 100%
- Single-slot / Reflection 約有 40–44% 的案例停在 PENDING（未完成）
- Reflection 有 16 筆 REFUSAL（model 自主拒絕），是四者中最高的

### 2. 品質 (LLM-as-Judge)

| 架構 | Judge 平均分 /100 | Judge 樣本數 |
|------|-----------------|------------|
| Single-slot | 59.00 | 148 |
| ReAct | **66.17** | 149 |
| Reflection | 54.73 | 150 |
| PlanExecute | 63.56 | 148 |

- ReAct 品質最高，PlanExecute 其次
- Reflection 品質最低，主因大量 PENDING / REFUSAL 拉低分數
- 四者 tone 分數均偏高（llama3.1:8b 在禮貌對話中語氣表現尚可）

### 3. Token 成本

| 架構 | 平均 Token | 相對倍數 |
|------|-----------|---------|
| PlanExecute | **14,898** | 1.0× |
| ReAct | 19,044 | 1.3× |
| Single-slot | 24,937 | 1.7× |
| Reflection | 89,675 | **6.0×** |

- Reflection 因多輪反思機制，token 用量是 PlanExecute 的 6 倍
- PlanExecute 最省 token；Single-slot 因 context 堆積反而比 ReAct 更貴

### 4. 成本效益（Judge 分 / 萬 token）

| 架構 | 質量 / 萬 Token |
|------|--------------|
| Single-slot | 23.7 |
| ReAct | 34.7 |
| Reflection | 6.1 |
| **PlanExecute** | **42.7** |

- PlanExecute 最高效：最低成本、近乎 100% 完成率、品質第二
- Reflection 最差性價比：token 暴增但品質最低

### 5. 綜合結論

| 維度 | 勝者 |
|------|------|
| 完成率 | ReAct ≈ PlanExecute |
| 品質 | ReAct |
| 成本 | PlanExecute |
| 成本效益 | **PlanExecute** |
| 最差 | Reflection（高成本、低品質、高 PENDING）|

**Polite persona 下，PlanExecute 是最推薦架構**，兼顧完成率、品質與成本。ReAct 品質略高但成本也略高，可視情況取捨。Reflection 在此 persona 下表現最差，不建議使用。

---

## Adversarial Persona — 四架構比較

### 1. 任務完成率

| 架構 | 已解決率 | EXECUTED | INFO | REFUSAL | PENDING (未解決) |
|------|---------|---------|------|---------|-----------------|
| Single-slot | 55.3% (83) | 33 | 49 | 1 | 67 (44.7%) |
| **ReAct** | **100%** (150) | 22 | 127 | 1 | **0** |
| Reflection | 72.7% (109) | 101 | 0 | 8 | 41 (27.3%) |
| PlanExecute | 97.3% (146) | 15 | 129 | 2 | 4 (2.7%) |

- ReAct 在 Adversarial 下達到 100% 完成率，是四者中唯一零 PENDING
- Single-slot 最差，幾乎一半案例未解決
- Reflection EXECUTED 數量最高（101），但仍有 41 筆 PENDING

### 2. 品質 (LLM-as-Judge)

| 架構 | Judge /100 | s_resolution | s_completeness | s_tone |
|------|-----------|-------------|---------------|--------|
| Single-slot | 50.60 | 2.89 | 3.02 | 3.37 |
| **ReAct** | **70.20** | **3.79** | **3.56** | **4.23** |
| Reflection | 63.05 | 3.38 | 3.23 | 4.14 |
| PlanExecute | 63.60 | 3.35 | 3.36 | 4.16 |

- ReAct 品質大幅領先，所有子項都最高
- Reflection 與 PlanExecute 品質相近（63 分左右）
- Single-slot 全面墊底，tone 只有 3.37（面對攻擊性客戶明顯失控）

### 3. Token 成本與效益

| 架構 | Token 平均 | 質量 / 萬 Token |
|------|-----------|--------------|
| Single-slot | 26,677 | 18.97 |
| ReAct | 25,852 | 27.15 |
| Reflection | 72,815 | 8.66 |
| **PlanExecute** | **20,946** | **30.36** |

- PlanExecute 成本最低且效益最高（30.36）
- ReAct 成本略高於 PlanExecute，但品質最好（27.15）
- Reflection 成本是 PlanExecute 的 3.5 倍，效益卻最差

### 4. 對比 Polite Persona

| 架構 | Polite 完成率 | Adversarial 完成率 | 變化 | Polite Judge | Adversarial Judge | 變化 |
|------|------------|-----------------|-----|------------|-----------------|-----|
| Single-slot | 56.0% | 55.3% | -0.7pp | 59.00 | 50.60 | **-8.4** |
| ReAct | 99.3% | **100%** | +0.7pp | 66.17 | **70.20** | **+4.0** |
| Reflection | 48.7% | 72.7% | +24pp | 54.73 | 63.05 | +8.3 |
| PlanExecute | 98.7% | 97.3% | -1.4pp | 63.56 | 63.60 | +0.04 |

- ReAct 在 Adversarial 下品質反而更高（+4分），完成率也持平——面對攻擊性客戶表現更好
- Reflection 完成率大幅提升（+24pp），可能因 Adversarial 案例情境較單純
- Single-slot 品質跌最多（-8.4分），無法應對攻擊性對話
- PlanExecute 跨 persona 最穩定，幾乎不受影響

### 5. 綜合結論

| 維度 | 勝者 |
|------|------|
| 完成率 | **ReAct（100%）** |
| 品質 | **ReAct（70.20）** |
| 成本 | PlanExecute |
| 成本效益 | PlanExecute |
| 最差 | Single-slot |

**Adversarial persona 下 ReAct 是最佳架構**，完成率 100%、品質最高，打破了 Polite 下 PlanExecute 領先的格局。PlanExecute 仍是成本效益最佳選擇。Reflection 表現中規中矩，Single-slot 完全不適合應對攻擊性客戶。

---

## VIP Persona — 四架構比較

### 1. 任務完成率

| 架構 | 已解決率 | EXECUTED | INFO | REFUSAL | PENDING (未解決) |
|------|---------|---------|------|---------|-----------------|
| Single-slot | 67.3% | 42 | 59 | 0 | 49 (32.7%) |
| **ReAct** | **98.0%** | 14 | 133 | 0 | 3 |
| Reflection | 74.7% | 104 | 0 | 8 | 38 (25.3%) |
| **PlanExecute** | **98.7%** | 14 | 132 | 2 | 2 |

- ReAct / PlanExecute 再次接近 100% 完成率，與其他 persona 表現一致
- Single-slot 在 VIP 下明顯改善（67.3% vs Polite 56%、Adversarial 55.3%），可能因 VIP 案例情境較明確
- Reflection 仍有 25% PENDING，且 INFO_PROVIDED=0（全靠 EXECUTED 或 REFUSAL 完成）

### 2. 品質 (LLM-as-Judge)

| 架構 | Judge /100 | fulfillment /5 | logic /5 | tone /5 |
|------|-----------|----------------|---------|---------|
| Single-slot | 62.73 | 4.50 | 4.00 | **5.00** |
| **ReAct** | **72.98** | **4.83** | 4.67 | **5.00** |
| Reflection | 64.43 | 4.33 | **5.00** | **5.00** |
| PlanExecute | 65.50 | 4.33 | 4.17 | 4.67 |

- ReAct 整體品質最高（72.98），且是三個 persona 中分數最高的一次
- Reflection 的 logic 分數完美（5.00），但 fulfillment 最低（4.33）——說明它 SOP 遵守好但任務完成度不足
- PlanExecute 的 tone 分數最低（4.67），略低於其他架構的 5.00

### 3. Token 成本

| 架構 | 平均 Token | 相對倍數 |
|------|-----------|---------|
| **PlanExecute** | **15,519** | **1.0×** |
| ReAct | 17,244 | 1.1× |
| Single-slot | 22,749 | 1.5× |
| Reflection | 75,305 | 4.9× |

- PlanExecute 仍是成本最低的架構，三個 persona 中最省
- Reflection token 用量是 PlanExecute 的 4.9 倍，但品質只高出 ~1 分

### 4. 成本效益（Judge 分 / 萬 token）

| 架構 | 質量 / 萬 Token |
|------|--------------|
| Single-slot | 27.58 |
| **ReAct** | **42.32** |
| Reflection | 8.56 |
| PlanExecute | 42.21 |

- VIP persona 下 ReAct（42.32）與 PlanExecute（42.21）效益幾乎並列第一
- ReAct 因品質顯著高於 PlanExecute（72.98 vs 65.50），以略高的 token 換取更好的輸出

### 5. 綜合結論

| 維度 | 勝者 |
|------|------|
| 完成率 | PlanExecute ≈ ReAct |
| 品質 | **ReAct（72.98，三個 persona 最高）** |
| 成本 | PlanExecute |
| 成本效益 | ReAct ≈ PlanExecute（42.32 vs 42.21）|
| 最差 | Reflection（高成本、低完成率） |

**VIP persona 下 ReAct 是最佳架構**，品質達到三個 persona 中的最高分（72.98），且成本效益與 PlanExecute 幾乎持平。PlanExecute 若考量成本仍是穩健選擇。Reflection 因大量 PENDING 與高 token 用量，性價比最差。

---

## 跨 Persona 比較

### 1. 完成率跨 Persona 對比

| 架構 | Polite | Adversarial | VIP | 趨勢 |
|------|--------|------------|-----|------|
| Single-slot | 56.0% | 55.3% | **67.3%** | VIP 明顯改善 |
| ReAct | 99.3% | **100%** | 98.0% | 全程穩定 |
| Reflection | 48.7% | 72.7% | 74.7% | 隨複雜度上升而改善 |
| PlanExecute | 98.7% | 97.3% | **98.7%** | 最穩定 |

### 2. Judge 品質跨 Persona 對比

| 架構 | Polite | Adversarial | VIP | 最高點 |
|------|--------|------------|-----|--------|
| Single-slot | 59.00 | 50.60 | 62.73 | VIP |
| **ReAct** | 66.17 | 70.20 | **72.98** | VIP（持續上升）|
| Reflection | 54.73 | 63.05 | 64.43 | VIP |
| PlanExecute | 63.56 | 63.60 | 65.50 | VIP（最穩定）|

- ReAct 品質隨 persona 複雜度單調遞增，VIP 下達到三個 persona 的最高分
- PlanExecute 跨 persona 品質最穩定，波動不超過 2 分
- Single-slot 在 Adversarial 下品質崩跌（-8.4 分），VIP 下回升

### 3. 成本效益跨 Persona 對比（Judge / 萬 token）

| 架構 | Polite | Adversarial | VIP |
|------|--------|------------|-----|
| Single-slot | 23.7 | 19.0 | 27.6 |
| ReAct | 34.7 | 27.2 | **42.3** |
| Reflection | 6.1 | 8.7 | 8.6 |
| PlanExecute | **42.7** | **30.4** | 42.2 |

### 4. 全局建議

| 使用情境 | 推薦架構 | 理由 |
|---------|---------|------|
| 成本優先 | **PlanExecute** | 三個 persona 均最省 token，完成率 97-99% |
| 品質優先 | **ReAct** | VIP 下 72.98，Adversarial 下 70.20，品質最高 |
| 均衡選擇 | **ReAct** or **PlanExecute** | 效益相近，依成本預算取捨 |
| 不建議 | **Reflection** | 高成本、效益最差，三個 persona 均墊底 |
| 不建議 | **Single-slot** | Adversarial 下崩跌明顯，整體完成率低 |
