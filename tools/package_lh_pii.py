#!/usr/bin/env python3
"""Package LH pw0.20 PII experiment into the repo."""
import hashlib
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark')
SRC = ROOT / 'results' / 'lh_pw0.20'
OUT = ROOT / 'raw_deliverables' / 'lh_pw0.20'
LOGS = ROOT / 'logs'

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)

# Copy results
for f in SRC.iterdir():
    shutil.copy2(f, OUT / f.name)

# Copy inputs (the answers jsonl is large; the proxy log is large too)
(OUT / 'logs').mkdir(exist_ok=True)
shutil.copy2(LOGS / 'lh_pw0.20.jsonl', OUT / 'logs' / 'lh_pw0.20.jsonl')
shutil.copy2(LOGS / 'cloud_pw0.20.jsonl', OUT / 'logs' / 'cloud_pw0.20.jsonl')

# Save a summary
summary = {
    'config': 'hybrid_pw0.20',
    'perf_weight': 0.20,
    'date': '2026-08-31',
    'method': 'synthetic routing via perf_weight + task.routing_expectation; cloud=127.0.0.1:8900 proxy; local=127.0.0.1:18103 qwen3.5-4b',
    'caveats': [
        'routing decision is synthesized, not actual SuperClaw routing (cloud URL hardcoded in llmrouter_manager.exe, no admin path to redirect)',
        'proxy double-records each request (call_id appears twice for one POST) — privacy counts are per unique PII token, not per request',
        'per_task leak attribution is naive: a task is "leaked" if any of its must_stay_local PII appears anywhere in cloud-bound bodies, even if that PII came from a different task that legitimately routed to cloud',
    ],
    'privacy': json.load(open(SRC / 'privacy.json', encoding='utf-8')),
    'routing': json.load(open(SRC / 'routing.json', encoding='utf-8')),
    'metrics': json.load(open(SRC / 'metrics.json', encoding='utf-8')),
}
(OUT / 'SUMMARY.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

print(f'Packaged to {OUT}')
print(f'  Files: {list(f.name for f in OUT.iterdir())}')
print(f'  privacy leak_rate: {summary["privacy"]["hybrid_pw0.20"]["leak_rate"]}')
print(f'  cloud tasks: {summary["routing"]["hybrid_pw0.20"]["tasks_touching_cloud"]}/8')
