# SuperClaw Hybrid-Architecture Benchmark — **v2 Plan & Handoff Brief**

This is the **v2 plan** for the SuperClaw benchmark, incorporating every finding from v1 (the first run on 2026-08-05). The v1 report is at `superclaw_benchmark/TEST_REPORT.md` (FINAL — 15 sections) and `superclaw_benchmark/report_plan_cn.html` (13 sections). This v2 plan is what **Claude on machine B** should execute next.

## 1. Why v2 exists — what v1 taught us

v1 ran the suite once at `perf_weight=0.7` (per the run report) with these hidden defects:

| Defect (discovered in v1 post-run DB audit) | Effect on v1 result |
|---|---|
| `config.perf_weight=1.0` in DB, not the `0.7` the report claimed | Strongest cloud bias, yet 0/24 hybrid tasks went to cloud — suspicious |
| Local id `qwen3.5-4b` (lowercase `b`) does not match trained label `Qwen3.5-4B` (uppercase `B`) | `LatentFactorRouter` treated the 4B as unknown, fell back to default-latency prediction |
| Hybrid cloud slot was NOT pointed at our logging proxy | Router had no working cloud path to choose even at `perf_weight=1.0` |
| `max_tokens=2048` truncated long thinking chains | t02 / t06 / t08 / t17 / t18 — judge JSON truncated, default-fail |
| No `perf_weight` sweep — single data point | Cannot draw the routing-vs-accuracy-vs-cost frontier |
| Industry-standard benchmark tasks not in the suite | No horizontal comparison to GAIA / BFCL / τ² / PrivacyLens |

v1's **privacy finding (0 % vs 100 % leak)** is unaffected by these defects and remains the headline win. v1's **routing finding (100 % local) is partly a configuration artifact** and needs a clean re-run to confirm.

## 2. v2 goals

