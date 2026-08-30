#!/usr/bin/env python3
"""Drill into the peak burst on 2005-06-11 03:03:xx."""
import re
from datetime import datetime
from collections import Counter

LINE_RE = re.compile(
    r'^\[(?P<dow>\w{3})\s+(?P<mon>\w{3})\s+(?P<day>\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<year>\d{4})\]\s+\[(?P<sev>[^\]]+)\]\s+(?P<msg>.*)$'
)
MONTHS = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

errors = []
with open('/workspace/apache_error.log') as f:
    for raw in f:
        raw = raw.rstrip('\n')
        m = LINE_RE.match(raw)
        if not m: continue
        dt = datetime(int(m['year']), MONTHS[m['mon']], int(m['day']),
                      *(int(x) for x in m['time'].split(':')))
        if m['sev'] == 'error':
            errors.append((dt, m['msg']))

errors.sort()
# Find peak window via sliding: for each i, j is max index with dt <= 11s after errors[i]
peak = (0, 0, 0)  # count, i, j
for i in range(len(errors)):
    j = i
    while j+1 < len(errors) and (errors[j+1][0] - errors[i][0]).total_seconds() <= 11:
        j += 1
    cnt = j - i + 1
    if cnt > peak[0]:
        peak = (cnt, i, j)

cnt, i, j = peak
start, end = errors[i][0], errors[j][0]
print(f"Peak burst: {start} -> {end}, duration={int((end-start).total_seconds())}s, count={cnt}")
print()

# First/last 10 lines
print("First 10 lines in peak burst:")
for k in range(i, min(i+10, j+1)):
    print(f"  {errors[k][0]}  {errors[k][1][:140]}")

print("\nLast 10 lines in peak burst:")
for k in range(max(i, j-9), j+1):
    print(f"  {errors[k][0]}  {errors[k][1][:140]}")

# Per-second histogram
from collections import defaultdict
per_sec = defaultdict(int)
for k in range(i, j+1):
    per_sec[errors[k][0].strftime('%H:%M:%S')] += 1
print("\nPer-second histogram in peak window:")
for s in sorted(per_sec):
    print(f"  {s}: {per_sec[s]} errors")

# Message breakdown
msgs = Counter(errors[k][1] for k in range(i, j+1))
print("\nMessage breakdown in peak burst:")
for m, c in msgs.most_common(20):
    print(f"  [{c:>4}] {m[:160]}")

# Distinct client IPs in peak burst
client_re = re.compile(r'\[client ([^\]]+)\]')
clients = Counter()
for k in range(i, j+1):
    m = client_re.search(errors[k][1])
    if m:
        clients[m.group(1)] += 1
print(f"\nDistinct clients in peak burst: {len(clients)}")
for ip, c in clients.most_common(15):
    print(f"  {ip}: {c}")

# Non-client errors (server-level)
print("\nNon-client (server-level) errors in peak burst:")
nonclient = [errors[k] for k in range(i, j+1) if '[client' not in errors[k][1]]
for dt, msg in nonclient[:30]:
    print(f"  {dt}  {msg[:140]}")
print(f"Total non-client: {len(nonclient)}")
