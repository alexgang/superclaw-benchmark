"""Run PinchBench top-3 categories benchmark across 3 arms.
Top-3 categories: log_analysis, meeting_analysis, csv_analysis = 84 tasks.
3 arms = 252 runs. Estimated 25 hours."""
import json, os, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import score_of, summarize

ROOT = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark')
LOGS = ROOT / 'logs'
RAW_BASE = ROOT / 'results' / 'v4_raw'
PB_FILE = ROOT / 'tasks' / 'tasks_pinchbench.jsonl'

ARMS = [
    {'model': 'local-model', 'label': 'local', 'pw': 0.5},
    {'model': 'cloud-model', 'label': 'cloud', 'pw': 0.5},
    {'model': 'auto',        'label': 'auto',  'pw': 0.5},
]

TOP_CATS = {
    'pinchbench/log_analysis',
    'pinchbench/meeting_analysis',
    'pinchbench/csv_analysis',
}

# Filter tasks by category
tasks = []
with open(PB_FILE, encoding='utf-8') as f:
    for line in f:
        if line.strip():
            d = json.loads(line)
            if d.get('category') in TOP_CATS:
                tasks.append(d)

print(f'Loaded {len(tasks)} PinchBench tasks (top-3 categories)')
for cat in TOP_CATS:
    n = sum(1 for t in tasks if t.get('category') == cat)
    print(f'  {cat}: {n}')

# Save indices file so lh_automation knows which tasks to run
indices = list(range(len(tasks)))
print(f'Indices: 0..{len(tasks)-1}')

# Run each arm
for arm in ARMS:
    out_log = LOGS / f'pb_top3_pw{arm["pw"]}_{arm["label"]}.jsonl'
    print(f'\n=== ARM {arm["label"]}: --model {arm["model"]} ({len(tasks)} tasks × 120s = est. {len(tasks)*120/60:.0f} min) ===')
    print(f'  output: {out_log}')
    cmd = [
        'python', str(ROOT / 'harness' / 'lh_automation.py'),
        '--perf-weight', str(arm['pw']),
        '--model', arm['model'],
        '--arm-label', arm['label'],
        '--save-raw',
        '--timeout', '120',
        '--tasks', ','.join(str(i) for i in indices),
        '--out', str(out_log),
    ]
    env = os.environ.copy()
    env.pop('HTTP_PROXY', None)
    env.pop('HTTPS_PROXY', None)
    env['LH_TASKS_FILE'] = str(PB_FILE)
    print(f'  env: LH_TASKS_FILE={PB_FILE}')
    t0 = time.time()
    result = subprocess.run(cmd, env=env, cwd=str(ROOT))
    elapsed = time.time() - t0
    print(f'  exit={result.returncode}, elapsed={elapsed:.1f}s')

print('\n=== PinchBench top-3 完成 ===')
for arm in ARMS:
    log = LOGS / f'pb_top3_pw{arm["pw"]}_{arm["label"]}.jsonl'
    if log.exists():
        with open(log, encoding='utf-8') as f:
            rows = [json.loads(l) for l in f if l.strip()]
        if rows:
            print(f'\n{arm["label"]}: {len(rows)} tasks')
            for r in rows[:5]:
                s = score_of(r)
                print(f'  {r["task_id"]:35} acc=' + ('UNGRADED' if s is None else f'{s:.2f}'))
            if len(rows) > 5:
                print(f'  ... ({len(rows)-5} more)')
            print('  ' + summarize(rows, 'avg'))
