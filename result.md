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

## 平均對話輪數（Dialogue Turns）

> 輪數 = 每個對話 log 的最後一筆 `turn` 值，代表客戶與 agent 完成一次完整對話所需的來回次數。  
> 資料來源：全部 1,944 筆 insample logs（4 架構 × 162 case × 3 persona）。

---

### 1. 各架構總體均值

| 架構 | 平均輪數 | 中位數 | 最少 | 最多 |
|------|---------|--------|------|------|
| **ReAct** | **2.60** | 2 | 2 | 4 |
| PlanExecute | 3.02 | 3 | 2 | 6 |
| Reflection | 3.67 | 3 | 1 | 6 |
| Single-slot | 4.14 | 4 | 2 | 6 |

- **ReAct 對話最短**：平均 2.6 輪，中位數僅 2——通常一個來回即可解決，極少需要第三輪
- **Single-slot 對話最長**：平均 4.1 輪，即便結構最簡單，卻常陷入重複澄清或無效回應的循環
- PlanExecute 雖然在架構上多了規劃步驟，但最終輪數僅 3.0，效率仍優於 Reflection 與 Single-slot
- Reflection 的 max=1 代表有案例一輪即中止（通常為 REFUSAL），上限 6 輪顯示少數案例在反思循環中耗時

---

### 2. 各架構 × Persona 輪數拆解

| 架構 | Polite | Adversarial | VIP |
|------|--------|------------|-----|
| **ReAct** | 2.30 | 3.35 | **2.15** |
| **PlanExecute** | 2.73 | 3.68 | **2.65** |
| Reflection | 3.86 | 3.92 | **3.24** |
| Single-slot | 4.14 | **4.66** | 3.62 |

- **Adversarial persona 使所有架構的對話輪數增加**：平均多 0.6–1.0 輪，對 Single-slot 衝擊最大（+0.5 輪）
- **VIP persona 輪數最短**：VIP 客戶表達精確，agent 需要的澄清輪次更少
- ReAct 在 VIP 下的 2.15 輪是所有組合中最低，幾乎每次一個來回就能解決

---

### 3. 輪數 vs 完成率交叉解讀

| 架構 | 平均輪數 | 完成率（均值）| 解讀 |
|------|---------|-------------|------|
| **ReAct** | **2.60** | **99.8%** | 少輪高效，邊做邊決策不拖延 |
| **PlanExecute** | 3.02 | 98.2% | 多規劃 step 輕微拉長，但仍高效 |
| Reflection | 3.67 | 65.4% | 多輪反思卻完成率低，輪數用於反思而非解決 |
| Single-slot | 4.14 | 59.5% | 輪數最多但完成率最低，反覆來回卻無效 |

- ReAct「少輪 + 高完成率」的組合最理想：高效且有效
- Single-slot / Reflection 的輪數多反而代表對話陷入困境，不代表問題更深入解決
- **輪數多 ≠ 品質好**：Reflection 平均 3.67 輪但 Judge 均分只有 60.7，Single-slot 4.14 輪但均分只有 57.4

---

## S_Agent 綜合評分

### 評分公式（立場 A — 以客戶為中心）

```
S_Agent = 0.50 × S_Outcome   +  0.20 × S_Tool  +  0.10 × S_Trajectory  +  0.20 × S_Efficiency
```

> W_Outcome 設為 0.50，反映「有沒有真正解決問題」是 CS agent 最核心的衡量標準。  
> W_Trajectory 降低至 0.10，因為推理軌跡是 agent 的內部過程，客戶感受不到。  
> 資料來源：全部 1,800 筆 insample logs。

---

### 1. 各架構子分項均值

| 架構 | S_Outcome | S_Tool | S_Trajectory | S_Efficiency | **S_Agent** |
|------|-----------|--------|--------------|--------------|-------------|
| **PlanExecute** | 79.0 | **72.8** | **99.4** | 97.0 | **83.07** |
| Single-slot | 74.4 | 71.7 | **99.9** | 85.2 | 78.53 |
| ReAct | **81.8** | 47.7 | 63.1 | **98.0** | 76.37 |
| Reflection | 75.2 | 67.8 | **100.0** | 23.6 | 65.80 |

**子分項解讀：**
- **S_Outcome**：ReAct 最高（81.8）——它的迭代推理讓它在真正解決問題上勝過其他架構
- **S_Tool**：ReAct 最低（47.7）——ReAct 的工具呼叫錯誤率高，常呼叫錯誤工具或傳錯參數
- **S_Trajectory**：Reflection / PlanExecute / Single-slot 均接近 100，ReAct 只有 63.1——ReAct 的 reason-act 迭代循環產生較多冗餘步驟
- **S_Efficiency**：Reflection 嚴重墊底（23.6）——token 用量是 PlanExecute 的 6 倍，效率懲罰最重

