# Evaluating LLM Agent Architectures for E-Commerce Customer Service: A Simulation-Based Benchmark

---

## 4. Results

### 4.1 In-Sample Evaluation Results (1,800 Conversations)

**Table 1. In-Sample Performance by Architecture (Average across Three Personas)**

| Architecture | Valid Termination Rate | S_Outcome | S_Tool | S_Traj | S_Eff | **S_Agent** | Judge Score |
|------|--------|-----------|--------|--------|-------|-------------|-----------|
| **PlanExecute** | 98.2% | 79.0 | **72.8** | **99.4** | 97.0 | **83.07** | 64.2 |
| Single-slot | 59.5% | 74.4 | 71.7 | **99.9** | 85.2 | 78.53 | 57.4 |
| ReAct | **99.1%** | **81.8** | 47.7 | 63.1 | **98.0** | 76.37 | **69.8** |
| Reflection | 65.4% | 75.2 | 67.8 | **100.0** | 23.6 | 65.80 | 60.7 |

PlanExecute stands out with S_Agent = 83.07. Its lead comes from balanced performance across all dimensions rather than one high score. ReAct has the highest S_Outcome (81.8), but its S_Tool of only 47.7 and S_Traj of 63.1 pull its total score down. Reflection's S_Efficiency of only 23.6 shows a heavy penalty for token usage (average 75,105 tokens, which is 4.4 times higher than PlanExecute). PlanExecute also shows the smallest S_Agent gap across Personas (1.65 points).

### 4.2 Out-of-Sample Generalization Evaluation (600 Conversations)

The OOS dataset contains 9 new intent types not seen in the IS set (such as `track_return`, `missing_item`, `fraud_dispute`), used to test how well each architecture handles unknown tasks.

**Table 2. OOS Performance and Drop from IS**

| Architecture | OOS Valid Termination Rate | **OOS S_Agent** | OOS Judge | IS→OOS S_Agent Drop |
|------|-----------|----------------|-----------|---------------------|
| **PlanExecute** | **96%** | **73.2** | 27.3 | -9.9 |
| Single-slot | 47% | 70.0 | 30.4 | -8.5 |
| ReAct | 76% | 65.8 | **35.3** | **-10.6** |
| Reflection | 80% | 60.8 | 33.5 | -5.0 |

The overall ranking (PE > SS > ReAct > Ref) stays the same in OOS, but ReAct has the largest drop (-10.6). Its Polite Persona LOOP_FAILURE rate reaches 42%, meaning the iterative loop cannot stop when it faces unknown intents. Judge scores fall sharply to 22–38 (compared to IS architecture averages of 57–70), showing that the current tool set cannot handle the new intents. PlanExecute shows an OOS paradox: it has the highest valid termination rate (96%) but the lowest Judge score (27.3). The termination rule marks the conversation as done, but the actual response quality does not meet customer needs.

### 4.3 Cost-Benefit Analysis

**Table 3. ProxyCost / NetValue / ΔMB (Average across Three Personas)**

| Architecture | Token IS | Token OOS | ProxyCost IS | NetValue IS | ΔMB IS | NetValue OOS | ΔMB OOS |
|------|---------|---------|-------------|-------------|--------|-------------|---------|
| **PlanExecute** | **16,999** | **21,222** | **20.83** | **1.429** | **+0.162** | **0.512** | **+0.125** |
| Single-slot | 24,086 | 29,856 | 28.70 | 1.247 | 0 (baseline) | 0.387 | 0 (baseline) |
| ReAct | 20,831 | 21,367 | 30.30 | 1.202 | -0.059 | 0.363 | -0.023 |
| Reflection | 75,105 | 72,928 | 33.90 | 0.938 | -0.267 | 0.274 | -0.113 |

PlanExecute is the only architecture with positive ΔMB in both IS and OOS. Its low-cost advantage holds well in OOS (ΔMB drops only from +0.162 to +0.125). In OOS, all architectures see NetValue fall by about 60% (IS: 0.94–1.43 → OOS: 0.27–0.51). The drop in quality has a much larger effect than the change in cost.

**λ Sensitivity Analysis**

