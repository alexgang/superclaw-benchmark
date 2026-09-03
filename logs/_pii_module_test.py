#!/usr/bin/env python3
"""Test the REAL PII module (security_manager :18826) on all 4 CN LH task workspace files.

For each task, submit its workspace files to /v1/file/redact/upload and check
which of the 15 planted Chinese PII tokens are caught.
"""
import json
import sys
import urllib.request
import urllib.error
import mimetypes
import os
from pathlib import Path

sys.path.insert(0, r'C:\Users\Trekker-PTL\superclaw_benchmark\harness')
from lh_automation import get_owt_token

ROOT = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark')
TOKEN = get_owt_token()
WORKSPACE_CN = ROOT / 'tasks' / 'workspace_lh_cn'

reg = json.load(open(ROOT / 'tasks' / 'pii_registry_cn.json', encoding='utf-8'))
pii_map = {p['id']: p for p in reg['pii']}

TASK_FILES = {
    'lh09': ['orders_cn.csv', 'returns_cn.csv'],
    'lh10': ['employees_cn.csv'],
    'lh11': ['vendor_invoices_cn.csv'],
    'lh12': ['audit_cn_01.log'],
}


def build_multipart(file_path, fields, file_field_name='file'):
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    lines = []
    for k, v in fields.items():
        lines.append(f'--{boundary}\r\n')
        lines.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n')
        lines.append(f'{v}\r\n')
    import os
    fname = os.path.basename(file_path)
    ftype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    with open(file_path, 'rb') as f:
        data = f.read()
    lines.append(f'--{boundary}\r\n')
    lines.append(f'Content-Disposition: form-data; name="{file_field_name}"; filename="{fname}"\r\n')
    lines.append(f'Content-Type: {ftype}\r\n\r\n')
    lines_bytes = ''.join(lines).encode('utf-8') + data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Authorization': f'Bearer {TOKEN}',
    }
    return lines_bytes, headers


def redact_file(file_path, use_ner=False):
    """Submit a file to the real PII module's redact endpoint.

    Returns: dict with status, columns_masked, masked_csv, etc.
    """
    fields = {
        'auto_pii': 'true',
        'min_confidence': '0.3',
        'use_ner': 'true' if use_ner else 'false',
        'return_mode': 'inline',
        'registry_return_mode': 'inline',
        'scan_free_text': 'true',
    }
    body, hdr = build_multipart(file_path, fields)
    req = urllib.request.Request(
        'http://127.0.0.1:18826/v1/file/redact/upload',
        data=body, headers=hdr, method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return {'status': r.status, **(json.loads(r.read()))}
    except urllib.error.HTTPError as e:
        try:
            return {'status': e.code, 'error': json.loads(e.read())}
        except Exception:
            return {'status': e.code, 'error': str(e)[:300]}


print('='*78)
print('REAL PII MODULE TEST — security_manager :18826')
print('='*78)
print()

summary = []
for task_id, files in TASK_FILES.items():
    print(f'\n=== {task_id} ===')
    for fname in files:
        path = WORKSPACE_CN / fname
        if not path.exists():
            print(f'  {fname}: MISSING')
            continue
        # Test with NER (will likely fail due to ONNX missing) AND without NER (regex only)
        for label, use_ner in [('no_ner', False), ('with_ner', True)]:
            r = redact_file(str(path), use_ner=use_ner)
            status = r.get('status')
            if status != 200:
                print(f'  {fname} ({label}): {status} {str(r.get("error", r))[:150]}')
                continue
            masked = r.get('masked_csv') or r.get('masked_file_path') or ''
            # Check which PII tokens survived
            survived = []
            caught = []
            for pid, p in pii_map.items():
                v = p['value']
                if v in masked:
                    survived.append((pid, v, p['type']))
                else:
                    caught.append((pid, p['type']))
            print(f'  {fname} ({label}): masked {r.get("rows_masked", 0)}/{r.get("rows_extracted", 0)} rows, '
                  f'survived {len(survived)}/{len(pii_map)} PII tokens')
            for pid, v, t in survived:
                print(f'    LEAK: {pid:25s} {t:12s} {v!r}')
            for pid, t in caught:
                print(f'    OK  : {pid:25s} {t:12s}')
            if label == 'no_ner':
                summary.append({
                    'task': task_id,
                    'file': fname,
                    'caught': [c[0] for c in caught],
                    'survived': [s[0] for s in survived],
                    'rows_masked': r.get('rows_masked', 0),
                    'rows_extracted': r.get('rows_extracted', 0),
                    'substitutions': r.get('substitutions', 0),
                    'columns_masked': r.get('columns_masked', []),
                })

# Final summary
print()
print('='*78)
print('SUMMARY (no_ner mode, the only working path)')
print('='*78)
total_caught = 0
total_survived = 0
for s in summary:
    total_caught += len(s['caught'])
    total_survived += len(s['survived'])
    print(f"  {s['task']:6s} {s['file']:25s} caught={len(s['caught'])}/15 survived={len(s['survived'])}/15")
print()
print(f'TOTAL: caught {total_caught} PII tokens, survived {total_survived} (out of {15*len(summary)} task-tokens tested)')

# Save detailed results
out = {
    'config': 'real_pii_module_test',
    'date': '2026-09-03',
    'method': 'POST /v1/file/redact/upload with use_ner=false (NER path is broken due to missing ONNX models)',
    'pii_module_state': {
        'redact_ready': True,
        'sanitize_ready': False,
        'sanitize_degraded_reason': 'ONNX model dirs missing (multilang-pii-ner-onnx-int8, finance_embedding_onnx-int8)',
    },
    'per_file': summary,
    'totals': {
        'caught': total_caught,
        'survived': total_survived,
        'planted': 15 * len(summary),
    },
}
out_path = r'C:\Users\Trekker-PTL\superclaw_benchmark\results\pii_module_real_test\results.json'
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f'\nResults saved to {out_path}')
