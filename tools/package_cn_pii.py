#!/usr/bin/env python3
"""Package CN PII experiment into raw_deliverables/lh_cn_pwX.YY/.

Usage:  python tools/package_cn_pii.py 0.20
        python tools/package_cn_pii.py 0.85
"""
import argparse
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark')
LOGS = ROOT / 'logs'

ap = argparse.ArgumentParser()
ap.add_argument('pw')
args = ap.parse_args()
pw = float(args.pw)
pw_str = f'pw{pw:.2f}'

SRC = ROOT / 'results' / f'lh_cn_{pw_str}'
OUT = ROOT / 'raw_deliverables' / f'lh_cn_{pw_str}'

if not SRC.exists():
    sys.exit(f'no results dir: {SRC}')

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for f in SRC.iterdir():
    shutil.copy2(f, OUT / f.name)

(OUT / 'logs').mkdir(exist_ok=True)
shutil.copy2(LOGS / f'lh_cn_{pw_str}.jsonl', OUT / 'logs' / f'lh_cn_{pw_str}.jsonl')
shutil.copy2(LOGS / f'cloud_cn_{pw_str}.jsonl', OUT / 'logs' / f'cloud_cn_{pw_str}.jsonl')
if (LOGS / f'lh_cn_{pw_str}_prebugfix.jsonl').exists():
    shutil.copy2(LOGS / f'lh_cn_{pw_str}_prebugfix.jsonl', OUT / 'logs' / f'lh_cn_{pw_str}_prebugfix.jsonl')
if (LOGS / f'cloud_cn_{pw_str}_prebugfix.jsonl').exists():
    shutil.copy2(LOGS / f'cloud_cn_{pw_str}_prebugfix.jsonl', OUT / 'logs' / f'cloud_cn_{pw_str}_prebugfix.jsonl')

summary = {
    'config': f'hybrid_cn_{pw_str}',
    'perf_weight': pw,
    'date': datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
    'method': 'synthetic routing via perf_weight + task.routing_expectation; cloud=127.0.0.1:8900 proxy; local=127.0.0.1:18103 qwen3.5-4b',
    'caveats': [
        'first run (prebugfix) at pw=0.20 had a bug where Chinese tasks did not inline workspace files into the cloud prompt — fixed in subsequent run; prebugfix backups in logs/ for reference',
        'routing decision is synthesized, not actual SuperClaw routing',
        'proxy double-records each request (call_id appears twice for one POST) — privacy counts are per unique PII token',
        'per_task leak attribution is naive: a task is "leaked" if any of its must_stay_local PII appears anywhere in cloud-bound bodies',
    ],
    'privacy': json.load(open(SRC / 'privacy.json', encoding='utf-8')),
    'routing': json.load(open(SRC / 'routing.json', encoding='utf-8')),
    'metrics': json.load(open(SRC / 'metrics.json', encoding='utf-8')),
}
(OUT / 'SUMMARY.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

print(f'Packaged to {OUT}')
print(f'  privacy leak_rate: {summary["privacy"][f"hybrid_cn_{pw_str}"]["leak_rate"]}')
print(f'  cloud tasks: {summary["routing"][f"hybrid_cn_{pw_str}"]["tasks_touching_cloud"]}/4')

