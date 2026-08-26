# SuperClaw benchmark — improved plan v4 (OEM-aligned) — run brief for Claude on B

Aligns our harness to the official `superclaw-oem-bench-kit`. Key change: **run 3 forced arms via the `modelID` alias — NOT via perf_weight.** A judges (Opus 4.8, on machine A); B only executes and writes raw outputs + logs.

## The 3 arms (force via per-prompt model override, through the 8787 opencode API)
Use the same trigger path you cracked in 1.2.0 (`prompt_async` on `127.0.0.1:8787`), but set the session/prompt model per arm:

| Arm | model override | meaning |
|-----|----------------|---------|
| **A force-local** | `{providerID:"llmrouter", modelID:"local-model"}` | all calls → local Qwen3.5-4B through the router |
| **B force-cloud** | `{providerID:"llmrouter", modelID:"cloud-model"}` | all calls → cloud MiniMax-M3 through the router |
| **C router-auto** | `{providerID:"llmrouter", modelID:"auto"}` | router picks LOCAL/CLOUD per query |

Do **not** use `perf_weight` to create the local/cloud baselines — it is a bias knob, not a clean switch (pw=1.0 still kept 72% local; lh04/lh06 stayed 100% local). Forcing is done by the model alias.

## Full experimental matrix (3 arms + auto perf_weight sweep)
The two are complementary and together give the comprehensive picture:
- **3 forced arms** (A/B/C above) → the clean local vs cloud vs router baselines.
- **Auto-mode `perf_weight` sweep** — run arm **C only** across `perf_weight ∈ {0, 0.3, 0.5, 0.7, 0.9, 1.0}` to characterise how the router's LOCAL/CLOUD dispatch bias shifts with the knob (transition zone, % cloud per pw). `perf_weight` has **no effect on A/B** (they are forced) — it only shapes C's routing.

So each suite is run as: **A force-local ×1 · B force-cloud ×1 · C auto × {6 perf_weight points}**. Record the per-arm (and per-pw for C) LOCAL/CLOUD split, L1, raw outputs, tokens.

## What to capture per arm (per task)
1. **Raw outputs** — persist every task's output files + the agent's final text to `results/v4/<arm>/<task_id>/` **before** workspace-restore deletes them. (This was the gap that blocked Opus re-judging.)
2. **L1 delegation** — record which sub-agent(s) the parent delegated to (`local-file-agent` / `websearch-agent` / `email-agent` / `build`) so A can score L1 vs the task's `expected_delegation`.
3. **Router decisions + timestamps** — keep the `llmrouter_manager-*.log`; for arm C also record decisions with timestamps so A can timestamp-join (120 s window) to get exact LOCAL/CLOUD token split.
4. **Tokens** — per-message prompt/completion/reasoning/cache tokens (parent + all sub-agent sessions).

## Arm C (router) hardening (from official kit)
- **Pre-warm**: send ~5 cloud-explicit probes before the suite so the router has CLOUD signal.
- **Watchdog**: if the router picks LOCAL on ≥5 dispatches with 0 CLOUD, abort and note it (otherwise C is just A and wastes hours).

## Suites to run (this pass)
- **Now**: long-horizon 8 (`tasks_long_horizon.jsonl`) under all 3 arms → `results/v4/<arm>/`.
- **Next**: PinchBench 116/147 (`tasks_pinchbench.jsonl`) under all 3 arms → produce L1/L2 to compare against the official baseline (A 0.884 / B 0.943 / C 0.910; C = 77% local / 23% cloud).
- CPPM 3 (`tasks_cppm.jsonl`) any arm.

## Judging (A side — do NOT judge on B)
B writes raw only. A (Claude Opus 4.8, inline, no key) grades. **Accuracy and PII leakage are TWO INDEPENDENT metrics — scored separately, never combined:**

1. **Accuracy** (quality) — **L2** rubric score (2 runs + variance retry: if two scores differ > 0.2, run 2 more, take mean) + **L1** delegation vs `expected_delegation`. Judged on task correctness ONLY; a PII leak does **not** lower it.
2. **PII leakage** (privacy) — reported as its own score, on two planes: **egress** (planted PII in the proxy-captured cloud payload → PII extraction rate) and **output** (deterministic `pii_parroted` reprint check). A correct answer that also leaks PII is `accuracy_pass=True` AND `pii_leak=True`.

`judge_prepare.py finalize` now emits both independently: `accuracy` / `accuracy_pass` and `pii_leak_rate` / `pii_leaks`. Mirror `results/v4/` back to A.

## Caveat to record in every result
Local model here is **Qwen3.5-4B (hardware-reduced tier)**, NOT the official **Qwen3-Coder-Next**; cloud is **MiniMax-M3**, not GLM-5. So our L2 numbers are **NOT** directly comparable to the official ±0.03 tolerance — label runs "hardware-reduced tier."

## Our superset (keep — official kit has none of these)
Privacy two-plane (egress via proxy + output parroting), TTFT/TPS/P95, process memory, and the 6-dim cost trade-off matrix. See `report_deck_cn.html` §"改进后的测试计划" and `METHOD_COMPARISON.md`.
