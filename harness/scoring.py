"""Shared scoring helpers.

Every consumer of a run log should go through `gradeable_scores()` rather than
reaching into `row['accuracy']['score']` directly. A row's score is None when no
check actually ran, and averaging those in as 0.0 (or as the old default 1.0) is
how the PinchBench pass rate ended up at a meaningless 98.8%.
"""


def score_of(row):
    """Return the row's main score, or None if the row was never really graded."""
    acc = row.get('accuracy')
    if not isinstance(acc, dict):
        return None
    if acc.get('gradeable') is False:
        return None
    # Legacy rows (written before the 2026-08-27 fix) carry score=1.0 with
    # total=0 and checks=[]. That 1.0 is a default, not a result — drop it.
    if acc.get('gradeable') is None and not acc.get('total'):
        return None
    return acc.get('score')


def gradeable_scores(rows):
    """Split rows into (scores, n_ungraded) — scores excludes ungraded rows."""
    scores = []
    ungraded = 0
    for r in rows:
        s = score_of(r)
        if s is None:
            ungraded += 1
        else:
            scores.append(s)
    return scores, ungraded


def summarize(rows, label=''):
    """One-line honest summary. Never hides how many rows had no checks."""
    scores, ungraded = gradeable_scores(rows)
    n = len(rows)
    if not scores:
        return f'{label}: {n} rows, 0 gradeable ({ungraded} ungraded) — no score'
    avg = sum(scores) / len(scores)
    out = f'{label}: {avg:.2f} over {len(scores)}/{n} gradeable'
    if ungraded:
        out += f' ({ungraded} ungraded, excluded)'
    return out


def dim_avg(rows, dim):
    """Average one dimension across rows, skipping rows where it is None."""
    vals = []
    for r in rows:
        acc = r.get('accuracy')
        if isinstance(acc, dict) and acc.get(dim) is not None:
            vals.append(acc[dim])
    if not vals:
        return None
    return sum(vals) / len(vals)
