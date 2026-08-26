"""diag_auto.py — Diagnose what model=auto returns."""
import urllib.request, urllib.error, json, time

body = json.dumps({
    'model': 'auto',
    'messages': [{'role':'user','content':'Reply with exactly: OK_AUTO'}],
    'max_tokens': 32,
    'temperature': 0,
}).encode()
req = urllib.request.Request('http://127.0.0.1:18321/v1/chat/completions',
                              data=body,
                              headers={'Content-Type':'application/json'})
try:
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read())
    dt = time.time() - t0
    print(f"upstream model: {resp.get('model')}")
    print(f"ttft_total: {dt:.2f}s")
    print(f"answer: {resp['choices'][0]['message']['content']!r}")
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(f"body: {e.read().decode('utf-8', errors='replace')[:600]}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