---

### 2. 整體 S_Agent 排名

| 排名 | 架構 | S_Agent | vs #1 |
|------|------|---------|-------|
| #1 | **PlanExecute** | **83.07** | — |
| #2 | Single-slot | 78.53 | -4.54 |
| #3 | ReAct | 76.37 | -6.70 |
| #4 | Reflection | 65.80 | -17.27 |

PlanExecute 在四個子分項中沒有任何一項是第一，但它在每個維度都表現穩健，沒有明顯弱點，最終以均衡優勢奪冠。

---

### 3. S_Agent 跨 Persona 比較

| 架構 | Polite | Adversarial | VIP | 波動幅度 |
|------|--------|------------|-----|---------|
| **PlanExecute** | **82.77** | **82.40** | **84.05** | **1.65** |
| Single-slot | 78.69 | 76.71 | 80.18 | 3.47 |
| ReAct | 76.20 | 74.92 | 77.99 | 3.07 |
| Reflection | 64.62 | 65.78 | 66.99 | 2.37 |

- PlanExecute 跨 persona 波動最小（1.65 分），與 PSS 分析結論一致
- 所有架構在 VIP persona 下 S_Agent 最高，Adversarial 下最低

---

### 4. 權重敏感度分析摘要

針對 969 種合法 weight 組合（每個 weight ≥ 0.05，四者總和 = 1，步長 0.05）掃描排名穩定性：

| 架構 | 排名 #1 | 排名 #2 | 排名 #3 | 排名 #4 |
|------|---------|---------|---------|---------|
| **PlanExecute** | **100%** | 0% | 0% | 0% |
| Single-slot | 0% | **87%** | 13% | 0% |
| ReAct | 0% | 13% | 46% | 41% |
| Reflection | 0% | 0% | 41% | 59% |

**PlanExecute 在所有 969 種 weight 組合下均排名第一，結論零例外。**  
這代表「PlanExecute 是最佳架構」這個結論對評分公式的設計假設完全穩健，不受 weight 選擇影響。

---

### 5. 綜合結論

| 維度 | 最強 | 最弱 |
|------|------|------|
| 整體 S_Agent | **PlanExecute（83.07）** | Reflection（65.80）|
| 問題解決品質（S_Outcome）| **ReAct（81.8）** | Single-slot（74.4）|
| 工具使用正確性（S_Tool）| **PlanExecute（72.8）** | ReAct（47.7）|
| 對話效率（S_Efficiency）| **ReAct（98.0）** | Reflection（23.6）|
| 排名穩健性 | **PlanExecute（100% #1）** | Reflection（0% top-2）|

**PlanExecute 是推薦的生產部署架構**，在客戶導向評分下各維度均衡且排名完全穩健。  
ReAct 的問題解決品質最高（S_Outcome 81.8），若場景允許略高的工具錯誤率，也是可行選擇。  
Reflection 因效率極低，在實際部署中成本效益最差，不建議採用。

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

---

---

# Out-of-Sample（OOS）泛化評估結果

> **資料來源**：50 筆 OOS 案例 × 4 架構 × 3 Persona = **600 場對話**  
> OOS 案例涵蓋 15 種意圖（含 `track_return`、`missing_item`、`fraud_dispute`、`product_inquiry` 等訓練分布外新意圖，以及 `track_order`、`cancel_order` 等與 in-sample 重疊的意圖）。  
> 成本代理指標改以**執行秒數（execution_seconds）**取代 token 數（OOS 日誌未統一記錄 token 用量）。

---

## OOS — Polite Persona

### 1. 任務完成率

| 架構 | SUCCESS | FAILED_INCOMPLETE | LOOP_FAILURE | 完成率 |
|------|---------|------------------|-------------|--------|
| Single-slot | 22 | 23 | 5 | 44% |
| ReAct | 29 | 0 | 21 | 58% |
| **PlanExecute** | **49** | 0 | 1 | **98%** |
| Reflection | 28 | 20 | 2 | 56% |

- PlanExecute 維持 98% 完成率，與 in-sample 幾乎相同
- **ReAct 完成率大幅下滑**：in-sample 99.3% → OOS 58%，21 筆 LOOP_FAILURE；面對分布外意圖，ReAct 的迭代推理無法收斂
- Single-slot / Reflection 完成率皆不足 60%，表現與 in-sample 相近或更差

