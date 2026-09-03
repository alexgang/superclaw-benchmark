import urllib.request, urllib.error, json, mimetypes
import sys
sys.path.insert(0, r'C:\Users\Trekker-PTL\superclaw_benchmark\harness')
from lh_automation import get_owt_token
token = get_owt_token()

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
        'Authorization': f'Bearer {token}',
    }
    return lines_bytes, headers

# Test: lh11 orders_cn.csv via /v1/file/redact/upload
src = r'C:\Users\Trekker-PTL\superclaw_benchmark\tasks\workspace_lh_cn\orders_cn.csv'
fields = {
    'auto_pii': 'true',
    'min_confidence': '0.3',
    'use_ner': 'false',
    'return_mode': 'inline',
    'registry_return_mode': 'inline',
    'scan_free_text': 'true',
    'suspected_sensitive_columns': 'customer,phone,idcard',
}
body, hdr = build_multipart(src, fields)
print('=== /v1/file/redact/upload on orders_cn.csv (auto_pii=True) ===')
try:
    req = urllib.request.Request('http://127.0.0.1:18826/v1/file/redact/upload', data=body, headers=hdr, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read())
        print(f'  status={r.status}')
        print(f'  columns_masked: {j.get("columns_masked", [])}')
        print(f'  rows_extracted: {j.get("rows_extracted", 0)}, rows_masked: {j.get("rows_masked", 0)}')
        print(f'  extra_pii_found: {j.get("extra_pii_found", [])}')
        print(f'  substitutions: {j.get("substitutions", 0)}')
        masked = j.get('masked_csv') or j.get('masked_file_path')
        if masked:
            print(f'  masked_csv (first 800 chars):')
            print(f'    {masked[:800]!r}')
        print(f'  recommended_system_prompt: {j.get("recommended_system_prompt", "?")[:200]}')
except urllib.error.HTTPError as e:
    print(f'  HTTPError {e.code} {e.read().decode()[:500]}')