To check whether the choice of λ = 0.01 affects the conclusions, this study scans λ across its full range (λ ∈ [0.001, 0.5]) and recalculates ΔMB for each architecture while keeping S_Agent and ProxyCost fixed.

**Table 5. ΔMB by Architecture at Key λ Values (IS)**

| λ | PlanExecute | ReAct | Reflection |
|---|---|---|---|
| 0.001 | +0.099 | −0.035 | −0.238 |
| **0.01 (adopted)** | **+0.162** | **−0.059** | **−0.267** |
| 0.05 | +0.444 | −0.169 | −0.396 |
| 0.1 | +0.797 | −0.307 | −0.558 |

In IS, the ranking does not change at any λ value. The reason is that PlanExecute has both the highest quality (S_Agent 83.1) and the lowest cost (ProxyCost 20.8), so it dominates Single-slot on both dimensions at once. This means the ranking does not depend on the value of λ.

In OOS, a small local reversal appears: ReAct's ΔMB becomes positive near λ ≈ 0.03, because Single-slot's OOS ProxyCost (31.3) is higher than ReAct's (29.5). When the cost penalty is large enough, the cost gap reverses the quality gap. At λ = 0.01, this reversal has not yet happened (ReAct OOS ΔMB = −0.023), so the λ value used in this study falls within the stable range before the reversal point. Reflection has negative ΔMB at all tested λ values, so its conclusion is not affected by the choice of λ.

### 4.4 Persona Sensitivity (PSS) and Ranking Stability

**Table 4. ProSA PSS and S_Agent Weight Sensitivity**

| Architecture | IS PSS | OOS PSS | IS Rank 1 (969 combinations) | OOS Rank 1 |
|------|--------|---------|----------------------|-----------|
| **PlanExecute** | **17.96** | 18.33 | **100%** | **99.9%** |
| ReAct | 20.27 | **17.20** | 0% | 0% |
| Single-slot | 25.08 | 20.87 | 0% | 0.1% |
| Reflection | 28.70 | 20.13 | 0% | 0% |

PlanExecute ranks first across all 969 valid weight combinations, showing that the study's conclusions are fully stable regardless of how the metrics are weighted. PlanExecute also achieves the lowest PSS in IS (17.96), showing consistent and stable output across all Personas. In OOS, ReAct's PSS drops to the lowest (17.20), reversing its IS rank from second to first by a margin of 1.13 points. PlanExecute's OOS PSS (18.33) is nearly the same as its IS value (17.96), showing that its stability has not gotten worse in OOS, while ReAct's gap across Personas does narrow in OOS. ReAct's lower OOS PSS reflects the fact that unknown intents create the same difficulty for all Personas: in IS there were 47 cases with PSS > 30 (where Persona behavior differences were large enough to affect the outcome), but in OOS only 5 such cases remain. Unknown intents create the same cognitive barrier for all Personas, so the gap between Personas becomes much smaller.

---

## 5. Analysis and Discussion

### 5.1 Quality Analysis

PlanExecute's lead comes from splitting the task into planning and execution, which lowers the cognitive load on the model. Traditional ReAct requires the model to handle reasoning, tool calls, and observation use all at once in each loop. PlanExecute instead breaks the task into two separate stages: the planning stage turns the customer's intent into a clear list of actions, and the execution stage only needs to complete one pre-defined action at a time. For llama3.1:8b, completing a single known action is much easier than doing multi-step reasoning on the fly, and this shows directly in S_Tool (highest overall) and S_Traj's top scores, as well as the smallest S_Agent gap across Personas.

The other three architectures each have their own quality problems rooted in their design. ReAct's tool call quality is notably low. The root cause is that the Thought-Action format places a demand on the model that cannot be removed — llama3.1:8b struggles to keep the format stable when context builds up across multiple turns, and tends to produce good reasoning in the Thought step but then use wrong parameters in the Action step, which also pulls S_Traj down. Reflection's problem is not in tool calls but in the gap between what the self-correction design assumes and what the model can actually do. The three-stage design assumes the model can spot and precisely fix problems in its draft, but in practice llama3.1:8b tends to add more content rather than making targeted fixes, so quality gains are not reflected in proportion in S_Agent, and it ends with the lowest S_Agent overall. Single-slot ranks second in IS, showing that a single-round design can still produce complete responses when the tool set is sufficient, but the lack of any correction step creates a structural ceiling on complex multi-step tasks.

