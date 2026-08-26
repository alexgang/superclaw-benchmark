"""cold_start_superclaw.py
Cold-restart SuperClaw stack and poll /v1/models until ready.
"""
import os, time, subprocess, sys
from pathlib import Path

EXE = r'C:\Program Files\Intel\SuperClaw\SuperClaw.exe'
LOG_DIR = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark\logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'superclaw_v3.4_post_reset.log'

# Launch with cleared proxy (B's HTTP(S)_PROXY is broken/unresolvable)
env = {**os.environ, 'HTTP_PROXY': '', 'HTTPS_PROXY': ''}
f = open(LOG_FILE, 'w')
proc = subprocess.Popen([EXE], env=env, stdout=f, stderr=subprocess.STDOUT,
                        creationflags=0x00000008 | 0x00000200)  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
print(f"Launched SuperClaw.exe PID={proc.pid}, log -> {LOG_FILE}")

# Poll /v1/models
import urllib.request, urllib.error, json
ready = False
for i in range(40):
    time.sleep(2)
    try:
        with urllib.request.urlopen('http://127.0.0.1:18321/v1/models', timeout=2) as r:
            data = json.loads(r.read())
            print(f"[{i+1}] /v1/models OK: {[m['id'] for m in data.get('data',[])]}")
            ready = True
            break
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        if i % 5 == 0:
            print(f"[{i+1}] waiting... ({type(e).__name__})")

if not ready:
    print(f"❌ router did not respond after 80s. See {LOG_FILE}")
    sys.exit(1)
print("✅ router up")
