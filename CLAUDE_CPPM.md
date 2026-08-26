# CPPM real-world task suite — run brief (for Claude on B)

3 real-world agent tasks from the CPPM *AI Agent Capability Assessment* (2026-06) added as `tasks/tasks_cppm.jsonl`. Run them through SuperClaw's real Auto Route and mirror raw answers back to A for Opus judging.

## Provenance (important)
The prompts are the **full TaskN-Prompt pages** (verbatim), NOT the slide summary cards ("REAL-WORLD ANALOG" / "THE ASK"). Each has `【任务开始】记录 T1 … 【任务结束】记录 T2`, exact output paths, and a deliverable checklist. Chinese prompt = `prompt`; English = `prompt_en`.

## The 3 tasks
- `cppm01` — Data Research (Factorio wiki): scrape 4 wiki pages, compute steam-vs-solar unit, write MD report. **Needs network** (`wiki.factorio.com`).
- `cppm02` — Sales Data Analysis: generate 36-row CSV (3 missing + 2 outliers), write+run a Python script (clean/compute/plot), report gross margin.
- `cppm03` — Project Framework: scaffold `hermes-toolkit` Python CLI project (10 files) + self-verify.

## How to run
1. Use the same agent-trigger path as the long-horizon suite (`harness/lh_automation.py`, the `prompt_async` route). Feed `prompt` (CN) verbatim as the user message; `model=auto`.
2. Optionally sweep `perf_weight` to observe per-task cloud/local dispatch (routing is per-task, not a clean switch — see report §14.3).
3. **Persist each task's raw output files + the agent's final text** (do NOT let workspace-restore delete them before capture) so A can Opus-judge. Write to `results/cppm/answers_pw{X}.jsonl` with `{task_id, perf_weight, answer_text, files:[{path,content}], router_log}`.

## Paths / gotchas
- Prompts write to Windows-style `~\Documents\Agent_Test\...`. If the WSL sandbox doesn't resolve it, map `~` to the agent workspace but keep the relative layout.
- `cppm01` needs outbound network — clear the broken proxy first (`fix_proxy_B.bat`), then `wiki.factorio.com` is directly reachable.
- Ground truth for judging is embedded per task under `checkpoints` (sizes, row counts, exit codes) — A uses `checkpoints.rubric` for Opus scoring.

## Judging (A side — do NOT judge on B)
B writes raw answers + output files only. A (Claude Opus 4.8, inline, no key) grades against each task's embedded `checkpoints.rubric` + deterministic anchors (cppm01 tile sizes / cppm02 row+range counts / cppm03 exit-code-1 & 10-file completeness).