In IS, the S_Agent ranking and the Judge score ranking do not match: ReAct has the highest Judge score but ranks third in S_Agent, while PlanExecute ranks first in S_Agent but only second in Judge score (see Table 1). This gap comes from the fact that the two measures capture different aspects of quality. S_Agent measures process quality, including verifiable execution metrics like tool call accuracy (S_Tool) and conversation format discipline (S_Traj). Judge score measures output quality, where an LLM evaluator judges how helpful and natural the final response sounds from the customer's point of view. ReAct's multi-turn reasoning builds up rich content that makes the final response detailed and clear, so it scores well on output quality. PlanExecute's execution steps are precise and correct, but the responses tend to be shorter and more structured, which leads to a slightly lower Judge score. This gap shows that if Judge score were the only metric, the real risks from ReAct's tool call failures would be hidden, and the multi-dimensional design of S_Agent is specifically meant to avoid this kind of blind spot.

OOS performance differences show how sensitive each architecture's stopping mechanism is to gaps in tool coverage. PlanExecute's stopping mechanism does not depend on a success signal from the tools. After the planning stage creates a list of actions, the execution stage simply works through the list and ends the conversation when done, without needing a successful tool result as a stop condition. This means PlanExecute can finish the conversation in a predictable way even when the tool set cannot handle a new intent, avoiding the endless loop problem. ReAct works in the opposite way: it uses a successful observation as its exit signal, and when the tool set cannot cover an OOS intent, the condition needed to stop the loop is structurally unreachable. The loop keeps running until the repeat-detection mechanism triggers a LOOP_FAILURE (reaching 42% for ReAct's Polite Persona in OOS). Single-slot outperforms ReAct in OOS because a single-round architecture outputs a general response and ends in the first round when it faces an unknown intent, skipping the process where an iterative architecture accumulates penalty with each failed attempt. This shows that when tool coverage is uncertain, failing quickly and predictably scores better overall than trying repeatedly and failing. Reflection has the smallest OOS drop but the lowest absolute score, and the small drop comes from its already low IS starting point rather than from strong generalization — it should not be read as a stability advantage.

The PSS analysis raises a theoretical question: in IS, simple cases have higher PSS than hard cases, which is the opposite of what ProSA (Zhuo et al., 2024) predicts. The real reason is not task difficulty but what this study calls the "success boundary effect." Hard cases are close to failure for all Personas, so scores are clustered in the low range and the gap between Personas is naturally compressed. Simple cases have the potential for success, which means Persona behavior differences are large enough to change the outcome and make the score gap bigger. It is also worth noting that part of the difference from ProSA comes from a difference in how perturbation is applied: ProSA uses prompt rewrites that mainly affect semantic understanding, while this study uses Persona behavior styles that introduce a challenging dynamic across multiple turns. The two approaches trigger different sensitivity mechanisms and should not be directly compared. In OOS, ReAct's lower PSS is a genuine reflection of how the architecture behaves: unknown intents create the same cognitive barrier for all Personas. In IS there were 47 cases with PSS > 30, but in OOS only 5 remain, and the success boundary effect almost disappears.

### 5.2 Cost Analysis

The cost ranking from lowest to highest is PlanExecute < Single-slot < ReAct < Reflection (see Table 3), and it is driven by three separate mechanisms. PlanExecute has the lowest ProxyCost, and it is surprisingly lower than Single-slot. The reason is that its structured division of work keeps each output short: the planning step only produces a short list of actions, and each execution step only needs to complete one pre-defined action. This keeps token usage 29% lower than Single-slot, which is enough to offset the cost of one extra LLM call.

Reflection has the highest ProxyCost because of two overlapping factors: deep pipeline and long outputs. The three-stage design produces at least three full LLM calls per conversation turn, and the Reflection step tends to add more content than the draft rather than making focused fixes. Token usage reaches 4.4 times that of PlanExecute, and this is a fixed structural cost built into the design that cannot be removed by adjusting prompts or settings.

ReAct shows an interesting cost pattern: its token count is lower than Single-slot, but its ProxyCost is higher. This is because ProxyCost gives 30% of its weight to LLM call count as a separate factor. In the Thought-Action loop, each Action step triggers one separate LLM call, and the call count builds up across multiple iterations, raising the total cost. The savings on tokens cannot fully cancel out the higher call count. In real API use, call count is usually billed alongside token count, so ReAct's actual cost pressure is higher than its token numbers suggest.

In OOS, NetValue falls by about 60% across all architectures while token cost rises only slightly. Quality and cost are driven by completely different forces: the small cost increase comes from a bit of extra exploration when facing unknown intents, while the quality drop reflects the combined effect of gaps in tool coverage and the model's reasoning limit, which no architecture can bypass. As a result, the only action that can actually improve OOS NetValue is expanding the tool set, not changing the architecture. For e-commerce platforms, this means that when intent coverage is limited, investing in expanding the tool set (such as adding support for holiday promotions, shipping problems, or customer complaints) will improve service outcomes more than upgrading to a more complex architecture.

### 5.3 Marginal Benefit Summary: Implications for Evaluation and Deployment

Looking at ΔMB, which combines quality and cost, PlanExecute is the only architecture with positive values in both IS (ΔMB = +0.162) and OOS (ΔMB = +0.125). Its positive ΔMB comes from dominating on two dimensions at once: it has both the highest quality and the lowest cost — the planning step reduces execution complexity and lowers token usage, while the execution step's format discipline improves tool call accuracy and raises quality. Because PlanExecute leads on both dimensions at once, its ΔMB ranking stays fully stable across all valid metric weight combinations. The conclusion does not depend on any specific metric design choice.

All other architectures have negative ΔMB, showing a common problem with complex designs when the underlying model has limited capability. ReAct has the highest S_Outcome, but its quality gain is cancelled out by its high-call-count cost structure (ProxyCost higher than Single-slot). Reflection's 4.4x token cost combined with its self-correction failure means costs far outweigh quality output. The shared root cause is that within the capability range of llama3.1:8b, the model's quality ceiling already controls the final result for all architectures. The design advantages of complex pipelines cannot be fully used, so the small quality gains cannot cover the added costs.

In OOS, the extreme gap between PlanExecute's valid termination rate (96%) and its Judge score (27.3) points to a basic problem in evaluation framework design. Rule-based metrics (valid termination rate) and semantic metrics (Judge score) move together in IS because the tool set is sufficient, but they break apart in OOS when the tool set hits its coverage limit. Valid termination rate only means the system produced some response when the tool set is not sufficient — it does not mean the task was actually solved. This breakdown shows a basic limit of proxy metrics: when a proxy metric and the true goal move together inside the training distribution, the proxy looks reliable, but once the distribution shifts, the relationship disappears. This study's OOS paradox is a concrete example of this problem in LLM Agent evaluation, and it suggests that benchmark designs should include OOS probes to actively test where proxy metrics stop being valid. It should be noted that this study's OOS sample size is 50 cases, which limits the statistical power for intent-level analysis. These OOS conclusions should be treated as exploratory findings rather than definitive results. In addition, the IS and OOS datasets come from different sources, so the observed performance drop includes both the effect of new intents and the effect of a different data distribution. These two sources cannot be fully separated under the current study design. The OOS conclusions in this study are best understood as a cross-dataset stress test rather than a strict out-of-distribution generalization evaluation.

In summary, this study recommends using ΔMB instead of valid termination rate or a single quality score as the main metric for choosing an architecture. Mature platforms with good intent coverage (such as those that have already defined standard intents for returns, order tracking, and promotions) should use PlanExecute first. Its advantage on both quality and cost holds in both IS and OOS, making it the most cost-effective choice when the LLM budget is limited. In cold-start situations where the intent distribution is not yet clear (such as a new platform launch or a new product category), Single-slot's predictable stopping mechanism provides more stable cost protection and can serve as a fallback in a mixed routing architecture for handling uncertain intents. In local lightweight model deployments, the design advantages of complex pipelines may not be usable due to the model's capability ceiling, and the ReAct and Reflection cases in this study are concrete examples of this risk. It is important to note that the conclusions of this study are closely tied to the capability of the underlying model. If this study were repeated with a more capable model, the relative performance of ReAct and Reflection might improve significantly, and the architecture ranking could change.

---
