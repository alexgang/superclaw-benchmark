import urllib.request, urllib.error, json
import sys
sys.path.insert(0, r'C:\Users\Trekker-PTL\superclaw_benchmark\harness')
from lh_automation import get_owt_token
token = get_owt_token()
hdr = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
body = {'text': '张伟 13800138001', 'session_id': 'probe'}
paths = [
    'http://127.0.0.1:18826/v1/text/redact',
    'http://127.0.0.1:18826/data-protection/v1/text/redact',
    'http://127.0.0.1:61976/data-protection/v1/text/redact',
    'http://127.0.0.1:61976/v1/text/redact',
    'http://127.0.0.1:61976/data-protection/v1/text/categories',
    'http://127.0.0.1:61976/v1/text/categories',
    'http://127.0.0.1:18826/v1/text/categories',
    'http://127.0.0.1:18826/v1/health',
    'http://127.0.0.1:18826/health',
    'http://127.0.0.1:18826/data-protection/health',
    'http://127.0.0.1:18826/data-protection/openapi.json',
    'http://127.0.0.1:18826/data-protection/',
]
for p in paths:
    try:
        req = urllib.request.Request(p, data=json.dumps(body).encode('utf-8'), headers=hdr, method='POST')
        with urllib.request.urlopen(req, timeout=5) as r:
            j = json.loads(r.read())
            print(f'{r.status} POST {p}')
            print(f'    {str(j)[:200]}')
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read())
        except Exception:
            j = e.read()[:100]
        print(f'{e.code} POST {p}  -> {str(j)[:200]}')
    except Exception as e:
        print(f'ERR  POST {p}  -> {e}')
