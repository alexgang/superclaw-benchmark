# Why the PII Module Wasn't Called — Architectural Analysis

**Date:** 2026-09-09
**Investigator:** Claude (Mavis) on machine B (`10.188.194.206`)
**Method:** Read the actual source code in `C:\Program Files\Intel\SuperClaw\servicehub\security_manager\_internal\protection_service\routes\*.py` and `llmrouter_manager\_internal\llmrouter_manager\routing\policy\model_profiles.json`, then cross-checked with runtime logs.

## TL;DR

**The PII module is a library, not a transparent proxy.** It is not in the chat-completion path at all. The SuperClaw design assumes the **agent (opencode) will explicitly call** the PII module's endpoints (`/v1/file/protect`, `/v1/session/query/rewrite`, `/v1/session/response/restore`) before and after each chat. **opencode is not making those calls.** The chat body therefore flows: opencode → llmrouter_manager → cloud, completely unredacted, regardless of `data-protection/mode`.

This is not a configuration issue. The mode is irrelevant for chat-body PII. It only governs `file.protect`.

---

## 1. The three places the PII module can be called

From `protection_service/routes/` (read directly from the .py files in the install dir):

| Endpoint | Purpose | Caller |
|---|---|---|
| `POST /v1/file/protect` | Protect a file (mask PII) before the agent reads it. Returns masked content + a **registry** (real-value ↔ placeholder map) stored under `pii_registry_store[session_id, operation_id]`. | **agent** (opencode) before reading a file |
| `POST /v1/session/query/rewrite` | Look up the latest registry for the session and replace real values with placeholders in the user query. | **agent** (opencode) before sending the user query to the model |
| `POST /v1/session/response/restore` | Inverse of the above: replace placeholders in the model response with real values, for display. | **agent** (opencode) after receiving the model response |
| `POST /v1/file/redact[/upload]` | Direct, stateless redaction (no session/registry context). What my earlier test scripts used. | **anything** — this is the manual-mode API |
| `POST /v1/text/redact` | Same, but for free text. Currently broken (`sanitize_ready=false`). | n/a |

The `session.query_rewrite` and `session.response.restore` are **lookup-only** — they only redact values that were already registered by a prior `file.protect` (or equivalent) call. If no entity was ever registered, the query is returned unchanged (the `found=False registry_path_set=False` we saw in the security_manager log).

## 2. The smoking gun: `routing/policy/model_profiles.json`

The file `C:\Program Files\Intel\SuperClaw\servicehub\llmrouter_manager\_internal\llmrouter_manager\routing\policy\model_profiles.json` contains this comment block:

```json
"_comment_2": "Field: system_prompt = filename under routing/policy/prompts/ to
REPLACE the request's system message with (weak-local task-hardening). Applies
on the LOCAL path only; cloud requests are never transformed. Unknown model_id
=> no transform (safe default)."
```

**`cloud requests are never transformed`** — that is the design statement. llmrouter_manager is a transparent pass-through to the cloud model. It does not invoke the PII module on the chat body. The `data-protection/mode` setting does not control chat-body redaction because **there is no chat-body redaction in the llmrouter_manager layer at all.**

The mode only governs what `file.protect` returns (see `protect_routes.py` lines around the `mode == "none"` early return and the `mode == "deterministic" / "hybrid" / "llm"` dispatch). And `file.protect` is only called by the agent.

## 3. What `data-protection/mode = none` actually does

Reading `protect_routes.py` (the function `protect_file`):

```python
mode, threshold = await fetch_file_protection_settings()  # from llmrouter

# Mode = none: skip all protection, return original path unchanged.
if mode == "none":
    logger.info("...step=completed resolved_by=none protection_applied=false")
    return ProtectFileResponse(
        success=True,
        masked_file_path=req.source_file_path,   # <-- original, unchanged
        resolved_by="none",
    )

# Mode = deterministic: DPS only, no LLM fallback.
# Mode = llm: LLM pipeline, DPS fallback.
# Mode = hybrid: DPS first, LLM fallback on low confidence.
```

So `mode = none` only affects `file.protect`. With `mode = hybrid`, a `file.protect` call would actually mask the file and return a registry. But it has no effect on anything the agent (opencode) does unless the agent calls `file.protect`.

## 4. What we observed in the logs

