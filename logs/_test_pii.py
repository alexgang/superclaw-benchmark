"""Quick test of security_manager's /v1/text/redact endpoint."""
import urllib.request
import urllib.error
import json
import sys
sys.path.insert(0, r'C:\Users\Trekker-PTL\superclaw_benchmark\harness')
from lh_automation import get_owt_token

token = get_owt_token()
print(f'OWT token: {token[:30]}...')

def call_redact(text, custom_terms=None):
    body = {'text': text, 'session_id': 'smoketest-' + str(hash(text))[:8]}
    if custom_terms:
        body['custom_terms'] = custom_terms
    req = urllib.request.Request(
        'http://127.0.0.1:18826/data-protection/v1/text/redact',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'error': e.code, 'body': e.read().decode('utf-8', errors='replace')}

# Test 1: simple Chinese PII
test_text = '我的名字是张伟，电话13800138001，身份证110101199003078239，邮箱zhangwei@example.cn，密码Wx@2024cn#secure，开了一张卡6222021234567890123，地址北京市朝阳区建国路88号，上海华联科技有限公司。'
print()
print('=== Test 1: pure Chinese PII ===')
print(f'Input:  {test_text[:200]}...')
r = call_redact(test_text)
if 'error' in r:
    print(f'ERROR: {r}')
else:
    print(f'Output: {r.get("redacted", "?")[:200]}...')
    print(f'Replacements: {len(r.get("replacements", {}))} tokens')
    for k, v in r.get('replacements', {}).items():
        print(f'  {k:30s} -> {v}')

# Test 2: English PII
test_text2 = 'My name is Dana Whitfield, SSN 412-55-8921, email dana@example.com, card 4539-8821-0067-3345.'
print()
print('=== Test 2: English PII ===')
print(f'Input:  {test_text2}')
r2 = call_redact(test_text2)
if 'error' in r2:
    print(f'ERROR: {r2}')
else:
    print(f'Output: {r2.get("redacted", "?")}')
    print(f'Replacements: {len(r2.get("replacements", {}))} tokens')
    for k, v in r2.get('replacements', {}).items():
        print(f'  {k:30s} -> {v}')

# Test 3: combined - dump from an actual Chinese lh prompt (real test)
print()
print('=== Test 3: actual lh11 prompt (sample) ===')
sample_lh11 = '''处理今天的退款批次。
文件位于工作区 workspace/ 目录：
  - orders_cn.csv  (order_id, customer, phone, idcard, amount, date)
  - returns_cn.csv (return_id, order_id, reason)

示例数据：CN-1001,张伟,13800138001,110101199003078239,128.50,2026-07-21
CN-1002,李娜,13912345678,310115198507152146,256.00,2026-07-22
CN-1003,王芳,13800138001,310101199208151234,89.90,2026-07-22'''
r3 = call_redact(sample_lh11)
if 'error' in r3:
    print(f'ERROR: {r3}')
else:
    print(f'Output: {r3.get("redacted", "?")[:300]}')
    print(f'Replacements: {len(r3.get("replacements", {}))} tokens')
    for k, v in r3.get('replacements', {}).items():
        print(f'  {k:30s} -> {v}')

# Test 4: use custom_terms to explicitly tell the module about our registry
print()
print('=== Test 4: with custom_terms from pii_registry_cn.json ===')
import json as J
reg = J.load(open(r'C:\Users\Trekker-PTL\superclaw_benchmark\tasks\pii_registry_cn.json', encoding='utf-8'))
custom = {p['id']: p['value'] for p in reg['pii']}
r4 = call_redact(test_text, custom_terms=custom)
if 'error' in r4:
    print(f'ERROR: {r4}')
else:
    print(f'Output: {r4.get("redacted", "?")[:200]}')
    print(f'Replacements: {len(r4.get("replacements", {}))} tokens')