### 2. 品質（LLM-as-Judge）

| 架構 | Judge 均分 /100 | s_resolution /5 | s_completeness /5 | s_tone /5 |
|------|----------------|-----------------|------------------|----------|
| Reflection | **32.7** | 1.92 | 2.00 | 3.74 |
| ReAct | 36.2 | 2.18 | 1.92 | **3.92** |
| Single-slot | 32.4 | 2.02 | 2.08 | 3.30 |
| PlanExecute | 29.4 | 1.86 | 1.76 | 3.60 |

- **四架構 Judge 均分全面崩跌**：in-sample Polite 均分 54–66，OOS 僅 29–36
- PlanExecute 出現悖論：完成率最高（98%）但 Judge 均分最低（29.4）——Immediate Synthesis 以「I can help with tracking/cancellation/refund」結束對話，runner 判定 SUCCESS，但 Judge 評分為顧客需求完全未被回應
- s_resolution 全架構均約 1.9（接近滿分 5 的最低段），顯示 OOS 意圖幾乎無法被正確解決
- s_tone 仍維持 3.3–3.9，語氣表現相對穩定，是唯一未明顯下滑的維度

### 3. 執行時間（成本代理）

| 架構 | 平均秒數 | 相對倍數 | Judge / 秒 × 10 |
|------|---------|---------|----------------|
| **ReAct** | **32.8s** | **1.0×** | **11.0** |
| PlanExecute | 36.0s | 1.1× | 8.2 |
| Single-slot | 54.5s | 1.7× | 5.9 |
| Reflection | 228.7s | **7.0×** | **1.4** |

- Reflection 在 OOS 下的執行時間是 ReAct 的 7 倍，但品質幾乎持平，效益最差
- ReAct 成本最低且品質最高，OOS Polite 下效益最佳（11.0）

### 4. S_Agent 子分項

| 架構 | S_Outcome | S_Tool | S_Trajectory | S_Efficiency | **S_Agent** |
|------|-----------|--------|--------------|-------------|-------------|
| **PlanExecute** | 56 | **79** | 98 | **100** | **73.8** |
| Single-slot | 53 | 75 | **100** | 90 | 69.6 |
| ReAct | **61** | 54 | 72 | 99 | 68.3 |
| Reflection | 49 | 62 | **100** | 32 | 53.3 |

- S_Trajectory 方面，ReAct 大幅下降（in-sample 63.1 → OOS Polite 72）：新意圖使 ReAct 的 reason-act 循環更容易進入死循環
- Reflection S_Efficiency 嚴重拖累（32），反思機制在 OOS 下產生大量無效迭代

---

## OOS — Adversarial Persona

### 1. 任務完成率

| 架構 | SUCCESS | FAILED_INCOMPLETE | LOOP_FAILURE | 完成率 |
|------|---------|------------------|-------------|--------|
| Single-slot | 23 | 21 | 6 | 46% |
| ReAct | 37 | 0 | 13 | 74% |
| **PlanExecute** | **46** | 3 | 1 | **92%** |
| Reflection | 43 | 6 | 1 | 86% |

- ReAct 相比 Polite 有所回升（58% → 74%）：Adversarial persona 的一次抵抗後提供 ID，反而加速進入工具呼叫，減少 LOOP
- Reflection 在 Adversarial 下完成率最高（86%），可能因情境觸發了更多程式化合成路徑

### 2. 品質（LLM-as-Judge）

| 架構 | Judge 均分 /100 | s_resolution /5 | s_completeness /5 | s_tone /5 |
|------|----------------|-----------------|------------------|----------|
| ReAct | **31.9** | **2.22** | 1.90 | 2.98 |
| Reflection | 29.4 | 1.94 | 1.80 | **3.32** |
| Single-slot | 23.3 | 1.78 | 1.78 | 2.54 |
| PlanExecute | 22.1 | 1.66 | 1.60 | 2.88 |

- 所有架構品質相比 Polite 進一步下滑（均降 6–8 分）
- s_tone 在 Adversarial 下普遍降低（特別是 Single-slot 2.54、ReAct 2.98），面對攻擊性客戶語氣受影響
- PlanExecute 在 Adversarial 下 Judge 均分墊底（22.1），PE Synthesis 模板對攻擊性語境更顯生硬

### 3. 執行時間（成本代理）

