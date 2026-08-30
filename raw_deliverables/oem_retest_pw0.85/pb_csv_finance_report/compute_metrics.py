#!/usr/bin/env python3
"""Compute comprehensive finance metrics for Apple 2014 stock data."""

import csv
import math
import json
import copy
from datetime import datetime
from collections import defaultdict

# Load data
data = []
with open('/workspace/apple_stock_2014.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        date_str = row['AAPL_x']
        price = float(row['AAPL_y'])
        dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        data.append({'date': dt, 'date_str': date_str, 'price': price})

data.sort(key=lambda x: x['date'])
n = len(data)
print(f"Total trading days: {n}")
print(f"First date: {data[0]['date_str']}, Price: {data[0]['price']}")
print(f"Last date: {data[-1]['date_str']}, Price: {data[-1]['price']}")

# ========== Basic Performance ==========
start_price = data[0]['price']
end_price = data[-1]['price']
total_return_pct = (end_price / start_price - 1) * 100
print(f"\n=== BASIC PERFORMANCE ===")
print(f"Starting price (2014-01-02): ${start_price:.4f}")
print(f"Ending price (2014-12-31): ${end_price:.4f}")
print(f"Total return: {total_return_pct:.4f}%")

# ========== Daily Returns ==========
returns = []
for i in range(1, n):
    prev_price = data[i-1]['price']
    curr_price = data[i]['price']
    ret = (curr_price / prev_price - 1) * 100
    returns.append({
        'date': data[i]['date'],
        'date_str': data[i]['date_str'],
        'prev_price': prev_price,
        'price': curr_price,
        'pct_return': ret,
        'log_return': math.log(curr_price / prev_price)
    })

mean_ret = sum(r['pct_return'] for r in returns) / len(returns)
var_ret = sum((r['pct_return'] - mean_ret)**2 for r in returns) / (len(returns) - 1)
std_ret = math.sqrt(var_ret)
annualized_vol = std_ret * math.sqrt(252)

print(f"\n=== DAILY RETURNS ===")
print(f"Mean daily return: {mean_ret:.6f}%")
print(f"Daily std dev: {std_ret:.6f}%")
print(f"Annualized volatility: {annualized_vol:.6f}%")

# ========== High and Low ==========
high = max(data, key=lambda x: x['price'])
low = min(data, key=lambda x: x['price'])
print(f"\n=== HIGH/LOW ===")
print(f"High: ${high['price']:.4f} on {high['date_str']}")
print(f"Low: ${low['price']:.4f} on {low['date_str']}")

# ========== Monthly Averages ==========
monthly = defaultdict(list)
for d in data:
    month_key = d['date_str'][:7]
    monthly[month_key].append(d['price'])

print(f"\n=== MONTHLY AVERAGES ===")
monthly_avg = {}
monthly_metrics = {}
for month_key in sorted(monthly.keys()):
    prices = monthly[month_key]
    avg = sum(prices) / len(prices)
    monthly_avg[month_key] = avg
    month_data = [d for d in data if d['date_str'].startswith(month_key)]
    first_p = month_data[0]['price']
    last_p = month_data[-1]['price']
    month_ret = (last_p / first_p - 1) * 100
    monthly_metrics[month_key] = {
        'avg': avg, 'count': len(prices),
        'first_price': first_p, 'last_price': last_p,
        'ret_pct': month_ret,
        'first_date': month_data[0]['date_str'],
        'last_date': month_data[-1]['date_str'],
        'high': max(prices), 'low': min(prices)
    }
    print(f"{month_key}: avg=${avg:.4f}, ret={month_ret:.4f}%")

# ========== Quarterly Metrics ==========
quarter_data = {1: [], 2: [], 3: [], 4: []}
for d in data:
    m = int(d['date_str'][5:7])
    q = (m - 1) // 3 + 1
    quarter_data[q].append(d)

quarter_metrics = {}
for q in [1, 2, 3, 4]:
    qd = quarter_data[q]
    qstart = qd[0]
    qend = qd[-1]
    qret = (qend['price'] / qstart['price'] - 1) * 100
    qavg = sum(d['price'] for d in qd) / len(qd)
    qreturns = []
    for i in range(1, len(qd)):
        r = (qd[i]['price'] / qd[i-1]['price'] - 1) * 100
        qreturns.append(r)
    qmean = sum(qreturns) / len(qreturns)
    qvar = sum((r - qmean)**2 for r in qreturns) / (len(qreturns) - 1) if len(qreturns) > 1 else 0
    qstd = math.sqrt(qvar)
    qannvol = qstd * math.sqrt(252)
    quarter_metrics[q] = {
        'start_date': qstart['date_str'],
        'end_date': qend['date_str'],
        'start_price': qstart['price'],
        'end_price': qend['price'],
        'avg_price': qavg,
        'return_pct': qret,
        'daily_std': qstd,
        'ann_vol': qannvol,
        'trading_days': len(qd)
    }
    print(f"\nQ{q}: start={qstart['date_str']} ${qstart['price']:.4f}, end={qend['date_str']} ${qend['price']:.4f}, ret={qret:.4f}%, ann_vol={qannvol:.4f}%")

# ========== Top/Bottom Days ==========
sorted_by_ret = sorted(returns, key=lambda x: x['pct_return'], reverse=True)
print(f"\n=== TOP 3 BEST DAYS ===")
for r in sorted_by_ret[:3]:
    print(f"{r['date_str']}: +{r['pct_return']:.4f}% (from ${r['prev_price']:.4f} to ${r['price']:.4f})")
print(f"\n=== TOP 3 WORST DAYS ===")
for r in sorted_by_ret[-3:]:
    print(f"{r['date_str']}: {r['pct_return']:.4f}% (from ${r['prev_price']:.4f} to ${r['price']:.4f})")

# ========== Streaks ==========
longest_up = 0
longest_down = 0
current_up = 0
current_down = 0
longest_up_end = None
longest_down_end = None
longest_up_start = None
longest_down_start = None
current_up_start = None
current_down_start = None

for r in returns:
    if r['pct_return'] > 0:
        if current_up == 0:
            current_up_start = r['date_str']
        current_up += 1
        current_down = 0
        if current_up > longest_up:
            longest_up = current_up
            longest_up_end = r['date_str']
            longest_up_start = current_up_start
    elif r['pct_return'] < 0:
        if current_down == 0:
            current_down_start = r['date_str']
        current_down += 1
        current_up = 0
        if current_down > longest_down:
            longest_down = current_down
            longest_down_end = r['date_str']
            longest_down_start = current_down_start
    else:
        current_up = 0
        current_down = 0

print(f"\n=== STREAKS ===")
print(f"Longest up streak: {longest_up} days ({longest_up_start} to {longest_up_end})")
print(f"Longest down streak: {longest_down} days ({longest_down_start} to {longest_down_end})")

# ========== Maximum Drawdown ==========
current_peak_price = data[0]['price']
current_peak_date = data[0]['date_str']
max_dd = 0
max_dd_peak_price = data[0]['price']
max_dd_peak_date = data[0]['date_str']
max_dd_trough_price = data[0]['price']
max_dd_trough_date = data[0]['date_str']

for d in data:
    if d['price'] > current_peak_price:
        current_peak_price = d['price']
        current_peak_date = d['date_str']
    dd = (d['price'] / current_peak_price - 1) * 100
    if dd < max_dd:
        max_dd = dd
        max_dd_peak_price = current_peak_price
        max_dd_peak_date = current_peak_date
        max_dd_trough_price = d['price']
        max_dd_trough_date = d['date_str']

recovery_date = None
for d in data:
    if d['date_str'] > max_dd_trough_date and d['price'] >= max_dd_peak_price:
        recovery_date = d['date_str']
        break

print(f"\n=== MAX DRAWDOWN ===")
print(f"Peak: ${max_dd_peak_price:.4f} on {max_dd_peak_date}")
print(f"Trough: ${max_dd_trough_price:.4f} on {max_dd_trough_date}")
print(f"Max drawdown: {max_dd:.4f}%")
print(f"Recovery: {recovery_date}")

# ========== Risk-adjusted ==========
annualized_return = ((end_price / start_price) ** (252 / (n - 1)) - 1) * 100
risk_adj_simple = total_return_pct / annualized_vol
sharpe_like = annualized_return / annualized_vol

print(f"\n=== RISK-ADJUSTED ===")
print(f"Annualized return: {annualized_return:.4f}%")
print(f"Simple ratio: {risk_adj_simple:.4f}")
print(f"Sharpe-like: {sharpe_like:.4f}")

# ========== Day counts ==========
pos_days = sum(1 for r in returns if r['pct_return'] > 0)
neg_days = sum(1 for r in returns if r['pct_return'] < 0)
flat_days = sum(1 for r in returns if r['pct_return'] == 0)

# ========== Rallies/Selloffs (1-month rolling window) ==========
window = 21
rallies = []
selloffs = []
for i in range(window, len(data)):
    window_data = data[i-window:i+1]
    wmin = min(window_data, key=lambda x: x['price'])
    wmax = max(window_data, key=lambda x: x['price'])
    move_pct = (wmax['price'] / wmin['price'] - 1) * 100
    if move_pct < 5:
        continue
    if wmax['date_str'] > wmin['date_str']:
        rallies.append((wmin['date_str'], wmax['date_str'], move_pct))
    else:
        selloffs.append((wmax['date_str'], wmin['date_str'], move_pct))

# Deduplicate by keeping only non-overlapping largest swings
def dedupe_swings(swings):
    if not swings:
        return []
    # Sort by magnitude
    sorted_swings = sorted(swings, key=lambda x: x[2], reverse=True)
    used_dates = set()
    result = []
    for s in sorted_swings:
        s_start, s_end, s_pct = s
        start_dt = datetime.strptime(s_start, '%Y-%m-%d').date()
        end_dt = datetime.strptime(s_end, '%Y-%m-%d').date()
        # Check if any date in this swing is already used
        overlap = False
        for ud in used_dates:
            if start_dt <= ud <= end_dt:
                overlap = True
                break
        if not overlap:
            result.append(s)
            # Mark all dates in this swing as used
            for d in data:
                if start_dt <= d['date'] <= end_dt:
                    used_dates.add(d['date'])
    return sorted(result, key=lambda x: x[1])

deduped_rallies = dedupe_swings(rallies)
deduped_selloffs = dedupe_swings(selloffs)

print(f"\n=== TOP RALLIES (1-month window) ===")
for r in deduped_rallies[:5]:
    print(f"  {r[0]} -> {r[1]}: +{r[2]:.2f}%")

print(f"\n=== TOP SELLOFFS (1-month window) ===")
for s in deduped_selloffs[:5]:
    print(f"  {s[0]} -> {s[1]}: -{s[2]:.2f}%")

# Save all metrics
output = {
    'n': n,
    'start_date': data[0]['date_str'],
    'end_date': data[-1]['date_str'],
    'start_price': start_price,
    'end_price': end_price,
    'total_return_pct': total_return_pct,
    'mean_daily_return': mean_ret,
    'daily_std': std_ret,
    'annualized_vol': annualized_vol,
    'high_price': high['price'],
    'high_date': high['date_str'],
    'low_price': low['price'],
    'low_date': low['date_str'],
    'max_dd': max_dd,
    'max_dd_peak_price': max_dd_peak_price,
    'max_dd_peak_date': max_dd_peak_date,
    'max_dd_trough_price': max_dd_trough_price,
    'max_dd_trough_date': max_dd_trough_date,
    'recovery_date': recovery_date,
    'annualized_return': annualized_return,
    'risk_adj_simple': risk_adj_simple,
    'sharpe_like': sharpe_like,
    'longest_up_streak': longest_up,
    'longest_up_start': longest_up_start,
    'longest_up_end': longest_up_end,
    'longest_down_streak': longest_down,
    'longest_down_start': longest_down_start,
    'longest_down_end': longest_down_end,
    'pos_days': pos_days,
    'neg_days': neg_days,
    'flat_days': flat_days,
    'total_return_days': len(returns),
    'monthly_metrics': monthly_metrics,
    'quarter_metrics': quarter_metrics,
    'top3_best': [{'date': r['date_str'], 'ret': r['pct_return'], 'prev': r['prev_price'], 'price': r['price']} for r in sorted_by_ret[:3]],
    'top3_worst': [{'date': r['date_str'], 'ret': r['pct_return'], 'prev': r['prev_price'], 'price': r['price']} for r in sorted_by_ret[-3:]],
    'top_rallies': [{'start': r[0], 'end': r[1], 'pct': r[2]} for r in deduped_rallies[:5]],
    'top_selloffs': [{'start': s[0], 'end': s[1], 'pct': s[2]} for s in deduped_selloffs[:5]],
}

with open('/workspace/metrics.json', 'w') as f:
    json.dump(output, f, indent=2, default=str)
print("\nMetrics saved to /workspace/metrics.json")