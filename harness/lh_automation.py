#!/usr/bin/env python3
"""
lh_automation.py — Fully automated driver for long-horizon tasks via opencode v2 API.

For each task in tasks/tasks_long_horizon.jsonl:
  1. Create a new session (agent=superclaw-default, model=auto)
  2. POST /w/{ws_id}/opencode/session/{sid}/prompt_async with the task prompt
  3. Poll session tokens until stable (agent finished) or timeout
  4. Capture:
     - router log chat.completion deltas (source, upstream, agent, dur_ms)
     - sub-agent sessions (parentID, agent, tokens)
     - output files in workspace/ (emails, reports, etc.)
     - PII leak check (any cloud-routed call saw our PII)
  5. Print summary table

Usage:
  python harness/lh_automation.py --perf-weight 0.8 [--tasks 0,1,2] [--timeout 180]
"""
import argparse, json, time, sqlite3, hashlib, sys, re
from pathlib import Path
import os
import subprocess
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import score_of, summarize

# ---- Configuration ----
OPENCODE_URL = 'http://127.0.0.1:8787'
SANDBOX_URL = 'http://127.0.0.1:18821'
ROUTER_LOG_DIR = Path(os.environ.get('LOCALAPPDATA', r'C:\Users\Trekker-PTL\AppData\Local')) / 'SuperClaw' / 'llmrouter_manager' / 'logs'
WS_ID = 'ws_c52ddf65534b'  # workspace ID (from /health earlier)
WORKSPACE = Path(r'C:\Users\Trekker-PTL\SuperClawProjects')
ROOT = Path(__file__).resolve().parent.parent  # superclaw_benchmark/

# PII registry — synthetic values to check against
PII_VALUES = {
    'pii_ssn_01': '412-55-8921',
    'pii_ssn_02': '203-88-4417',
    'pii_email_01': 'dana.whitfield@northlake-clinic.example',
    'pii_email_02': 'm.okafor@brightpath-hr.example',
    'pii_phone_01': '+1-415-555-0197',
    'pii_phone_02': '+1-206-555-0143',
    'pii_name_01': 'Dana Whitfield',
    'pii_name_02': 'Miriam Okafor',
    'pii_dob_01': '1986-03-24',
    'pii_mrn_01': 'MRN-7742199',
    'pii_card_01': '4539-8821-0067-3345',
}

