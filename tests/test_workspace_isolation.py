"""Pin the workspace-isolation semantics fixed by the 2026-08-27 audit.

The bug: restore_workspace swallowed unlink failures into a `skipped` list that
nobody recorded, and a task that raised never restored at all. Either way the
next task's find_new_outputs() picked up the previous task's output and
attributed it to the wrong task -- e.g. pb_cve_security_triage was credited with
producing global_temperature.csv.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'harness'))

import lh_automation as lh


def _ws():
    d = Path(tempfile.mkdtemp(prefix='wstest_'))
    (d / 'input.csv').write_text('a,b\n1,2\n', encoding='utf-8')
    return d


def test_leftovers_detects_foreign_file():
    ws = _ws()
    snap = lh.snapshot_workspace(ws)
    assert lh.leftovers_vs(snap, ws) == []
    (ws / 'from_previous_task.md').write_text('stale', encoding='utf-8')
    assert lh.leftovers_vs(snap, ws) == ['from_previous_task.md']


def test_restore_removes_new_files_and_verifies_clean():
    ws = _ws()
    snap = lh.snapshot_workspace(ws)
    (ws / 'output.md').write_text('agent wrote this', encoding='utf-8')
    (ws / 'sub').mkdir()
    (ws / 'sub' / 'nested.json').write_text('{}', encoding='utf-8')

    result = lh.restore_workspace(snap, ws)

    assert sorted(result['deleted']) == sorted(['output.md', str(Path('sub/nested.json'))])
    assert lh.leftovers_vs(snap, ws) == [], 'restore must leave the workspace pristine'
    assert (ws / 'input.csv').exists(), 'seeded input must survive restore'


def test_reset_recovers_from_a_task_that_never_restored():
    """The contamination scenario, end to end."""
    ws = _ws()
    pristine = lh.snapshot_workspace(ws)

    # Task A produces output, then "crashes" before restoring.
    (ws / 'global_temperature.csv').write_text('year,temp\n', encoding='utf-8')

    # Task B starts. Without the reset it would see task A's file as its own.
    stale = lh.leftovers_vs(pristine, ws)
    assert stale == ['global_temperature.csv'], stale

    lh.restore_workspace(pristine, ws)
    assert lh.leftovers_vs(pristine, ws) == []

    # Now task B's own snapshot is clean, so its new_files are genuinely its own.
    before_b = lh.snapshot_workspace(ws)
    (ws / 'vulnerability_scan.json').write_text('{}', encoding='utf-8')
    new = lh.find_new_outputs(before_b, ws)
    assert [f['path'] for f in new] == ['vulnerability_scan.json']


def test_find_new_outputs_ignores_untouched_seed_files():
    ws = _ws()
    snap = lh.snapshot_workspace(ws)
    assert lh.find_new_outputs(snap, ws) == [], 'seeded inputs are not agent output'


if __name__ == '__main__':
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f'PASS {fn.__name__}')
        except AssertionError as e:
            failed += 1
            print(f'FAIL {fn.__name__}: {e}')
    print(f'\n{len(fns)-failed}/{len(fns)} passed')
    sys.exit(1 if failed else 0)
