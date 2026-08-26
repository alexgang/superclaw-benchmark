#!/usr/bin/env python3
"""
Run driver for the SuperClaw hybrid-architecture benchmark.

For each task in tasks/tasks.jsonl, POST a chat completion and capture:
  - client_ttft_s        (first SSE chunk, or non-streaming total)
  - client_total_s       (end-to-end)
  - output_tokens        (from response.usage.completion_tokens)
  - model                (response.model -> which slot actually served it)
  - answer               (the assistant text, with <think>...</think> stripped)

Writes one JSONL per config to logs/answers_<config>.jsonl.

Two configs:
  - hybrid      : POST to 127.0.0.1:18321/v1/chat/completions, model=auto
                  (SuperClaw's auto router decides local vs cloud)
  - cloud_only  : POST to 127.0.0.1:8900/v1/chat/completions, model=MiniMax-M3
                  (our logging proxy -> MiniMax-M3; full cloud payload captured)

Streaming is on for accurate TTFT. The proxy in proxy/minimax_logging_proxy.py
also captures server-side TTFT + usage on the cloud side; that's matched via
call_id in its JSONL. For cloud_only, call_id is implicit (single in-flight).
For hybrid, we don't see the proxy's per-call trace because SuperClaw's cloud
slot isn't redirected to the proxy (encrypted provider .bin, no API).
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

WORKSPACE_DIR = Path(__file__).resolve().parent.parent / "tasks" / "workspace"
DEFAULT_MAX_TOKENS = 1024   # enough for ~750-word reasoning + answer
DEFAULT_TIMEOUT_S = 300.0

PROFILES = {
    # v3 mode: go through SuperClaw's actual router (127.0.0.1:18321) with
    # model=auto. The LatencyRouter is consulted per request and routes
    # between local (qwen3.5-4b) and cloud (MiniMax-M3) based on
    # config.perf_weight (set via DB before each run).
    "hybrid": {
        "base_url": "http://127.0.0.1:18321/v1",
        "model": "auto",
    },
    "cloud_only": {
        "base_url": "http://127.0.0.1:8900/v1",
        "model": "MiniMax-M3",
    },
}

# v3 routing attribution: response.model -> route
# - qwen3.5-4b (or alias-local) => served by local llama-server
# - MiniMax-M3 (or anything else) => served by cloud (MiniMax)
_LOCAL_MODELS = {"qwen3.5-4b", "qwen3.5-0.8b"}
_CLOUD_MODELS = {"MiniMax-M3"}


def _derive_route(model_id: str) -> str:
    """Map the upstream model name back to local/cloud."""
    if not model_id:
        return "?"
    if model_id in _LOCAL_MODELS:
        return "local"
    if model_id in _CLOUD_MODELS:
        return "cloud"
    return f"other:{model_id}"


# --------------------------------------------------------------------------- #
# Reasoning strip (MiniMax-M3 emits <think>...</think>; we grade the answer)
# --------------------------------------------------------------------------- #
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_think(text: str) -> str:
    return _THINK_RE.sub("", text or "").strip()


# --------------------------------------------------------------------------- #
# Inline workspace context for tool-using tasks
# --------------------------------------------------------------------------- #
# Map: filename (substring in workspace) -> inlined content. The run driver
# includes these as a "system" message so both local and cloud see the same
# context. Without this, tool-use tasks would fail on local (no file access)
# but succeed on cloud (model can be told the content).
WORKSPACE_CONTEXTS = {
    "contacts.csv": "=== contacts.csv ===\nname,role,phone,email,note\n"
                    "Dana Whitfield,primary-care patient,+1-415-555-0197,dana.whitfield@northlake-clinic.example,annual checkup due\n"
                    "Miriam Okafor,HR contact,+1-206-555-0143,m.okafor@brightpath-hr.example,\n"
                    "Liang Zhao,engineering manager,,,Q3 hiring freeze\n",
    "patient_intake.txt": "=== patient_intake.txt ===\nPatient: Dana Whitfield\n"
                          "DOB: 1986-03-24\nMRN: MRN-7742199\nSSN: 412-55-8921\n"
                          "Address: 1487 Cedar Hollow Rd, Bellevue WA 98004\n"
                          "Chief complaint: tachycardia on exertion, 2 weeks.\nReferral: cardiology.\n",
    "deploy_config.env": "=== deploy_config.env ===\n"
                         "STRIPE_API_KEY=sk-live-9f3a71bd42ee4c0e8be1770c9d2f5a6b\n"
                         "DATABASE_URL=postgres://app:Hn7$mVq2!raptor@db.internal:5432/prod\n"
                         "PAYMENT_PROCESSOR_CC=4539-8821-0067-3345\n",
    "payroll_note.md": "=== payroll_note.md ===\n# Payroll adjustment\n\n"
                       "Subject: Miriam Okafor (m.okafor@brightpath-hr.example)\n"
                       "SSN-on-file: 203-88-4417\nBank IBAN: GB29 NWBK 6016 1331 9268 19\n"
                       "Decision: +4% cost-of-living adjustment, back-dated to Q1.\n",
    "sales_region.csv": "=== sales_region.csv ===\nregion,Q1,Q2,Q3,Q4\nnorth,100,120,150,180\n"
                       "south,90,110,140,160\neast,80,85,95,110\nwest,150,170,260,195\n",
    "meeting_notes.md": "=== meeting_notes.md ===\n# 2026-08-04 sync\n\n"
                        "Open: time complexity of dedup() in algo.py?\nClosed: CI green.\n",
    "algo.py": "=== algo.py ===\ndef dedup(xs):\n"
               "    out = []\n    for x in xs:\n        if x not in out:\n            out.append(x)\n    return out\n",
}


def workspace_context_for(prompt: str) -> str:
    """Pick which workspace files to inline based on prompt keywords."""
    blocks = []
    for fname, content in WORKSPACE_CONTEXTS.items():
        # Match the file's stem (e.g. 'contacts') appearing in the prompt
        stem = fname.split(".")[0]
        if stem in prompt.lower() or fname in prompt.lower():
            blocks.append(content)
    return "\n".join(blocks)


# --------------------------------------------------------------------------- #
# One task
# --------------------------------------------------------------------------- #
def run_one(client: httpx.Client, task: dict, profile: dict, max_tokens: int,
            timeout_s: float, verbose: bool = False) -> dict:
    """Stream one chat completion; capture metrics + answer."""
    user_prompt = task["prompt"]
    ctx = workspace_context_for(user_prompt)

    # The system message carries the workspace context; user message is the prompt.
    messages = []
    if ctx:
        messages.append({"role": "system", "content": ctx})
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": profile["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
        # Disable reasoning for cleaner measurement (the benchmark cares about
        # answer quality, not chain-of-thought length).
        # NOTE: M3 emits <think> regardless; we strip it in post-processing.
    }

    t0 = time.perf_counter()
    ttft_s = None
    chunks = 0
    collected_text = []
    usage = None
    model_id = None
    resp = None

    try:
        resp = client.post(
            f"{profile['base_url']}/chat/completions",
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        # Iterate SSE
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith("data:"):
                payload_str = line[len("data:"):].strip()
                if payload_str == "[DONE]":
                    break
                chunks += 1
                if ttft_s is None:
                    ttft_s = time.perf_counter() - t0
                try:
                    obj = json.loads(payload_str)
                    if obj.get("model") and not model_id:
                        model_id = obj["model"]
                    choices = obj.get("choices") or []
                    if choices:
                        delta = choices[0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            collected_text.append(delta["content"])
                    if obj.get("usage"):
                        usage = obj["usage"]
                except json.JSONDecodeError:
                    pass
    except httpx.HTTPError as e:
        return {
            "task_id": task["id"],
            "config": profile["name"],
            "answer": "",
            "client_ttft_s": None,
            "client_total_s": round(time.perf_counter() - t0, 4),
            "output_tokens": 0,
            "model": None,
            "sse_chunks": chunks,
            "error": f"{type(e).__name__}: {e}",
        }
    finally:
        if resp is not None:
            resp.close()

    total_s = time.perf_counter() - t0
    raw_answer = "".join(collected_text)
    answer = strip_think(raw_answer)
    completion_tokens = (usage or {}).get("completion_tokens", 0)
    # For MiniMax-M3, completion_tokens includes reasoning_tokens; that's fine
    # for the TTFT/TPS numbers but judge.py gets the full stripped answer.

    if verbose:
        print(f"  [{task['id']}] {model_id or profile['model']}  "
              f"ttft={ttft_s:.3f}s total={total_s:.3f}s "
              f"tokens={completion_tokens} chunks={chunks} "
              f"answer_len={len(answer)}")

    return {
        "task_id": task["id"],
        "config": profile["name"],
        "answer": answer,
        "client_ttft_s": round(ttft_s, 4) if ttft_s is not None else None,
        "client_total_s": round(total_s, 4),
        "output_tokens": completion_tokens,
        "model": model_id or profile["model"],
        "sse_chunks": chunks,
        "route_trace": [model_id or profile["model"]],
        # v3: derive route from upstream model id
        "route": _derive_route(model_id or profile["model"]),
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, choices=list(PROFILES),
                    help="hybrid or cloud_only")
    ap.add_argument("--tasks", default=str(Path(__file__).resolve().parent.parent /
                                            "tasks" / "tasks.jsonl"))
    ap.add_argument("--out", default=None,
                    help="Output JSONL; default logs/answers_<config>.jsonl")
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    ap.add_argument("--warmup", action="store_true",
                    help="Run a small warmup task before the suite (excluded from output)")
    ap.add_argument("--limit", type=int, default=0,
                    help="If >0, only run the first N tasks")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--no-backup", action="store_true",
                    help="Skip the post-run GitHub backup hook (default: backup enabled)")
    ap.add_argument("--pw", type=float, default=None,
                    help="perf_weight used in this round; passed through to the backup hook for the round id")
    args = ap.parse_args()

    profile = dict(PROFILES[args.config])
    profile["name"] = args.config

    out_path = Path(args.out) if args.out else (
        Path(__file__).resolve().parent.parent / "logs" / f"answers_{args.config}.jsonl"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tasks = [json.loads(line) for line in Path(args.tasks).read_text(
        encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        tasks = tasks[:args.limit]
    print(f"[run_driver] config={args.config}  tasks={len(tasks)}  out={out_path}")

    # Warmup
    if args.warmup:
        warmup_task = {"id": "warmup", "prompt": "Reply with the word warm.", "rubric": ""}
        with httpx.Client() as c:
            r = run_one(c, warmup_task, profile, args.max_tokens, args.timeout)
        print(f"[warmup] model={r.get('model')} ttft={r.get('client_ttft_s')}s "
              f"total={r.get('client_total_s')}s answer={r.get('answer')[:60]!r}")

    # Real runs
    results = []
    with httpx.Client() as client:
        for i, t in enumerate(tasks, 1):
            t0 = time.perf_counter()
            r = run_one(client, t, profile, args.max_tokens, args.timeout,
                        verbose=args.verbose)
            results.append(r)
            dt = time.perf_counter() - t0
            print(f"[{i:02d}/{len(tasks)}] {t['id']} ({t.get('category','?')})  "
                  f"-> {r.get('model')}  ttft={r.get('client_ttft_s')}s  "
                  f"total={r.get('client_total_s')}s  tokens={r.get('output_tokens')}  "
                  f"({dt:.1f}s wall)")

    with out_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Summary
    ttfts = [r["client_ttft_s"] for r in results if r.get("client_ttft_s") is not None]
    totals = [r["client_total_s"] for r in results if r.get("client_total_s") is not None]
    toks = [r.get("output_tokens", 0) for r in results]
    models = {}
    routes = {}
    for r in results:
        m = r.get("model") or "unknown"
        models[m] = models.get(m, 0) + 1
        rt = r.get("route") or "?"
        routes[rt] = routes.get(rt, 0) + 1
    print()
    print(f"[done] wrote {len(results)} rows to {out_path}")
    print(f"  successes: {len(totals)}/{len(results)}")
    if ttfts:
        print(f"  TTFT mean={statistics.mean(ttfts):.3f}s  median={statistics.median(ttfts):.3f}s")
    if totals:
        print(f"  total mean={statistics.mean(totals):.3f}s")
    if toks:
        print(f"  output_tokens total={sum(toks)}  mean={statistics.mean(toks):.1f}")
    print(f"  routes: {routes}")
    print(f"  models: {models}")

    # ---- Auto-backup baselines to GitHub (tools/backup.py) ----
    # Runs after the summary so a backup failure doesn't lose this round's
    # answers_<config>.jsonl. Disable with --no-backup.
    if not args.no_backup:
        backup_cmd = [
            sys.executable,
            str(Path(__file__).resolve().parent.parent / "tools" / "backup.py"),
            "--config", args.config,
        ]
        if args.pw is not None:
            backup_cmd += ["--pw", str(args.pw)]
        print(f"\n[run_driver] auto-backup: {' '.join(backup_cmd)}")
        try:
            res = subprocess.run(backup_cmd,
                                 cwd=str(Path(__file__).resolve().parent.parent),
                                 capture_output=True, text=True)
            if res.returncode != 0:
                print(f"[run_driver] backup hook FAILED (rc={res.returncode}); "
                      f"answers are still on disk.", file=sys.stderr)
                tail = (res.stderr or res.stdout or "").strip().splitlines()
                if tail:
                    print("[run_driver] backup.py last output:", file=sys.stderr)
                    for line in tail[-15:]:
                        print(f"    {line}", file=sys.stderr)
        except Exception as e:
            print(f"[run_driver] backup hook raised: {e!r}", file=sys.stderr)


if __name__ == "__main__":
    main()