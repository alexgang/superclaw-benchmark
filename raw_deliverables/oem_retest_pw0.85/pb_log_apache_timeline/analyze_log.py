#!/usr/bin/env python3
"""Analyze Apache error log: daily error counts, notable events, and peak burst."""

import re
from datetime import datetime
from collections import Counter, defaultdict

LOG_PATH = "/workspace/apache_error.log"
OUTPUT_PATH = "/workspace/error_timeline.json"

# Pattern: [Day Mon DD HH:MM:SS YYYY] [severity] message
LINE_RE = re.compile(
    r'^\[(?P<dow>\w{3})\s+(?P<mon>\w{3})\s+(?P<day>\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<year>\d{4})\]\s+\[(?P<sev>[^\]]+)\]\s+(?P<msg>.*)$'
)

MONTHS = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

entries = []
parse_errors = 0
with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
    for ln, raw in enumerate(f, 1):
        raw = raw.rstrip('\n')
        if not raw.strip():
            continue
        m = LINE_RE.match(raw)
        if not m:
            parse_errors += 1
            continue
        dt = datetime(int(m['year']), MONTHS[m['mon']], int(m['day']),
                      *(int(x) for x in m['time'].split(':')))
        entries.append({
            'dt': dt,
            'sev': m['sev'],
            'msg': m['msg'],
            'dow': m['dow'],
            'raw': raw,
        })

print(f"Parsed entries: {len(entries)}")
print(f"Parse errors:   {parse_errors}")

# Severity breakdown
sev_counts = Counter(e['sev'] for e in entries)
print(f"Severity counts: {dict(sev_counts)}")

# Per-day error counts (severity exactly "[error]")
DOW_FULL = {'Mon':'Monday','Tue':'Tuesday','Wed':'Wednesday','Thu':'Thursday',
            'Fri':'Friday','Sat':'Saturday','Sun':'Sunday'}

per_day = defaultdict(list)
for e in entries:
    per_day[e['dt'].date()].append(e)

print("\n=== DAILY BREAKDOWN ===")
print(f"{'Date':<12} {'Dow':<10} {'Errors':<7} {'Total':<7} First-Last")
for d in sorted(per_day.keys()):
    day_entries = per_day[d]
    errs = [e for e in day_entries if e['sev'] == 'error']
    first = day_entries[0]['dt']
    last  = day_entries[-1]['dt']
    print(f"{d}  {DOW_FULL[day_entries[0]['dow']]:<10} {len(errs):<7} {len(day_entries):<7} {first.time()}-{last.time()}")

# Notable events per day
print("\n=== NOTABLE EVENTS ===")
for d in sorted(per_day.keys()):
    day_entries = per_day[d]
    msgs = [e['msg'] for e in day_entries]
    print(f"\n--- {d} ({DOW_FULL[day_entries[0]['dow']]}) ---")
    # Server start/stop
    start_lines = [m for m in msgs if 'resuming normal operations' in m or 'configured -- resuming' in m]
    stop_lines  = [m for m in msgs if 'caught SIGTERM' in m or 'shutting down' in m or 'stopping' in m.lower()[:30]]
    if start_lines:
        print(f"  Server start: {start_lines[0]}")
    if stop_lines:
        print(f"  Server stop:  {stop_lines[0]}")
    # Top repeated messages
    msg_counts = Counter(msgs)
    top = msg_counts.most_common(10)
    print("  Top messages:")
    for m, c in top:
        if c >= 2:
            print(f"    [{c:>4}] {m[:120]}")

# Peak burst detection: sliding window over [error] timestamps
print("\n=== PEAK BURST DETECTION ===")
error_entries = sorted([e for e in entries if e['sev'] == 'error'], key=lambda e: e['dt'])
print(f"Total [error] entries: {len(error_entries)}")

# Compute timestamp gaps between consecutive errors
gaps = []
for i in range(1, len(error_entries)):
    dt = (error_entries[i]['dt'] - error_entries[i-1]['dt']).total_seconds()
    gaps.append((dt, i-1, i))
print(f"Largest 10 gaps (seconds): {sorted(gaps, reverse=True)[:10]}")

# Strategy: for each possible window size W in seconds, find the window that
# contains the MOST errors. We want the smallest-duration window that has
# the highest density AND high absolute count.
# Implementation: sweep through sorted errors; for each starting error, find
# the largest index such that timestamp diff <= W. Track (count, duration)
# for each W. Then among all windows found, pick the one with best
# count-per-duration density, breaking ties by largest count, then smallest duration.

