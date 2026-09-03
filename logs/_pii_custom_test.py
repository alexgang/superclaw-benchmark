import urllib.request, urllib.error, json
import sys
sys.path.insert(0, r'C:\Users\Trekker-PTL\superclaw_benchmark\harness')
from lh_automation import get_owt_token
token = get_owt_token()

reg = json.load(open(r'C:\Users\Trekker-PTL\superclaw_benchmark\tasks\pii_registry_cn.json', encoding='utf-8'))
pii_map = {p['id']: p for p in reg['pii']}

# Text redact with custom_terms: explicitly tell the module "treat these strings as PII"
hdr = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}

# Build a text with all 15 PII tokens inline
text = '客户张伟(110101199003078239)电话13800138001邮箱zhangwei@example.cn住北京市朝阳区建国路88号；'\
       '员工李娜(310115198507152146)13912345678，地址上海市浦东新区世纪大道100号；'\
       '王芳(310101199208151234)上海华联科技有限公司法人6222021234567890123密码Wx@2024cn#secure sk-cn-9f3a71bd42ee4c0e8be1770c9d2f5a6b。'

custom_terms = {p['id']: p['value'] for p in reg['pii']}

print('=== /v1/text/redact with custom_terms (15 PII tokens explicitly named) ===')
body = {
    'text': text,
    'session_id': 'custom-terms-test',
    'custom_terms': custom_terms,
    'use_ner': False,
}
try:
    req = urllib.request.Request('http://127.0.0.1:18826/v1/text/redact', data=json.dumps(body, ensure_ascii=False).encode('utf-8'), headers=hdr, method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read())
        print(f'  status={r.status}')
        print(f'  redacted: {j.get("redacted", "?")[:500]}')
        print(f'  replacements: {len(j.get("replacements", {}))}')
        for k, v in j.get('replacements', {}).items():
            print(f'    {k:30s} -> {v!r}')

        # Check which PII tokens survived
        survived = [pid for pid, p in pii_map.items() if p['value'] in j.get('redacted', '')]
        caught = [pid for pid, p in pii_map.items() if p['value'] not in j.get('redacted', '')]
        print()
        print(f'  SURVIVED in redacted text: {len(survived)}/{len(pii_map)}')
        for pid in survived:
            p = pii_map[pid]
            print(f'    LEAK: {pid:25s} {p["type"]:12s} {p["value"]!r}')
        print(f'  CAUGHT: {len(caught)}/{len(pii_map)}')
        for pid in caught:
            p = pii_map[pid]
            print(f'    OK  : {pid:25s} {p["type"]:12s}')
except urllib.error.HTTPError as e:
    print(f'  HTTPError {e.code} {e.read().decode()[:500]}')
