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

---

## 敏感度分析（PSS — Prompt Sensitivity Score）

### 方法說明

借用 ProSA（Zhuo et al., 2024）的 PSS 框架，衡量同一案例在不同客戶表達風格（Polite / Adversarial / VIP）下的品質一致性。

對每個 case i，計算三個 persona 之間 judge 分數的平均絕對差距：

```
PSS_i = (|score_P - score_A| + |score_P - score_V| + |score_A - score_V|) / 3
```

整體 PSS = 所有 case 的 PSS_i 均值。**PSS 越低 = 架構對客戶風格越穩健。**

> 本研究的 PSS 測量的是「客戶表達風格敏感性」，與 ProSA 原版測量「instruction prompt 寫法敏感性」在概念上等價，但切入點更貼近真實客服部署情境。

---

### 1. 整體 PSS 比較

| 架構 | PSS 均值 | PSS 最大值 | PSS 標準差 | 高敏感案例 (PSS > 20) |
|------|---------|----------|----------|----------------------|
| Single-slot | 25.08 | 63.33 | 19.71 | 70 筆 (47%) |
| ReAct | 20.27 | 63.33 | 17.54 | 69 筆 (46%) |
| Reflection | 28.70 | 63.33 | 16.69 | 97 筆 (65%) |
| **PlanExecute** | **17.96** | 63.33 | 17.80 | 52 筆 (35%) |

- **PlanExecute 敏感度最低（最穩健）**，PSS = 17.96
- Reflection 敏感度最高，近三分之二的案例 PSS 超過 20
- 四個架構的 PSS 最大值均為 63.33（即某些案例在三種 persona 間分數差距極大）

---

### 2. Pairwise Persona Delta（各組 persona 間平均絕對差距）

| 架構 | Polite vs Adversarial | Polite vs VIP | Adversarial vs VIP |
|------|----------------------|--------------|-------------------|
| Single-slot | 28.67 | 19.40 | 27.17 |
| ReAct | 20.37 | 21.62 | 18.82 |
| Reflection | **32.32** | **30.93** | 22.85 |
| **PlanExecute** | 20.48 | **15.48** | **17.90** |

- Reflection 在 Polite vs Adversarial 間落差最大（32.32）——對攻擊性對話最無法穩定應對
- PlanExecute 在所有 pair 中表現最一致，尤其 Polite vs VIP 差距僅 15.48
- ReAct 三個 pair 的 delta 最為平衡（18.82–21.62），無明顯弱點

---

### 3. PSS 分布

| 架構 | 低敏感 PSS ≤ 10 | 中敏感 10–30 | 高敏感 PSS > 30 |
|------|---------------|------------|----------------|
| Single-slot | 45 (30%) | 52 (35%) | 53 **(35%)** |
| ReAct | 57 (38%) | 46 (31%) | 47 (31%) |
| Reflection | 24 **(16%)** | 59 (39%) | 67 **(45%)** |
| **PlanExecute** | **66 (44%)** | 48 (32%) | 36 (24%) |

- PlanExecute 有 44% 的案例屬於低敏感，高敏感僅 24%
- Reflection 只有 16% 低敏感，45% 高敏感——品質最不一致
- ReAct 分布居中，高敏感比例（31%）在四者中第二低

---

### 4. 完成率跨 Persona 一致性

| 架構 | 三 persona 全數解決 | 部分 PENDING（混合） | 三 persona 全部 PENDING |
|------|-------------------|-------------------|------------------------|
| Single-slot | 60 (40%) | 53 (35%) | 37 **(25%)** |
| **ReAct** | **147 (98%)** | 3 (2%) | 0 (0%) |
| Reflection | 49 (33%) | 94 **(63%)** | 7 (5%) |
| **PlanExecute** | **143 (95%)** | 7 (5%) | 0 (0%) |

- ReAct 有 98% 的案例在三個 persona 下均成功解決，完成率一致性最高
- Reflection 的 63% 案例落在「混合」狀態——同一個問題，有些 persona 解決、有些沒有，一致性最差
- Single-slot 有 25% 的案例在所有 persona 下均失敗，顯示其在某類問題上存在系統性缺陷

---

### 5. 敏感度分析綜合結論

| 維度 | 最穩健 | 最脆弱 |
|------|-------|-------|
| PSS 均值（品質穩定性）| **PlanExecute（17.96）** | Reflection（28.70）|
| Polite vs Adversarial 落差 | PlanExecute | Reflection |
| 完成率一致性 | **ReAct（98% 全解）** | Single-slot（25% 全失）|
| 低敏感案例比例 | **PlanExecute（44%）** | Reflection（16%）|

**PlanExecute 是品質敏感度最低的架構**——面對不同類型的客戶，輸出品質最穩定。**ReAct 的完成率一致性最高**——幾乎不會因客戶風格而影響任務解決率。兩者均適合需要穩健部署的場景，Reflection 和 Single-slot 則在敏感度各指標上均表現較差。

---

## ProSA 分析（Prompt Sensitivity by Task Category）

### 方法說明

延伸敏感度分析，參照 ProSA（Zhuo et al., EMNLP 2024）的 instance-level PSS 框架，進一步拆解敏感度的**任務來源**與**難度分層**。分析維度：