best_by_W = {}
for W in [1, 5, 10, 30, 60, 120, 300, 600]:
    best_count = 0
    best_range = None
    j = 0
    for i in range(len(error_entries)):
        while j < len(error_entries) and (error_entries[j]['dt'] - error_entries[i]['dt']).total_seconds() <= W:
            j += 1
        count = j - i  # entries from i to j-1 inclusive
        if count > best_count:
            best_count = count
            best_range = (i, j-1)
    if best_range:
        start_dt = error_entries[best_range[0]]['dt']
        end_dt   = error_entries[best_range[1]]['dt']
        dur = (end_dt - start_dt).total_seconds()
        best_by_W[W] = (best_count, dur, start_dt, end_dt, best_range)
        print(f"  Window W={W}s: max errors in window = {best_count}, span = {dur}s ({start_dt} -> {end_dt})")

# Also: find densest sub-cluster across ALL windows via two-pointer sweep.
# For every i, find max j for each cumulative i; the window [i,j] with
# smallest duration for a given count >= MIN_COUNT tells us peak burst.
# We'll search for the window maximizing count - alpha*duration to balance
# density and count. Better: find the window with smallest duration that
# still has >= MIN_COUNT errors, then check density.
print("\n=== DENSEST CLUSTER (smallest window with max count) ===")
# For each possible end index j, find earliest i such that j-i+1 == max count
# contained within that j's prefix.
# Simpler: for each i, slide j to maximize count; record (count, dur).
# Then sort by density (count/dur) descending, then by count descending, then dur ascending.

records = []
# Two-pointer: for each i, advance j as far as you like and record all
# window sizes (j-i+1). We do this efficiently by noting that for fixed i,
# as j increases, count grows and duration grows.
j = 0
for i in range(len(error_entries)):
    if j < i:
        j = i
    while j < len(error_entries):
        dur = (error_entries[j]['dt'] - error_entries[i]['dt']).total_seconds()
        cnt = j - i + 1
        records.append((cnt, dur, i, j))
        # Don't extend past a reasonable bound; we'll capture all windows.
        j += 1

# Deduplicate (cnt, dur, i, j) is unique by construction since j only increases.
# Score = count / (duration+0.5) to break ties at zero duration.
scored = [(cnt / (dur + 0.5), cnt, dur, i, j) for cnt, dur, i, j in records]
scored.sort(key=lambda x: (-x[0], -x[1], x[2]))

print("Top 15 by density (count/sec):")
for score, cnt, dur, i, j in scored[:15]:
    sdt = error_entries[i]['dt']
    edt = error_entries[j]['dt']
    print(f"  density={score:.2f} count={cnt} dur={dur}s {sdt} -> {edt}")

# The "peak burst" definition: smallest window containing the MOST errors
# with high density. Pick top by density among those with count >= 50
# (substantial burst), then refine.
# But actually: we want THE peak burst = single most intense burst. The
# criteria: maximize count, subject to high density. Let's pick the
# window with highest count whose density (count/dur) is at least 1
# error per second (very dense).
candidate = None
for score, cnt, dur, i, j in scored:
    if dur > 0 and cnt / dur >= 1.0:
        # Prefer highest count with density >= 1
        if candidate is None or cnt > candidate[1]:
            candidate = (score, cnt, dur, i, j)
print(f"\nBest candidate (density>=1 err/sec, max count): score={candidate[0]:.2f} count={candidate[1]} dur={candidate[2]}s")
i, j = candidate[3], candidate[4]
peak_start = error_entries[i]['dt']
peak_end   = error_entries[j]['dt']
print(f"Peak window: {peak_start} -> {peak_end}")

print(f"\nMessages in peak window (first 20):")
for k in range(i, j+1):
    print(f"  {error_entries[k]['dt']} {error_entries[k]['msg'][:140]}")

# Message breakdown within peak window
peak_msgs = Counter(error_entries[k]['msg'] for k in range(i, j+1))
print(f"\nMessage frequency within peak window:")
for m, c in peak_msgs.most_common(10):
    print(f"  [{c}] {m[:140]}")

# Sample raw lines from peak window for inspection
print(f"\nFirst 5 raw lines from peak window:")
for k in range(i, min(i+5, j+1)):
    print(f"  {error_entries[k]['raw'][:200]}")
