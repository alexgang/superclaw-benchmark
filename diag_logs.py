import re
from pathlib import Path
# Check latest llmrouter_manager log for local_provider values
log_dir = Path(r'C:\Users\Trekker-PTL\AppData\Local\SuperClaw\llmrouter_manager')
logs = sorted(log_dir.glob('llmrouter_manager-*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
print("logs:", [p.name for p in logs[:5]])
if logs:
    latest = logs[0]
    txt = latest.read_text(encoding='utf-8', errors='ignore')
    # find lines mentioning local_provider or active_provider
    for kw in ['local_provider', 'active_provider', 'routing_mode', 'profile-state', 'primary_bundle']:
        print(f"\n=== {kw} (latest {latest.name}) ===")
        for line in txt.splitlines():
            if kw in line:
                print(line[:300])
                if 'local_provider' in line.lower() and ('set' in line.lower() or 'update' in line.lower() or 'config' in line.lower()):
                    print('  ^^')
        if sum(1 for l in txt.splitlines() if kw in l) > 30:
            print(f'  ... ({sum(1 for l in txt.splitlines() if kw in l)} total)')