| 架構 | 平均秒數 | Judge / 秒 × 10 |
|------|---------|----------------|
| **ReAct** | **42.8s** | **7.5** |
| Single-slot | 54.7s | 4.3 |
| PlanExecute | 45.1s | 4.9 |
| Reflection | 166.5s | 1.8 |

### 4. S_Agent 子分項

| 架構 | S_Outcome | S_Tool | S_Trajectory | S_Efficiency | **S_Agent** |
|------|-----------|--------|--------------|-------------|-------------|
| **PlanExecute** | 53 | **77** | **100** | 98 | **71.4** |
| Single-slot | 49 | 75 | **100** | **95** | 68.6 |
| ReAct | **58** | 54 | 50 | **100** | 64.6 |
| Reflection | 56 | 79 | **100** | 37 | 61.1 |

- **ReAct S_Trajectory = 50**：Adversarial 的一次抵抗加上 OOS 意圖不確定性，導致 ReAct 反覆嘗試工具呼叫後仍無法收斂，路徑品質大幅惡化
- Reflection S_Tool 上升至 79，在此 persona 下表現異常優秀——可能因攻擊性語境觸發更直接的工具呼叫決策

---

## OOS — VIP Persona

### 1. 任務完成率

| 架構 | SUCCESS | FAILED_INCOMPLETE | LOOP_FAILURE | 完成率 |
|------|---------|------------------|-------------|--------|
| Single-slot | 26 | 16 | 8 | 52% |
| **ReAct** | **48** | 0 | 2 | **96%** |
| **PlanExecute** | **49** | 0 | 1 | **98%** |
| **Reflection** | **49** | 0 | 1 | **98%** |

- VIP persona 使 ReAct 和 Reflection 的完成率大幅回升：VIP 客戶表達明確、目標清晰，OOS 意圖雖然新穎，但對話結構較有規律，agent 更容易找到收斂路徑
- Reflection 在 VIP 下達到 98%，與 PlanExecute 並列第一——與 Polite 的 56% 對比巨大

### 2. 品質（LLM-as-Judge）

| 架構 | Judge 均分 /100 | s_resolution /5 | s_completeness /5 | s_tone /5 |
|------|----------------|-----------------|------------------|----------|
| **Reflection** | **38.4** | 2.16 | 1.88 | **4.46** |
| ReAct | 37.8 | **2.26** | 1.78 | 4.24 |
| Single-slot | 35.4 | 2.00 | **2.30** | 3.62 |
| PlanExecute | 30.4 | 1.92 | 1.84 | 3.52 |

- VIP 下 Judge 均分最高，四架構均較 Adversarial 回升
- **Reflection 品質反超 ReAct**（38.4 vs 37.8）：VIP 情境下 Reflection 的多輪反思找到了更自然的語調，s_tone = 4.46 是所有 OOS 組合中最高
- PlanExecute 品質仍墊底（30.4）：PE Synthesis 模板對 VIP 的尊貴語境最不適配

### 3. 執行時間（成本代理）

| 架構 | 平均秒數 | Judge / 秒 × 10 |
|------|---------|----------------|
| **ReAct** | **27.3s** | **13.8** |
| PlanExecute | 34.6s | 8.8 |
| Single-slot | 56.6s | 6.3 |
| Reflection | 108.7s | 3.5 |

- VIP 下 ReAct 最快（27.3s）且品質第二高，成本效益（13.8）是三個 persona 中最佳

### 4. S_Agent 子分項

| 架構 | S_Outcome | S_Tool | S_Trajectory | S_Efficiency | **S_Agent** |
|------|-----------|--------|--------------|-------------|-------------|
| **PlanExecute** | 58 | **79** | **99** | **100** | **74.4** |
| Single-slot | 57 | 76 | **100** | 89 | 71.6 |
| Reflection | **63** | **80** | **100** | 52 | 68.0 |
| ReAct | 53 | 54 | 75 | 99 | 64.6 |

- Reflection 在 VIP 下 S_Outcome（63）和 S_Tool（80）均達到 OOS 最高值，但 S_Efficiency（52）的低效懲罰拉低了 S_Agent
- ReAct 的 S_Trajectory（75）在 VIP 下略有回升，但仍低於 in-sample（63.1）

---

## OOS 跨 Persona 比較

### 1. 完成率跨 Persona（OOS）

| 架構 | Polite | Adversarial | VIP | 趨勢 |
|------|--------|------------|-----|------|
| Single-slot | 44% | 46% | 52% | 微幅上升，全程低位 |
| ReAct | 58% | 74% | **96%** | VIP 大幅回升（+38pp）|
| PlanExecute | **98%** | 92% | **98%** | 全程穩定高位 |
| Reflection | 56% | 86% | **98%** | Adversarial/VIP 大幅改善 |