**`security_manager_2026-09-09.log`** (32369 bytes, today's only non-empty security_manager log):

- 6 `file.redact` calls between 02:17:34 and 02:19:21. These are from my earlier test scripts (`_e2e_full.py` etc.) hitting `/v1/file/redact/upload` directly. They all returned successful masks (e.g. `columns_masked=4`).
- 1 `session.query_rewrite` call at 02:26:03:
  ```
  data_protection endpoint=session.query_rewrite step=lookup
  operation_id=none explicit_op=False found=False registry_path_set=False
  ```
  `found=False` because no entity was ever registered for the session. The call was a no-op.

**`pipeline_runs/<session>/<timestamp>/pipeline.log`** (the last 5 runs, all from previous weeks):

```
data_protection operation_id=... endpoint=file.protect step=settings_resolved
mode=none threshold=0.750 source_ext=.md source_size_bytes=...
data_protection operation_id=... endpoint=file.protect step=completed
resolved_by=none protection_applied=false
```

**Every prior agent-initiated `file.protect` was also `mode=none`, so the agent was bypassing the redaction even when it actually called the endpoint.** This is consistent with the GUI default: the SuperClaw data-protection slider is at "off" by default.

## 5. The complete call chain (what should happen vs. what actually happens)

### What the design assumes (the happy path)

```
User types in Tauri chat
  ↓
Tauri → opencode (port 8787)
  ↓
opencode reads workspace file via file.protect
  security_manager file.protect → masked content + registry (per-session)
  ↓
opencode builds the prompt with masked content
  ↓
opencode calls session.query_rewrite on the user query
  security_manager session.query_rewrite → query with placeholders
  ↓
opencode → llmrouter_manager → cloud model
  (cloud only sees placeholders, no real PII)
  ↓
cloud model responds with placeholders
  ↓
opencode calls session.response.restore
  security_manager session.response.restore → response with real values
  ↓
Tauri shows the final answer
```

### What actually happens in this build

```
User types in Tauri chat
  ↓
Tauri → opencode (port 8787)
  ↓
opencode reads workspace file via ??? (we don't know the path opencode uses)
  (if it doesn't call file.protect, the file is read raw)
  ↓
opencode builds the prompt with raw content
  ↓
opencode → llmrouter_manager → cloud model      ← NO REDACTION
  (cloud sees all 15 PII tokens verbatim)
  ↓
cloud model responds, possibly echoing PII
  ↓
opencode calls session.query_rewrite (?)  ← we see found=False in logs
  (this is a restore attempt, not a pre-redaction, because no registry exists)
  ↓
Tauri shows the answer (with whatever PII the model echoed)
```

The "session.query_rewrite" call that I see at 02:26:03 in the log is the agent's post-hoc restore attempt: it has no registry to look up, so it returns the text unchanged. **It is not a pre-redaction step.**

## 6. Why each of my PII module tests had this same blind spot

| Test | What I drove | Was security_manager in the path? | Reason |
|---|---|---|---|
| `lh_proxy_runner.py` | logging proxy → cloud | **No** (bypassed both llmrouter_manager and security_manager) | synthetic routing, never touched security_manager |
| `security_manager /v1/file/redact/upload` direct | security_manager only | **Yes, but for files only** | direct API, no chat path |
| `127.0.0.1:18321/v1/chat/completions` model=cloud-model | llmrouter_manager only | **No** | llmrouter_manager does not invoke security_manager on chat bodies (this file proves it) |
| `opencode /w/.../session/.../message` | opencode → llmrouter_manager | **No** | opencode does not pre-process chat through security_manager either |

In all four cases, the **chat body was never seen by security_manager**. The only times security_manager was invoked for non-direct-API use was `file.protect` and the no-op `session.query_rewrite` from opencode's restore attempt.

## 7. What would actually fix the leak

Three orthogonal axes; doing only one will not work:

1. **Have opencode call `file.protect` before reading any workspace file**, and pass the masked content to the model. (This would have masked the SSN/phone/idcard in the lh09 CSV. The CN_PERSON column would still be unmasked unless the agent also calls `query_rewrite` with the user-typed PII.)
2. **Have opencode call `session.query_rewrite` on the user query** before sending it to the model. This requires the agent to detect PII in the user's typed input, or to always re-rewrite against the latest file.protect registry.
3. **Have opencode call `session.response.restore` on the model response** to put real values back. Without this, the user sees placeholders forever, which is unusable.

The PII module has all three endpoints, and the design is internally consistent. The gap is that **opencode doesn't drive this state machine**.

The architectural alternatives (which I am NOT recommending — just listing) would be:

- **Add a transparent chat-body redactor in llmrouter_manager** that intercepts every `chat.completion` request, calls `file.protect`-equivalent auto-detection on the messages, and masks PII in-place. This would break the `model_profiles.json` comment ("cloud requests are never transformed") and would require returning to the client the registry, so the response can be restored. Conceptually simple, but the registry round-trip is tricky.
- **Move PII detection to a sidecar proxy** that sits between opencode and llmrouter_manager and applies regex redaction to every request/response. This is what my synthetic `lh_proxy_runner.py` did. Intel's design chose not to do this, presumably to keep the PII pipeline entirely in user-space and avoid double-redaction issues.

## 8. The honest answer to the user's "I don't see any test records" question

When the user opened the Tauri GUI and saw no PII module activity, it was because:
- The data-protection/mode is `none` (default). `file.protect` would return the file unredacted even if called.
- The PII module is not in the chat-completion path. The chat body is never redacted.
- opencode is not pre-registering entities via `file.protect`, so `session.query_rewrite` has nothing to look up.

The combination means: **the PII module is fully installed and working, but no one in the chain asks it to do anything for the chat body.** The module effectively sits idle for normal agentic chat usage. The 19-20 / 60 leak rate we measured is therefore a property of the unprotected chat, not a failure of the PII module per se.

## 9. Evidence index

- `C:\Program Files\Intel\SuperClaw\servicehub\security_manager\_internal\protection_service\routes\session_routes.py` — `/v1/session/query/rewrite` and `/v1/session/response/restore` source.
- `C:\Program Files\Intel\SuperClaw\servicehub\security_manager\_internal\protection_service\routes\protect_routes.py` — `/v1/file/protect` source, including the `mode == "none"` early-return path.
- `C:\Program Files\Intel\SuperClaw\servicehub\llmrouter_manager\_internal\llmrouter_manager\routing\policy\model_profiles.json` — comment that cloud requests are never transformed.
- `C:\Users\Trekker-PTL\AppData\Local\SuperClaw\security\logs\security_manager_2026-09-09.log` — 6 file.redact calls (from my test scripts) + 1 session.query_rewrite lookup (found=False).
- `C:\Users\Trekker-PTL\AppData\Local\SuperClaw\security\logs\pipeline_runs\...\pipeline.log` — historical evidence that all prior agent-initiated `file.protect` calls were `mode=none → protection_applied=false`.
- `C:\Users\Trekker-PTL\superclaw_benchmark\logs\cn_lh_e2e_responses.md` — the 19-20 PII echoes measured against the unprotected chat.
