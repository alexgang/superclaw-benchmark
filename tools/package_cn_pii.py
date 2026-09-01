#!/usr/bin/env python3
"""Package CN PII experiment into raw_deliverables/lh_cn_pw0.20/."""
import hashlib
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark')
LOGS = ROOT / 'logs'
SRC = ROOT / 'results' / 'lh_cn_pw0.20'
OUT = ROOT / 'raw_deliverables' / 'lh_cn_pw0.20'

if not SRC.exists():
    sys.exit(f'no results dir: {SRC}')

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for f in SRC.iterdir():
    shutil.copy2(f, OUT / f.name)

(OUT / 'logs').mkdir(exist_ok=True)
shutil.copy2(LOGS / 'lh_cn_pw0.20.jsonl', OUT / 'logs' / 'lh_cn_pw0.20.jsonl')
shutil.copy2(LOGS / 'cloud_cn_pw0.20.jsonl', OUT / 'logs' / 'cloud_cn_pw0.20.jsonl')
if (LOGS / 'lh_cn_pw0.20_prebugfix.jsonl').exists():
    shutil.copy2(LOGS / 'lh_cn_pw0.20_prebugfix.jsonl', OUT / 'logs' / 'lh_cn_pw0.20_prebugfix.jsonl')
if (LOGS / 'cloud_cn_pw0.20_prebugfix.jsonl').exists():
    shutil.copy2(LOGS / 'cloud_cn_pw0.20_prebugfix.jsonl', OUT / 'logs' / 'cloud_cn_pw0.20_prebugfix.jsonl')

summary = {
    'config': 'hybrid_cn_pw0.20',
    'perf_weight': 0.20,
    'date': datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
    'method': 'synthetic routing via perf_weight + task.routing_expectation; cloud=127.0.0.1:8900 proxy; local=127.0.0.1:18103 qwen3.5-4b',
    'caveats': [
        'first run (prebugfix) had a bug where Chinese tasks did not inline workspace files into the cloud prompt — fixed in commit; this package is the v2 result',
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
print(f'  privacy leak_rate: {summary["privacy"]["hybrid_cn_pw0.20"]["leak_rate"]}')
print(f'  cloud tasks: {summary["routing"]["hybrid_cn_pw0.20"]["tasks_touching_cloud"]}/4')