### 2. Judge 品質跨 Persona（OOS）

| 架構 | Polite | Adversarial | VIP | 最高點 |
|------|--------|------------|-----|--------|
| Single-slot | 32.4 | 23.3 | 35.4 | VIP |
| ReAct | **36.2** | **31.9** | 37.8 | VIP（持續最高）|
| PlanExecute | 29.4 | 22.1 | 30.4 | VIP（全程最低）|
| Reflection | 32.7 | 29.4 | **38.4** | VIP（VIP 反超）|

- 四架構 OOS Judge 均分均集中在 22–38 分，對比 in-sample 的 51–73 分，品質呈系統性崩跌
- **PlanExecute 在三個 persona 下 Judge 均分均最低**，完成率與品質形成最大悖論
- Reflection 在 VIP 下品質最高（38.4），是唯一在某個 persona 下超越 ReAct 的架構

### 3. 執行時間跨 Persona（OOS）

> 單位：秒（execution_seconds）。OOS 未統一記錄 token，以執行秒數作為成本代理。

| 架構 | Polite | Adversarial | VIP | **均值** | 相對倍數 |
|------|--------|------------|-----|---------|---------|
| **ReAct** | **32.8s** | 42.8s | **27.3s** | **34.3s** | **1.0×** |
| PlanExecute | 36.0s | 45.1s | 34.6s | 38.6s | 1.1× |
| Single-slot | 54.5s | 54.7s | 56.6s | 55.3s | 1.6× |
| Reflection | 228.7s | 166.5s | 108.7s | 168.0s | **4.9×** |

- ReAct 在 OOS 下速度最快（in-sample 時 token 用量中等）；其 reason-act 循環在 LOOP 案例中雖多輪，但成功案例收斂很快
- Reflection 仍是最慢架構，Polite 下平均 228.7 秒（近 4 分鐘），但 VIP 下降至 108.7 秒——VIP 對話觸發了較多早期終止路徑

### 4. 成本效益跨 Persona（OOS）

> 指標：Judge 均分 / 秒 × 10（數值越高 = 每單位時間產生的品質越高）

| 架構 | Polite | Adversarial | VIP | **均值效益** |
|------|--------|------------|-----|------------|
| **ReAct** | **11.0** | **7.5** | **13.8** | **10.8** |
| PlanExecute | 8.2 | 4.9 | 8.8 | 7.3 |
| Single-slot | 5.9 | 4.3 | 6.3 | 5.5 |
| Reflection | 1.4 | 1.8 | 3.5 | 2.2 |

- **OOS 下成本效益排名與 in-sample 不同**：in-sample PlanExecute 第一（42.7），OOS 反而 ReAct 第一（10.8）
- PlanExecute 在 OOS 下品質大幅下滑（Judge 均分 22–30），而執行速度維持相近，導致效益排名從第一滑落至第二
- Reflection 效益最差（2.2），Polite 下僅 1.4，每秒產出的品質遠不如其他架構
- Single-slot 效益中等（5.5），執行時間偏長但結構簡單

### 5. S_Agent 跨 Persona（OOS）

| 架構 | Polite | Adversarial | VIP | **OOS 均值** | In-sample 均值 | 跌幅 |
|------|--------|------------|-----|------------|--------------|------|
| **PlanExecute** | **73.8** | **71.4** | **74.4** | **73.2** | 83.07 | -9.9 |
| Single-slot | 69.6 | 68.6 | 71.6 | 70.0 | 78.53 | -8.5 |
| ReAct | 68.3 | 64.6 | 64.6 | 65.8 | 76.37 | **-10.6** |
| Reflection | 53.3 | 61.1 | 68.0 | 60.8 | 65.80 | -5.0 |

- **ReAct 跌幅最大（-10.6 分）**：in-sample 下靠迭代推理解決問題，OOS 新意圖讓推理循環無法收斂，S_Trajectory 大幅惡化
- **Reflection 跌幅最小（-5.0 分）**：本身在 in-sample 表現已低，OOS 下跌空間有限；且 Programmatic Synthesis 在某些情境意外提供了穩定的輸出
- **排名逆轉**：in-sample ReAct > Single-slot（76.37 vs 78.53），OOS Single-slot > ReAct（70.0 vs 65.8）

---

## OOS S_Agent 總體子分項分析

