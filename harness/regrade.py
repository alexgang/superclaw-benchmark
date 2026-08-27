"""Re-score existing run logs under the post-audit grading rules.

Historical rows can be re-scored without rerunning anything, because each row
persists the individual `checks[]` it ran. What changes is only how those checks
are turned into a number:

  old: zero checks            -> score 1.0   (a default masquerading as a result)
  new: zero checks            -> score None  (excluded from any average)

  old: `no_files` privacy check, passed=True, "no output => privacy N/A"
  new: that check is not evidence of anything; a row whose only check is
       `no_files` has no real assertions and is therefore ungraded.

  old: a dimension with no checks -> 1.0
  new: a dimension with no checks -> None

Usage:
    python harness/regrade.py logs/*.jsonl
    python harness/regrade.py --write logs/pb_top3_pw0.85_auto_v5.jsonl
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import dim_avg  # noqa: E402

# Checks that assert nothing about whether the agent did its job.
VACUOUS_CHECKS = {'no_files'}


def regrade_row(row):
    """Return a new accuracy dict computed from the row's recorded checks."""
    acc = row.get('accuracy')
    if not isinstance(acc, dict):
        return None
    checks = acc.get('checks') or []
    real = [c for c in checks if c.get('check') not in VACUOUS_CHECKS]

    dims = {'completeness': [], 'correctness': [], 'privacy': []}
    for c in real:
        d = c.get('dim')
        if d in dims:
            dims[d].append(1 if c.get('passed') else 0)

    def avg(lst):
        return round(sum(lst) / len(lst), 3) if lst else None

    main = dims['completeness'] + dims['correctness']
    return {
        'score': avg(main),
        'completeness': avg(dims['completeness']),
        'correctness': avg(dims['correctness']),
        'privacy': avg(dims['privacy']),
        'passed': sum(1 for c in real if c.get('passed')),
        'total': len(real),
        'gradeable': bool(main),
        'checks': real,
        'grader': acc.get('grader', 'heuristic'),
        'regraded': True,
        'dropped_vacuous_checks': len(checks) - len(real),
    }


def report(path, write=False):
    rows = []
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    if not rows:
        return None

    old_scores, new_scores, newly_ungraded = [], [], []
    for r in rows:
        acc = r.get('accuracy')
        if not isinstance(acc, dict):
            continue
        old_scores.append(acc.get('score'))
        new_acc = regrade_row(r)
        if new_acc['score'] is None:
            newly_ungraded.append(r.get('task_id'))
        else:
            new_scores.append(new_acc['score'])
        r['accuracy'] = new_acc

    old_valid = [s for s in old_scores if isinstance(s, (int, float))]
    old_avg = sum(old_valid) / len(old_valid) if old_valid else None
    new_avg = sum(new_scores) / len(new_scores) if new_scores else None

    name = Path(path).name
    print(f'{name}')
    print(f'  rows: {len(rows)}')
    print(f'  old: avg {old_avg:.3f} over {len(old_valid)}/{len(rows)}'
          if old_avg is not None else '  old: no scores')
    if new_avg is None:
        print(f'  new: NO GRADEABLE ROWS — all {len(newly_ungraded)} rows had zero real checks')
    else:
        print(f'  new: avg {new_avg:.3f} over {len(new_scores)}/{len(rows)} gradeable '
              f'({len(newly_ungraded)} ungraded, excluded)')
        print(f'       completeness={_f(dim_avg(rows, "completeness"))} '
              f'correctness={_f(dim_avg(rows, "correctness"))} '
              f'privacy={_f(dim_avg(rows, "privacy"))}')

    if write:
        out = Path(path).with_suffix('.regraded.jsonl')
        with out.open('w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + '\n')
        print(f'  wrote {out}')
    print()
    return {'file': name, 'rows': len(rows), 'old_avg': old_avg, 'new_avg': new_avg,
            'gradeable': len(new_scores), 'ungraded': len(newly_ungraded)}


def _f(v):
    return 'n/a' if v is None else f'{v:.3f}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('logs', nargs='+')
    ap.add_argument('--write', action='store_true',
                    help='also emit <name>.regraded.jsonl next to each input')
    args = ap.parse_args()

    summaries = [s for s in (report(p, args.write) for p in args.logs) if s]

    print('=' * 78)
    print(f'{"file":44} {"rows":>5} {"gradeable":>10} {"old":>6} {"new":>6}')
    for s in summaries:
        old = f'{s["old_avg"]:.3f}' if s['old_avg'] is not None else '  n/a'
        new = f'{s["new_avg"]:.3f}' if s['new_avg'] is not None else '  n/a'
        print(f'{s["file"]:44} {s["rows"]:5} {s["gradeable"]:10} {old:>6} {new:>6}')


if __name__ == '__main__':
    main()
