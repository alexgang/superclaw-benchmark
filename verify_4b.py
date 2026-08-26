"""verify_4b.py — Verify SuperClaw is correctly configured for 4B."""
import urllib.request, json, time, sqlite3, os
from pathlib import Path

DB = Path(os.path.expandvars(r'%LOCALAPPDATA%\SuperClaw\llmrouter_manager\llmrouter_manager.db'))

def show_models():
    with urllib.request.urlopen('http://127.0.0.1:18321/v1/models', timeout=5) as r:
        data = json.loads(r.read())
    print("=== /v1/models ===")
    for m in data.get('data', []):
        print(f"  {m['id']:20} {m.get('description','')[:90]}")
    return data

def db_state():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    print("\n=== DB state ===")
    cur.execute("SELECT value FROM config WHERE key='active_chat_model_id'")
    print(f"  active_chat_model_id = {cur.fetchone()[0]}")
    cur.execute("SELECT primary_bundle FROM bundle_lifecycle WHERE singleton=1")
    pb = json.loads(cur.fetchone()[0])
    print(f"  primary_bundle.bundle_id    = {pb['bundle_id']}")
    print(f"  primary_bundle.chat_model   = {pb['chat_model_id']}")
    print(f"  primary_bundle.state        = {pb['state']}")
    print(f"  primary_bundle.revision     = {pb['bundle_revision']}")
    cur.execute("SELECT asset_id, size_bytes FROM model_verifications WHERE asset_id='qwen3.5-4b'")
    row = cur.fetchone()
    print(f"  model_verifications(4B)     = {row}")
    con.close()

def test_local():
    print("\n=== test model=local-model (should route to 4B) ===")
    body = json.dumps({
        'model': 'local-model',
        'messages': [{'role':'user','content':'Reply with exactly: OK_4B_LOCAL'}],
        'max_tokens': 32,
        'temperature': 0,
    }).encode()
    req = urllib.request.Request('http://127.0.0.1:18321/v1/chat/completions',
                                  data=body,
                                  headers={'Content-Type':'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read())
    dt = time.time() - t0
    print(f"  upstream model: {resp.get('model')}")
    print(f"  ttft_total: {dt:.2f}s")
    print(f"  answer: {resp['choices'][0]['message']['content']!r}")
    return resp

def test_auto():
    print("\n=== test model=auto ===")
    body = json.dumps({
        'model': 'auto',
        'messages': [{'role':'user','content':'Reply with exactly: OK_AUTO'}],
        'max_tokens': 32,
        'temperature': 0,
    }).encode()
    req = urllib.request.Request('http://127.0.0.1:18321/v1/chat/completions',
                                  data=body,
                                  headers={'Content-Type':'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read())
    dt = time.time() - t0
    print(f"  upstream model: {resp.get('model')}")
    print(f"  ttft_total: {dt:.2f}s")
    print(f"  answer: {resp['choices'][0]['message']['content']!r}")
    return resp

if __name__ == '__main__':
    show_models()
    db_state()
    test_local()
    test_auto()