| 架構 | S_Outcome | S_Tool | S_Trajectory | S_Efficiency | **S_Agent（OOS）** | **S_Agent（In-sample）** |
|------|-----------|--------|--------------|-------------|-----------------|---------------------|
| **PlanExecute** | 56 | **78** | **99** | **99** | **73.2** | 83.07 |
| Single-slot | 53 | 75 | **100** | 91 | 70.0 | 78.53 |
| ReAct | **57** | 54 | 66 | **99** | 65.8 | 76.37 |
| Reflection | 56 | 74 | **100** | 40 | 60.8 | 65.80 |

**關鍵發現：**
- **S_Trajectory**：ReAct 在 OOS 下從 63.1 進一步惡化至 66（且 Adversarial 下僅 50）——新意圖讓 ReAct 的 reason-act 循環更難收斂
- **S_Tool**：ReAct 在 OOS 下仍維持 54，與 in-sample（47.7）略有改善——工具呼叫正確性反而不是主要問題
- **S_Efficiency**：Reflection 在 OOS 下降至 40（in-sample 23.6 → OOS 40）反而略有改善，因反思循環在部分 OOS 案例中提早終止
- **S_Outcome**：四架構均集中在 53–57，差距縮小——OOS 下所有架構的問題解決能力趨於相近

---

## OOS 權重敏感度分析

### 方法說明

與 in-sample 相同，對 S_Agent 公式的四個 weight 進行全量掃描（step=0.05，每個 weight ≥ 0.05，加總=1），共 **969 種**合法組合，針對 OOS 600 筆紀錄重新計算各架構 S_Agent 均值並記錄排名。

---

### 1. Rank Frequency（各排名出現比例）

| 架構 | Rank 1 | Rank 2 | Rank 3 | Rank 4 |
|------|--------|--------|--------|--------|
| **PlanExecute** | **99.9%** | 0.1% | 0.0% | 0.0% |
| Single-slot | 0.1% | **94.6%** | 5.3% | 0.0% |
| ReAct | 0.0% | 5.3% | **43.7%** | 51.1% |
| Reflection | 0.0% | 0.0% | 51.1% | **48.9%** |

### 2. Top-1 穩定性

| 指標 | 數值 |
|------|------|
| 基準 Top-1 | PlanExecute |
| Top-1 不變的 weight 組合數 | **968 / 969（99.9%）** |
| 唯一翻轉條件 | W_Trajectory = 0.85（其餘各 0.05）→ Single-slot 以 95.7 奪冠 |

**PlanExecute 在 OOS 下的排名穩健性與 in-sample 幾乎相同（in-sample 100%，OOS 99.9%）**，只有在「軌跡權重極端誇大（85%）」的非現實條件下才被翻轉。

### 3. 分數區間

| 架構 | 最低分 | 均分 | 最高分 | 區間幅度 |
|------|--------|------|--------|---------|
| PlanExecute | 61.2 | 82.9 | 95.8 | 34.6 |
| Single-slot | 58.5 | 80.0 | 95.7 | 37.2 |
| ReAct | 57.0 | 69.1 | 93.2 | 36.2 |
| Reflection | 45.8 | 67.5 | 93.2 | **47.3** |

- Reflection 的分數區間最大（47.3），顯示其 S_Agent 對 weight 設計最敏感——S_Efficiency 極低，一旦效率權重降低，其他維度的優勢就顯現
- PlanExecute 均分（82.9）與 Single-slot（80.0）差距在 OOS 下縮小（in-sample 差 4.5 分，OOS 均值差縮至 2.9）

---

## OOS ProSA 分析（Prompt Sensitivity Score）

### 方法說明

與 in-sample PSS 相同，以三個 persona 之間的 Judge 均分（s_answer_quality）計算各 case 的 PSS_i：

```
PSS_i = (|score_Polite - score_Adversarial| + |score_Polite - score_VIP| + |score_Adversarial - score_VIP|) / 3
```

> **注意**：OOS Judge 均分集中在 22–38 分（vs in-sample 51–73），分數範圍壓縮，OOS PSS 絕對值天然偏小，重點看**架構間相對排名**，而非與 in-sample 數字直接比較。

---

### 1. 整體 PSS 比較（OOS）

| 架構 | PSS 均值 | PSS 最大值 | PSS 標準差 | PSS > 20（高敏感） |
|------|---------|----------|----------|-----------------|
| **ReAct** | **17.20** | 60.00 | 12.78 | 10（20%）|
| **PlanExecute** | 18.33 | 63.33 | 15.89 | 12（24%）|
| Reflection | 20.13 | 63.33 | 14.09 | 18（36%）|
| Single-slot | 20.87 | 63.33 | 18.33 | 18（36%）|

