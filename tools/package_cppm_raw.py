#!/usr/bin/env python3
"""Package cppm raw deliverables into raw_deliverables/ following the existing pattern.

Source: results/v4_raw/<batch>/<task_id>/
Target: raw_deliverables/<batch>/<task_id>/<file>
Manifest: append entries to raw_deliverables/MANIFEST.json (preserving existing entries)
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark')
SRC = ROOT / 'results' / 'v4_raw'
DEST = ROOT / 'raw_deliverables'
MANIFEST = DEST / 'MANIFEST.json'

# (batch, run_date)
BATCHES = [
    ('cppm3_pw0.60', '2026-08-31', 'cppm3_pw0.60 first run -- 1800s timeout, contaminated by 5 polluted extract_factorio_data2*.py residue (pre-cleared before rerun1)'),
    ('cppm3_rerun1_pw0.60', '2026-08-31', 'cppm3_pw0.60 rerun1 -- pristine workspace, valid comparison baseline'),
    ('cppm3_pw0.40', '2026-08-31', 'cppm3_pw0.40 -- 1800s timeout, best mean of 0.6/0.4'),
    ('cppm3_pw0.20', '2026-08-31', 'cppm3_pw0.20 -- 1800s timeout, best mean 0.785, cppm03=1.0 clean (no path bug)'),
]

# Accuracies per (batch, task) for reference
ACC = {
    ('cppm3_pw0.60', 'cppm01'): 0.818,
    ('cppm3_pw0.60', 'cppm02'): 0.308,
    ('cppm3_pw0.60', 'cppm03'): 0.0,
    ('cppm3_rerun1_pw0.60', 'cppm01'): 0.818,
    ('cppm3_rerun1_pw0.60', 'cppm02'): 0.308,
    ('cppm3_rerun1_pw0.60', 'cppm03'): 0.375,
    ('cppm3_pw0.40', 'cppm01'): 0.818,
    ('cppm3_pw0.40', 'cppm02'): 0.462,
    ('cppm3_pw0.40', 'cppm03'): 0.375,
    ('cppm3_pw0.20', 'cppm01'): 0.818,
    ('cppm3_pw0.20', 'cppm02'): 0.538,
    ('cppm3_pw0.20', 'cppm03'): 1.0,
}


def md5(p: Path) -> str:
    h = hashlib.md5()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    else:
        manifest = {
            'generated_at': '',
            'purpose': '',
            'source_dirs': {},
            'note_path_separator': '',
            'stats': {'total_tasks': 0, 'total_files': 0, 'total_bytes': 0, 'total_kb': 0, 'batches': {}},
            'files': [],
        }

    # Track existing (batch, task, file) to avoid dup
    existing = {(e['batch'], e['task_id'], e['file']) for e in manifest['files']}

    new_files = []
    new_batches = {}

    for batch, run_date, note in BATCHES:
        src_batch = SRC / batch
        if not src_batch.exists():
            print(f'WARN: missing {src_batch}')
            continue
        dest_batch = DEST / batch
        dest_batch.mkdir(parents=True, exist_ok=True)
        n_files = 0
        n_bytes = 0
        for task_dir in sorted(src_batch.iterdir()):
            if not task_dir.is_dir():
                continue
            task_id = task_dir.name
            dest_task = dest_batch / task_id
            dest_task.mkdir(parents=True, exist_ok=True)
            for f in sorted(task_dir.iterdir()):
                if not f.is_file():
                    continue
                rel = f.name
                # Handle case where file collides with a file already at dest_task (e.g. across runs)
                # Existing pattern: just place as-is; if same name, prefer latest (overwrite with warning)
                dest_f = dest_task / rel
                if dest_f.exists():
                    # If md5 differs, suffix with -<run>
                    if md5(dest_f) != md5(f):
                        suffix = f'-{batch.replace("cppm3_", "")}'
                        new_name = f'{f.stem}{suffix}{f.suffix}'
                        dest_f = dest_task / new_name
                        rel = new_name
                shutil.copy2(f, dest_f)
                h = md5(f)
                sz = f.stat().st_size
                n_files += 1
                n_bytes += sz
                key = (batch, task_id, rel)
                if key not in existing:
                    entry = {
                        'batch': batch,
                        'run_date': run_date,
                        'task_id': task_id,
                        'file': rel,
                        'bytes': sz,
                        'md5': h,
                    }
                    if (batch, task_id) in ACC:
                        entry['auto_accuracy'] = ACC[(batch, task_id)]
                    entry['note'] = note if ACC.get((batch, task_id)) is None else None
                    new_files.append(entry)
                    existing.add(key)
        new_batches[batch] = {
            'tasks': sum(1 for td in src_batch.iterdir() if td.is_dir()),
            'files': n_files,
            'run_date': run_date,
            'note': note,
        }
        print(f'{batch}: {new_batches[batch]["tasks"]} tasks, {n_files} files, {n_bytes} B')

    # Update manifest
    manifest['files'].extend(new_files)
    for batch, info in new_batches.items():
        manifest['stats']['batches'][batch] = {
            'tasks': info['tasks'],
            'files': info['files'],
            'run_date': info['run_date'],
        }
    # Add note for cppm batches
    manifest.setdefault('cppm_notes', {})
    for batch, _, note in BATCHES:
        manifest['cppm_notes'][batch] = note

    # Recompute totals
    total_files = len(manifest['files'])
    total_bytes = sum(e['bytes'] for e in manifest['files'])
    total_tasks = len({(e['batch'], e['task_id']) for e in manifest['files']})
    manifest['stats']['total_tasks'] = total_tasks
    manifest['stats']['total_files'] = total_files
    manifest['stats']['total_bytes'] = total_bytes
    manifest['stats']['total_kb'] = round(total_bytes / 1024, 1)

    tz = timezone(timedelta(hours=8))
    manifest['generated_at'] = datetime.now(tz).isoformat(timespec='seconds')
    manifest['last_added'] = 'cppm3_pw sweep (0.6, 0.6 rerun1, 0.4, 0.2) on 2026-08-31'

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print()
    print(f'Manifest: {total_files} files, {total_bytes} B ({total_bytes/1024:.1f} KB), {total_tasks} tasks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
