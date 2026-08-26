import json, os
from pathlib import Path

# Look at ALL files in the SuperClaw appdata that could influence routing
root = Path(os.environ['LOCALAPPDATA']) / 'SuperClaw'
for p in sorted(root.rglob('*')):
    if not p.is_file():
        continue
    sz = p.stat().st_size
    if sz > 100_000:
        continue
    name = p.name.lower()
    if any(k in name for k in ['routing','route','mode','provider','edge','openwork','setting','config.json','profile','router','model_id','alias']):
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
            data = json.loads(txt)
            short = json.dumps(data, ensure_ascii=False)[:500]
            print(f"{p.relative_to(root)}: {short}")
            print()
        except Exception:
            pass