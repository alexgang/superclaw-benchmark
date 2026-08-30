#!/usr/bin/env python3
"""Compile per-day notable events and final JSON."""
import re, json
from datetime import datetime
from collections import Counter, defaultdict

LINE_RE = re.compile(
    r'^\[(?P<dow>\w{3})\s+(?P<mon>\w{3})\s+(?P<day>\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<year>\d{4})\]\s+\[(?P<sev>[^\]]+)\]\s+(?P<msg>.*)$'
)
MONTHS = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
DOW_FULL = {'Mon':'Monday','Tue':'Tuesday','Wed':'Wednesday','Thu':'Thursday',
            'Fri':'Friday','Sat':'Saturday','Sun':'Sunday'}

entries = []
with open('/workspace/apache_error.log') as f:
    for raw in f:
        raw = raw.rstrip('\n')
        m = LINE_RE.match(raw)
        if not m: continue
        dt = datetime(int(m['year']), MONTHS[m['mon']], int(m['day']),
                      *(int(x) for x in m['time'].split(':')))
        entries.append({'dt': dt, 'sev': m['sev'], 'msg': m['msg'], 'dow': m['dow']})

per_day = defaultdict(list)
for e in entries:
    per_day[e['dt'].date()].append(e)

# For each day, find the most active hour(s) and distinct attacker IPs
CLIENT_RE = re.compile(r'\[client ([^\]]+)\]')

def day_notable(day_entries, day_errors):
    notes = []

    # 1) Server start / stop
    starts = [e for e in day_entries if 'resuming normal operations' in e['msg']]
    stops  = [e for e in day_entries if 'caught SIGTERM' in e['msg'] or 'shutting down' in e['msg'].lower() or 'stopping' in e['msg'].lower()[:30]]
    if starts:
        notes.append(f"Apache start: '{starts[0]['msg']}' at {starts[0]['dt'].strftime('%H:%M:%S')}")
    if stops:
        notes.append(f"Apache shutdown: '{stops[0]['msg']}' at {stops[0]['dt'].strftime('%H:%M:%S')}")

    # 2) mod_jk Tomcat connector churn (sign of child restarts)
    #    Counts are over ALL severities for that day because workerEnv.init()
    #    and mod_jk2 Shutting down are typically [notice], while jk2_init()
    #    "Can't find child N" and mod_jk child init are [error].
    jk2_init = sum(1 for e in day_errors if e['msg'].startswith('jk2_init()'))
    jk_child = sum(1 for e in day_errors if e['msg'].startswith('mod_jk child init'))
    jk_shut  = sum(1 for e in day_entries if 'mod_jk2 Shutting down' in e['msg'])
    jk_env   = sum(1 for e in day_entries if 'workerEnv.init()' in e['msg'])
    if jk_shut >= 5 or jk2_init >= 5 or jk_env >= 5 or jk_child >= 5:
        notes.append(f"mod_jk/Tomcat connector churn: {jk_shut} shutdowns, {jk_env} workerEnv.init() notices, {jk2_init} jk2_init() errors, {jk_child} child inits")

    # 3) Distinct attacker IPs and their request counts
    client_msgs = defaultdict(list)
    for e in day_errors:
        cm = CLIENT_RE.search(e['msg'])
        if cm:
            client_msgs[cm.group(1)].append(e)
    top_attackers = sorted(client_msgs.items(), key=lambda kv: -len(kv[1]))[:3]
    if top_attackers and len(top_attackers[0][1]) >= 5:
        ip_top = top_attackers[0]  # (ip, [msgs...])
        if len(ip_top[1]) >= 20:
            notes.append(f"Major attack burst from {ip_top[0]}: {len(ip_top[1])} errors targeting the server")
        else:
            notes.append(f"Notable probing from {ip_top[0]}: {len(ip_top[1])} errors")
        if len(top_attackers) > 1:
            others = ', '.join(f'{ip} ({len(msgs)})' for ip, msgs in top_attackers[1:] if len(msgs) >= 3)
            if others:
                notes.append(f"Other active sources: {others}")

    # 4) Specific attack patterns
    awstats = sum(1 for e in day_errors if 'awstats' in e['msg'].lower())
    if awstats >= 10:
        notes.append(f"Awstats vulnerability scan: {awstats} errors hitting awstats/cgi-bin paths (CVE-2005-0116 probe pattern)")
    vti_bin = sum(1 for e in day_errors if '_vti_bin' in e['msg'])
    if vti_bin >= 10:
        notes.append(f"FrontPage probe: {vti_bin} hits on /_vti_bin paths")
    scripts_traversal = sum(1 for e in day_errors if 'scripts/..%5c' in e['msg'] or 'scripts/..%2f' in e['msg'] or '..%5c..' in e['msg'])
    if scripts_traversal >= 3:
        notes.append(f"Directory traversal probes: {scripts_traversal} hits on scripts/..%5c.. (IIS unicode/dot-dot attack)")
    sumthin = sum(1 for e in day_errors if '/sumthin' in e['msg'])
    if sumthin >= 5:
        notes.append(f"Worm/scanner signature: {sumthin} hits on /sumthin (Code Red/Nimda-style scanner)")
    dir_index = sum(1 for e in day_errors if 'Directory index forbidden' in e['msg'])
    if dir_index >= 20:
        unique_clients_diridx = len({CLIENT_RE.search(e['msg']).group(1) for e in day_errors if 'Directory index forbidden' in e['msg'] and CLIENT_RE.search(e['msg'])})
        notes.append(f"Directory index forbidden warnings: {dir_index} from {unique_clients_diridx} distinct clients")

    # 5) Peak hour for the day
    hour_counts = Counter(e['dt'].hour for e in day_errors)
    if hour_counts:
        peak_hour, peak_hour_cnt = hour_counts.most_common(1)[0]
        if peak_hour_cnt >= 20:
            notes.append(f"Peak hour: {peak_hour:02d}:00 with {peak_hour_cnt} errors")

    return notes

