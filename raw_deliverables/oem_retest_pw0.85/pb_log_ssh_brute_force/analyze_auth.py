#!/usr/bin/env python3
"""
Analyze OpenSSH authentication log for brute-force attack patterns.
"""

import re
import json
from collections import defaultdict
from datetime import datetime

LOG_FILE = "/workspace/auth.log"

# Regex patterns
# Failed password lines: "Failed password for [user] from [IP] port [port] ssh2"
# Authentication failure lines: "authentication failure; ... rhost=[IP] user=[user]"
# Invalid user lines: "Invalid user [user] from [IP]"
# Reverse DNS warning: "POSSIBLE BREAK-IN ATTEMPT!"

def parse_log_line(line):
    """Parse a log line and extract relevant information."""
    result = {
        'timestamp': None,
        'ip': None,
        'username': None,
        'event_type': None,
        'reverse_dns_warning': False
    }
    
    # Try to extract timestamp (format: Dec 10 HH:MM:SS)
    ts_match = re.match(r'^(\w+\s+\d+\s+\d+:\d+:\d+)', line)
    if ts_match:
        result['timestamp'] = ts_match.group(1)
    
    # Try to extract IP address
    ip_match = re.search(r'from\s+(\d+\.\d+\.\d+\.\d+)', line)
    if ip_match:
        result['ip'] = ip_match.group(1)
    
    # Try to extract username
    user_match = re.search(r'(?:for\s+)?(?:invalid\s+)?user\s+(\w+)', line)
    if user_match:
        result['username'] = user_match.group(1)
    
    # Check for reverse DNS warning
    if 'POSSIBLE BREAK-IN ATTEMPT!' in line:
        result['reverse_dns_warning'] = True
    
    # Determine event type
    if 'Failed password' in line:
        result['event_type'] = 'failed_password'
    elif 'authentication failure' in line:
        result['event_type'] = 'auth_failure'
    elif 'Invalid user' in line:
        result['event_type'] = 'invalid_user'
    
    return result

def analyze_log():
    """Analyze the log file and extract brute-force attack data."""
    
    # Data structures
    ip_data = defaultdict(lambda: {
        'failed_attempts': 0,
        'timestamps': [],
        'usernames': set(),
        'reverse_dns_warnings': False
    })
    
    # Read and parse the log
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()
    
    print(f"Processing {len(lines)} log lines...")
    
    for line in lines:
        parsed = parse_log_line(line.strip())
        
        if not parsed['ip']:
            continue
        
        ip = parsed['ip']
        
        # Count failed authentication attempts
        if parsed['event_type'] in ('failed_password', 'auth_failure', 'invalid_user'):
            ip_data[ip]['failed_attempts'] += 1
            if parsed['timestamp']:
                ip_data[ip]['timestamps'].append(parsed['timestamp'])
            if parsed['username']:
                ip_data[ip]['usernames'].add(parsed['username'])
            if parsed['reverse_dns_warning']:
                ip_data[ip]['reverse_dns_warnings'] = True
    
    # Filter brute-force sources (>10 failed attempts)
    brute_force_sources = []
    for ip, data in ip_data.items():
        if data['failed_attempts'] > 10:
            timestamps = sorted(data['timestamps'])
            first_seen = timestamps[0] if timestamps else None
            last_seen = timestamps[-1] if timestamps else None
            
            # Calculate attack intensity (attempts per minute)
            if len(timestamps) >= 2:
                try:
                    first_dt = datetime.strptime(first_seen, '%b %d %H:%M:%S')
                    last_dt = datetime.strptime(last_seen, '%b %d %H:%M:%S')
                    duration_minutes = (last_dt - first_dt).total_seconds() / 60
                    if duration_minutes > 0:
                        attempts_per_minute = data['failed_attempts'] / duration_minutes
                    else:
                        attempts_per_minute = data['failed_attempts']
                except ValueError:
                    attempts_per_minute = data['failed_attempts']
            else:
                attempts_per_minute = data['failed_attempts']
            
            # Determine attack type
            usernames = list(data['usernames'])
            if len(usernames) > 5:
                attack_type = "dictionary"
            else:
                attack_type = "targeted"
            
            brute_force_sources.append({
                'ip': ip,
                'total_attempts': data['failed_attempts'],
                'first_seen': first_seen,
                'last_seen': last_seen,
                'usernames_tried': sorted(list(data['usernames'])),
                'attack_type': attack_type,
                'reverse_dns_warning': data['reverse_dns_warnings']
            })
    
    # Sort by total attempts descending
    brute_force_sources.sort(key=lambda x: x['total_attempts'], reverse=True)
    
    # Calculate overall risk level
    total_attempts = sum(s['total_attempts'] for s in brute_force_sources)
    num_attackers = len(brute_force_sources)
    
    if total_attempts > 100 or num_attackers > 5:
        risk_level = "critical"
    elif total_attempts > 50 or num_attackers > 3:
        risk_level = "high"
    elif total_attempts > 20 or num_attackers > 2:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    # Generate recommendations
    recommendations = []
    if risk_level in ("critical", "high"):
        recommendations.append("Implement IP-based rate limiting on SSH")
        recommendations.append("Enable fail2ban or similar intrusion prevention system")
        recommendations.append("Configure SSH to reject repeated failed login attempts")
    recommendations.append("Block IPs with reverse DNS warnings")
    recommendations.append("Monitor and alert on new brute-force attempts")
    recommendations.append("Consider implementing multi-factor authentication")
    
    # Build summary
    summary = f"Detected {num_attackers} brute-force attack sources from {total_attempts} failed authentication attempts. "
    summary += f"Most aggressive attacker: {brute_force_sources[0]['ip']} with {brute_force_sources[0]['total_attempts']} attempts."
    
    report = {
        'summary': summary,
        'brute_force_sources': brute_force_sources,
        'risk_level': risk_level,
        'recommendations': recommendations
    }
    
    return report

if __name__ == '__main__':
    report = analyze_log()
    
    # Write to JSON file
    with open('/workspace/brute_force_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Report written to /workspace/brute_force_report.json")
    print(json.dumps(report, indent=2))
