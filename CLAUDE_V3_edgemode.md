# v3 — Edge-Server-Mode routing test (activates the REAL Auto Route + PII module)

> **Architecture: B executes, A judges.**
> - **B** runs all 189 tasks on SuperClaw edge mode, writes raw answers + per-step traces to `results/v3_edge/`. B never runs an LLM judge.
> - **A** (machine with Claude Code): the judge **is Claude Code / Opus 4.8 itself** — it reads the pulled answers via `harness/judge_prepare.py prepare`, grades each rubric inline in its own reasoning, then `judge_prepare.py finalize` merges the deterministic PII-parrot guard and computes accuracy. **No Anthropic API key, no SDK call anywhere.**
> - **Answer transfer:** batch — B finishes all 189 tasks, A SSH-pulls `results/v3_edge/` and grades.
>
> **v3 bundle is fully staged on A (2026-08-08).** Next session: when A and B share a subnet, run **`python push_v3_to_b.py`** from A — it auto-detects B, source-binds, and mirrors every file below. Then run this plan on B. No further downloads needed.
>
> **Combined task suite (189 tasks, all self-contained):**
> | Suite | File | Tasks | Notes |
> |---|---|:-:|---|
> | Original privacy-instrumented | `tasks/tasks.jsonl` | 24 | 15 planted PII + 3 adversarial |
> | Long-horizon multi-step | `tasks/tasks_long_horizon.jsonl` | 8 | 5–12 steps each; bundles in `tasks/workspace_lh/` |
> | **PinchBench (OpenClaw public — FULL 147)** | `tasks/tasks_pinchbench.jsonl` | **147** | every task `ready_to_run=true`; data + inline content under `pinchbench/data/` (42 external + 122 inline) |
> | Industry standards | `tasks/tasks_industry.jsonl` | 10 | GAIA/BFCL/τ²/PrivacyLens exemplars |
>
> **Workspace staging:** the run driver must call `stage_workspace.stage(task, run_dir)` before each task — it lays the right files at the right relative paths (original→`workspace/`, long-horizon→`workspace/`, PinchBench→per `pinchbench/_staging_manifest.json`, incl. renamed images + inline Dockerfile/research files). Verified: `python stage_workspace.py --all` stages 52/68 (rest are prompt-only).
>
> **Recommended v3 run:** all 189 under `model=auto` edge mode, judge=MiniMax-M3, max_tokens=8192. PinchBench's full 147 gives public-benchmark comparability (vs 614 published OpenClaw runs); long-horizon tasks exercise per-step routing; original+PII tasks test the masking module.


**Why this run matters:** v1 and v2 both **bypassed** SuperClaw's router (Config A hit the local llama-server directly at `:18103`; Config B hit the proxy directly). So neither run tested (a) Auto Route's real routing decision or (b) SuperClaw's **on-device PII-masking pipeline** (`security_manager` :18826) — the product's headline privacy claim. We proved "0 leak because 0 cloud calls", never "PII gets masked *while still using* the cloud".

**The workaround (from the user):** set SuperClaw's routing to **edge-server mode** and point the **edge server address at the local Qwen3.5-4B llama-server** already running on B. This makes the edge/local slot a valid, reachable OpenAI endpoint, which activates the router + masking path that the broken `auto`/`local-model` aliases blocked in v2.

## Target topology
```
 model=auto @ 127.0.0.1:18321  (SuperClaw gateway)
        │
   LatencyRouter (perf_weight)   ← NOW actually consulted
        ├── edge/local slot → http://127.0.0.1:18103/v1  (local Qwen3.5-4B llama-server, already up)
        └── cloud slot ─── security_manager PII masking ──→ http://127.0.0.1:8900/v1 (our logging proxy) → MiniMax-M3
```

## Steps (all on B)

### 1. Configure edge-server mode in the SuperClaw GUI
- Open SuperClaw → Settings → routing / model configuration.
- Set routing mode to **Edge server** (a.k.a. enterprise edge resource).
- **Edge server URL** = `http://127.0.0.1:18103/v1`, model id `qwen3.5-4b` (the local llama-server already serving the 4B with MTP).
- **Cloud slot** = `http://127.0.0.1:8900/v1`, model `MiniMax-M3`, key = the `sk-cp-…` mmx key. (This routes cloud calls through our logging proxy so we capture exactly what egresses — the whole point.)
- Save. Confirm `/v1/models` now lists `auto` as usable (no more `424 auto_route_not_configured`).