- **OOS 下 ReAct PSS 最低（最穩健）**，與 in-sample 結果相反（in-sample ReAct PSS = 20.27，PlanExecute 最低 17.96）
- Single-slot PSS 最高（20.87），OOS 下跨 persona 品質最不一致
- 四架構最大值均達到 63.33，表示每個架構都有某些 case 在三個 persona 間分數差距極大

### 2. Pairwise Persona Delta（OOS）

| 架構 | Polite vs Adversarial | Polite vs VIP | Adversarial vs VIP |
|------|----------------------|--------------|-------------------|
| **ReAct** | **15.97** | 20.35 | **15.61** |
| PlanExecute | 18.00 | **16.35** | 20.65 |
| Reflection | 23.35 | 19.00 | 18.05 |
| Single-slot | **24.35** | 17.20 | 21.05 |

- Single-slot 在 Polite vs Adversarial 落差最大（24.35）——與 in-sample 結論一致，攻擊性客戶讓 Single-slot 品質崩跌
- Reflection 在 Polite vs Adversarial 也高（23.35），但 Adversarial vs VIP 相對穩定（18.05）
- ReAct 的三組 pair delta 最為均衡（15.61–20.35），無明顯弱點 persona

### 3. PSS 分布（OOS）

| 架構 | 低敏感 PSS ≤ 10 | 中敏感 10–20 | 高敏感 PSS > 20 |
|------|--------------|------------|---------------|
| PlanExecute | 18（36%）| 20（40%）| 12（24%）|
| **ReAct** | **16（32%）**| **24（48%）**| **10（20%）**|
| Reflection | 14（28%）| 18（36%）| 18（36%）|
| Single-slot | 18（36%）| 14（28%）| 18（36%）|

- ReAct 高敏感案例最少（20%），Reflection / Single-slot 並列最多（36%）
- PlanExecute 低敏感比例最高（36%），適合需要跨客戶風格穩定輸出的場景

### 4. PSS by Difficulty（OOS）

| 難度 | n | PSS 均值 | Judge 均分 |
|------|---|---------|----------|
| easy | 60 | 19.11 | 33.44 |
| medium | 68 | 20.39 | 32.77 |
| hard | 72 | **17.96** | 29.00 |

- **OOS 下困難案例 PSS 反而最低（17.96）**：新意圖的困難案例在三個 persona 下均一致低分（均分 29.0），差距自然縮小——「一致失敗」讓 PSS 小
- Easy 案例 PSS 反而偏高（19.11），因部分 overlapping 意圖（如 track_order）在 easy 難度下偶有高分，形成跨 persona 的分差

### 5. PSS by Intent（OOS）

| Intent | n | PSS 均值 | Judge 均分 | 類型 |
|--------|---|---------|---------|------|
| **cancel_order** | 16 | **39.90** | 56.41 | 重疊意圖 |
| return_request | 4 | 30.00 | 30.62 | 新意圖 |
| payment_issue | 16 | 26.56 | 28.23 | 重疊意圖 |
| change_order | 4 | 22.92 | 80.62 | 重疊意圖 |
| get_refund | 32 | 21.93 | 38.46 | 重疊意圖 |
| cancel_return | 4 | 20.83 | 25.83 | 新意圖 |
| product_inquiry | 12 | 18.89 | 22.99 | 新意圖 |
| track_order | 36 | 15.83 | 40.00 | 重疊意圖 |
| track_return | 40 | 12.83 | 18.67 | 新意圖 |
| missing_item | 8 | 12.08 | 22.50 | 新意圖 |
| installation_request | 8 | 8.75 | 15.73 | 新意圖 |
| **check_warranty** | 4 | **5.83** | 11.46 | 新意圖 |

**關鍵發現 — 重疊意圖 vs 純新意圖的 PSS 分化**：

- **重疊意圖（PSS 高）**：`cancel_order`（39.90）、`payment_issue`（26.56）、`change_order`（22.92）——這些意圖 in-sample 時 agent 有機會成功，OOS 下有些 persona 觸發成功路徑（高分），有些失敗（低分），分差大
- **純新意圖（PSS 低）**：`track_return`（12.83）、`installation_request`（8.75）、`check_warranty`（5.83）——無論哪個 persona，agent 均一致無法處理，三個 persona 分數均偏低，差距自然縮小
- **`cancel_order` PSS 高達 39.90** 的解釋：此意圖在 OOS 下偶爾被 agent 成功執行（Judge 均分 56），Polite 下更容易成功，Adversarial 下常失敗，導致三個 persona 間出現大幅落差

