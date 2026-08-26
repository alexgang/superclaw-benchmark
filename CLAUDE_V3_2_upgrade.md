# SuperClaw 1.2.0.812 upgrade + re-test brief (for Claude on B)

The 1.2.0.812 installer is on B at `C:\Users\Trekker-PTL\Downloads\SuperClaw-Setup-1.2.0.812.exe` (byte-verified by A). This run tests whether **1.2.0 fixes the three blockers that limited v3 on 1.1.0**, then re-runs the benchmark.

## What 1.1.0 could NOT do (the things to re-check on 1.2.0)
1. **`security_manager` PII masking was inactive** — a 371-token PII-laden prompt reached the cloud unmasked; privacy relied on the cloud model's own discretion. → **Does 1.2.0 actually mask PII before egress?**
2. **Cloud slot could not be redirected to our logging proxy** — provider config is an encrypted `.bin`; all PUT variants were silently ignored. → **Does 1.2.0 expose a supported way to point the cloud slot at `http://<A>:8900/v1` (our proxy)?** Without this we can't scan the real egress payload.
3. **Edge mode failed dual-probe validation** (needed both chat + embeddings) → had to fall back to local-llamacpp mode. → **Does 1.2.0's edge/route config validate cleanly?**

## Install steps (on B console — GUI installer)
1. Quit any running SuperClaw (`taskkill /F /IM SuperClaw.exe /T`).
2. Run `SuperClaw-Setup-1.2.0.812.exe` (double-click; it's a GUI/NSIS-style installer). Accept defaults; note the install dir (likely `C:\Program Files\Intel\SuperClaw`, overwriting 1.1.0).
3. **Clear the broken proxy first** if not already: the machine-level `HTTP(S)_PROXY=child-prc.sh.intel.com:913` breaks HF/model downloads. `fix_proxy_B.bat` on the Desktop removes it (admin). Then launch SuperClaw so the router model bundle downloads.
4. Confirm version: check `%LOCALAPPDATA%\SuperClaw\...\version` or the app's About; confirm the gateway is on `127.0.0.1:18321`.

## Re-inspect the architecture (read-only, before re-running)
Capture what changed vs 1.1.0:
- `curl --noproxy "*" http://127.0.0.1:18321/v1/models` — is `auto` usable (200, not 424)? are `local-model`/`cloud-model` aliases present?
- Ports: is `security_manager` still on `:18826`? new services?
- **PII-masking probe (the headline):** send one PII-laden task through `model=auto` forced to cloud; capture the **actual prompt that egresses**. If 1.2.0 exposes a cloud-slot base_url override, point it at our logging proxy (`http://10.188.193.79:8900/v1` — A's proxy, or run the proxy locally on B) and read `logs/*_cloud_calls.jsonl`: **is the PII masked/redacted (`[REDACTED]`, `<PERSON>`, hashed) or verbatim?**
- Check for a settings flag that enables PII masking (Settings → Privacy/Security). 1.1.0 had none.

## Re-run the benchmark (same v3 harness, already on B)
Everything from v3 is already staged at `C:\Users\Trekker-PTL\superclaw_benchmark\`:
- Task suites: `tasks/tasks.jsonl` (24) + `tasks_long_horizon.jsonl` (8) + `tasks_pinchbench.jsonl` (147) + `tasks_industry.jsonl` (10)
- `stage_workspace.py`, `harness/judge_prepare.py`, `proxy/minimax_logging_proxy.py`
- Run per `CLAUDE_V3_edgemode.md` (edge mode if it now validates; else local-llamacpp mode as before)
- **`perf_weight` sweep** {0.3, 0.5, 0.7, 0.9, 1.0}; **`max_tokens=8192`** this time (v3 used 1024 — too low)
- Write answers to `results/v3_2/answers_pw*.jsonl` + routing traces + (if proxy wired) `logs/v3_2_cloud_calls.jsonl`

## Judging (A side — do NOT judge on B)
B writes raw answers only. A (Claude Opus 4.8, inline, no API key) grades via `judge_prepare.py prepare → grade → finalize`. Mirror `results/v3_2/` back to A.

## The one comparison that matters most
**1.1.0 vs 1.2.0 on the PII-masking verdict.** If 1.2.0's `security_manager` now masks PII on the wire, that flips the headline privacy finding from "not verifiable / relies on cloud model discretion" to "actively enforced on-device" — the single most important thing this upgrade could change. Capture the egress payload either way.
