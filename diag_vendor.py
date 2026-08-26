import re
from pathlib import Path

# Vendor config files (in install dir)
install_root = Path(r'C:\Program Files\Intel\SuperClaw')
for p in sorted(install_root.rglob('*.json')):
    try:
        txt = p.read_text(encoding='utf-8', errors='ignore')
        if 'local_provider' in txt or 'local-provider' in txt or 'active_provider' in txt:
            print(f"=== {p.relative_to(install_root)} ===")
            # Find the relevant sections
            for m in re.finditer(r'(local[_-]?provider|active[_-]?provider)[^,}\n]*', txt, re.I):
                start = max(0, m.start() - 50)
                end = min(len(txt), m.end() + 100)
                snippet = txt[start:end].replace('\n', ' ')
                print(f"  ...{snippet}...")
            print()
    except Exception as e:
        pass

# Also any *.jsonc, *.toml
for ext in ['*.jsonc', '*.toml']:
    for p in sorted(install_root.rglob(ext)):
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if 'local_provider' in txt or 'local-provider' in txt:
                print(f"=== {p.relative_to(install_root)} ===")
                print(txt[:2000])
                print()
        except Exception:
            pass