### 2. Start the logging proxy (on B, proxy env cleared)
```
cd C:\Users\Trekker-PTL\superclaw_benchmark
set "HTTP_PROXY=" & set "HTTPS_PROXY="
set UPSTREAM_BASE_URL=https://api.minimaxi.com/v1
set UPSTREAM_API_KEY=<mmx key from ~/.mmx/config.json>
set CONFIG_LABEL=v3_edge
set PROXY_LOG=logs\v3_cloud_calls.jsonl
python proxy\minimax_logging_proxy.py --host 127.0.0.1 --port 8900
```
(The proxy already has the v2 `stream_options.include_usage` fix — token accounting will be correct.)

### 3. Sanity — confirm the router is really in the path
- `curl --noproxy "*" http://127.0.0.1:18321/v1/models` → `auto` present and usable.
- Send one obviously-local task and one obviously-cloud task via `model=auto`:
  - Watch `llmrouter_manager` log for a `LatencyRouter`/`route decision` line naming edge vs cloud (this is the line that was NEVER emitted in v1/v2 because auto returned 424).
  - Confirm a cloud-routed task produces a hit in `logs/v3_cloud_calls.jsonl`.

### 4. THE PII-masking test (the new capability)
This is the most important part — it directly tests `security_manager`. Use the tasks that carry `pii_must_stay_local` **and** are likely to route to cloud (mixed/cloud expectation), e.g. t09, t10, t13, t18, t22, plus the adversarial probes t16/t17/t18.
- Run each via `model=auto`.
- For every task that the router sends to cloud, inspect `logs/v3_cloud_calls.jsonl`: **did the planted PII appear in the cloud payload, or was it masked/redacted by `security_manager` before egress?**
- Compare against the plain planted values in `tasks/pii_registry.json`. A masked value (e.g. `[REDACTED]`, `<PERSON>`, hashed, or tokenised) = the module works. A verbatim value = it leaked.
- This finally answers: **"does SuperClaw's on-device PII masking actually protect data when the cloud IS used?"** — not answerable in v1/v2.

### 5. Full run matrix (if step 3–4 confirm the router is live)
- Sweep `perf_weight ∈ {0.3, 0.5, 0.7, 0.9, 1.0}` (set `config.perf_weight` in `llmrouter_manager.db`, restart router each time).
- For each: run the 24-task suite via `model=auto`, capture route decisions + cloud payloads.
- Record per-perf_weight: % routed local vs cloud, PII-masking rate on cloud-routed tasks, accuracy, cloud tokens.
- Also run the 10 industry tasks (`tasks/tasks_industry.jsonl`) once at the default perf_weight.
- Raise `max_tokens` to **8192** this time (fixes the v1/v2 truncation on t06/t07/t16/t20).

### 5b. Judge model — use MiniMax-M3
Run `judge.py` with **`JUDGE_MODEL=MiniMax-M3`** (the default is now M3). Caveat to record in the write-up: M3 is also the cloud baseline, so on the Cloud-only config the judge is grading its own outputs (self-preference bias). Report accuracy with this caveat noted; if an unbiased number is needed later, re-judge with an independent model.

### 6. Output
Write results to `results/v3_edge/` and `logs/v3_*`, and a `results/v3_section.md` summarizing:
- **Routing frontier**: perf_weight vs {local%, cloud%, accuracy, PII-mask rate, cloud tokens}.
- **PII-masking verdict**: for cloud-routed sensitive tasks, masked vs leaked (per entity type).
- Whether Auto Route's split is "sensible" (local-expected stayed local, cloud-expected escalated).
- Any `security_manager` masking failures (the highest-value finding for Intel).

Then mirror `results/v3_edge/` + `logs/v3_*` + `results/v3_section.md` back so A can fold a **§18 v3 Edge-Mode Routing & PII-Masking Results** into both reports.

## Key checks (how we know v3 finally worked)
- [ ] `/v1/models` `auto` no longer 424 — router is live.
- [ ] `llmrouter_manager` log shows per-task route decisions (edge vs cloud).
- [ ] At least some tasks route to **cloud** (so the masking path is exercised).
- [ ] `logs/v3_cloud_calls.jsonl` is non-empty and captured via the proxy.
- [ ] For cloud-routed sensitive tasks: report the planted-PII **masking rate** (the headline new metric).
- [ ] perf_weight sweep shows a routing-mix change (proves the knob works).

## Guardrails
- Keep B's machine proxy env cleared (`child-prc…:913` stays removed).
- Only edit `llmrouter_manager.db` for `perf_weight`; do NOT touch the encrypted `state/providers/*.bin` or vendor bundle JSONs.
- If edge-server mode still won't route to cloud (e.g., the cloud slot is still pinned to the encrypted `.bin`), document it and fall back to reporting the edge-vs-nothing routing decision + whatever cloud calls do occur.