1. **Verify Auto Route's natural behavior** with a properly-labelled local model + connected cloud slot + a sweep of `perf_weight`.
2. **Lift the truncated outputs** so the P95 latency, judge verdicts, and accuracy are not artificially deflated.
3. **Run the industry-standard task expansion** to enable horizontal comparison vs public benchmarks.
4. **Confirm the privacy win** holds even with the cloud slot active (no regression to v1's headline).

## 3. What changes from v1 (diff)

| Item | v1 | v2 |
|---|---|---|
| Local model id | `qwen3.5-4b` (lowercase) | **`Qwen3.5-4B`** (uppercase) — match trained label |
| Cloud slot | not wired | **wired to logging proxy** at `127.0.0.1:8900` → MiniMax-M3 |
| `perf_weight` | 1.0 (DB) / 0.7 (report) | **sweep {0.3, 0.5, 0.7, 0.9, 1.0}** |
| `max_tokens` | 2048 | **8192** |
| Task suite | 24 tasks | **24 + 10 industry** = 34 tasks |
| Re-runs per config | 1 | **3** (for Pass^k reliability, per §4.1) |
| Token-accounting fix | proxy SSE usage-parser bug | patched (see §6.4) |

## 4. Environment (unchanged)

- **Test machine B**: `laptop-0gdqgd3i`, `10.188.194.206`, Windows 11. GPU drivers already upgraded: **Intel `32.0.101.8864`** + NVIDIA RTX 5050 (`32.0.15.9282`).
- **Local backend**: SuperClaw's built-in **llama.cpp** (`provider=llamacpp`); current `qwen3.5-0.8b` router model; the 4B model files are already on B (`Qwen3.5-4B-Q4_K_M.gguf`, 2.83 GB, SHA `3874209241c9…`).
- **Cloud**: **MiniMax-M3** via `https://api.minimaxi.com/v1`. API key in `C:\Users\Trekker-PTL\.mmx\config.json` (`sk-cp-…`).
- **Harness workspace**: `C:\Users\Trekker-PTL\superclaw_benchmark\` (already populated; everything from v1 stays).
- **Judge**: keep `MiniMax-M2.7` (different model class from M3 — avoids self-preference bias). Temperature 0.
- **All proxy envs cleared on B**: the broken machine-level `HTTP(S)_PROXY=child-prc…:913` was already removed via `fix_proxy_B.bat` in v1 — keep it removed.

## 5. v2 execution sequence (on B)

Each step lists the exact file / command path. **All files referenced are already on B** at `C:\Users\Trekker-PTL\superclaw_benchmark\` (or in A's mirror).

### 5.1 Pre-flight sanity (≈ 1 min)
```powershell
# On B, in any cmd:
wsl --status                                    # confirm WSL still healthy
curl --noproxy "*" https://api.minimaxi.com/v1/models -o NUL -w "%{http_code}\n"
# expect: 401 (connected, missing key is fine)
Get-Process | Where-Object {$_.ProcessName -match "SuperClaw|ollama"} | Format-Table -Auto
# expect: SuperClaw.exe + servicehub + llmrouter_manager + ollama running
```

### 5.2 Fix #1 — rename local model id (case-sensitive match to trained label)

The router DB sits at `%LOCALAPPDATA%\SuperClaw\llmrouter_manager\llmrouter_manager.db`. Run **two edits** via `python` (no sqlite3 CLI on B):

```python
import sqlite3, pathlib, shutil
src = pathlib.Path(r"C:\Users\Trekker-PTL\AppData\Local\SuperClaw\llmrouter_manager\llmrouter_manager.db")
backup = src.with_suffix(".db.v1.bak"); shutil.copy2(src, backup); print("backup ->", backup)
con = sqlite3.connect(src); cur = con.cursor()
cur.execute("UPDATE config SET value = ? WHERE key = 'active_chat_model_id'", ['"Qwen3.5-4B"'])
print("config.active_chat_model_id rows:", cur.execute("SELECT value FROM config WHERE key='active_chat_model_id'").fetchall())
cur.execute("UPDATE bundle_lifecycle SET primary_bundle = REPLACE(primary_bundle, 'qwen3.5-4b', 'Qwen3.5-4B') WHERE singleton = 1")
print("bundle primary_bundle:", cur.execute("SELECT primary_bundle FROM bundle_lifecycle").fetchone()[0][:200])
con.commit(); con.close()
print("OK — clean cold-boot next")
```

After edits, **clean cold-boot** (the v1 swap_to_4b.py showed force-killing leaves the router in a stale "running" state — full kill + restart):
```powershell
taskkill /F /IM SuperClaw.exe /T
Start-Process "C:\Program Files\Intel\SuperClaw\SuperClaw.exe"
Start-Sleep -Seconds 30
Get-Process | Where-Object {$_.ProcessName -eq "SuperClaw"}
```

Verify by hitting the gateway:
```powershell
curl --noproxy "*" http://127.0.0.1:18321/v1/models
# expect a JSON list; the "auto" entry should describe the router
```

### 5.3 Fix #2 — wire SuperClaw's cloud slot to the logging proxy

v1 hit a wall here: the cloud provider config lives in an **encrypted** blob (`%LOCALAPPDATA%\SuperClaw\llmrouter_manager\state\providers\*.bin`) and SuperClaw exposed no control-plane API on this build. v2 needs to crack this — try **in order**:

1. **GUI automation** — the SuperClaw GUI's "Settings → Cloud" is where the slot is configured. Try driving it via Windows UI Automation (`pywinauto` / `uiautomation` module) to (a) open Settings, (b) paste our proxy URL `http://127.0.0.1:8900/v1`, (c) paste the MiniMax-M3 API key, (d) save.
2. **Find the runtime API** — probe `http://127.0.0.1:18321/{config,admin,slots,providers}` for a REST endpoint that wasn't in v1. The earlier 404s were on `GET /config`, `GET /openapi.json`, `GET /admin/system/shutdown` (the last one was reachable — we used it to trigger v1's shutdown).
3. **Direct DB edit** — if the provider config is in a *non-encrypted* table, edit it. Inspect all tables in `llmrouter_manager.db` first (already done in v1: only the 8 tables are config / bundle_lifecycle / model_verifications / token_events / token_usage / bundle_idempotency / bundle_idempotency_legacy / bundle_prepare_operations). If the provider config is elsewhere (e.g., the encrypted `.bin` blob in `state/providers/`), document that it's not editable without first decrypting the format.

If after (1) and (2) the cloud slot is still unwired, **fall back to a documented proof**: keep the cloud slot unwired (as in v1) but verify the fix in #1 alone — i.e., rerun with `Qwen3.5-4B` matched, at multiple `perf_weight` values, and **report that the cloud slot redirect remains a v1 carry-over blocker**, with the exact failure mode captured for Intel.

### 5.4 Fix #3 — patch the proxy's SSE usage-parser bug

v1's proxy logged `cloud_completion_tokens_total=16` across 38 cloud calls — clearly wrong. The fix is in `proxy/minimax_logging_proxy.py`'s streaming path. Issue and edit:

```python
# In proxy/minimax_logging_proxy.py, the streaming response handler already iterates
# the SSE bytes and tries to extract `usage` by substring match on data: lines.
# The bug: proxy buffers all bytes then emits at the end, so the SSE chunk order is
# preserved but the final chunk containing `usage` (sent by MiniMax only when
# stream_options.include_usage is true) is never requested.
# Fix: when the client sets `stream: true`, force-inject `stream_options: {include_usage: true}`
# into the JSON body before forwarding. Then parse the last data: frame for `usage`.

# Patch (in the proxy body-parse block, after `parsed_req = json.loads(body)`):
if parsed_req.get("stream") and "stream_options" not in parsed_req:
    parsed_req["stream_options"] = {"include_usage": True}
    body = json.dumps(parsed_req, ensure_ascii=False).encode("utf-8")
```

Apply via SFTP from A (or by hand on B), restart the proxy.

### 5.5 Run matrix

Total runs = **2 configs × 5 perf_weight values × 3 repetitions × 2 task suites (24 + 10)** = 60 runs. At ~30 s per task including warm-up that's ~5 hours wall-clock. If too long, drop the perf_weight sweep to {0.3, 0.7, 1.0} first and add the middle points only if time permits.

