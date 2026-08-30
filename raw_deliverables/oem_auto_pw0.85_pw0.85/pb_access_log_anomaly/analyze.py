import pandas as pd
import json
import re

df = pd.read_csv('/workspace/access_events.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Derive building from location column
def get_building(loc):
    if 'HQ' in str(loc):
        return 'HQ Building'
    if 'Annex' in str(loc):
        return 'Annex Building'
    return loc

df['building'] = df['location'].apply(get_building)
df['access_result'] = df['result']

anomalies = []

# --- 1. impossible_travel ---
for badge, sub in df.groupby('badge_id'):
    sub = sub.sort_values('timestamp').reset_index(drop=True)
    for i in range(len(sub)):
        for j in range(i+1, len(sub)):
            b1 = sub.iloc[i]
            b2 = sub.iloc[j]
            if b1['building'] != b2['building']:
                delta = (b2['timestamp'] - b1['timestamp']).total_seconds() / 60
                if delta <= 15:
                    anomalies.append({
                        'badge_id': str(badge),
                        'anomaly_type': 'impossible_travel',
                        'description': f"Badge {badge} scanned at {b1['building']} at {b1['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} and at {b2['building']} at {b2['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} ({int(round(delta))} min apart)"
                    })

# --- 2. after_hours_restricted ---
def is_business_hours(ts):
    wd = ts.weekday()
    h = ts.hour
    if wd >= 5:
        return False
    if h < 7 or h >= 19:
        return False
    return True

for _, row in df[df['door_id'].str.contains('SRV') & (df['access_result'] == 'GRANTED')].iterrows():
    if not is_business_hours(row['timestamp']):
        anomalies.append({
            'badge_id': str(row['badge_id']),
            'anomaly_type': 'after_hours_restricted',
            'description': f"Badge {row['badge_id']} granted access to {row['door_id']} (server room) at {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} outside business hours"
        })

# --- 3. repeated_denials ---
# Find all maximal clusters of 4+ denials at same (badge, door) within a 10-min window.
# Then every denial that belongs to any such cluster is flagged.
# Report the cluster size in each event's description.
denied = df[df['access_result'] == 'DENIED'].copy().sort_values(['badge_id','door_id','timestamp']).reset_index(drop=True)

cluster_of = {}  # idx -> cluster_id
clusters = []    # list of (idx_set, size)

for (bd, dr), sub in denied.groupby(['badge_id','door_id']):
    sub = sub.sort_values('timestamp').reset_index(drop=True)
    times = sub['timestamp'].tolist()
    n = len(times)
    used = [False]*n
    for i in range(n):
        if used[i]:
            continue
        # build forward window from i
        members = [i]
        for j in range(i+1, n):
            if (times[j] - times[i]).total_seconds()/60 <= 10:
                members.append(j)
            else:
                break
        # also check backward: i might be within a window that started earlier
        # We process in order so a previous cluster may have already covered it.
        if len(members) >= 4:
            for k in members:
                used[k] = True
            cluster_id = len(clusters)
            clusters.append((set(members), len(members)))
            for k in members:
                cluster_of[(bd, dr, k)] = cluster_id

# Now emit one anomaly per denial event that belongs to a cluster of >=4
# Compute the cluster size per (badge, door) — clusters are per (badge, door) group
# Actually I tracked cluster_id per (bd, dr). But cluster_of was keyed with the local index k.
# Simpler: iterate sub-groups again.

emitted = set()  # (idx_in_denied) -> ensure once
for (bd, dr), sub in denied.groupby(['badge_id','door_id']):
    sub = sub.sort_values('timestamp').reset_index(drop=True)
    times = sub['timestamp'].tolist()
    n = len(times)
    for i in range(n):
        members = [i]
        for j in range(i+1, n):
            if (times[j] - times[i]).total_seconds()/60 <= 10:
                members.append(j)
            else:
                break
        if len(members) >= 4:
            size = len(members)
            ts0 = times[i]
            ts_last = times[members[-1]]
            # every member of this cluster is flagged (each appears as one anomaly entry)
            for k in members:
                ts_k = times[k]
                anomalies.append({
                    'badge_id': str(bd),
                    'anomaly_type': 'repeated_denials',
                    'description': f"Badge {bd} had {size} DENIED scans at {dr} between {ts0.strftime('%Y-%m-%d %H:%M:%S')} and {ts_last.strftime('%Y-%m-%d %H:%M:%S')}; event at {ts_k.strftime('%Y-%m-%d %H:%M:%S')}"
                })

# Deduplicate exact duplicates (shouldn't be any, but be safe)
seen = set()
unique = []
for a in anomalies:
    key = (a['badge_id'], a['anomaly_type'], a['description'])
    if key not in seen:
        seen.add(key)
        unique.append(a)

def sort_key(a):
    m = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', a['description'])
    ts = m.group(1) if m else ''
    return (ts, a['badge_id'], a['anomaly_type'])

unique.sort(key=sort_key)

with open('/workspace/anomaly_report.json','w') as f:
    json.dump(unique, f, indent=2)

from collections import Counter
counts = Counter(a['anomaly_type'] for a in unique)
print('Total anomalies:', len(unique))
for k, c in counts.items():
    print(f'  {k}: {c}')
print('---')
for a in unique:
    print(a)