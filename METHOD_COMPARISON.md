# 官方 OEM 套件 vs 我们的测试方法 — 差异比对与改进计划

> 依据 `superclaw-oem-bench-kit-main`（官方 SuperClaw Local LLM Evaluation Kit, OEM Edition）。
> 来源：`README.md` §3–6 + `lib/api.py`（模式映射）+ `lib/config.py`（arm/judge 配置）+ `lib/grader.py`（L1/L2）+ `data/task_evaluation_manifest.json`（116 题）。

## 1. 官方方法摘要

- **语料**：PinchBench **116 题** OEM 子集，9 类（log_analysis 30 / meeting_analysis 28 / csv_analysis 26 / analysis 9 / productivity 7 / research 5 / coding 5 / writing 5 / memory 1）。
- **3 个测试臂**（经 `127.0.0.1:8787` 后端 opencode API，用每-prompt 模型 override 强制，见 `lib/api.py`）：
  - **A force-local** = `{providerID:llmrouter, modelID:local-model}`
  - **B force-cloud** = `{providerID:llmrouter, modelID:cloud-model}`
  - **C router-auto** = `{providerID:llmrouter, modelID:auto}`
- **SUT 模型**：本地 = Qwen3-Coder-Next；云 = `z-ai/glm-5`（可配）。
- **裁判**：DeepSeek-V3.1 单裁判（刻意在 SUT 池外，避免自偏置），**每题 2 跑 + 方差重试**（差>0.2→补到 4 跑取均值）；可选双裁判（Pinchbench 风格）。
- **指标**：
  - **L1** = 委派正确性（是否路由到 `expected_delegation` 指定的 sub-agent：`local-file-agent`/`websearch-agent`/`email-agent`/`build`）。
  - **L2 mean/std** = 质量分（116 题均值 / 标准差）。
  - **Total tok / LOCAL / CLOUD** = token 总量与本地/云切分。
  - **L2 / M cloud tok** = 每百万云 token 买到的质量（效率）。
- **router 臂加固**：5 个 cloud 探针预热 + 看门狗（≥5 次分派 0 次选 cloud 即中止，防 C 退化成 A）+ 决策记录 + **决策↔消息时间戳 120s join** 得精确 LOCAL/CLOUD 归因（未命中记 `OTHER` 告警）。
- **认证口径**：容差 ±0.03 L2、C 的 LOCAL/CLOUD 份额 ±5pp。
- **参考基线（release/1.0）**：A force-local L2 **0.8841**（100% 本地）；B force-cloud **0.9428**（100% 云）；C router-auto **0.9099**（本地 77.1% / 云 22.9%）。
- **无隐私/PII 维度；无 TTFT/时延/内存维度。**

## 2. 差异比对

| 维度 | 官方 OEM | 我们（原方法） | 差异性质 |
|---|---|---|---|
| 分臂机制 | 3 臂用 `modelID` 别名强制 | 2 配置，曾纠结 perf_weight | 官方**印证**：强制靠模型别名，非 perf_weight |
| force-local vs router | A(强制本地) 与 C(路由实选) 分开 + 看门狗 | 混为"Hybrid=本地"（硬件上路由器总选本地） | **我们缺一个臂** |
| 本地模型 | Qwen3-Coder-Next（认证大模型） | Qwen3.5-4B（硬件缩水档） | 分数**不可直接对基线** |
| 云模型 | z-ai/GLM-5 | MiniMax-M3 | 云基线不同 |
| 裁判 | DeepSeek-V3.1，单，2 跑+方差重试 | Opus 4.8，单，1 跑无重试 | 都在 SUT 池外✓；**我们缺多跑** |
| token 归因 | 决策↔时间戳 120s join | 数 router log `source=` | 官方**更精确** |
| L1 委派正确性 | 有 | 无 | 我们缺 |
| 隐私/PII | **无** | 有（出云 egress + 输出 output 两面 + 提取率 + 复读把关） | **我们独有** |
| 时延/内存 | **无** | 有（TTFT/TPS/P95/内存 + 6 维成本代价） | **我们独有** |
| PinchBench 评分 | 116 出 L1/L2 | 147 已 staged 但**未 L1/L2 判分** | 我们**尚无可比分数** |
| 认证框架 | 容差 pass/fail | 探索性刻画 | 用途不同 |
| 传输路径 | 8787 opencode + 模型 override | 1.1.0 走 :18321(424)；1.2.0 才用 8787 prompt_async | 官方文档化=B 后来攻克的路径 |

## 3. 三个关键判断

1. **官方印证了"用模型别名强制、不用 perf_weight"的纠正**，并补上我们缺的 force-local 独立臂 + 看门狗（官方直接把"路由器从不选云"当失败模式防）。
2. **我们的准确率与官方基线不可比**——主因本地模型不同（4B vs Qwen3-Coder-Next）。要对齐须换认证模型或明确标注"硬件缩水档"。
3. **两套互补**：官方在质量判分（L1+L2 多跑+token join+容差）更严谨；我们在隐私(两面)+性能(TTFT/内存)+成本代价上是官方的**超集**——恰好覆盖官方 deck "Next Steps" 里的 Security & Privacy study。

## 4. 改进计划（已并入 `report_deck_cn.html`）

### 吸收（提升严谨度）
1. **3 臂重构**：`local-model` / `cloud-model` / `auto`；C 臂加 5 探针预热 + 看门狗。**不再用 perf_weight 造基线**。
2. **新增 L1 委派正确性**（对 `expected_delegation`）。
3. **裁判 2 跑 + 方差重试**（Opus 4.8；差>0.2→4 跑取均值）。
4. **token 时间戳 join** 精确归因 auto 模式的 LOCAL/CLOUD 切分。
5. **跑 PinchBench 116 出 L1/L2**，与官方基线（A .884 / B .943 / C .910；77%/23%）对表。
6. **持久化每题 raw 输出** 供 Opus 判分（替换启发式）。

### 保留（官方没有的超集）
- 隐私/PII 两面（出云 egress + 输出 output）+ security_manager 掩码判定。
- 性能：TTFT / TPS / P95 / 内存。
- 成本代价 6 维 trade-off 矩阵（节省 vs 准确率/时延税）。

### 口径校正
- 本地模型不同 → 不套官方 ±0.03 容差；对基线时换认证本地模型或标注"缩水档"。
- 云模型不同（MiniMax-M3 vs GLM-5）需在报告注明。
