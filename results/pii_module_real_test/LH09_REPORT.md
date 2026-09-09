# lh09 End-to-End PII Module Test (Focused)

**Date:** 2026-09-09
**Task:** lh09 — 处理今天的退款批次（中文场景）— refund email processing
**Path tested:** original prompt → real `security_manager` regex redaction → real `MiniMax-M3` cloud
**Comparison:** same task with the PII module bypassed

---

## TL;DR

| Metric | Bypass (no PII module) | With PII module (regex) | Delta |
|---|---:|---:|---:|
| PII tokens in cloud-bound request | 8 | 3 | **−5 (62% caught)** |
| PII tokens echoed in model response | 8 | 3 | **−5 (62% reduction)** |
| Model produced a usable deliverable | yes (1785 chars) | yes (1893 chars) | parity |
| Cloud saw real Chinese SSN, phone, ID-card | yes | **no** | full block |

The single remaining leak type is **CN_PERSON (Chinese names)** — `customer` is not a column the regex flags. Everything else (`CN_SSN`, `CN_PHONE`, `CN_IDCARD`) is fully redacted before the cloud ever sees the request.

---

## 1. Setup

- Original prompt = lh09 task text + inlined `orders_cn.csv` (4 rows) + `returns_cn.csv` (3 rows) + `opencode.jsonc`. 1010 chars.
- Registered PII tokens in this prompt: **8** (`CN_SSN × 2`, `CN_PHONE × 2`, `CN_PERSON × 3`, `CN_IDCARD × 1`).
- Redact endpoint: `POST http://127.0.0.1:18826/v1/file/redact/upload` with `auto_pii=true, use_ner=false, min_confidence=0.3, scan_free_text=true`. Both CSV files submitted separately.
- Cloud endpoint: `POST http://127.0.0.1:8900/v1/chat/completions` (the logging reverse-proxy forwarding to `api.minimaxi.com`), model `MiniMax-M3`, temperature 0.0, max_tokens 6000.

## 2. security_manager regex output

### orders_cn.csv → masked
```
columns_masked: ['order_id', 'phone', 'idcard', 'date']
order_id,customer,phone,idcard,amount,date
<ID_1>,张伟,<ID_5>,<ID_8>,128.5,<DATETIME_1>
<ID_2>,李娜,<ID_6>,<ID_9>,256.0,<DATETIME_2>
<ID_3>,王芳,<ID_5>,<ID_10>,89.9,<DATETIME_2>
<ID_4>,赵磊,<ID_7>,<ID_11>,512.0,<DATETIME_3>
```
→ `customer` column untouched (CN_PERSON blind spot). phone/idcard/order_id/date replaced.

### returns_cn.csv → masked
```
columns_masked: ['order_id']
return_id,order_id,reason
R-CN-1,<ID_1>,质量问题
R-CN-2,<ID_2>,七天无理由
R-CN-3,<ID_3>,商品损坏
```

### Net result on the request
8 PII tokens in original → **3 PII tokens in masked** (only the 3 names `张伟`, `李娜`, `王芳`).

## 3. Cloud response — BYPASS path

The model followed the prompt's "only retain last 4 digits" rule in the actual deliverable (emails + summary CSV), but it ALSO wrote a 脱敏核验 (masking verification) table that listed every original value alongside its masked form. So all 8 PII tokens still appear in the response, just in a meta-table.

```
…【脱敏核验】
| CN-1001 phone | 13800138001 | ****8001 |
| CN-1001 idcard | 110101199003078239 | ****8239 |
| CN-1002 phone | 13912345678 | ****5678 |
| CN-1002 idcard | 310115198507152146 | ****2146 |
…
```
→ 8 PII echoed.

## 4. Cloud response — END-TO-END path (PII module in path)