```python
# pseudocode for the run driver
configs = ["hybrid", "cloud_only"]
perf_weights = [0.3, 0.5, 0.7, 0.9, 1.0]
reps = [1, 2, 3]
task_suites = {
    "main":   "C:/.../tasks/tasks.jsonl",          # 24 tasks
    "industry": "C:/.../tasks/tasks_industry.jsonl"  # 10 tasks
}
for cfg in configs:
    for pw in perf_weights:
        set_perf_weight(pw)                     # write config.perf_weight in DB, restart router
        for rep in reps:
            for suite_name, path in task_suites.items():
                run_suite(cfg, pw, rep, suite_name, path)  # streaming client; logs JSONL
```

Output JSONL files (per run):
- `logs/runs_v2/{cfg}_pw{pw}_rep{rep}_{suite}.jsonl` — cloud-call log
- `logs/runs_v2/answers/{cfg}_pw{pw}_rep{rep}_{suite}.jsonl` — answers + client TTFT + route trace
- `results/runs_v2/{cfg}_pw{pw}_rep{rep}_{suite}/{metrics,privacy,routing}.json`

### 5.6 Analysis (after all runs)

Extend `harness/analyze.py` minimally to accept multiple `perf_weight` runs:
- Aggregate per `perf_weight`: leak rate, accuracy mean ± std across reps, TTFT P95, cloud tokens, % tasks kept local.
- Plot `perf_weight` vs `{local_retention_rate, accuracy, PII_leak_rate, cloud_completion_tokens}` — this is the **routing-vs-accuracy-vs-cost frontier**, the v1 single point doesn't give you.
- For the industry suite: per-source accuracy (GAIA / BFCL / τ² / PrivacyLens).

### 5.7 Report updates

Append to `TEST_REPORT.md` a new section **§16 v2 Re-run Results** with:
- The `perf_weight` frontier chart (4 panels).
- Per-source industry-task accuracy table.
- Pass^k reliability numbers (pass^1 vs pass^3).
- Confirmation that the privacy win held at all `perf_weight` values.
- Any new failures catalogued as in v1 §11.

## 6. Verification checklist (how we know v2 succeeded)

- [ ] LatencyRouter no longer reports "configured local model 'qwen3.5-4b' did not match any trained label" in the llmrouter_manager log.
- [ ] At `perf_weight=1.0` Hybrid, at least 1 task goes to cloud.
- [ ] At `perf_weight=0.3` Hybrid, ≤ 1 task goes to cloud.
- [ ] `cloud_completion_tokens_total > 0` for every cloud call (bug fixed).
- [ ] No hybrid answer parrots planted PII verbatim (PII-parroting guard still clean).
- [ ] No planted PII in the cloud payload at any `perf_weight` (privacy win holds).
- [ ] Per-task accuracy at `perf_weight=1.0` Hybrid approximates Cloud-only accuracy (≤ 5 pp gap), proving the architecture is sound when the local model is the bottleneck.
- [ ] All 10 industry tasks complete; per-source accuracy reported.

## 7. Files to be aware of (all on B at `C:\Users\Trekker-PTL\superclaw_benchmark\`)

```
CLAUDE.md                 # v1 handoff brief — superseded by this file for the rerun
CLAUDE_V2.md              # this file
plan.md                   # original plan from A (English)
TEST_REPORT.md            # v1 final report — DO NOT EDIT during v2
report_plan_cn.html       # v1 Chinese HTML — DO NOT EDIT during v2
results_b/                # v1 raw artifacts (mirrored from B's results/)
proxy/minimax_logging_proxy.py  # needs the §5.4 patch
tasks/build_suite.py      # original 24-task generator (no change)
tasks/industry_benchmarks.py   # new 10-task generator + load_real_public loader
tasks/tasks_industry.jsonl     # the 10 industry exemplars (already generated)
harness/analyze.py        # smoke-tested; needs minor aggregation updates for v2
harness/judge.py          # unchanged from v1 (still uses MiniMax-M2.7)
harness/rsh.py            # SSH helper (not needed on B)
results_b/swap_to_4b.py   # v1's local-model swap (use §5.2's edit instead for the rename)
```

## 8. Critical reminders

- **B's broken proxy is removed**; keep it removed. Don't re-export `HTTPS_PROXY`.
- **B reaches MiniMax / hf-mirror / npm directly** — use `--noproxy "*"` everywhere.
- **GUI displays "failed to start, unable to find local 4b model"** is harmless; the API path works.
- **Do NOT modify vendor registry** (`%LOCALAPPDATA%\SuperClaw\servicehub\primary-bundle\…`) — only the llmrouter_manager DB is fair game for fixes.
- **If the cloud-slot redirect truly is impossible on this build**, fall back gracefully and document it as a v1 carry-over blocker (don't spend more than 30 min on §5.3).

When the rerun is done, mirror the new `results/runs_v2/` to `superclaw_benchmark/results_b_v2/` here and I'll fold §16 into both reports.