### 6. S_Agent 跨 Persona 一致性（OOS）

> S_Agent ≥ 50 視為「已解決」

| 架構 | 三 persona 全解決 | 混合（部分解決）| 三 persona 全失敗 |
|------|----------------|-------------|----------------|
| **PlanExecute** | **49（98%）** | 1（2%）| 0（0%）|
| ReAct | 45（90%）| 5（10%）| 0（0%）|
| Single-slot | 45（90%）| 5（10%）| 0（0%）|
| Reflection | 26（**52%**）| 24（**48%**）| 0（0%）|

- PlanExecute 在 OOS 下完成一致性最高（98%），幾乎每個 case 在所有 persona 下都能達到 S_Agent ≥ 50
- Reflection 只有 52% 的 case 三個 persona 全部解決，48% 處於混合狀態——同一個 OOS 問題，某些 persona 下成功、某些 persona 下失敗，完成一致性最差
- 值得注意：OOS 下四架構均無「三 persona 全失敗」案例（vs in-sample Single-slot 有 25% 全失敗），說明 OOS 的失敗主要是「品質差」而非「完全無法完成」

### 7. OOS ProSA 綜合結論

| 維度 | 最穩健 | 最脆弱 |
|------|-------|-------|
| PSS 均值（品質穩定性）| **ReAct（17.20）** | Single-slot（20.87）|
| Polite vs Adversarial 落差 | **ReAct（15.97）** | Single-slot（24.35）|
| 完成一致性 | **PlanExecute（98%）** | Reflection（52%）|
| 高敏感案例比例 | **ReAct（20%）** | Reflection / Single-slot（36%）|
| 最敏感意圖 | — | cancel_order（PSS 39.90，重疊意圖高分差）|
| 最穩健意圖 | — | check_warranty（PSS 5.83，新意圖一致低分）|

**OOS 下 ReAct 是品質最穩健的架構**（PSS 17.20），與 in-sample 下 PlanExecute 最穩健的結論相反。這是因為 OOS 壓縮了所有架構的 Judge 分數，而 ReAct 在跨 persona 間的分差最小。**PlanExecute 的完成一致性仍是最高（98%）**，但品質穩定性排第二。Reflection 在 OOS 下完成一致性最差（52%），顯示反思機制對 OOS 新意圖的適應能力最弱。

---

## OOS 整體結論

### 泛化能力排名

| 排名 | 架構 | OOS S_Agent | In-sample S_Agent | 泛化跌幅 | 評語 |
|------|------|------------|-----------------|---------|------|
| #1 | **PlanExecute** | **73.2** | 83.07 | -9.9 | 最佳泛化，Immediate Synthesis 提供穩定結構 |
| #2 | Single-slot | 70.0 | 78.53 | -8.5 | 意外穩健，結構簡單反而減少 OOS 誤判 |
| #3 | ReAct | 65.8 | 76.37 | **-10.6** | 泛化跌幅最大，迭代推理在新意圖下容易失控 |
| #4 | Reflection | 60.8 | 65.80 | -5.0 | 跌幅最小但基礎最低，OOS 下無明顯亮點 |

### 主要 OOS 行為模式

| 現象 | 觀察 | 解釋 |
|------|------|------|
| **PlanExecute 完成率虛高** | 98% SUCCESS 但 Judge 均分僅 29–30 | PE Synthesis 以通用模板結束對話，runner 計為 SUCCESS，但顧客需求未被實際回應 |
| **ReAct LOOP 激增** | Polite LOOP 率 42%（in-sample 幾乎 0） | 新意圖無對應的工具動作，ReAct 在 reason-act 循環中不斷嘗試直到上限 |
| **Single-slot 反超 ReAct** | OOS S_Agent 70.0 > 65.8 | Single-slot 無迭代機制，遇到無法處理的意圖直接結束，反而避免了長時間 LOOP 的懲罰 |
| **全架構 Judge 崩跌** | OOS Judge 22–38 vs In-sample 51–73 | 新意圖（track_return、product_inquiry 等）無法被現有工具集處理，agent 只能給出通用回覆 |
| **Reflection VIP 異常優秀** | VIP 完成率 98%、Judge 38.4（最高）| VIP 對話結構清晰，觸發 Programmatic Synthesis 的機率較低，反思機制反而能有效生成回覆 |
