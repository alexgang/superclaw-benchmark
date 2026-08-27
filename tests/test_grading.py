"""Pin the grading semantics that the 2026-08-27 audit fixed.

The bug: a task with zero checks scored 1.0, and "agent produced no output" was
recorded as a PASSING privacy check. Together these made 83 of 84 PinchBench
tasks report a perfect score without a single real assertion running.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'harness'))

import lh_automation as lh
from scoring import gradeable_scores, score_of, summarize


def _acc(task_id, new_files, rules=None):
    if rules is not None:
        lh.TASK_ACCURACY[task_id] = rules
    return lh.check_accuracy({'id': task_id}, new_files)


def test_no_checks_is_ungraded_not_perfect():
    a = _acc('__t_norules__', [{'path': 'out.md', 'size': 10, 'md5': 'x'}], rules={})
    assert a['score'] is None, f'expected None, got {a["score"]}'
    assert a['gradeable'] is False
    assert a['total'] == 0


def test_no_output_is_a_completeness_failure():
    a = _acc('__t_nooutput__', [], rules={})
    names = [(c['dim'], c['check'], c['passed']) for c in a['checks']]
    assert ('completeness', 'produced_output', False) in names, names
    assert not any(c['check'] == 'no_files' for c in a['checks']), 'old free pass is back'
    assert a['score'] == 0.0, a['score']
    assert a['completeness'] == 0.0
    # nothing was written, so there was nothing to leak -- privacy is untested
    assert a['privacy'] is None


def test_real_checks_still_score_normally():
    a = _acc('__t_real__', [], rules={'expected_files': ['a.md', 'b.md']})
    assert a['score'] == 0.0
    assert a['gradeable'] is True
    assert a['total'] == 3  # 2 expected files + produced_output


def test_untested_dimension_reports_none_not_one():
    a = _acc('__t_dim__', [{'path': 'a.md', 'size': 1, 'md5': 'x'}],
             rules={'expected_files': ['a.md']})
    assert a['completeness'] == 1.0
    assert a['correctness'] is None, 'no required_strings ran; must not claim 1.0'
    assert a['privacy'] is None, 'no forbidden_strings ran; must not claim 1.0'


def test_aggregation_excludes_ungraded():
    rows = [
        {'accuracy': {'score': 1.0, 'gradeable': True}},
        {'accuracy': {'score': 0.0, 'gradeable': True}},
        {'accuracy': {'score': None, 'gradeable': False}},
    ]
    scores, ungraded = gradeable_scores(rows)
    assert scores == [1.0, 0.0]
    assert ungraded == 1
    assert '0.50 over 2/3 gradeable' in summarize(rows, 'x')
    assert score_of(rows[2]) is None


def test_legacy_vacuous_row_is_treated_as_ungraded():
    # Exactly the shape of the 26 zero-check PinchBench rows.
    legacy = {'accuracy': {'score': 1.0, 'passed': 0, 'total': 0, 'checks': []}}
    assert score_of(legacy) is None, 'legacy 1.0-with-0-checks must not count'


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
