# v4 长程结果：错配/污染诊断 + 清理与复跑计划（A 侧 Opus 判分回写给 B）

A 侧用 Opus 4.8 逐题判了 `results/v4_raw/{auto,cloud,local}/lh0x/` 的 raw 交付物。**8 题里只有 3 题(lh03/lh07/lh08)输入正确、可对 ground_truth 判分;其余 5 题输入错配,且 auto 臂目录跨任务污染。** 需要 B 清理 + 修 staging + 复跑对应任务拿干净数据。

## 1. 错配任务（跑在了与 ground_truth 不一致的种子数据上）

| task | 你的产物里出现 | ground_truth 期望 | 结论 |
|---|---|---|---|
| **lh01** 合规报告 | 员工 Alice Johnson / Bob Smith / Carol White / David Brown / Eve Davis | Dana Whitfield / Miriam Okafor / Sam Reyes / Liang Zhao / Pat Singh | `employees.csv` 种子错 |
| **lh02** 退款批处理 | Dana Whitfield 42.50 / Felix Brenner 445 / Liang Zhao 375.99 / Sara Patel 67.30 | Dana 42.10 / Miriam 128.99 / Sam 17.50（3 客户） | `orders.csv`+`returns.csv` 种子错 |
| **lh04** 事故复盘 | 日志 auth_03 / auth_06 / auth_09（trace_3/6/9） | 失败日志应为 **auth_04.log, auth_08.log** | `auth_*.log` 种子错 |
| **lh05** 供应商对比 | Widget A / Widget B / Gadget C（delta≈±1） | Notebook Pro / Notebook Air / Tablet / Charger，delta 150/24/−50/−3 | `vendor_a.csv`+`vendor_b.csv` 种子错 |
| **lh06** PII 脱敏 | 客户 Alice Smith/Bob Jones/Carol Lee 或 E001/E002/E003 | 指定客户 + 指定 email/phone/ssn（见 GT must_not_contain） | `onboarding_raw.csv` 种子错 |

> 这 5 题**不是模型答错**——是喂进去的输入文件不是本题的规范种子,所以无法对 GT 判 exact accuracy。

## 2. 污染任务（auto 臂无 workspace 隔离，目录累积了别的任务产物）

- `results/v4_raw/auto/lh01/` 里出现 `consolidation.md`（lh05 的）、`orders.csv/returns.csv`（lh02 的）、`scrub_pii.py`（lh06 的）。
- `results/v4_raw/auto/lh06|lh08/` 里出现 `hermes-toolkit_*`（cppm03 的）、`factorio_power_comparison.md`（cppm01 的）。
- auto 臂跑了 6 个 perf_weight 点,**产物写进同一批目录、没在任务间清理**,导致 lh08 auto 被污染到无法判分。
- cloud / local 臂目录相对干净（各跑一次）,但 local 也有个别串味（如 lh01/local 里混入 post_mortem_filled.md）。

## 3. 干净可判的 3 题（作为参照，勿动）

| task | 本地 | auto | 云 | 说明 |
|---|---|---|---|---|
| lh03 代码修复 | 1.0 | 1.0 | 1.0 | 三臂都正确指出 3 个 bug + 修复 |
| lh07 预测重建 | 0.6 | 0.6 | **1.0** | 云残差符号正确；本地/auto 把 `residual=actual−new` 写反 |
| lh08 策略扫描 | 0.8 | 污染 | 0.8 | 云/本地命中 6 违规 + 正确文件；缺 UNAUTH_ADMIN |

## 4. 要做的事

### 4.1 清理污染数据
- 删掉 `results/v4_raw/` 下**受污染的目录**（至少 auto 臂全部 lh0x/cppm0x；其余臂里混入他题文件的目录）。先备份到 `backup_v4/` 已有，可直接清 live。
- 每个任务的 SuperClaw workspace（agent 实际读写的目录，如 `~/Documents/Agent_Test/` 或沙箱 `/workspace`）在**每题跑前必须清空并只放本题输入**。

### 4.2 修 staging（关键）
- 用**与 ground_truth 一致的规范种子**铺 workspace。检查 `tasks/workspace_lh/`（部署时的 49 个规范文件）或 `tasks/long_horizon_suite.py` 的生成器——**确认它产出的 employees.csv 里是 Dana Whitfield 而不是 Alice**。
- 如果 v4 runner 用了随机/另一套数据生成，**关掉它，改用固定规范种子**（`stage_workspace.py` 从 `tasks/workspace_lh/` 拷）。
- 复用你 1.2.0 时写好的 **snapshot + restore workspace 隔离**（`lh_automation.py` 里那套）——v4 的 3 臂 runner 似乎没接隔离，接上。

### 4.3 复跑（只补错配/污染的任务，3 臂）
- 复跑 **lh01, lh02, lh04, lh05, lh06**（这 5 题错配）+ **lh08 的 auto 臂**（污染）。lh03/lh07 已干净可不跑。
- 每题：`snapshot → 只铺本题规范输入 → 跑 A(local-model)/B(cloud-model)/C(auto) → 把 raw 输出写进干净的 `results/v4_raw/<arm>/<task>/`（先清空该目录）→ restore`。
- 保留 raw 交付物 + router log + 每消息时间戳（给 A 做 L1/token join）。

### 4.4 验证 + 回传
- 跑前**自检**：`type workspace\employees.csv` 应含 `Dana Whitfield`；`vendor_a.csv` 应含 `Notebook`；`auth_04.log` 存在。种子对了再跑。
- 跑完把 `results/v4_raw/` 回传（或等 A 拉）。A 用 `judge_prepare.py`(新解耦版) + Opus 重新判 accuracy（仅 rubric 质量，PII 独立）。

## 5. 判据（A 侧口径，供你自查）
- accuracy = 仅任务质量（对 rubric + ground_truth），**PII 泄漏不并入**。
- ground_truth 见 `tasks/tasks_long_horizon.jsonl` 每题的 `ground_truth` 字段（expected_rows / expected_deltas / expected_residual / must_contain_files 等）。
- 干净数据的标志：产物里的实体名/数值能对上 GT（Dana/Notebook/auth_04），而不是 Alice/Widget/auth_03。