# Build daily summary
daily_summary = []
for d in sorted(per_day.keys()):
    day_entries = per_day[d]
    day_errors  = [e for e in day_entries if e['sev'] == 'error']
    dow = DOW_FULL[day_entries[0]['dow']]
    notes = day_notable(day_entries, day_errors)
    daily_summary.append({
        'date': d.strftime('%Y-%m-%d'),
        'day_of_week': dow,
        'error_count': len(day_errors),
        'notable_events': notes,
    })

# Peak burst — the sliding-window result:
# 2005-06-11 03:03:03 -> 2005-06-11 03:03:14, 11 seconds, 254 errors.
# All from client 202.133.98.6, awstats vulnerability scan. Server-side
# errors (jk2_init / mod_jk child init) are Apache spawning workers
# under the request flood.

peak_burst = {
    'start_time': '2005-06-11 03:03:03',
    'end_time':   '2005-06-11 03:03:14',
    'duration_seconds': 11,
    'error_count': 254,
    'description': (
        "Single-IP awstats vulnerability scan/worm probe from 202.133.98.6 firing ~23 errors/sec "
        "for 11 seconds (254 errors total, peak 54 errors in a single second at 03:03:09). "
        "184 errors are client-side 'File does not exist' / 'script not found' hits against "
        "awstats paths (/cgi-bin/awstats, /cgi-bin/awstats.pl, /cgi-bin/stats, /awstats/awstats.pl, "
        "/awstats.pl) — the canonical signature of the AWStats configdir RCE exploit (CVE-2005-0116) "
        "probing for vulnerable installs. The remaining 70 errors are server-side fallout: Apache "
        "spawning many child processes under the request flood produced jk2_init() 'Can't find child "
        "N in scoreboard' and 'mod_jk child init' warnings."
    ),
}

out = {
    'date_range': '2005-06-09 to 2005-06-16',
    'daily_summary': daily_summary,
    'peak_burst': peak_burst,
}

with open('/workspace/error_timeline.json', 'w') as f:
    json.dump(out, f, indent=2)

print(json.dumps(out, indent=2))
