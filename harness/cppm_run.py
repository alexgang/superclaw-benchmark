"""Run CPPM benchmark across 3 arms with raw output preservation."""
import json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark')
LOGS = ROOT / 'logs'
RAW_BASE = ROOT / 'results' / 'v4_raw'
CPPM_FILE = ROOT / 'tasks' / 'tasks_cppm.jsonl'

ARMS = [
    {'model': 'local-model', 'label': 'local', 'pw': 0.5},
    {'model': 'cloud-model', 'label': 'cloud', 'pw': 0.5},
    {'model': 'auto',        'label': 'auto',  'pw': 0.5},
]

# Verify CPPM file
assert CPPM_FILE.exists(), f'CPPM file not found: {CPPM_FILE}'
print(f'CPPM file: {CPPM_FILE}')

# Run each arm
for arm in ARMS:
    out_log = LOGS / f'cppm_pw{arm["pw"]}_{arm["label"]}.jsonl'
    print(f'\n=== ARM {arm["label"]}: --model {arm["model"]} ===')
    print(f'  output: {out_log}')
    cmd = [
        'python', str(ROOT / 'harness' / 'lh_automation.py'),
        '--perf-weight', str(arm['pw']),
        '--model', arm['model'],
        '--arm-label', arm['label'],
        '--save-raw',
        '--timeout', '180',
        '--out', str(out_log),
    ]
    env = os.environ.copy()
    env.pop('HTTP_PROXY', None)
    env.pop('HTTPS_PROXY', None)
    env['LH_TASKS_FILE'] = str(CPPM_FILE)
    print(f'  cmd: {" ".join(cmd)}')
    print(f'  tasks file: {CPPM_FILE}')
    t0 = time.time()
    result = subprocess.run(cmd, env=env, cwd=str(ROOT))
    elapsed = time.time() - t0
    print(f'  exit={result.returncode}, elapsed={elapsed:.1f}s')

print('\n=== CPPM 全部完成 ===')
for arm in ARMS:
    log = LOGS / f'cppm_pw{arm["pw"]}_{arm["label"]}.jsonl'
    if log.exists():
        with open(log, encoding='utf-8') as f:
            rows = [json.loads(l) for l in f if l.strip()]
        if rows:
            print(f'\n{arm["label"]}:')
            for r in rows:
                acc = r.get('accuracy', {}).get('score', 0) if isinstance(r.get('accuracy'), dict) else 0
                print(f'  {r["task_id"]:10} acc={acc:.2f} chat={r["chat_count"]:3} cloud={r["cloud_calls"]:2} sec={r["duration_s"]:5.1f}')
            if any(isinstance(r.get('accuracy'), dict) for r in rows):
                avg = sum(r.get('accuracy', {}).get('score', 0) for r in rows if isinstance(r.get('accuracy'), dict)) / sum(1 for r in rows if isinstance(r.get('accuracy'), dict))
                print(f'  avg: {avg:.2f}')
