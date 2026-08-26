# SuperClaw 4B v4 Test Plan (OEM-aligned, 2026-08-16)

> **Update to v3**: Per `CLAUDE_PLAN_V4.md`, switch from `perf_weight` arm switching to **model override alias** for cleaner local/cloud separation. Add PinchBench + CPPM suites.

## T15. Methodology v4 — 3-arm via model alias (not perf_weight)

| Arm | Override | Meaning |
|---|---|---|
| **A force-local** | `--model local-model` | all calls → 4B through router |
| **B force-cloud** | `--model cloud-model` | all calls → M3 through router |
| **C router-auto** | `--model auto` | router decides per call |

**Why switch from perf_weight**: pw is a *bias* knob, not a clean switch. pw=1.0 still kept 72% local calls (verified earlier). Forcing via alias is the clean baseline.

**Implementation status**: ✅ Already done (`lh_automation.py --model` flag)
- arm A: `lh_automation_pw0.5_local.jsonl` (8 tasks, 0.35 acc)
- arm B: `lh_automation_pw0.5_cloud.jsonl` (8 tasks, 0.80 acc)
- arm C: `lh_automation_pw0.5.jsonl` (8 tasks, 0.65 acc)

## T16. Raw output preservation (before restore deletes)

**Current bug**: `restore_workspace()` runs after `find_new_outputs()` — files are captured in metadata but actual content may be lost if restore fails. Also: lh_automation captures file metadata (path, size, md5) but NOT file content.

**Fix**:
- Save raw output files BEFORE restore in `results/v4_raw/<arm>/<task_id>/`
- Include the agent's final text (full assistant message)
- Include L1 delegation: which sub-agents called

## T17. L1 delegation capture

**Per v4**: record which sub-agent(s) the parent delegated to. We have this data via `/w/.../session/{sid}/children` endpoint.

**Fix**:
- After each task, GET children endpoint
- Record parent → child relationship
- Cross-reference with `expected_delegation` from task spec (PinchBench has this field)

## T18. Router pre-warming for arm C

**Per v4**: "send ~5 cloud-explicit probes before the suite so the router has CLOUD signal."

**Implementation**: send 5 simple "Hello" probes with `model=cloud-model` before the arm C runs. Then switch to `model=auto` for the actual runs.

## T19. New suites — PinchBench 147 + CPPM 3

### PinchBench (147 tasks)

`tasks/tasks_pinchbench.jsonl` — 147 tasks across 12 categories:
- log_analysis: 30
- meeting_analysis: 28
- csv_analysis: 26
- coding: 14
- analysis: 12
- research: 11
- productivity: 8
- writing: 6
- skills: 6
- integrations: 3
- memory: 2

**Run**: all 147 × 3 arms = 441 runs (~6 min/run × 441 = ~44 hours)

**Need**: pre-filter by category if time-limited. Start with top-3 categories: log_analysis (30), meeting_analysis (28), csv_analysis (26) = 84 tasks × 3 = 252 runs.

### CPPM (3 tasks)

`tasks/tasks_cppm.jsonl` — 3 tasks:
- cppm01: Data Research (Factorio early-game power) — web scraping + numeric + report
- cppm02: Web Page to Issue (extract from repo URL) — code + analysis
- cppm03: Code Analysis (review PR) — code review

**Run**: 3 × 3 arms = 9 runs (~10 min/run × 9 = ~1.5 hours)

## T20. Total scope

| Suite | Tasks | Arms | Total runs | Est time |
|---|---:|---:|---:|---:|
| Long-horizon (done) | 8 | 3 | 24 | ✅ done |
| PinchBench top-3 cat | 84 | 3 | 252 | ~25 h |
| PinchBench all | 147 | 3 | 441 | ~44 h |
| CPPM | 3 | 3 | 9 | ~1.5 h |

## T21. Captures needed per run (v4 compliance)

1. **Raw outputs**: `results/v4_raw/<arm>/<task_id>/*.md` — files BEFORE restore
2. **Agent final text**: full assistant message text + reasoning chain
3. **L1 delegation**: `[parent_session, child_session, agent_type]` list
4. **Router decisions**: timestamp + agent + source (already in router log)
5. **Tokens**: per-message in_tok, out_tok, reasoning, cache_read, cache_write

## T22. Caveats (from v4)

- 4B local model here is **Qwen3.5-4B** (hardware-reduced), NOT official **Qwen3-Coder-Next**
- Cloud model is **MiniMax-M3**, NOT official **GLM-5**
- L2 numbers NOT directly comparable to official ±0.03 tolerance — label runs "hardware-reduced tier"
