# SuperClaw Hybrid-Architecture Benchmark — Handoff Brief (for Claude running ON machine B)

You are Claude Code running **on machine B** (`10.188.194.206`, hostname `laptop-0gdqgd3i`, user `Trekker-PTL`), the same machine where **Intel SuperClaw** is installed. This benchmark was set up by another Claude instance on machine A that drove B over SSH; the task is now being handed to you because you run **locally on B** — you can reach SuperClaw on `127.0.0.1` directly and B has the correct regional network (reaches `hf-mirror.com` directly, no proxy).

## The goal
Benchmark whether SuperClaw's hybrid architecture (a) decomposes agentic tasks and routes sensibly between **local** (Ollama/Intel) and **cloud**, (b) preserves **accuracy**, (c) performs well (**TTFT / TPS / memory**), and (d) does **not** leak local PII to the cloud. Compare **Hybrid (Auto Route)** vs **forced Cloud-only**, both using **MiniMax-M3** as the cloud model.

## What is already built (in this folder, `superclaw_benchmark/`)
- `proxy/minimax_logging_proxy.py` — OpenAI-compatible logging reverse-proxy. Sits between SuperClaw's cloud slot and MiniMax; logs every cloud request/response + token usage + timing to JSONL. **Live-tested against MiniMax-M3.** Launch with env `UPSTREAM_BASE_URL=https://api.minimaxi.com/v1`, `UPSTREAM_API_KEY=<mmx key>`, `HTTPS_PROXY=<proxy>`, `CONFIG_LABEL=hybrid|cloud_only`, `PROXY_LOG=logs/…jsonl`.
- `tasks/build_suite.py` → generates `tasks/tasks.jsonl` (24 agentic tasks), `tasks/workspace/` (local files w/ planted synthetic PII), `tasks/pii_registry.json` (15 PII tokens). Routing mix: local 11 / cloud 7 / mixed 6, incl. adversarial "tempt the model to send PII to cloud" probes.
- `harness/analyze.py` — turns proxy log + answers into `privacy.json` (PII leak rate), `metrics.json` (TTFT/TPS/tokens), `routing.json`. **Smoke-tested.**
- `harness/judge.py` — LLM-judge accuracy scorer (uses MiniMax) + PII-parroting check.
- `harness/rsh.py` — SSH helper A used to reach B; **you don't need it** (you're already on B).
- `push_superclaw.py` — how the installer got to B (historical).

## Key facts / working config
- **MiniMax-M3 cloud baseline**: endpoint `https://api.minimaxi.com/v1`, model id `MiniMax-M3`, key in `~/.mmx/config.json` (`sk-cp-…` Agent-Plan key — must be present on B). Reasoning model (emits `<think>…</think>` — strip before grading). **VERIFIED: B reaches `api.minimaxi.com` directly (HTTP 401 without key = connected).**
- **NETWORK RULE FOR B (critical)**: B's inherited `HTTP(S)_PROXY=http://child-prc.sh.intel.com:913` is **broken/unresolvable**. Everything B needs — MiniMax, hf-mirror.com, npm registry — is reachable **directly with the proxy cleared** (`curl --noproxy "*"`, or remove the env vars). Always clear/ignore the proxy for outbound calls on B.
- **SuperClaw control surface** = OpenAI-compatible API on `http://127.0.0.1:18321/v1`. Model `auto` = Auto Route ("latency router decides when both cloud+local slots configured; falls back to whichever single slot is configured"). Other services: `security_manager` :18826 (PII pipeline), `sandbox_manager` :18821 (WSL tool sandbox). Ollama (local backend) :11434 with `qwen3.5:9b` (has tools) + `deepseek-r1:7b`.
- **CURRENT STATE (2026-08-13, after v3.4 setup)**: 4B bundle is **healthy and active**. The original 0.8B blocker is no longer relevant — the local tier was upgraded to `qwen3.5-4b` (with draft-MTP speculative decoding). Concrete state:
  - `bundle_lifecycle.primary_bundle = local-4b` / `chat_model_id = "qwen3.5-4b"` / `state = "ready"` / `bundle_revision = 5` (system bumps on each restart)
  - 4B GGUF at `%LOCALAPPDATA%\SuperClaw\llmrouter_manager\models\qwen3.5-4b\Qwen3.5-4B-Q4_K_M.gguf` (2,834,975,040 B, SHA256 `3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630`). Copied from `superclaw_benchmark/backup_for_reinstall/models/qwen3.5-4b/` — **NOT** downloaded from `hf-mirror.com`.
  - llama-server (PID varies) holds the loaded 4B in memory — ~7.5 GB working set.
  - Cloud slot: `provider = minimax-cn-coding-plan`, `model = MiniMax-M3` (api_key already configured). If pointing at the logging proxy, reconfigure via SuperClaw GUI.
  - `perf_weight = 0.85` (default after last boot; live + persisted). Editable in DB: `config.perf_weight`.
  - Hardware probe (per `llmrouter_manager-*.log`): Core Ultra 7 356H / 32 GB / **mem_speed=5600 MT/s** — passes the relaxed `min_mem_speed_mts=4800` floor we set for `qwen3.5-4b`.
  - If you need to rebuild this from scratch (clean install, fresh backup, etc.), see `SUPERCLAW_LOCAL_4B_GUIDE.md`. Detailed run log of the v3.4 setup: `results/superclaw_4b_setup_v3.4.md`.