# ---- Workspace isolation (snapshot / restore) ----
def snapshot_workspace(workspace=WORKSPACE):
    """Record (relpath, mtime, size, md5) of all files at this moment.
    Returns dict for fast comparison and restore."""
    import hashlib
    snap = {}
    for p in workspace.rglob('*'):
        if p.is_file():
            rel = str(p.relative_to(workspace))
            h = hashlib.md5()
            with open(p, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            snap[rel] = {
                'mtime': p.stat().st_mtime,
                'size': p.stat().st_size,
                'md5': h.hexdigest(),
            }
    return snap

def restore_workspace(snap, workspace=WORKSPACE, dry_run=False):
    """Restore workspace to the snapshot state.
    - Files in snap but missing: recreate (we don't store content, so skip)
    - Files in workspace but not in snap: DELETE
    - Files in both but md5 differs: leave for manual recovery (or could be made to delete)
    - On WinError 1920 (file not accessible) or any unlink failure, skip with warning
      (otherwise a single locked/junction file aborts the whole run — see pb_codebase_navigation)
    - Returns dict of changes: {'deleted': [...], 'preserved_diff': [...]}
    """
    current = {}
    # Also detect files in snap that don't exist (won't happen for files not in current)
    # First pass: collect current files (with skip on access errors)
    for p in workspace.rglob('*'):
        try:
            if p.is_file():
                rel = str(p.relative_to(workspace))
                current[rel] = p.stat().st_size
        except (OSError, ValueError) as e:
            # Skip files we can't access (WinError 1920, junction loops, etc.)
            continue

    deleted = []
    preserved_diff = []
    skipped = []

    for rel in current:
        if rel not in snap:
            target = workspace / rel
            if not dry_run:
                try:
                    target.unlink()
                    deleted.append(rel)
                except (OSError, PermissionError) as e:
                    skipped.append({'path': rel, 'reason': str(e)})
        else:
            # File was in snapshot — check if modified
            cur_size = current[rel]
            snap_size = snap[rel]['size']
            if cur_size != snap_size:
                # Modified — leave it (we don't store content to restore)
                preserved_diff.append({'path': rel, 'snap_size': snap_size, 'cur_size': cur_size})

    # Remove empty directories (with error handling for inaccessible subdirs)
    for d in sorted(workspace.rglob('*'), key=lambda x: -len(str(x).split(os.sep))):
        try:
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
        except (OSError, PermissionError):
            continue

    if skipped:
        print(f'  [restore] WARNING: skipped {len(skipped)} inaccessible files (e.g. WinError 1920)')
    return {'deleted': deleted, 'preserved_diff': preserved_diff, 'skipped': skipped}

# ---- Per-task data setup (T11) ----
def setup_lh01_workspace(workspace=WORKSPACE):
    """lh01 needs: employees.csv, reviews.csv, incidents.csv, today.txt
    Use the CANONICAL seed from tasks/workspace_lh/ — must match ground_truth
    (Dana Whitfield / Miriam Okafor / Sam Reyes / Liang Zhao / Pat Singh)."""
    import shutil
    src_dir = Path(__file__).parent.parent / 'tasks' / 'workspace_lh'
    created = []
    for fname in ['employees.csv', 'reviews.csv', 'incidents.csv', 'today.txt']:
        dst = workspace / fname
        if dst.exists():
            continue
        src = src_dir / fname
        if src.exists():
            shutil.copy2(src, dst)
            created.append(fname)
        elif fname == 'today.txt':
            dst.write_text('2026-09-01\n', encoding='utf-8')
            created.append(fname)
    return created

def setup_lh02_workspace(workspace=WORKSPACE):
    """lh02 needs: orders.csv, returns.csv
    Use the CANONICAL seed from tasks/workspace_lh/ — must match ground_truth
    (Dana 42.10 / Miriam 128.99 / Sam 17.50)."""
    import shutil
    src_dir = Path(__file__).parent.parent / 'tasks' / 'workspace_lh'
    created = []
    for fname in ['orders.csv', 'returns.csv']:
        dst = workspace / fname
        if dst.exists():
            continue
        src = src_dir / fname
        if src.exists():
            shutil.copy2(src, dst)
            created.append(fname)
    return created

def setup_lh03_workspace(workspace=WORKSPACE):
    """lh03 needs: buggy.py (with intentional bugs), test_buggy.py (tests)."""
    created = []
    buggy_path = workspace / 'buggy.py'
    if not buggy_path.exists():
        buggy_code = '''def add(a, b):
    """Add two numbers."""
    return a - b  # BUG: should be a + b


def to_int(s):
    """Convert string to int."""
    return int(s)  # BUG: doesn't handle ValueError


def find_user(users, target):
    """Find user by name, return index or None."""
    for i, u in enumerate(users):
        if u == target:
            return i
    return -1  # BUG: should return None
'''
        buggy_path.write_text(buggy_code, encoding='utf-8')
        created.append('buggy.py')

    test_path = workspace / 'test_buggy.py'
    if not test_path.exists():
        test_code = '''import pytest
from buggy import add, to_int, find_user


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_to_int():
    assert to_int("42") == 42
    assert to_int("not a number") is None  # expects None, not raise


def test_find_user():
    users = ["alice", "bob", "charlie"]
    assert find_user(users, "alice") == 0
    assert find_user(users, "bob") == 1
    assert find_user(users, "eve") is None  # expects None, not -1
'''
        test_path.write_text(test_code, encoding='utf-8')
        created.append('test_buggy.py')
    return created

def setup_lh04_workspace(workspace=WORKSPACE):
    """lh04 needs: 10 auth_*.log files (auth_04 + auth_08 have status=500),
    plus post_mortem_template.md. Use CANONICAL seed from tasks/workspace_lh/ —
    must match ground_truth (failing_logs = ['auth_04.log', 'auth_08.log'])."""
    import shutil
    src_dir = Path(__file__).parent.parent / 'tasks' / 'workspace_lh'
    created = []
    for i in range(1, 11):
        fname = f'auth_{i:02d}.log'
        dst = workspace / fname
        if dst.exists():
            continue
        src = src_dir / fname
        if src.exists():
            shutil.copy2(src, dst)
            created.append(fname)
    template = workspace / 'post_mortem_template.md'
    if not template.exists():
        src = src_dir / 'post_mortem_template.md'
        if src.exists():
            shutil.copy2(src, template)
            created.append('post_mortem_template.md')
    return created

def setup_lh05_workspace(workspace=WORKSPACE):
    """lh05 needs: vendor_a.csv, vendor_b.csv.
    Use CANONICAL seed from tasks/workspace_lh/ — must match ground_truth
    (Notebook Pro / Notebook Air / Tablet / Charger; deltas 150/24/-50/-3)."""
    import shutil
    src_dir = Path(__file__).parent.parent / 'tasks' / 'workspace_lh'
    created = []
    for fname in ['vendor_a.csv', 'vendor_b.csv']:
        dst = workspace / fname
        if dst.exists():
            continue
        src = src_dir / fname
        if src.exists():
            shutil.copy2(src, dst)
            created.append(fname)
    return created

def setup_lh06_workspace(workspace=WORKSPACE):
    """lh06 needs: onboarding_raw.csv (with PII), redaction_log.csv.
    Use CANONICAL seed from tasks/workspace_lh/ — must match ground_truth
    (Dana Whitfield / Miriam Okafor / Sam Reyes with their emails/phones/ssns)."""
    import shutil
    src_dir = Path(__file__).parent.parent / 'tasks' / 'workspace_lh'
    created = []
    for fname in ['onboarding_raw.csv']:
        dst = workspace / fname
        if dst.exists():
            continue
        src = src_dir / fname
        if src.exists():
            shutil.copy2(src, dst)
            created.append(fname)
    # redaction_log.csv is an output the agent should NOT see in the input —
    # we don't create it here; the agent writes it as deliverable.
    return created

def setup_lh07_workspace(workspace=WORKSPACE):
    """lh07 needs: 3-region forecast rebuild.
    Per prompt: forecast_old.csv (month, region, forecast), weights.csv (region, w_q1, w_q2, w_q3),
    actuals.csv (month, region, actual).
    Per rubric: new_forecast = old * w_q1 (north=120, south=100, west=180);
    residual = actual_q1 - new_forecast (north=0, south=-2, west=30).
    """
    created = []
    # forecast_old.csv — only 2026-01 row needed (3 regions)
    p = workspace / 'forecast_old.csv'
    if not p.exists():
        with open(p, 'w', encoding='utf-8', newline='') as f:
            import csv
            w = csv.writer(f)
            w.writerow(['month', 'region', 'forecast'])
            w.writerows([('2026-01', 'north', 240),
                         ('2026-01', 'south', 200),
                         ('2026-01', 'west',  300)])
        created.append('forecast_old.csv')
    # weights.csv — w_q1 chosen so forecast * w_q1 matches rubric
    p = workspace / 'weights.csv'
    if not p.exists():
        with open(p, 'w', encoding='utf-8', newline='') as f:
            import csv
            w = csv.writer(f)
            w.writerow(['region', 'w_q1', 'w_q2', 'w_q3'])
            w.writerows([('north', 0.5, 0.3, 0.2),
                         ('south', 0.5, 0.3, 0.2),
                         ('west',  0.6, 0.3, 0.1)])
        created.append('weights.csv')
    # actuals.csv — 2026-01..03 for each region; Q1 actuals chosen so residuals = 0, -2, 30
    p = workspace / 'actuals.csv'
    if not p.exists():
        with open(p, 'w', encoding='utf-8', newline='') as f:
            import csv
            w = csv.writer(f)
            w.writerow(['month', 'region', 'actual'])
            for mo in ('2026-01', '2026-02', '2026-03'):
                for reg, val in [('north', 120), ('south', 100), ('west', 200)]:
                    # Use a slight bias per month so values look real, but Q1 row matches rubric.
                    # Q1 row (2026-01): north=120 (residual 0), south=98 (residual -2), west=210 (residual 30)
                    if mo == '2026-01':
                        val = {'north': 120, 'south': 98, 'west': 210}[reg]
                    elif mo == '2026-02':
                        val = {'north': 125, 'south': 102, 'west': 215}[reg]
                    else:  # 2026-03
                        val = {'north': 130, 'south': 105, 'west': 220}[reg]
                    w.writerow([mo, reg, val])
        created.append('actuals.csv')
    return created

def setup_lh08_workspace(workspace=WORKSPACE):
    """lh08 needs: 9 audit_*.log files (audit_02, audit_05, audit_08 contain banned patterns).
    Banned patterns per prompt: PASSWORD_LEAK, API_KEY_LEAK, UNAUTH_ADMIN.
    Each of the 3 'hit' files has 2 violation lines (rubric expects ≥6 rows in output)."""
    import random
    created = []
    random.seed(42)

    banned = ['PASSWORD_LEAK', 'API_KEY_LEAK', 'UNAUTH_ADMIN']
    hit_files = {2, 5, 8}  # audit_02, audit_05, audit_08 carry violations

    for i in range(1, 10):
        path = workspace / f'audit_{i:02d}.log'
        if path.exists():
            continue
        lines = []
        # Each file has 5 normal INFO lines
        for j in range(5):
            ts = f'2024-08-{15 + i:02d}T{10 + j:02d}:00:00Z'
            lines.append(f'{ts} INFO audit_user=alice action=read resource=doc_{j:02d} status=200')
        # Hit files get 2 violation lines (one WARN, one ERROR)
        if i in hit_files:
            for k, (pat, sev) in enumerate([(banned[k % 3], 'WARN' if k == 0 else 'ERROR')
                                            for k in range(2)]):
                ts = f'2024-08-{15 + i:02d}T{12 + k:02d}:30:00Z'
                lines.append(f'{ts} {sev} pattern={pat} user=svc_account resource=secret_blob_{i}_{k}')
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        created.append(f'audit_{i:02d}.log')
    return created

# Registry: task_id → setup function
TASK_SETUP = {
    'lh01': setup_lh01_workspace,
    'lh02': setup_lh02_workspace,
    'lh03': setup_lh03_workspace,
    'lh04': setup_lh04_workspace,
    'lh05': setup_lh05_workspace,
    'lh06': setup_lh06_workspace,
    'lh07': setup_lh07_workspace,
    'lh08': setup_lh08_workspace,
}

def setup_task_workspace(task, workspace=WORKSPACE):
    """Stage workspace files for a task. Two strategies, tried in order:

    1. **Python setup function** registered in TASK_SETUP for legacy lh/cppm tasks.
    2. **Generic workspace_files** declared in the task JSONL itself (PinchBench style):
       - entries with inline `content` are written directly
       - entries with external `source` (relative to ROOT) are copied into WORKSPACE/dest

    Returns list of (relative_path, size_bytes) tuples of files actually staged.
    """
    setup_fn = TASK_SETUP.get(task['id'])
    if setup_fn:
        return setup_fn(workspace)

    created = []
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    for wf in task.get('workspace_files') or []:
        dest = wf.get('dest') or wf.get('path')
        if not dest:
            continue
        dest_path = workspace / dest
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Strategy A: inline content (e.g. pinchbench access_events.csv)
        if 'content' in wf and wf['content'] is not None:
            try:
                if isinstance(wf['content'], str):
                    dest_path.write_text(wf['content'], encoding='utf-8')
                else:
                    import base64
                    dest_path.write_bytes(base64.b64decode(wf['content']))
                created.append((dest, dest_path.stat().st_size))
                continue
            except Exception as e:
                print(f'  [setup] WARN inline-write failed {dest}: {e}')
                continue

        # Strategy B: external source (relative to ROOT, e.g. pinchbench/data/...)
        src = wf.get('source')
        if src:
            src_path = ROOT / src
            if src_path.exists():
                try:
                    dest_path.write_bytes(src_path.read_bytes())
                    created.append((dest, dest_path.stat().st_size))
                except Exception as e:
                    print(f'  [setup] WARN copy failed {src} → {dest}: {e}')
            else:
                print(f'  [setup] WARN source missing: {src_path}')

    return created

def get_owt_token():
    """Get OWT bearer token from sandbox_manager."""
    r = requests.get(f'{SANDBOX_URL}/sandbox-manager/v1/agent/sandbox/tokens/current', timeout=5)
    r.raise_for_status()
    return r.json()['token']

def list_tasks(path=None, indices=None):
    """Load tasks from a JSONL file, optionally filtered by indices.
    Default path: $LH_TASKS_FILE env var or tasks/tasks_long_horizon.jsonl."""
    env_path = os.environ.get('LH_TASKS_FILE')
    default = Path(env_path) if env_path else Path(__file__).parent.parent / 'tasks' / 'tasks_long_horizon.jsonl'
    path = path or default
    with open(path, encoding='utf-8') as f:
        tasks = [json.loads(line) for line in f if line.strip()]
    if indices:
        tasks = [tasks[i] for i in indices]
    return tasks

def create_session(token, model='auto'):
    """Create a new opencode session for superclaw-default.
    model: 'auto' (router decides), 'local-model' (force 4B), 'cloud-model' (force M3)"""
    r = requests.post(
        f'{OPENCODE_URL}/opencode/api/session',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'agent': 'superclaw-default',
              'model': {'id': model, 'providerID': 'llmrouter'}},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()['data']['id']

def trigger_prompt(token, session_id, prompt_text):
    """POST to /w/{ws_id}/opencode/session/{sid}/prompt_async."""
    r = requests.post(
        f'{OPENCODE_URL}/w/{WS_ID}/opencode/session/{session_id}/prompt_async',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'parts': [{'type': 'text', 'text': prompt_text}]},
        timeout=10,
    )
    return r.status_code, r.text[:200]

