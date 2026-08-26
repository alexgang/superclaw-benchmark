import re
from pathlib import Path

# Vendor config files (in install dir)
install_root = Path(r'C:\Program Files\Intel\SuperClaw')
print("scanning", install_root)
hits = 0
for p in sorted(install_root.rglob('*')):
    if not p.is_file():
        continue
    if p.suffix.lower() not in {'.json','.jsonc','.toml','.yaml','.yml'}:
        continue
    try:
        txt = p.read_text(encoding='utf-8', errors='ignore')
        for kw in ['local_provider','active_provider','localProvider','routingMode','routing_mode']:
            if kw in txt:
                print(f"\n=== {p.relative_to(install_root)} (kw={kw}) ===")
                for m in re.finditer(re.escape(kw) + r'[^,}\n]*', txt):
                    start = max(0, m.start() - 30)
                    end = min(len(txt), m.end() + 80)
                    print(f"  ...{txt[start:end]}...")
                hits += 1
                break
    except Exception:
        pass
print(f"\ntotal hits: {hits}")