- **Re-bootstrap recipe (if needed)**:
  1. Confirm 4B GGUF is at `%LOCALAPPDATA%\SuperClaw\llmrouter_manager\models\qwen3.5-4b\Qwen3.5-4B-Q4_K_M.gguf` (use backup if missing).
  2. Confirm `models.builtin.json` has relaxed `qwen3.5-4b` requirements (`min_mem_speed_mts=4800`, `igpu_keywords=[]`).
  3. Confirm DB: `active_chat_model_id="qwen3.5-4b"`, `bundle_lifecycle.primary_bundle` references `local-4b / qwen3.5-4b / state=ready`, `model_verifications` row for `qwen3.5-4b` (SHA matches).
  4. Cold-restart: kill SuperClaw + servicehub + llmrouter_manager + llama-server, wait 5 s, relaunch `C:\Program Files\Intel\SuperClaw\SuperClaw.exe` with `HTTP_PROXY` and `HTTPS_PROXY` **cleared**. Wait ~40 s. Then `curl 127.0.0.1:18321/v1/models`.
  5. **Verify quickly** — processes can disappear silently if the Tauri GUI is closed (no shutdown log line). Do `/v1/models` + a `model=local-model` test in the same shell session right after relaunch.
- Config store: `%LOCALAPPDATA%\SuperClaw\llmrouter_manager\llmrouter_manager.db`. Backups: `.db.v3.4.bak` (current). Cloud/local slots are configured via the SuperClaw **GUI Settings** (Tauri app, WebView2).

## Your first steps on B
1. **Confirm SuperClaw health** (already bootstrapped on 4B since 2026-08-13 — see "CURRENT STATE" above). `curl 127.0.0.1:18321/v1/models` should return `auto`, `local-model` (Primary llama: qwen3.5-4b), `cloud-model` (MiniMax-M3). If empty or router down, follow the re-bootstrap recipe above.
2. In SuperClaw GUI: configure the **cloud slot** to point at the **logging proxy** (run it on B: `127.0.0.1:8900`, upstream MiniMax-M3), and the **local slot** to Ollama. This makes `auto` = Hybrid. (Current state has cloud already pointed at MiniMax directly — re-point through the proxy before the benchmark so we capture traffic.)
3. Build the run driver (Phase 3–4): for each task in `tasks/tasks.jsonl`, POST to `127.0.0.1:18321/v1/chat/completions` (model `auto`), capturing client TTFT/TPS + answer; write `answers.jsonl` with `{task_id,config,answer,client_ttft_s,client_total_s,output_tokens,used_cloud}`. Run **Config A (hybrid: both slots)** and **Config B (cloud-only: disable local slot or force cloud)**.
4. Analyze: `python harness/analyze.py --cloud-log logs/<cfg>.jsonl --registry tasks/pii_registry.json --tasks tasks/tasks.jsonl --answers logs/answers.jsonl --out results/<cfg>` and `python harness/judge.py …`. Then chart with the `dataviz` skill + write the report.

## Constraints / notes
- Planted PII is **synthetic** (fake). The privacy test = scan what the cloud actually received (proxy log) for those exact values.
- B hardware: Core Ultra 7 356H (NPU) + Intel iGPU + RTX 5050, 32 GB. Local model tier is smaller than SuperClaw's reference 80B — **document this as a hardware-reduced local tier**; the routing/privacy/latency comparison is still valid.
- Full plan: `plan.md` (copied alongside). Point Claude's memory here.