The model received placeholders like `<ID_1>`, `<ID_5>`, `<ID_8>`. It went into a 12K-character `<think>` loop trying to figure out what to do with them, then produced a coherent deliverable using placeholder-derived fake "last 4" values (`****0005`, `****0008` etc.). All real PII (phone, SSN, ID card) is absent because the model never saw the original values.

The names (`张伟`, `李娜`, `王芳`) were still in the request (the regex didn't mask the `customer` column), so the model used them in the email salutations:
```
尊敬的 张伟 先生/女士：
…
尊敬的 李娜 女士：
…
尊敬的 王芳 女士：
…
```
→ 3 PII echoed, all CN_PERSON.

## 5. Per-token tally

| PII token | type | in request (bypass) | in request (PII on) | in response (bypass) | in response (PII on) |
|---|---|---:|---:|---:|---:|
| 110101199003078239 | CN_SSN | 1 | 0 | 1 | 0 |
| 310115198507152146 | CN_SSN | 1 | 0 | 1 | 0 |
| 13800138001 | CN_PHONE | 1 | 0 | 1 | 0 |
| 13912345678 | CN_PHONE | 1 | 0 | 1 | 0 |
| 310101199208151234 | CN_IDCARD | 1 | 0 | 1 | 0 |
| 张伟 | CN_PERSON | 1 | 1 | 1 | 1 |
| 李娜 | CN_PERSON | 1 | 1 | 1 | 1 |
| 王芳 | CN_PERSON | 1 | 1 | 1 | 1 |
| **TOTAL** | | **8** | **3** | **8** | **3** |

## 6. What this tells us about the PII module's behavior

1. **Request-side value is real**: for lh09 the cloud genuinely never sees the 5 structured PII values (2 SSN, 2 phone, 1 ID-card). The `<ID_*>` placeholders are opaque to the cloud. That is a hard privacy guarantee, not a "model-chooses-not-to-echo" one.

2. **The bypass risk isn't the deliverable, it's the meta-table**: the model followed the "last 4 digits" rule for the actual emails, but it also wrote a "verification" table exposing the originals. Real users would send that table to the cloud too — that's the leak that the PII module prevents entirely.

3. **The Chinese-name blind spot is real and consistent**: the `customer` column isn't a PII column the regex recognizes. Across lh09 and lh11, **all 3 registered CN_PERSON names still reach the cloud**. The only path to fix this is the NER pipeline, which is currently broken in this SuperClaw build (`sanitize_ready: false`, AppLocker DLL-load block).

4. **Utility is preserved** (in this run): the PII-module-on response produced a usable deliverable — three refund emails and a summary CSV — using placeholder-derived `****NNNN` for "last 4 digits". The 12K-char `<think>` block is the only real cost; the final 1893-char deliverable is complete and structurally correct.

5. **False positives are still there**: `order_id` (`CN-1001` → `<ID_1>`) and `date` (`2026-07-21` → `<DATETIME_1>`) are over-masked. Order IDs are not PII in this context and the model loses the ability to refer to them in the deliverable as `CN-1001` — it has to use `<ID_1>`, which a human reading the email would not understand.

## 7. Files produced

- `logs/_lh09_e2e.py` — the test driver
- `logs/lh09_e2e_proxy.jsonl` — every cloud-bound request/response the proxy saw during this test
- `logs/lh09_masked.csv` — the literal masked `orders_cn.csv` (proves names survive)
- `logs/lh09_orig.csv` — the original `orders_cn.csv` (for comparison)
- `logs/lh09_e2e_report.md` — full per-call markdown report (with both model responses verbatim)
- `results/pii_module_real_test/LH09_REPORT.md` — this summary

## 8. Methodological note

This run restricts inlining to lh09's actual workspace (`orders_cn.csv`, `returns_cn.csv`, `opencode.jsonc`). The prior end-to-end test inlined all 5 CN workspace files because the runner does that for all 4 LH-CN tasks, which inflated the PII count. Here we report only what lh09 actually depends on.
