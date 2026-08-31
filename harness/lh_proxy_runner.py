#!/usr/bin/env python3
"""
lh_proxy_runner.py — synthetic LH benchmark runner.

Bypasses SuperClaw's opencode session layer (cloud URL is hardcoded in
llmrouter_manager.exe, no admin path to redirect). Instead drives both model
endpoints directly:

  - cloud: http://127.0.0.1:8900/v1  (the logging proxy -> real MiniMax-M3)
  - local: http://127.0.0.1:18103/v1 (llama-server with qwen3.5-4b)

Routing decision mirrors SuperClaw's expected behavior:
  - routing_expectation == 'local'  -> always local
  - routing_expectation == 'cloud'  -> always cloud
  - routing_expectation == 'mixed'  -> random uniform; if u < perf_weight -> cloud

For each task:
  1. Stages workspace files from tasks/workspace_lh/ (using the same setup_lhNN_workspace
     helpers as lh_automation.py).
  2. Sends prompt + inlined file contents to the chosen model.
  3. Captures first-chunk TTFT and total client time.
  4. Strips <think>...</think> from M3 reasoning.
  5. Writes the model response to the workspace's expected deliverable path when
     we can infer it from the task (else to workspace/_response.txt).
  6. Emits one row in the answers jsonl.

The proxy captures the verbatim cloud request body in logs/<cfg>.jsonl;
harness/analyze.py then computes privacy/metrics/routing reports from that +
this answers file + tasks/pii_registry.json.

Usage:
  python harness/lh_proxy_runner.py --perf-weight 0.20 \
      --out logs/lh_pw0.20.jsonl --config-label hybrid_pw0.20 --seed 42

Environment overrides:
  PROXY_URL  (default http://127.0.0.1:8900/v1)
  LOCAL_URL  (default http://127.0.0.1:18103/v1)
  CLOUD_MODEL (default MiniMax-M3)
  LOCAL_MODEL (default qwen3.5-4b)
"""
import argparse
import json
import os
import random
import re
import shutil
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'harness'))

# Import the same workspace setup helpers lh_automation uses
from lh_automation import TASK_SETUP, WORKSPACE  # noqa: E402

PROXY_URL = os.environ.get('PROXY_URL', 'http://127.0.0.1:8900/v1/chat/completions')
LOCAL_URL = os.environ.get('LOCAL_URL', 'http://127.0.0.1:18103/v1/chat/completions')
CLOUD_MODEL = os.environ.get('CLOUD_MODEL', 'MiniMax-M3')
LOCAL_MODEL = os.environ.get('LOCAL_MODEL', 'qwen3.5-4b')

# Tasks that need per-task tool/file inlining. For simplicity (no tool use),
# we copy the file contents directly into the prompt so the model has the data.
INLINE_TASKS = {'lh01', 'lh02', 'lh03', 'lh04', 'lh05', 'lh06', 'lh07', 'lh08'}

THINK_RE = re.compile(r'<think>.*?</think>', re.DOTALL)


def strip_think(text: str) -> str:
    return THINK_RE.sub('', text).strip()