1. **Intent 分層 PSS**：哪類客服請求最容易因客戶表達風格而產生品質落差？
2. **Difficulty 分層 PSS**：案例難度是否影響敏感度？
3. **PSS vs 品質相關性**：敏感度高的案例，品質是否也較低？

資料來源：（intent、difficulty_level）× 1,800 筆 judge 分數。

---

### 1. PSS by Intent（合併四架構）

| Intent | n | PSS 均值 | 平均 Judge 分 |
|--------|---|---------|-------------|
| cancel_order | 56 | **29.97** | 67.31 |
| check_refund_policy | 44 | **29.92** | 67.88 |
| delivery_options | 52 | 27.34 | 74.71 |
| change_order | 8 | 27.29 | 78.54 |
| place_order | 16 | 26.15 | 39.22 |
| get_refund | 44 | 25.61 | 49.43 |
| track_order | 40 | 24.67 | 47.23 |
| recover_password | 4 | 23.75 | 30.21 |
| payment_issue | 40 | 23.42 | 36.75 |
| delivery_period | 68 | 23.16 | 46.91 |
| check_payment_methods | 80 | 21.94 | 85.14 |
| get_invoice | 4 | 20.83 | 34.38 |
| set_up_shipping_address | 60 | 16.58 | 82.19 |
| track_refund | 36 | 15.05 | 33.31 |
| **change_shipping_address** | 48 | **13.58** | 84.72 |

**關鍵發現：**
- **最敏感**：（PSS 29.97）和 （29.92）——這類任務有明確的可執行動作，但成功與否高度依賴客戶表達的清晰度，Adversarial 表達方式容易導致 agent 判斷失誤
- **最穩健**：（PSS 13.58）和 （16.58）——這類任務有固定的政策回應（不支援修改），不論客戶語氣如何，synthesis 層都能穩定輸出模板答案
- **高分但高敏感**：（PSS 27.29，avg 78.54）——表示有些 persona 表現極佳，有些則失敗，分數方差大

---

### 2. PSS by Difficulty Level

| 難度 | n | PSS 均值 | 平均 Judge 分 |
|------|---|---------|-------------|
| 1（簡單）| 200 | **24.93** | 69.55 |
| 2（中等）| 200 | 21.57 | 65.15 |
| 3（困難）| 200 | 22.50 | 54.74 |

**反直覺發現**：難度 1（簡單案例）的 PSS 反而最高。

ProSA 原論文發現困難任務（MATH）PSS 較高，但在本研究中呈相反趨勢。可能的解釋：
- 簡單案例本身有能力被解決，**不同 persona 的表達方式才有機會產生品質分化**——Polite 下完美，Adversarial 下可能失誤
- 困難案例（如 、）在三個 persona 下往往**一致性地失敗**，分數均低，因此 PSS（差距）反而小

這一現象說明：**PSS 高不一定代表任務困難，而是代表任務的成功對表達風格更敏感。**

---

### 3. Per-Architecture PSS by Intent（節選高差異 intent）

| Intent | Single-slot | ReAct | Reflection | PlanExecute |
|--------|------------|-------|-----------|------------|
| cancel_order | **48.7** | 17.1 | 22.6 | 31.4 |
| change_shipping_address | 13.6 | 9.9 | 29.0 | **1.8** |
| check_refund_policy | 32.6 | 28.5 | 29.4 | 29.2 |
| delivery_options | 38.8 | 22.9 | 31.8 | 15.8 |
| get_refund | 30.9 | 18.6 | 28.3 | 24.5 |
| set_up_shipping_address | 11.1 | **8.9** | 34.8 | 11.6 |
| track_refund | 21.9 | **10.7** | 17.8 | 9.8 |

**架構特性分析：**
-  對 Single-slot 的衝擊最大（PSS 48.7）——面對攻擊性客戶的取消請求，Single-slot 幾乎必然失誤
- PlanExecute 在  的 PSS 僅 1.8，近乎完全穩定——synthesis 模板對此意圖有完美覆蓋
- Reflection 在  的 PSS 高達 34.8，遠超其他架構——顯示其 synthesis 覆蓋在此意圖上不完整

---

### 4. PSS 與品質的相關性

| 架構 | PSS vs Judge 相關係數 (r) |
|------|------------------------|
| Single-slot | -0.085 |
| ReAct | **-0.293** |
| Reflection | -0.008 |
| PlanExecute | -0.229 |

- 所有架構均呈**負相關**：PSS 越高（越敏感），平均品質越低
- ReAct 相關性最強（r = -0.293）：敏感的案例對 ReAct 影響最大，品質下滑明顯
- Reflection 幾乎無相關（r = -0.008）：無論案例敏感與否，Reflection 的品質本就高度不穩定，PSS 無法解釋其變異

---

### 5. ProSA 分析綜合結論

| 維度 | 發現 |
|------|------|
| 最敏感意圖 | 、（有動作但成功高度依賴表達） |
| 最穩健意圖 | 、（固定政策回應，synthesis 完整覆蓋）|
| 難度 vs 敏感性 | 簡單案例 PSS 反而最高（能做到才有分化空間） |
| PSS-品質相關性 | ReAct 最強（-0.29），敏感 = 品質風險；Reflection 幾乎無關 |
| 架構建議 | PlanExecute 在大多數意圖下敏感度最低，適合需穩健部署的場景 |