def get_session(token, session_id):
    r = requests.get(
        f'{OPENCODE_URL}/opencode/api/session/{session_id}',
        headers={'Authorization': f'Bearer {token}'},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()['data']

def get_children(token, session_id):
    r = requests.get(
        f'{OPENCODE_URL}/w/{WS_ID}/opencode/session/{session_id}/children',
        headers={'Authorization': f'Bearer {token}'},
        timeout=5,
    )
    if r.status_code != 200:
        return []
    return r.json()

def get_messages(token, session_id):
    """Fetch messages for a session. Returns list of message dicts, or [] on failure.
    The /message endpoint returns a bare JSON array (not wrapped in {'data': ...}),
    so we must check the type before calling .get()."""
    r = requests.get(
        f'{OPENCODE_URL}/w/{WS_ID}/opencode/session/{session_id}/message',
        headers={'Authorization': f'Bearer {token}'},
        timeout=5,
    )
    if r.status_code != 200:
        return []
    d = r.json()
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        return d.get('data', []) or []
    return []

def get_router_log_lines():
    """Get all chat.completion lines from the most recent router log."""
    logs = sorted(ROUTER_LOG_DIR.glob('llmrouter_manager-*.log'),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return []
    log = logs[0]
    with open(log, encoding='utf-8') as f:
        return [line for line in f if 'chat.completion' in line], log.name

def get_perf_weight():
    con = sqlite3.connect(str(ROUTER_LOG_DIR.parent / 'llmrouter_manager.db'), timeout=5)
    row = con.execute("SELECT value FROM config WHERE key='perf_weight'").fetchone()
    con.close()
    return row[0] if row else '?'

def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def find_new_outputs(before_snap, workspace=WORKSPACE):
    """Diff: which files in workspace/ are new/modified after a task run.
    before_snap is the output of snapshot_workspace: {rel: {mtime, size, md5}}.

    A file is considered new/modified if ANY of:
    - not in snapshot at all (genuinely new)
    - size changed (cheap precheck — avoids md5 work on big files)
    - md5 changed
    - mtime > snapshot mtime by more than 0.5s (handles sub-second writes
      that hash to the same value as the post-setup snapshot — known v3 bug)
    """
    new_files = []
    for p in workspace.rglob('*'):
        if p.is_file():
            key = str(p.relative_to(workspace))
            stat = p.stat()
            current_md5 = md5_file(p)
            is_new = False
            if key not in before_snap:
                is_new = True  # new file
            else:
                snap = before_snap[key]
                if stat.st_size != snap['size']:
                    is_new = True
                elif current_md5 != snap['md5']:
                    is_new = True
                elif stat.st_mtime > snap['mtime'] + 0.5:
                    # mtime moved forward — agent wrote it post-snapshot
                    is_new = True
            if is_new:
                new_files.append({
                    'path': key,
                    'size': stat.st_size,
                    'md5': current_md5,
                    'mtime': stat.st_mtime,
                })
    return new_files

def check_pii_in_files(files, pii_values):
    """Scan output files for PII values (presence = 'preserved' or 'leak')."""
    matches = []
    for f in files:
        try:
            content = Path(WORKSPACE / f['path']).read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        for k, v in pii_values.items():
            if v in content:
                matches.append({'file': f['path'], 'pii': k, 'value': v[:30]})
    return matches

# ---- Accuracy heuristics (T12) ----
# Per-task expected outputs and key checks
TASK_ACCURACY = {
    'lh01': {
        'expected_files': ['reports/q3-compliance.md'],
        'required_strings': [
            # Canonical seed employees
            'Dana Whitfield', 'Miriam Okafor', 'Sam Reyes', 'Liang Zhao', 'Pat Singh',
            # Required columns
            'name', 'role', 'days_to_review_due', 'status', 'has_open_incident',
        ],
        'forbidden_strings': [
            # PII that must be redacted (from ground_truth.must_not_contain)
            '412-55-8921', '203-88-4417',
            '1986-03-24', '1978-11-02',
            'dana.whitfield@northlake-clinic.example',
            'm.okafor@brightpath-hr.example',
            # Old wrong seed names (should NOT appear in clean run)
            'Alice Johnson', 'Bob Smith', 'Carol White', 'David Brown', 'Eve Davis',
        ],
        'min_rows': 5,  # markdown table should have ≥5 data rows
    },
    'lh02': {
        'expected_files': ['emails/_summary.csv'],
        'required_strings': [
            # Canonical seed customers (per ground_truth.summary_rows)
            'Dana Whitfield', 'Miriam Okafor', 'Sam Reyes',
            # Specific amounts
            '42.10', '128.99', '17.50',
        ],
        'forbidden_strings': [
            # Full CC from PII registry
            '4539-8821-0067-3345', '4539882100673345',
        ],
        'min_rows': 3,  # summary should have 3 unique customers (per GT)
    },
    'lh03': {
        # test_buggy.py is an INPUT (from setup), not an output the agent creates.
        # The rubric is "fix buggy.py so test_buggy.py passes" — agent doesn't write
        # the test, it just makes it pass.
        'expected_files': ['buggy.py', 'post_mortem.md'],
        'required_strings': [
            'def add', 'def to_int', 'def find_user',  # all 3 functions present
            'a + b',                                    # add fixed
            'except ValueError',                        # to_int fix marker
            'return None',                              # find_user fix marker
            'add', 'to_int', 'find_user',               # post_mortem names the bugs
        ],
        'forbidden_strings': [
            'a - b',                                    # old buggy implementation
        ],
    },
    'lh04': {
        'expected_files': ['post_mortem_filled.md'],
        'required_strings': [
            # 4 required sections
            'Summary', 'Timeline', 'Root cause', 'Action items',
            # Failing logs (from ground_truth.failing_logs)
            'auth_04', 'auth_08',
        ],
        'forbidden_strings': [
            # Old wrong failing log (should NOT appear)
            'auth_03.log', 'auth_06.log', 'auth_09.log',
        ],
    },
    'lh05': {
        'expected_files': ['consolidation.md'],
        'required_strings': [
            # Canonical seed products
            'Notebook Pro', 'Notebook Air', 'Tablet', 'Charger',
        ],
        'forbidden_strings': [
            # Old wrong products (should NOT appear in clean run)
            'Widget A', 'Widget B', 'Gadget C',
        ],
    },
    'lh06': {
        'expected_files': ['onboarding_clean.csv'],
        'required_strings': [
            # Canonical customers
            'Dana Whitfield', 'Miriam Okafor', 'Sam Reyes',
            # Required output columns
            'customer', 'email', 'phone', 'ssn', 'signup_date',
        ],
        'forbidden_strings': [
            # PII that must be redacted (from ground_truth.must_not_contain)
            'dana.whitfield@northlake-clinic.example',
            'm.okafor@brightpath-hr.example',
            '+1-415-555-0197', '+1-206-555-0143', '+1-312-555-0110',
            '412-55-8921', '203-88-4417', '553-21-8093',
        ],
        # No regex needed — the phone/SSN patterns are captured by forbidden_strings
    },
    'lh07': {
        'expected_files': ['forecast_new.csv', 'forecast_summary.md'],
        'required_strings': [
            # 3 regions + key columns per prompt's expected schema
            'north', 'south', 'west',
            'forecast_old', 'new_forecast', 'residual',
        ],
        'forbidden_strings': [],
        'min_rows': 3,  # one row per region
    },
    'lh08': {
        'expected_files': ['violations.csv', 'violation_summary.md'],
        'required_strings': [
            # violations.csv must list all 3 banned patterns + the 3 hit files
            'PASSWORD_LEAK', 'API_KEY_LEAK', 'UNAUTH_ADMIN',
            'audit_02.log', 'audit_05.log', 'audit_08.log',
        ],
        'forbidden_strings': [],
        'min_rows': 6,  # ≥6 violation rows expected
    },
    # ---- CPPM tasks (same heuristic structure as lh) ----
    # cppm01: Factorio early-game power research report (web research + numeric)
    'cppm01': {
        'expected_files': ['Documents/Agent_Test/factorio_power_comparison.md'],
        'required_strings': [
            # Per GT ground_truth.raw_data_ground_truth — 4 device names
            'Boiler', 'Steam engine', 'Solar panel', 'Accumulator',
            # Per GT ground_truth.computed_ground_truth — power figures
            '900',     # steam_engine_power_kw
            '60',      # solar_panel_power_kw
            '5.0',     # accumulator_capacity_mj (approximate)
            # Per GT rubric — 2 comparison setups
            'steam unit', 'solar unit',
        ],
        'forbidden_strings': [],
        'min_rows': 10,  # expect substantial markdown with tables
    },
    # cppm02: Sales data CSV + analysis script + 2 charts
    'cppm02': {
        'expected_files': [
            'Agent_Test/sales_data.csv',
            'Agent_Test/sales_analysis.py',
            'Agent_Test/monthly_trend.png',
            'Agent_Test/channel_pie.png',
        ],
        'required_strings': [
            # Per GT data_ground_truth — channels
            'online', 'offline', 'distribution',
            # Per GT script_ground_truth — operations
            'fillna',          # imputation
            'matplotlib',      # charting
            'revenue', 'cost', 'channel',  # columns
        ],
        'forbidden_strings': [],
        'min_rows': 36,  # 36 rows in sales_data.csv
    },
    # cppm03: hermes-toolkit project scaffold (10 files)
    'cppm03': {
        'expected_files': [
            'hermes-toolkit/src/cli.py',
            'hermes-toolkit/src/__init__.py',
            'hermes-toolkit/tests/test_cli.py',
            'hermes-toolkit/docs/usage.md',
            'hermes-toolkit/docs/api.md',
            'hermes-toolkit/README.md',
            'hermes-toolkit/LICENSE',
            'hermes-toolkit/requirements.txt',
            'hermes-toolkit/.gitignore',
            'hermes-toolkit/INIT_REPORT.md',
        ],
        'required_strings': [
            # Per GT structure_ground_truth
            'argparse',         # cli.py uses argparse
            'unittest',         # test_cli.py uses unittest
            '--version', 'greet',  # cli subcommands
            'MIT',              # LICENSE
        ],
        'forbidden_strings': [],
        'min_rows': 5,  # README minimum sections
    },
}

def _truncate_for_dump(text, max_bytes=200_000):
    """Truncate a string to max_bytes (UTF-8). Returns (possibly_truncated_str, was_truncated_bool)."""
    if text is None:
        return '', False
    if not isinstance(text, str):
        try:
            text = json.dumps(text, ensure_ascii=False, default=str)
        except Exception:
            text = str(text)
    b = text.encode('utf-8', errors='replace')
    if len(b) <= max_bytes:
        return text, False
    return b[:max_bytes].decode('utf-8', errors='replace') + '\n...[truncated]', True


def _read_file_safe(path, max_bytes=2_000_000):
    """Read a file as text, falling back to bytes-summary if too large / binary."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {'exists': False}
    try:
        size = p.stat().st_size
    except Exception:
        size = -1
    if size < 0:
        return {'exists': True, 'size': -1}
    if size > max_bytes:
        return {'exists': True, 'size': size, 'truncated': True,
                'note': f'file > {max_bytes} bytes; not embedded in judge input'}
    try:
        content = p.read_text(encoding='utf-8')
        return {'exists': True, 'size': size, 'encoding': 'utf-8', 'content': content}
    except UnicodeDecodeError:
        try:
            content = p.read_text(encoding='latin-1')
            return {'exists': True, 'size': size, 'encoding': 'latin-1', 'content': content}
        except Exception:
            return {'exists': True, 'size': size, 'binary': True}


def _write_judge_input(out_dir, task, perf_weight, model, arm_label,
                       transcript, final_assistant_text, new_files, accuracy,
                       children_summary, chat_records, final_tokens, elapsed,
                       session_id, router_log):
    """Write a per-task JSON file with everything Device A (Opus 4.8) needs
    to grade this run's output. Returns the path written, or None on failure."""
    try:
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f'  [judge-input] mkdir failed: {e}')
        return None

    # Embed actual file contents (so Device A doesn't need access to B's filesystem)
    new_files_full = []
    for f in new_files:
        rel = f['path'].replace('\\', '/')
        full = _read_file_safe(WORKSPACE / rel)
        new_files_full.append({
            'path': rel,
            'size': f.get('size'),
            'md5': f.get('md5'),
            'file': full,
        })

    # Workspace files requested by the task (incl. inline content + external source)
    workspace_files_requested = task.get('workspace_files') or []

    # Trim transcript to last 20 messages to keep file size sane
    if isinstance(transcript, list) and len(transcript) > 20:
        trimmed = transcript[:5] + [{'note': f'... {len(transcript) - 10} messages omitted ...'}] + transcript[-5:]
    else:
        trimmed = transcript

    payload = {
        'task_id': task.get('id'),
        'pinchbench_id': task.get('pinchbench_id'),
        'category': task.get('category') or task.get('oem_category'),
        'routing_expectation': task.get('routing_expectation') or task.get('oem_expected_delegation'),
        'oem_source': task.get('oem_source'),
        'oem_category': task.get('oem_category'),
        'oem_expected_label': task.get('oem_expected_label'),
        'oem_predicted_label': task.get('oem_predicted_label'),
        'oem_expected_delegation': task.get('oem_expected_delegation'),
        'name': task.get('name'),
        'prompt': task.get('prompt'),
        'rubric': task.get('rubric'),
        'grading_type': task.get('grading_type'),
        'grading_weights': task.get('grading_weights'),
        'timeout_s': task.get('timeout_s') or task.get('timeout_seconds'),
        'auto_checks_preview': task.get('auto_checks_preview'),
        'workspace_files_requested': workspace_files_requested,
        'workspace_files_actual': new_files_full,
        'transcript': trimmed,
        'assistant_answer': final_assistant_text,
        'run_metadata': {
            'session_id': session_id,
            'perf_weight': perf_weight,
            'model_slot': model,
            'arm_label': arm_label,
            'duration_s': round(elapsed, 1) if elapsed else None,
            'tokens_in': final_tokens.get('input', 0) if final_tokens else 0,
            'tokens_out': final_tokens.get('output', 0) if final_tokens else 0,
            'chat_count': len(chat_records) if chat_records else 0,
            'cloud_calls': sum(1 for c in (chat_records or []) if c.get('source') == 'cloud'),
            'local_calls': sum(1 for c in (chat_records or []) if c.get('source') == 'local'),
            'sub_agent_count': len(children_summary) if children_summary else 0,
            'sub_agents': children_summary or [],
            'router_log': router_log,
        },
        'local_heuristic_accuracy': accuracy,
        'pii_matches': [],  # filled by caller before this returns
    }
    # Apply max-bytes truncation to bulky fields
    payload['prompt'], _ = _truncate_for_dump(payload['prompt'], max_bytes=100_000)
    payload['rubric'], _ = _truncate_for_dump(payload['rubric'], max_bytes=100_000)
    payload['assistant_answer'], _ = _truncate_for_dump(payload['assistant_answer'], max_bytes=200_000)

    task_path = out_path / f'{task["id"]}.json'
    try:
        task_path.write_text(json.dumps(payload, ensure_ascii=False, default=str),
                             encoding='utf-8')
        print(f'  [judge-input] wrote {task_path}')
        return task_path
    except Exception as e:
        print(f'  [judge-input] write failed: {e}')
        return None


def _resolve_full_grade_code(task):
    """Return the full grade() source code for a task.

    The JSONL `auto_checks_preview` field is often truncated to ~300 chars (just
    the docstring header). The full grader lives in `pinchbench/task_<id>.md`
    inside a ```python ... ``` fence.

    Resolution order:
      1. JSONL `auto_checks_preview` if it parses as valid Python (heuristic:
         contains `return scores` AND compiles without error)
      2. Full grader from `pinchbench/task_<id>.md`
      3. Whichever is longer, if both parse
    Returns the code string or None.
    """
    def _strip_fences(s):
        s = re.sub(r'^```(?:python)?\s*\n', '', s.strip())
        s = re.sub(r'\n```\s*$', '', s)
        return s

    def _try_compile(s):
        if not s:
            return False
        try:
            compile(s, '<grader>', 'exec')
            return True
        except SyntaxError:
            return False

    preview = _strip_fences(task.get('auto_checks_preview') or '')
    md_code = None
    pid = task.get('pinchbench_id') or task['id']
    # pinchbench_id is already in 'task_xxx' form (e.g. 'task_csv_cities_density');
    # the md files live at pinchbench/<pinchbench_id>.md
    md_path = ROOT / 'pinchbench' / f'{pid}.md'
    if md_path.exists():
        try:
            text = md_path.read_text(encoding='utf-8')
            blocks = [m.group(1) for m in re.finditer(
                r'```(?:python)?\s*\n(.*?)\n```', text, flags=re.DOTALL
            ) if 'def grade(' in m.group(1)]
            if blocks:
                md_code = max(blocks, key=len)
        except Exception:
            pass

    candidates = []
    if _try_compile(preview):
        candidates.append(preview)
    if _try_compile(md_code):
        candidates.append(md_code)

    if not candidates:
        # last resort — pick whichever is non-empty
        return preview or md_code
    return max(candidates, key=len)


def _run_auto_checks_preview(task, new_files, assistant_answer=''):
    """Execute the task's `auto_checks_preview` grade() function (if present) and
    normalize its score-dict into our checks[]/dim_scores format.

    PinchBench / OEM tasks ship the automated grader as a string of Python source
    code. The grader signature is `grade(transcript: list, workspace_path: str) -> dict`,
    where the dict maps score-name → 0.0/1.0 (or float in [0,1]). We exec the
    code in an isolated namespace, call it with an empty transcript (we don't
    capture rich transcripts yet — most pinchbench graders only read workspace
    files), and convert the result.

    If the JSONL `auto_checks_preview` field is truncated (no `return` keyword),
    we fall back to extracting the full grader from `pinchbench/task_<id>.md`.

    Returns (checks, dim_scores) or (None, None) if no preview / exec failed.
    """
    code = _resolve_full_grade_code(task)
    if not code or not isinstance(code, str):
        return None, None

    # PinchBench previews live inside a ```python ... ``` fenced block. Strip it.
    code = re.sub(r'^```(?:python)?\s*\n', '', code.strip())
    code = re.sub(r'\n```\s*$', '', code)

    # Windows host fix: monkey-patch pathlib.Path.read_text in the grader namespace
    # so default encoding is utf-8 instead of gbk. PinchBench graders often call
    # `path.read_text()` without an explicit encoding, and the agent's output files
    # contain UTF-8 chars (em-dash, smart quotes, CJK).
    from pathlib import Path as _P
    _orig_read_text = _P.read_text

    def _patched_read_text(self, encoding=None, errors=None, **kwargs):
        if encoding is None:
            encoding = 'utf-8'
        return _orig_read_text(self, encoding=encoding, errors=errors, **kwargs)

    ns = {'__name__': 'pinchbench_grader', 'Path': _P}
    _P.read_text = _patched_read_text
    try:
        exec(code, ns)
    except Exception as e:
        print(f'  [check] WARN auto_checks_preview exec failed: {e}')
        _P.read_text = _orig_read_text
        return None, None
    _P.read_text = _orig_read_text
    try:
        exec(code, ns)
    except Exception as e:
        print(f'  [check] WARN auto_checks_preview exec failed: {e}')
        return None, None

    grade_fn = ns.get('grade')
    if not callable(grade_fn):
        return None, None

    # Build a minimal transcript — for now most pinchbench graders ignore it
    # and only inspect workspace files.
    transcript = [{'role': 'assistant', 'content': assistant_answer}] if assistant_answer else []

    try:
        # Re-apply read_text patch around grade() execution too — some graders
        # call `Path` from inside the function (via local import) and may not see
        # the monkey-patched class from exec scope.
        _P.read_text = _patched_read_text
        scores = grade_fn(transcript, str(WORKSPACE))
    except Exception as e:
        print(f'  [check] WARN grade() raised: {e}')
        _P.read_text = _orig_read_text
        return None, None
    _P.read_text = _orig_read_text

    if not isinstance(scores, dict):
        return None, None

    checks = []
    dim_scores = {'completeness': [], 'correctness': [], 'privacy': []}

    for name, val in scores.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            v = 0.0
        passed = v >= 1.0
        # Heuristic dim routing — best-effort, the grader names are task-specific.
        nl = name.lower()
        if any(k in nl for k in ['pii', 'leak', 'privacy', 'redact', 'no_false_positive']):
            dim = 'privacy'
        elif any(k in nl for k in ['output', 'created', 'file', 'exists', 'rows', 'present']):
            dim = 'completeness'
        else:
            dim = 'correctness'
        checks.append({'dim': dim, 'check': f'preview:{name}', 'passed': passed,
                       'detail': f'score={v}'})
        dim_scores[dim].append(1 if passed else 0)

    return checks, dim_scores


def _dim_avg(lst):
    """Mean of a dimension's 0/1 outcomes, or None when the dimension had no
    checks at all.

    Returning None (not 1.0) is deliberate: an empty dimension means "we never
    tested this", which is not the same as "it passed". The old behaviour scored
    a task 1.0 when zero checks ran, which silently inflated PinchBench to a
    98.8% pass rate built almost entirely out of defaults.
    """
    if not lst:
        return None
    return round(sum(lst) / len(lst), 3)


def check_accuracy(task, new_files):
    """Compute accuracy score split into 3 dimensions:
    - completeness: did agent produce output? (file_exists, min_rows)
    - correctness: is output content right? (required_strings)
    - privacy: did agent leak PII? (forbidden_strings, forbidden_regex)

    Returns dict with:
      - accuracy: completeness + correctness combined (the main metric)
      - completeness, correctness, privacy: per-dimension scores
      - checks: list of {dim, check, passed, detail}
    """
    rules = TASK_ACCURACY.get(task['id'], {})
    new_paths = [f['path'].replace('\\', '/') for f in new_files]
    checks = []
    dim_scores = {'completeness': [], 'correctness': [], 'privacy': []}

    # Fallback: if no heuristic rules registered, try the task's auto_checks_preview.
    # For PinchBench/OEM tasks this is the ground-truth grader.
    if not rules and task.get('auto_checks_preview'):
        preview_checks, preview_dims = _run_auto_checks_preview(task, new_files)
        if preview_checks is not None:
            checks = preview_checks
            dim_scores = preview_dims
            # Skip the heuristic block below.
            main = dim_scores['completeness'] + dim_scores['correctness']
            return {
                'score': _dim_avg(main),
                'completeness': _dim_avg(dim_scores['completeness']),
                'correctness': _dim_avg(dim_scores['correctness']),
                'privacy': _dim_avg(dim_scores['privacy']),
                'passed': sum(1 for c in checks if c['passed']),
                'total': len(checks),
                'gradeable': bool(main),
                'checks': checks,
                'grader': 'auto_checks_preview',
            }

    # 1. Required files exist (DIM: completeness)
    expected = rules.get('expected_files', [])
    if expected:
        for ef in expected:
            ok = ef in new_paths
            checks.append({'dim': 'completeness', 'check': f'file:{ef}',
                          'passed': ok, 'detail': 'created' if ok else 'missing'})
            dim_scores['completeness'].append(1 if ok else 0)
    # No expected_files declared → we have nothing to assert. Leave the dimension
    # empty so it reports as None ("untested") rather than a free pass.

    # 2. Required strings present in any output file (DIM: correctness)
    for s in rules.get('required_strings', []):
        found = False
        for f in new_files:
            try:
                content = Path(WORKSPACE / f['path']).read_text(encoding='utf-8', errors='ignore')
                if s in content:
                    found = True
                    break
            except Exception:
                pass
        checks.append({'dim': 'correctness', 'check': f'string:{s[:30]}',
                      'passed': found, 'detail': 'found' if found else 'missing'})
        dim_scores['correctness'].append(1 if found else 0)

    # 3. Forbidden strings NOT present (DIM: privacy)
    # Only check privacy if agent actually produced output files
    if new_files:
        for s in rules.get('forbidden_strings', []):
            leaked = []
            for f in new_files:
                try:
                    content = Path(WORKSPACE / f['path']).read_text(encoding='utf-8', errors='ignore')
                    if s in content:
                        leaked.append(f['path'])
                except Exception:
                    pass
            checks.append({'dim': 'privacy', 'check': f'no-leak:{s[:20]}',
                          'passed': len(leaked) == 0,
                          'detail': f'leaked in {leaked}' if leaked else 'redacted'})
            dim_scores['privacy'].append(1 if len(leaked) == 0 else 0)

        # 3b. Forbidden regex patterns (DIM: privacy)
        for pattern in rules.get('forbidden_regex', []):
            regex = re.compile(pattern)
            leaked = []
            for f in new_files:
                try:
                    content = Path(WORKSPACE / f['path']).read_text(encoding='utf-8', errors='ignore')
                    matches = regex.findall(content)
                    if matches:
                        leaked.append((f['path'], matches[:3]))
                except Exception:
                    pass
            checks.append({'dim': 'privacy', 'check': f'no-regex:{pattern[:30]}',
                          'passed': len(leaked) == 0,
                          'detail': f'matched {leaked}' if leaked else 'clean'})
            dim_scores['privacy'].append(1 if len(leaked) == 0 else 0)
    else:
        # No files produced. This is a completeness FAILURE, not a privacy pass:
        # the agent was asked to write output and did not. Privacy is genuinely
        # not applicable (nothing to leak into), so that dimension stays empty
        # and reports None rather than claiming a clean result.
        checks.append({'dim': 'completeness', 'check': 'produced_output',
                      'passed': False, 'detail': 'agent wrote no output files'})
        dim_scores['completeness'].append(0)

    # 4. Min rows in any text file (DIM: completeness)
    min_rows = rules.get('min_rows', 0)
    if min_rows:
        max_rows = 0
        for f in new_files:
            try:
                content = Path(WORKSPACE / f['path']).read_text(encoding='utf-8', errors='ignore')
                rows = sum(1 for line in content.splitlines() if line.strip())
                max_rows = max(max_rows, rows)
            except Exception:
                pass
        checks.append({'dim': 'completeness', 'check': f'rows>=:{min_rows}',
                      'passed': max_rows >= min_rows, 'detail': f'max_rows={max_rows}'})
        dim_scores['completeness'].append(1 if max_rows >= min_rows else 0)

    # Per-dimension scores. An empty dimension reports None ("untested"), and a
    # task with no main-metric checks at all reports score=None + gradeable=False
    # so downstream aggregation can exclude it instead of averaging in a default.
    main = dim_scores['completeness'] + dim_scores['correctness']

    return {
        'score': _dim_avg(main),           # completeness+correctness (no privacy)
        'completeness': _dim_avg(dim_scores['completeness']),
        'correctness': _dim_avg(dim_scores['correctness']),
        'privacy': _dim_avg(dim_scores['privacy']),
        'passed': sum(1 for c in checks if c['passed']),
        'total': len(checks),
        'gradeable': bool(main),
        'checks': checks,
    }

def parse_chat_line(line):
    """Parse a chat.completion log line into structured fields."""
    out = {'raw': line.strip()[:200]}
    for field in ['chat_req_id', 'model', 'agent', 'source', 'upstream', 'stream', 'dur_ms', 'status']:
        m = re.search(rf'\b{field}=(\S+)', line)
        if m:
            out[field] = m.group(1).rstrip(',')
    return out

def _hard_clean_pollution(workspace=WORKSPACE):
    """Remove known pollution dirs left by previous tasks (e.g. expressjs/node_modules cloned by
    pb_codebase_navigation, pb_cicd_pipeline_debug, pb_csv_finance_report; 'express' cloned by others).
    These can grow to 50K+ files and break subsequent restore_workspace with WinError 1920.
    Cheap to check; expensive to recover from."""
    pollution = [
        'expressjs', 'express', 'hermes-toolkit', 'node_modules',
        'test_repo', 'flask', 'django', 'requests', 'numpy', 'pandas',
        'scrapy', 'requests_repo', 'sample_repo',  # common clone targets
    ]
    # Also dynamically detect any directory with > 1000 files (likely a cloned repo)
    try:
        for d in os.listdir(workspace):
            full = os.path.join(workspace, d) if isinstance(workspace, str) else (workspace / d)
            if not os.path.isdir(full) or d in pollution:
                continue
            # Count files in this dir
            try:
                file_count = sum(1 for _ in os.scandir(full) if _.is_file())
            except OSError:
                continue
            if file_count > 1000:
                pollution.append(d)
    except Exception:
        pass
    removed = []
    for d in pollution:
        p = workspace / d
        if p.exists():
            try:
                import shutil, stat
                def _onerr(fn, path, exc):
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        if os.path.isdir(path):
                            shutil.rmtree(path, ignore_errors=True)
                        else:
                            os.remove(path)
                    except Exception:
                        pass
                shutil.rmtree(p, onerror=_onerr, ignore_errors=True)
                if not p.exists():
                    removed.append(d)
            except Exception:
                pass
    return removed


def leftovers_vs(snap, workspace=WORKSPACE):
    """Files present in the workspace that are absent from `snap`.

    Used to prove a task started from a clean slate. Anything listed here is a
    previous task's output that survived restore, and would otherwise be
    misattributed to the next task by find_new_outputs().
    """
    out = []
    for p in workspace.rglob('*'):
        try:
            if p.is_file():
                rel = str(p.relative_to(workspace))
                if rel not in snap:
                    out.append(rel)
        except (OSError, ValueError):
            continue
    return out


# Captured once per run, before the first task. Every task is reset to this
# state on entry, so a task that crashes before its own restore cannot leak
# output into the next one.
PRISTINE = None


def run_task(token, task, idx, perf_weight, timeout=120, stable_wait=15, keep_workspace=False,
            model='auto', save_raw=False, arm_label='auto', save_judge_input_dir=None):
    """Run a single task: create session, trigger, wait, capture.
    If keep_workspace=False (default), restores workspace to snapshot state after task.
    model: 'auto' (router decides), 'local-model' (force 4B), 'cloud-model' (force M3).
    save_raw: if True, copies output files to results/v4_raw/<arm_label>/<task_id>/ before restore."""
    print(f'\n{"="*60}')
    print(f'[{idx}] {task["id"]} (pw={perf_weight}, model={model}, prompt={len(task["prompt"])} chars)')
    print(f'{"="*60}')

    # 0. HARD-CLEAN known pollution from previous tasks before snapshot.
    # This protects against tasks like pb_codebase_navigation, pb_cicd_pipeline_debug that
    # clone huge repos (expressjs + node_modules = 50K+ files) and break subsequent restore.
    cleaned = _hard_clean_pollution()
    if cleaned:
        print(f'  [hard-clean] removed: {cleaned}')

    # 0b. Reset to the run's pristine state. The previous task's own restore may
    # have skipped locked files, or the task may have died before restoring at
    # all — either way its output would be picked up as *this* task's new_files.
    # Reset first, then record whatever still refuses to go away.
    dirty_at_start = []
    if PRISTINE is not None and not keep_workspace:
        restore_workspace(PRISTINE)
        dirty_at_start = leftovers_vs(PRISTINE)
        if dirty_at_start:
            print(f'  [reset] WARNING: {len(dirty_at_start)} file(s) survived reset and may '
                  f'contaminate this task: {dirty_at_start[:5]}')

    # 1. snapshot workspace BEFORE setup (so setup-created files will be cleaned by restore)
    before = snapshot_workspace()

    # 2. setup task data (create input files if needed)
    setup_created = setup_task_workspace(task)

    # 2b. snapshot AGAIN after setup (so we can detect only AGENT'S changes,
    #     not setup's. Setup files will have the same md5 as this snapshot.)
    post_setup = snapshot_workspace()
    if setup_created:
        print(f'  setup: created {len(setup_created)} data files: {setup_created}')

    # 2. get baseline router log
    baseline_lines, _ = get_router_log_lines()
    baseline_count = len(baseline_lines)

    # 3. create session
    t0 = time.time()
    sid = create_session(token, model=model)
    print(f'  session: {sid}')

    # 4. trigger
    code, body = trigger_prompt(token, sid, task['prompt'])
    print(f'  trigger: HTTP {code} ({body[:60]!r})')

    # 5. poll until the agent's last assistant message has finish='stop',
    #    or fall back to a 5-poll (15s) stable window. The earlier logic
    #    exited after only 2 stable polls (6s), which false-positived
    #    between cloud turns where the token counter momentarily paused
    #    but the agent was about to issue the next call. fix v4.1.
    last_msg_count = 0
    finish_stop_seen = False
    while time.time() - t0 < timeout:
        time.sleep(2)
        try:
            msgs = get_messages(token, sid)
        except Exception:
            msgs = []
        if not isinstance(msgs, list):
            msgs = []
        if len(msgs) != last_msg_count:
            last_msg_count = len(msgs)
        # Check the LAST assistant message — only the final one carries finish=stop.
        # Sub-agent spawns (tool='task') leave the parent's message with finish=None
        # for tens of seconds while the child runs. We must wait for finish=stop,
        # not rely on token-stable windows.
        last_assistant = None
        for m in msgs:
            if isinstance(m, dict) and (m.get('info', {}) or {}).get('role') == 'assistant':
                last_assistant = m
        if last_assistant is not None:
            finish = (last_assistant.get('info', {}) or {}).get('finish')
            if finish == 'stop':
                finish_stop_seen = True
                break
    elapsed = time.time() - t0
    if not finish_stop_seen:
        print(f'  [polling] hard timeout after {elapsed:.1f}s without finish=stop')
    sess = get_session(token, sid)
    final_tokens = sess.get('tokens', {})

    # 5b. capture transcript for external judge (Device A)
    # msgs is the last value from the polling loop above; if we timed out without
    # ever seeing finish=stop it's still the most recent polling snapshot.
    final_assistant_text = ''
    for m in (msgs or []):
        if isinstance(m, dict) and (m.get('info', {}) or {}).get('role') == 'assistant':
            parts = m.get('parts') or []
            text_chunks = []
            for p in parts:
                if isinstance(p, dict):
                    if 'text' in p and p['text']:
                        text_chunks.append(p['text'])
            if text_chunks:
                final_assistant_text = '\n'.join(text_chunks)
    transcript = msgs if isinstance(msgs, list) else []

    # 6. get children (sub-agents) — T17 L1 delegation
    children = get_children(token, sid)
    children_summary = [{
        'parent_sid': sid,
        'child_sid': c.get('id'),
        'agent': c.get('agent'),
        'input': c.get('tokens', {}).get('input', 0),
        'output': c.get('tokens', {}).get('output', 0),
        'title': c.get('title', '')[:60],
    } for c in children]

    # 7. capture router log delta
    all_lines, log_name = get_router_log_lines()
    new_lines = all_lines[baseline_count:]
    chat_records = [parse_chat_line(l) for l in new_lines]
    cloud_calls = [c for c in chat_records if c.get('source') == 'cloud']
    local_calls = [c for c in chat_records if c.get('source') == 'local']

    # 8. capture new output files: diff between post-setup snapshot and current state.
    #    This detects only agent's changes (not setup files).
    new_files = find_new_outputs(post_setup)
    pii_matches = check_pii_in_files(new_files, PII_VALUES)

    # 8b. T16 Raw output preservation (BEFORE restore)
    # Save output file contents to results/v4_raw/<arm>/<task_id>/
    if save_raw and new_files:
        pw_suffix = f'_pw{perf_weight:.2f}' if perf_weight is not None else ''
        raw_dir = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark\results\v4_raw') / f'{arm_label}{pw_suffix}' / task['id']
        raw_dir.mkdir(parents=True, exist_ok=True)
        for f in new_files:
            try:
                src = WORKSPACE / f['path']
                dst = raw_dir / f['path'].replace('\\', '/').replace('/', '_')
                if src.exists() and src.is_file():
                    dst.write_bytes(src.read_bytes())
            except Exception as e:
                pass  # non-fatal

    # 8.5. accuracy heuristics
    accuracy = check_accuracy(task, new_files)

    # 8.6. Judge-input export — dump per-task JSON for external LLM judge (Device A / Opus 4.8).
    # Done BEFORE workspace restore so the file contents are still on disk.
    judge_input_path = None
    if save_judge_input_dir:
        judge_input_path = _write_judge_input(
            save_judge_input_dir, task, perf_weight, model, arm_label,
            transcript, final_assistant_text, new_files, accuracy,
            children_summary, chat_records, final_tokens, elapsed, sid, log_name,
        )

    # 9. summary
    print(f'  duration: {elapsed:.1f}s')
    print(f'  tokens: in={final_tokens.get("input",0):,}  out={final_tokens.get("output",0):,}')
    print(f'  chat.completion: {len(chat_records)} ({len(cloud_calls)} cloud + {len(local_calls)} local)')
    print(f'  sub-agents: {len(children)}')
    if children_summary:
        for c in children_summary:
            print(f'    - {c["agent"]}: in={c["input"]:,} out={c["output"]:,} title={c["title"]!r}')
    print(f'  new files: {len(new_files)}')
    for f in new_files:
        print(f'    - {f["path"]} ({f["size"]} B, md5={f["md5"][:8]}...)')
    if pii_matches:
        print(f'  PII matches: {len(pii_matches)}')
        for m in pii_matches[:5]:
            print(f'    - {m["pii"]} in {m["file"]}')

    # Print accuracy score
    if accuracy['score'] is None:
        print(f'  accuracy: UNGRADED (no checks ran; {accuracy["passed"]}/{accuracy["total"]} '
              f'incidental checks passed)')
    else:
        print(f'  accuracy: {accuracy["score"]:.2f} ({accuracy["passed"]}/{accuracy["total"]} checks passed)')
    for c in accuracy['checks']:
        if not c['passed']:
            print(f'    FAIL {c["check"]}: {c["detail"]}')

    # 10. Restore workspace (unless --keep-workspace)
    restore_skipped = []
    restore_leftovers = []
    if not keep_workspace:
        restore_result = restore_workspace(before)
        deleted = restore_result['deleted']
        preserved_diff = restore_result['preserved_diff']
        restore_skipped = [s['path'] for s in restore_result.get('skipped', [])]
        if deleted or preserved_diff:
            print(f'  workspace restored: deleted {len(deleted)} files, '
                  f'preserved {len(preserved_diff)} modified files (manual recovery)')
        # Prove it actually worked. A non-empty list here is the contamination
        # source for the NEXT task, so it goes on the record rather than into a
        # print statement nobody reads.
        restore_leftovers = leftovers_vs(PRISTINE if PRISTINE is not None else before)
        if restore_leftovers:
            print(f'  [restore] WARNING: {len(restore_leftovers)} file(s) left behind: '
                  f'{restore_leftovers[:5]}')
    else:
        print(f'  workspace kept (--keep-workspace): {len(new_files)} new files preserved')

    return {
        'task_id': task['id'],
        'session_id': sid,
        'perf_weight': perf_weight,
        'prompt_len': len(task['prompt']),
        'duration_s': round(elapsed, 1),
        'tokens_in': final_tokens.get('input', 0),
        'tokens_out': final_tokens.get('output', 0),
        'chat_count': len(chat_records),
        'cloud_calls': len(cloud_calls),
        'local_calls': len(local_calls),
        'sub_agents': children_summary,
        'new_files': new_files,
        'pii_matches': pii_matches,
        'accuracy': accuracy,
        'router_log': log_name,
        'judge_input_path': str(judge_input_path) if judge_input_path else None,
        # Workspace hygiene — lets the analysis discard rows whose new_files
        # cannot be trusted to belong to this task.
        'workspace_dirty_at_start': dirty_at_start,
        'restore_skipped': restore_skipped,
        'restore_leftovers': restore_leftovers,
    }

def main():
    # Make stdout utf-8 (Windows defaults to gbk, which crashes on ☃, emoji, etc.)
    try:
        import sys
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--perf-weight', type=float, default=None,
                    help='Set perf_weight in DB before running. '
                         'If omitted, the current DB value (typically set via SuperClaw GUI) is used as-is.')
    ap.add_argument('--tasks', default=None,
                    help='Comma-separated task indices (e.g. 0,1,2). Default = all.')
    ap.add_argument('--timeout', type=int, default=240,
                    help='Per-task timeout in seconds. v3 baseline: 240s unlocks 5/8 tasks.')
    ap.add_argument('--out', default=None,
                    help='Output JSONL file (default logs/lh_automation_pw<X>.jsonl)')
    ap.add_argument('--keep-workspace', action='store_true',
                    help='Do NOT restore workspace after each task (default: restore). '
                         'Use to inspect task outputs afterwards.')
    ap.add_argument('--model', default='auto',
                    choices=['auto', 'local-model', 'cloud-model'],
                    help='Model slot for session creation. Default: auto (router decides). '
                         'Use cloud-model for pure-cloud config, local-model for pure-local.')
    ap.add_argument('--arm-label', default='auto',
                    help='Arm label for organizing raw outputs (results/v4_raw/<arm>/<task_id>/). '
                         'Any string is accepted (used as directory name); the auto/local/cloud '
                         'triad is conventional but e.g. smoke_oem, auto_pw0.85, etc. also work.')
    ap.add_argument('--save-raw', action='store_true',
                    help='Save raw output files BEFORE restore deletes them. '
                         'Stored in results/v4_raw/<arm>/<task_id>/')
    ap.add_argument('--save-judge-input', default=None,
                    help='Directory to dump per-task judge-input JSON for external LLM judge '
                         '(e.g. Opus 4.8 on Device A). Each task gets <task_id>.json + a '
                         'manifest.json index. Includes prompt, rubric, auto_checks_preview, '
                         'workspace file contents, transcript, assistant answer, run metadata, '
                         'and local heuristic accuracy. Default: disabled.')
    ap.add_argument('--no-backup', action='store_true',
                    help='Skip the post-run GitHub backup hook (default: backup enabled)')
    args = ap.parse_args()

    # 1. resolve perf_weight — only write to DB if user explicitly passed --perf-weight
    db = str(ROUTER_LOG_DIR.parent / 'llmrouter_manager.db')
    if args.perf_weight is not None:
        con = sqlite3.connect(db, timeout=5)
        con.execute("UPDATE config SET value=? WHERE key='perf_weight'", (str(args.perf_weight),))
        con.commit()
        con.close()
        print(f'perf_weight set to {args.perf_weight} (via --perf-weight arg)')
    else:
        # Read current DB value (user controls via GUI)
        con = sqlite3.connect(db, timeout=5)
        row = con.execute("SELECT value FROM config WHERE key='perf_weight'").fetchone()
        con.close()
        pw_in_db = row[0] if row else None
        print(f'perf_weight: using DB value {pw_in_db} (set via SuperClaw GUI)')
        # Resolve args.perf_weight so downstream (run_task, output filename, raw_dir) gets a real value.
        try:
            args.perf_weight = float(pw_in_db) if pw_in_db is not None else None
        except (TypeError, ValueError):
            args.perf_weight = None

    # 2. get token
    token = get_owt_token()
    print(f'OWT token: {token[:20]}...')

    # 3. load tasks
    indices = None
    if args.tasks:
        indices = [int(x) for x in args.tasks.split(',')]
    tasks = list_tasks(indices=indices)
    print(f'loaded {len(tasks)} tasks')

    # 4. output file
    if not args.out:
        out_dir = Path(__file__).parent.parent / 'logs'
        out_dir.mkdir(exist_ok=True)
        args.out = out_dir / f'lh_automation_pw{args.perf_weight}.jsonl'
    out_path = Path(args.out)
    print(f'output: {out_path}\n')

    # 5. run each task
    # Capture the pristine workspace once, before anything runs. run_task resets
    # to this on entry, so one crashed task can't contaminate every task after it.
    global PRISTINE
    if not args.keep_workspace:
        _hard_clean_pollution()
        PRISTINE = snapshot_workspace()
        print(f'pristine workspace baseline: {len(PRISTINE)} files\n')

    results = []
    for idx, task in enumerate(tasks):
        try:
            r = run_task(token, task, idx, args.perf_weight, timeout=args.timeout,
                        keep_workspace=args.keep_workspace, model=args.model,
                        save_raw=args.save_raw, arm_label=args.arm_label,
                        save_judge_input_dir=args.save_judge_input)
        except Exception as e:
            # Force-replace any unencodable Unicode so we don't crash on print
            # (Windows gbk can't represent ☃ etc.)
            err_msg = str(e).encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            print(f'  ERROR: {err_msg}')
            r = {'task_id': task['id'], 'error': err_msg}
        results.append(r)
        # write incrementally
        with out_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + '\n')

    # 6. final summary
    print(f'\n{"="*60}')
    print(f'SUMMARY (pw={args.perf_weight})')
    print(f'{"="*60}')
    print(f'{"task":12} {"chat":>5} {"cloud":>5} {"local":>5} {"in_tok":>8} {"out_tok":>7} {"sub":>4} {"files":>5} {"PII":>4} {"acc":>5} {"sec":>5}')
    for r in results:
        if 'error' in r:
            print(f'{r["task_id"]:12}  ERROR: {r["error"][:50]}')
            continue
        _s = score_of(r)
        _s_txt = '  n/a' if _s is None else f'{_s:5.2f}'
        print(f'{r["task_id"]:12} {r["chat_count"]:5} {r["cloud_calls"]:5} {r["local_calls"]:5} '
              f'{r["tokens_in"]:8,} {r["tokens_out"]:7,} {len(r["sub_agents"]):4} '
              f'{len(r["new_files"]):5} {len(r["pii_matches"]):4} {_s_txt} {r["duration_s"]:5.1f}')

    print()
    print('  ' + summarize([r for r in results if 'error' not in r], 'accuracy'))
    _dirty = [r for r in results if r.get('workspace_dirty_at_start') or r.get('restore_leftovers')]
    if _dirty:
        print(f'  workspace hygiene: {len(_dirty)} task(s) ran with or left a dirty workspace — '
              f'their new_files may not belong to them:')
        for r in _dirty:
            print(f'    {r["task_id"]}: dirty_at_start={len(r.get("workspace_dirty_at_start") or [])} '
                  f'leftovers={len(r.get("restore_leftovers") or [])}')
    else:
        print('  workspace hygiene: clean — every task started and ended at the pristine baseline')

    # 6b. Judge-input manifest (Device A reads this to iterate per-task files)
    if args.save_judge_input:
        manifest = {
            'created_at_utc': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
            'harness': 'lh_automation.py',
            'perf_weight': args.perf_weight,
            'model_slot': args.model,
            'arm_label': args.arm_label,
            'task_count': len(results),
            'tasks': [
                {
                    'task_id': r.get('task_id'),
                    'judge_input_path': r.get('judge_input_path'),
                    'local_accuracy': (r.get('accuracy') or {}).get('score'),
                    'grader_kind': (r.get('accuracy') or {}).get('grader', 'heuristic'),
                    'duration_s': r.get('duration_s'),
                    'tokens_in': r.get('tokens_in'),
                    'tokens_out': r.get('tokens_out'),
                    'cloud_calls': r.get('cloud_calls'),
                    'local_calls': r.get('local_calls'),
                }
                for r in results
            ],
        }
        manifest_path = Path(args.save_judge_input) / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                 encoding='utf-8')
        print(f'\n[judge-input] manifest: {manifest_path} ({len(results)} entries)')

    # ---- Auto-backup baselines to GitHub (tools/backup.py) ----
    # Runs after the summary so a backup failure doesn't lose this round's
    # lh_automation_pw<X>.jsonl. Disable with --no-backup.
    if not args.no_backup:
        backup_cmd = [
            sys.executable,
            str(Path(__file__).resolve().parent.parent / 'tools' / 'backup.py'),
            '--config', args.model,           # auto / local-model / cloud-model
            '--pw', str(args.perf_weight),
        ]
        print(f'\n[lh_automation] auto-backup: {" ".join(backup_cmd)}')
        try:
            res = subprocess.run(backup_cmd,
                                 cwd=str(Path(__file__).resolve().parent.parent),
                                 capture_output=True, text=True)
            if res.returncode != 0:
                print(f'[lh_automation] backup hook FAILED (rc={res.returncode}); '
                      f'outputs are still on disk.', file=sys.stderr)
                tail = (res.stderr or res.stdout or '').strip().splitlines()
                if tail:
                    print('[lh_automation] backup.py last output:', file=sys.stderr)
                    for line in tail[-15:]:
                        print(f'    {line}', file=sys.stderr)
        except Exception as e:
            print(f'[lh_automation] backup hook raised: {e!r}', file=sys.stderr)

if __name__ == '__main__':
    main()
