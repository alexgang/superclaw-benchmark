# SuperClaw Hybrid-Architecture Benchmark Plan

## Context

We are benchmarking **Intel SuperClaw** (https://aibuilder.intel.com/#/superclaw) — an OpenClaw-based *hybrid agentic AI* whose "Auto Route" model router decomposes a task and decides, per sub-step, whether to run it on a **local** model (on-device / edge workstation) or escalate to a **cloud** model. SuperClaw also masks PII on-device before anything reaches the cloud.

The goal is a product-grade benchmark answering four questions:
1. **Decomposition/routing quality** — does Auto Route split tasks sensibly between local and cloud?
2. **Accuracy** — is task accuracy preserved under hybrid routing vs. a pure-cloud baseline?
3. **Performance** — TTFT, TPS (tokens/s), and memory usage, captured for both modes.
4. **Privacy** — does local/sensitive information (PII) actually *not* leave for the cloud?

Per user decisions:
- **Task domain:** agentic / tool-use tasks (exercises Auto Route decomposition directly).
- **Privacy ground truth:** a logging proxy placed *in front of MiniMax* — we inspect exactly what the cloud endpoint received.
- **Cloud baseline:** **MiniMax-M3** via its OpenAI-compatible API; compare **hybrid (Auto Route)** vs **forced cloud-only** on the identical task suite.
- **Deployment:** SuperClaw is **not yet deployed** — the plan includes bringing it up on a LAN machine that we control remotely.

## Kickoff prerequisites (confirm before execution — exploration was interrupted)

These local facts must be verified first (the local-context scan was stopped early):
1. **Remote access to the LAN test machine** — connection method (SSH host/user/IP; there is a memory note `lan-target-206-network.md` about reaching `192.168.2.206` with dual-NIC routing pitfalls — HTTP must bind source IP / `curl --interface`, SMB needs a `route` fix). Confirm the actual test-machine IP, OS, and credentials.
2. **Hardware fit** — SuperClaw's beta targets a 2-system setup (a Panther Lake / AI-PC companion running the desktop app + a workstation with 4× Arc Pro B70 serving Qwen3-Coder-Next-80B). Confirm what the LAN machine actually is; if it can't serve the full local model, we fall back to the smallest supported local-serving config or a single-machine dev deployment.
3. **MiniMax access** — the mmx credentials live at `~/.mmx/config.json`. Confirm the key can reach **MiniMax-M3** over the OpenAI-compatible endpoint (base URL + model id). If M3 is unavailable, use the latest available MiniMax model and record the substitution.

## Evaluation standards we anchor to (from research)

- **Accuracy / capability:** methodology from HELM (multi-metric, transparent) and the LM-Eval-Harness ecosystem; for *agentic* tasks we grade by task-success (rubric / execution) + an LLM-judge, since MMLU-style exact-match doesn't apply. We report per-task success rate with a fixed rubric.
- **Serving performance:** MLPerf-Inference-style metrics — **TTFT** (prefill), **TPOT/ITL** and **TPS** (decode), end-to-end latency, reported as mean + P95/P99, plus peak memory. These are the industry-standard axes.
- **Privacy:** there is *no* single accepted standard, but the established methodology is **PII-extraction-rate** (a sample counts as leaked if ≥1 planted PII entity appears in what the cloud received) — Wang et al. (2023) approach used by PII-Scope / PII-Bench / AgentLeak. Detection via **Microsoft Presidio NER + regex + LLM-judge** on the captured cloud payloads. Intel's own claim is "99% PII-masking accuracy on industry-standard privacy benchmarks" — our test independently checks this.

## Architecture of the test harness

```
[Control machine (this box)] --SSH--> [LAN test machine]
                                         ├─ SuperClaw desktop app (agent + Auto Route)
                                         ├─ local model server (Qwen3-Coder or fallback)
                                         └─ SuperClaw cloud slot ─┐
                                                                  ▼
                                    [Logging proxy (mitmproxy/FastAPI)] ──► MiniMax-M3 (OpenAI-compatible)
                                       (records every cloud-bound request/response = privacy + cloud-token ground truth)
```

Two run configurations, identical task suite, identical proxy in front of MiniMax:
- **Config A — Hybrid:** Auto Route ON. Local model handles what it decides; only escalations hit MiniMax-M3 through the proxy.
- **Config B — Cloud-only:** Auto Route forced to always-cloud (or local model disabled). Every step goes to MiniMax-M3 through the proxy.

The proxy is the single choke point that gives us: (a) exact cloud payloads → privacy leak detection, (b) cloud token counts → the "70% token reduction" style comparison, (c) cloud-side TTFT/TPS.

## Execution steps

### Phase 0 — Remote bring-up (on LAN machine, driven over SSH)
- Establish/verify SSH; respect the dual-NIC routing note from `lan-target-206-network.md` (bind correct interface).
- Install SuperClaw per the `intel/intel-ai-builder` (superclaw) beta instructions (Node ≥20; OpenClaw base; config at `~/.openclaw`/SuperClaw config yaml). Bring up the local model server; verify the web UI/gateway port responds (OpenClaw defaults ~`18789`; confirm SuperClaw's actual port).
- Note: GitHub/raw are blocked from the control box by enterprise policy — fetch repo/instructions **from the LAN machine** (Intel proxy) or via the desktop installer.

### Phase 1 — MiniMax logging proxy
- Stand up a small **OpenAI-compatible logging proxy** (mitmproxy addon or a ~80-line FastAPI reverse proxy) that forwards to MiniMax's OpenAI-compatible endpoint using the mmx key, and appends every request/response (messages, token usage, timestamps) to a JSONL log.
- Point **SuperClaw's cloud provider** at this proxy (base_url = proxy) for Config A, and a **standalone cloud-only client** at the same proxy for Config B. Reuse mmx auth from `~/.mmx/config.json`.

### Phase 2 — Task suite (agentic/tool-use, privacy-instrumented)
- Build ~20–30 agentic tasks (file parsing/editing, local search/memory retrieval, code, web-research, calendar/email-style tool use) — the categories SuperClaw claims to keep local vs. escalate.
- Into a defined subset, **plant synthetic PII** (fake names, emails, SSNs, phone numbers, API keys) in local files/context that the task must *use locally* but that has *no legitimate reason to reach the cloud*. Keep a ground-truth registry of every planted PII token for leak scanning.
- Each task has a machine-checkable success rubric (execution result, expected artifact, or LLM-judge with a fixed prompt).

### Phase 3 — Instrumentation
- **TTFT / TPS / latency:** capture at two layers — (1) client-observed end-to-end via the SuperClaw API/UI automation, (2) cloud-segment via proxy timestamps + `usage` token counts. Compute TTFT, TPOT/ITL, TPS, e2e; report mean + P95/P99.
- **Memory:** sample RSS/GPU memory of the SuperClaw app + local model server on the LAN machine (`psutil` / `xpu-smi`/`intel_gpu_top` equivalent for Arc) at fixed intervals during each run.
- **Routing:** record Auto Route decisions per sub-step (local vs cloud) from SuperClaw logs and cross-check against proxy hit counts.

### Phase 4 — Run matrix
- Run the full suite under **Config A (Hybrid)** and **Config B (Cloud-only)**, N repetitions each for stability. Fixed decoding params, warm-up excluded.

### Phase 5 — Privacy analysis
- Scan **all captured cloud payloads** (from the proxy JSONL) for any planted PII using Presidio NER + regex + LLM-judge.
- Metrics: **PII leak rate** (fraction of planted entities that appeared cloud-side), per-entity-type breakdown, and % of tasks with zero leakage. Independently validate SuperClaw's masking claim.

### Phase 6 — Report
- Comparison tables: Hybrid vs Cloud-only on **accuracy, TTFT, TPS, memory, cloud-token volume, PII leak rate**.
- Routing analysis: % of steps/tokens kept local, and whether decomposition was sensible.
- Chart the results (use the `dataviz` skill for consistent, accessible charts). Note all substitutions/limitations (e.g., hardware fallback, MiniMax model actually used).

## Reusable assets to leverage
- `~/.mmx/config.json` + the `minimax-multimodal-toolkit` (mmx) for MiniMax auth/models (per memory `minimax-image-gen-vs-seedream.md`).
- `lan-target-206-network.md` memory for the LAN routing workaround.
- `dataviz` skill for the final charts; Microsoft **Presidio** for PII detection.

## Verification / how we know it works
- **Proxy sanity:** issue one manual MiniMax call through the proxy; confirm the JSONL logs the exact request+response and token usage.
- **Routing sanity:** run one obviously-local task and one obviously-cloud task; confirm Auto Route logs and proxy hits match expectations.
- **Privacy sanity:** run one PII-laden local task; confirm the planted PII appears in the local model context but the proxy log shows it masked/absent (or flag it if it leaks).
- **Metric sanity:** confirm TTFT/TPS/memory numbers are captured and non-degenerate for a single task before running the full matrix.
- **End-to-end:** the full run matrix completes and produces the comparison tables + charts.

## Open risks
- Hardware may not meet SuperClaw's 4×B70 local-serving requirement → fall back to smallest supported local model or single-machine dev mode (documented).
- MiniMax-M3 may not be enabled on the key → use latest available MiniMax model.
- SuperClaw beta may not expose a scriptable API → drive via UI automation or its gateway/CLI; confirm during Phase 0.