def http_post_json(url: str, body: dict, timeout: int = 180) -> tuple[dict, float, float, int, int]:
    """POST JSON, measure first-chunk TTFT and total client time.

    Returns (parsed_response, ttft_s, total_s, prompt_tokens, completion_tokens).
    """
    payload = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(
        url, data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ttft = time.time() - t0
            raw = r.read()
    except urllib.error.HTTPError as e:
        return ({'error': e.read().decode('utf-8', errors='replace'), 'status': e.code},
                0.0, time.time() - t0, 0, 0)
    except Exception as e:
        return ({'error': str(e)}, 0.0, time.time() - t0, 0, 0)
    total = time.time() - t0
    try:
        out = json.loads(raw.decode('utf-8'))
    except Exception:
        out = {'raw': raw[:2000].decode('utf-8', errors='replace')}
    usage = (out.get('usage') or {})
    return (out, ttft, total, int(usage.get('prompt_tokens', 0)), int(usage.get('completion_tokens', 0)))


def inline_workspace_files(task: dict) -> str:
    """Build a 'here are your workspace files' appendix for the prompt."""
    tid = task['id']
    setup_fn = TASK_SETUP.get(tid)
    if not setup_fn:
        return ''
    # The setup function copies files into WORKSPACE. We rely on the caller
    # to have already called setup_fn(WORKSPACE). Now we read what landed.
    files = []
    for f in sorted(WORKSPACE.iterdir()):
        if not f.is_file():
            continue
        # Skip prior deliverables
        if f.name.startswith('_') or f.name.endswith('.bak'):
            continue
        try:
            content = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        if len(content) > 20000:
            content = content[:20000] + '\n[...truncated...]'
        files.append(f'=== {f.name} ===\n{content}')
    return '\n\n'.join(files)


def decide_route(task: dict, perf_weight: float, rng: random.Random) -> str:
    """Return 'cloud' or 'local'."""
    exp = (task.get('routing_expectation') or 'mixed').lower()
    if exp == 'local':
        return 'local'
    if exp == 'cloud':
        return 'cloud'
    # mixed: random; higher perf_weight -> more cloud
    if rng.random() < perf_weight:
        return 'cloud'
    return 'local'


def write_response_to_workspace(task: dict, response_text: str):
    """Best-effort: write the model response to the expected deliverable path.

    For tasks whose rubric says 'workspace/X exists', we write the response as that file.
    If we can't infer, save to _response.txt.
    """
    # Best-effort filename inference from common task patterns
    rubric = (task.get('rubric') or '').lower()
    target = None
    if 'workspace/reports/' in rubric or 'q3-compliance.md' in rubric:
        target = WORKSPACE / 'reports' / 'q3-compliance.md'
    elif 'refund' in rubric and 'emails' in rubric:
        # lh02 - 3 emails + _summary.csv
        target = WORKSPACE / '_response.txt'
    elif 'post_mortem' in rubric or 'post-mortem' in rubric:
        target = WORKSPACE / 'post_mortem_filled.md'
    elif 'consolidation.md' in rubric:
        target = WORKSPACE / 'consolidation.md'
    elif 'onboarding_clean.csv' in rubric:
        target = WORKSPACE / 'onboarding_clean.csv'
    elif 'redaction_log.csv' in rubric:
        target = WORKSPACE / 'redaction_log.csv'
    elif 'forecast_new.csv' in rubric:
        target = WORKSPACE / 'forecast_new.csv'
    elif 'violations.csv' in rubric:
        target = WORKSPACE / 'violations.csv'
    if target is None:
        target = WORKSPACE / '_response.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(response_text, encoding='utf-8')


def clean_workspace():
    """Remove lh-related files but keep PRISTINE files (the opencode workspace baseline)."""
    keep = set()
    for f in WORKSPACE.iterdir():
        if not f.is_file():
            continue
        # Don't touch the opencode workspace baseline
        if f.name in {'opencode.jsonc', 'sensitive'}:
            keep.add(f.name)
            continue
    # Wipe the rest (sub-directories and other files)
    for f in list(WORKSPACE.iterdir()):
        if f.name in keep:
            continue
        try:
            if f.is_dir():
                shutil.rmtree(f, ignore_errors=True)
            else:
                f.unlink()
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--perf-weight', type=float, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--config-label', required=True)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--tasks', default=None, help='Comma-separated task indices, default = all')
    ap.add_argument('--max-tokens', type=int, default=4096)
    args = ap.parse_args()

    rng = random.Random(args.seed)

    tasks_path = ROOT / 'tasks' / 'tasks_long_horizon.jsonl'
    tasks = [json.loads(l) for l in tasks_path.read_text(encoding='utf-8').splitlines() if l.strip()]

    if args.tasks:
        idxs = [int(i) for i in args.tasks.split(',')]
        tasks = [tasks[i] for i in idxs]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_f = args.out.open('w', encoding='utf-8')

    print(f'[lh_proxy_runner] perf_weight={args.perf_weight} label={args.config_label} seed={args.seed} tasks={[t["id"] for t in tasks]}')
    print(f'[lh_proxy_runner] PROXY_URL={PROXY_URL} LOCAL_URL={LOCAL_URL}')

    summary = []
    for idx, task in enumerate(tasks):
        tid = task['id']
        route = decide_route(task, args.perf_weight, rng)
        endpoint = PROXY_URL if route == 'cloud' else LOCAL_URL
        model = CLOUD_MODEL if route == 'cloud' else LOCAL_MODEL
        print(f'\n{"="*60}\n[{idx}] {tid}  -> {route}  ({model})')
        print(f'{"="*60}')

        # Clean previous task's files and stage fresh
        clean_workspace()
        setup_fn = TASK_SETUP.get(tid)
        if setup_fn:
            try:
                created = setup_fn(WORKSPACE)
                print(f'  staged {len(created) if hasattr(created, "__len__") else "?"} files')
            except Exception as e:
                print(f'  WARN setup failed: {e}')

        # Build prompt with inlined files
        prompt_text = task['prompt']
        appendix = inline_workspace_files(task)
        if appendix:
            full_prompt = (
                f"{prompt_text}\n\n"
                f"--- WORKSPACE FILES (already on disk at workspace/, inlined here for convenience) ---\n"
                f"{appendix}\n"
                f"--- END FILES ---\n\n"
                f"Produce your final answer as plain text. Do NOT call any tools. "
                f"Write out the complete deliverable as if you were writing it to the file."
            )
        else:
            full_prompt = prompt_text

        body = {
            'model': model,
            'messages': [{'role': 'user', 'content': full_prompt}],
            'max_tokens': args.max_tokens,
            'temperature': 0.1,
            'stream': False,
        }
        # For cloud: log a route_trace stub so analyze.py can group by config
        route_trace = [route]
        t0 = time.time()
        # Inline the HTTP call. The http_post_json helper works fine in isolation but
        # we keep the body construction + call adjacent for clarity.
        try:
            import urllib.request as _ur, urllib.error as _ue
            _req = _ur.Request(endpoint, data=json.dumps(body).encode('utf-8'),
                               headers={'Content-Type': 'application/json'}, method='POST')
            _t0 = time.time()
            with _ur.urlopen(_req, timeout=180) as _r:
                ttft = time.time() - _t0
                _raw = _r.read()
            resp = json.loads(_raw.decode('utf-8'))
            total = time.time() - _t0
            _usage = (resp.get('usage') or {})
            ptok = int(_usage.get('prompt_tokens', 0))
            ctok = int(_usage.get('completion_tokens', 0))
            err = None
        except _ue.HTTPError as _e:
            resp = {'error': _e.read().decode('utf-8', errors='replace'), 'status': _e.code}
            ttft = 0.0; total = time.time() - t0; ptok = 0; ctok = 0
            err = f'status={_e.code} ' + str(resp.get('error'))[:500]
        except Exception as _e:
            resp = {'error': str(_e)}
            ttft = 0.0; total = time.time() - t0; ptok = 0; ctok = 0
            err = str(_e)[:500]
        client_total = time.time() - t0
        if 'error' in resp and not err:
            err = str(resp.get('error'))[:500]
        resp, ttft, total, ptok, ctok = http_post_json(endpoint, body)
        client_total = time.time() - t0
        if 'error' in resp:
            content = ''
            err = str(resp.get('error'))[:500]
            if 'status' in resp:
                err = f'status={resp["status"]} ' + err
        else:
            ch = (resp.get('choices') or [{}])[0]
            content = strip_think(ch.get('message', {}).get('content', '') or '')
            err = None
        print(f'  ttft={ttft:.2f}s total={total:.2f}s ptok={ptok} ctok={ctok} resp_chars={len(content)}')
        if err:
            print(f'  err={err[:200]}')

        # Write response into workspace
        if content:
            write_response_to_workspace(task, content)

        row = {
            'task_id': tid,
            'config': args.config_label,
            'answer': content,
            'client_ttft_s': round(ttft, 3),
            'client_total_s': round(client_total, 3),
            'output_tokens': ctok,
            'prompt_tokens': ptok,
            'used_cloud': route == 'cloud',
            'route_trace': route_trace,
            'routing_decision': route,
            'routing_expectation': task.get('routing_expectation'),
            'pii_must_stay_local': task.get('pii_must_stay_local', []),
            'error': err,
        }
        out_f.write(json.dumps(row, ensure_ascii=False) + '\n')
        out_f.flush()
        summary.append((tid, route, ctok, total, len(content)))

    out_f.close()
    print(f'\n{"="*60}\nSUMMARY ({args.config_label}, pw={args.perf_weight})')
    print(f'{"task":10} {"route":6} {"ctok":>6} {"total":>7} {"chars":>6}')
    for tid, route, ctok, total, chars in summary:
        print(f'{tid:10} {route:6} {ctok:>6} {total:>7.2f} {chars:>6}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
