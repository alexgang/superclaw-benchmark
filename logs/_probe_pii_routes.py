import urllib.request, urllib.error, json
import sys
sys.path.insert(0, r'C:\Users\Trekker-PTL\superclaw_benchmark\harness')
from lh_automation import get_owt_token
token = get_owt_token()
hdr = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}

# 1. /v1/text/redact with use_ner=false (just regex path)
print('=== /v1/text/redact (no NER) ===')
body = {'text': 'My name is 张伟, SSN 412-55-8921, phone 13800138001, ID 110101199003078239, card 4539-8821-0067-3345, email zhangwei@example.cn, password Wx@2024cn#secure, address 北京市朝阳区建国路88号, company 上海华联科技有限公司.', 'session_id': 't1', 'use_ner': False}
try:
    req = urllib.request.Request('http://127.0.0.1:18826/v1/text/redact', data=json.dumps(body, ensure_ascii=False).encode('utf-8'), headers=hdr, method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read())
        print(f'  status={r.status}')
        print(f'  redacted: {j.get("redacted", "?")[:300]}')
        print(f'  replacements: {len(j.get("replacements", {}))}')
        for k, v in j.get('replacements', {}).items():
            print(f'    {k:30s} -> {v}')
except urllib.error.HTTPError as e:
    print(f'  HTTPError {e.code} {e.read().decode()[:300]}')

# 2. /v1/file/redact with the actual lh11 CSV
print()
print('=== /v1/file/redact on lh11 orders_cn.csv ===')
import shutil
src = r'C:\Users\Trekker-PTL\superclaw_benchmark\tasks\workspace_lh_cn\orders_cn.csv'
# Need a path readable by the service
body = {
    'source': src,
    'auto_pii': True,
    'min_confidence': 0.3,
    'use_ner': False,
    'return_mode': 'inline',
    'registry_return_mode': 'inline',
    'scan_free_text': True,
}
try:
    req = urllib.request.Request('http://127.0.0.1:18826/v1/file/redact', data=json.dumps(body).encode('utf-8'), headers=hdr, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read())
        print(f'  status={r.status}')
        print(f'  columns_masked: {j.get("columns_masked", [])}')
        print(f'  rows_extracted: {j.get("rows_extracted", 0)}, rows_masked: {j.get("rows_masked", 0)}')
        print(f'  extra_pii_found: {j.get("extra_pii_found", [])}')
        print(f'  substitutions: {j.get("substitutions", 0)}')
        masked = j.get('masked_csv') or j.get('masked_file_path')
        if masked:
            print(f'  masked (first 500 chars):')
            print(f'    {masked[:500]!r}')
        print(f'  recommended_system_prompt: {j.get("recommended_system_prompt", "?")[:200]}')
        print(f'  registry: {j.get("registry", {})}')
except urllib.error.HTTPError as e:
    print(f'  HTTPError {e.code} {e.read().decode()[:500]}')

# 3. /v1/file/detect_and_redact
print()
print('=== /v1/file/detect_and_redact ===')
body2 = dict(body)
body2['suspected_sensitive_columns'] = ['customer', 'phone', 'idcard']
try:
    req = urllib.request.Request('http://127.0.0.1:18826/v1/file/detect_and_redact', data=json.dumps(body2).encode('utf-8'), headers=hdr, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read())
        print(f'  status={r.status}')
        print(f'  columns_masked: {j.get("columns_masked", [])}')
        print(f'  suggestions: {j.get("suggestions", [])[:3]}')
        print(f'  detected_sensitive_columns: {j.get("detected_sensitive_columns", {})}')
        print(f'  substitutions: {j.get("substitutions", 0)}')
except urllib.error.HTTPError as e:
    print(f'  HTTPError {e.code} {e.read().decode()[:500]}')

# 4. /v1/text/redact with use_ner=True (will fail with 503)
print()
print('=== /v1/text/redact with use_ner=True (expect 503) ===')
body3 = dict(body)
body3['use_ner'] = True
try:
    req = urllib.request.Request('http://127.0.0.1:18826/v1/text/redact', data=json.dumps(body3, ensure_ascii=False).encode('utf-8'), headers=hdr, method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read())
        print(f'  status={r.status} {str(j)[:200]}')
except urllib.error.HTTPError as e:
    print(f'  HTTPError {e.code} {e.read().decode()[:300]}')
