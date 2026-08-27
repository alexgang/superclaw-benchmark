"""Rerun all 116 OEM PinchBench cases under the fixed harness, auto arm, pw=0.85.

Scope and arms were selected by the user on 2026-08-27:
  - scope = all 116 (Recommended)
  - arms  = auto only, pw=0.85 (Recommended)

This is the post-audit rerun. It replaces the 84-row pb_top3_pw0.85_auto_v5.jsonl
(retracted; 0/84 gradeable) with a clean gradeable dataset covering every OEM
case, not just the three top categories.

The original v5 took ~110s/task on average for 84 tasks (~2.5h). With 116 tasks
and a slightly more conservative 240s timeout (the fixed harness does extra
workspace-reset + completeness grading work, more headroom is wise), the upper
bound is ~7.7h; expected wall-clock ~3.5h based on the same mean.

Prerequisites (verified 2026-08-27 09:49 local):
  - SuperClaw router healthy: auto / local-model=qwen3.5-4b / cloud-model=MiniMax-M3
  - DB perf_weight already 0.85 (lh_automation --perf-weight 0.85 re-asserts,
    so passing it explicitly is safe even if the GUI flipped it)

Output: logs/oem116_auto_pw085.jsonl  (one row per task, score None for the 14
LLM-judge-only cases that have no auto_checks_preview).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import score_of, summarize

ROOT = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark')
LOGS = ROOT / 'logs'
TASKS_FILE = ROOT / 'tasks' / 'tasks_pinchbench_oem.jsonl'

PY = r'C:\Users\Trekker-PTL\miniforge3\python.exe'
HARNESS = ROOT / 'harness' / 'lh_automation.py'

ARM = {'model': 'auto', 'label': 'oem_auto_pw0.85', 'pw': 0.85}
OUT = LOGS / f'oem116_auto_pw085.jsonl'

# --start-from N to resume a previously interrupted rerun. lh_automation opens
# --out in append mode, so resuming preserves earlier rows in-place.
import argparse
_argparser = argparse.ArgumentParser(add_help=False)
_argparser.add_argument('--start-from', type=int, default=0,
                        help='First task INDEX to run. Earlier rows already in '
                             'OUT are preserved (append). Default: 0 (start over).')
_args, _rest = _argparser.parse_known_args()
START_FROM = _args.start_from

# 14 tasks in the OEM suite have no auto_checks_preview (LLM-judge / hybrid).
# They will run, but score=None until an external Opus judge grades them.
tasks = [json.loads(line) for line in TASKS_FILE.read_text(encoding='utf-8').splitlines() if line.strip()]
indices = list(range(START_FROM, len(tasks)))

print(f'OEM PinchBench rerun — auto, pw=0.85')
print(f'  tasks file: {TASKS_FILE.name} ({len(tasks)} cases)')
print(f'  python:     {PY}')
print(f'  harness:    {HARNESS.name}')
print(f'  output:     {OUT.name}')
print(f'  arm-label:  {ARM["label"]}')
print(f'  timeout:    240s/task (v3 lh baseline)')
print(f'  estimated:  ~3.5h wall-clock (mean 110s/task; 116 tasks)')
print()

if OUT.exists():
    n_existing = sum(1 for line in OUT.read_text(encoding='utf-8').splitlines() if line.strip())
    print(f'NOTE: {OUT.name} already exists with {n_existing} rows.')
    if START_FROM == 0:
        print(f'  Refusing to start from scratch (would duplicate rows).')
        print(f'  Use --start-from {n_existing} to resume, or delete the file.')
        sys.exit(1)
    elif START_FROM < n_existing:
        print(f'  WARNING: --start-from {START_FROM} is below the {n_existing} rows')
        print(f'  already on disk. The first {n_existing - START_FROM} new rows will')
        print(f'  duplicate existing ones. Continuing anyway (append mode).')
    else:
        print(f'  Resuming from index {START_FROM} (append mode).')

cmd = [
    PY, str(HARNESS),
    '--perf-weight', str(ARM['pw']),
    '--model', ARM['model'],
    '--arm-label', ARM['label'],
    '--save-raw',
    '--timeout', '240',
    '--tasks', ','.join(str(i) for i in indices),
    '--out', str(OUT),
]
env = os.environ.copy()
env.pop('HTTP_PROXY', None)
env.pop('HTTPS_PROXY', None)
env['LH_TASKS_FILE'] = str(TASKS_FILE)

print(f'cmd: {" ".join(cmd[:6])} ... (truncated)')
print(f'env: LH_TASKS_FILE={TASKS_FILE.name}, HTTP(S)_PROXY unset')
print()
print(f'starting at {time.strftime("%Y-%m-%d %H:%M:%S")} ...')
t0 = time.time()
result = subprocess.run(cmd, env=env, cwd=str(ROOT))
elapsed = time.time() - t0
print(f'\nexit={result.returncode}, elapsed={elapsed:.1f}s ({elapsed/3600:.2f}h)')

# Summarize the new log
if OUT.exists():
    rows = [json.loads(l) for l in OUT.read_text(encoding='utf-8').splitlines() if l.strip()]
    print(f'\n=== {OUT.name}: {len(rows)} rows ===')
    if rows:
        print(summarize(rows, 'overall'))
        # Per-task accuracy for the auto-graded subset
        graded = [(r['task_id'], score_of(r)) for r in rows if score_of(r) is not None]
        ungraded = [r['task_id'] for r in rows if score_of(r) is None]
        if graded:
            n = len(graded)
            mean = sum(s for _, s in graded) / n
            print(f'\nauto-graded: {n} tasks, mean {mean:.3f}')
            for tid, s in graded[:10]:
                print(f'  {tid:45} {s:.3f}')
            if len(graded) > 10:
                print(f'  ... ({len(graded)-10} more)')
        print(f'\nungraded (LLM-judge or no checks): {len(ungraded)}')
        for tid in ungraded[:5]:
            print(f'  {tid}')
        if len(ungraded) > 5:
            print(f'  ... ({len(ungraded)-5} more)')