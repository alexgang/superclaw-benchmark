import json, os
from pathlib import Path

# Tauri / OpenWork state locations the GUI might read
candidates = [
    Path(os.environ['LOCALAPPDATA']) / 'SuperClaw',
    Path(os.environ['APPDATA']) / 'SuperClaw',
    Path(os.environ['LOCALAPPDATA']) / 'com.intel.superclaw',
    Path(os.environ['APPDATA']) / 'com.intel.superclaw',
    Path(os.environ['LOCALAPPDATA']) / 'openwork',
    Path(os.environ['APPDATA']) / 'openwork',
]

for root in candidates:
    if not root.exists():
        continue
    print(f"\n=== {root} ===")
    for p in root.rglob('*.json'):
        try:
            sz = p.stat().st_size
            if sz > 200_000:
                continue
            data = json.loads(p.read_text(encoding='utf-8', errors='ignore'))
            txt = json.dumps(data)[:600]
            if any(k in txt.lower() for k in ['local', 'auto', 'provider', 'routing', 'edge', 'llamacpp', 'model']):
                print(f"  {p.relative_to(root)}: {txt}")
        except Exception:
            pass

# Also check the SuperClaw install dir for OpenWork config
for cand in [Path(r'C:\Program Files\Intel\SuperClaw\openwork'),
             Path(r'C:\Program Files\Intel\SuperClaw\config')]:
    if cand.exists():
        print(f"\n=== {cand} ===")
        for p in cand.rglob('*'):
            if p.is_file() and p.suffix in {'.json','.jsonc','.toml'}:
                print(f"  {p}")