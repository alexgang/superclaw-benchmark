# Naming audit — 2026-08-27

Audit of `logs/` and `results/v4_raw/` after noticing that files named `*_local_*`
appeared to contain auto-routed runs. All findings below are confirmed by three
independent sources; nothing was deleted, only renamed.

## Finding 1 — the pw sweep was `model=auto`, not forced local

Files named `{lh,cppm}_local_pw{02,04,06}[_rerun].jsonl` were produced with
`--model auto`. Evidence:

1. Every matching `*.stdout.log` / `*.runlog.txt` records `model=auto`, and the
   backup round ids are `auto_pw0.2 / auto_pw0.4 / auto_pw0.6`.
2. The cppm logs contain non-zero `cloud_calls` (e.g. `cppm_..._pw04_rerun`:
   30 cloud / 205 local), which is impossible under a forced-local run.
3. `logs/sweep_summary.md` already annotated every one of them as `(auto, pw=0.x)`
   — the analysis was right, only the filenames were wrong.

The `lh_*` sweep logs do show 0 cloud calls, but that is a *result*, not a mode:
under auto routing at pw ≤ 0.6 all 8 lh tasks were routed to the local tier.

**Action:** renamed `*_local_pw*` → `*_auto_pw*` (jsonl + stdout/stderr/runlog
siblings, 34 files). References updated in `logs/sweep_summary.md`,
`logs/summary_pw0{2,4,6}.md`, `logs/_crosscheck.py`.

`logs/cppm_local_1800s.*` is genuinely `model=local-model` and keeps its name.

## Finding 2 — `baseline_pw0.85_cloud_cppm.jsonl` held 11 rows, not 3

The file is a single contiguous cloud run of the full suite: `lh01`–`lh08` plus
`cppm01`–`cppm03`. A separate, later cloud run of lh only lives in
`baseline_pw0.85_cloud_lh.jsonl` (distinct `session_id`s and durations; both
score 1.0 on every lh task).

`results/v4_benchmark_report.md` used the `_lh` file for lh and only the cppm
rows of the other, so the published numbers are **not** double-counted. The risk
was latent: any future aggregator globbing `baseline_*_cloud_*.jsonl` would
count lh twice.

**Action:** renamed to `baseline_pw0.85_cloud_all11.jsonl`.
`baseline_pw0.85_cloud_lh.jsonl` is unchanged and remains the authoritative lh
cloud arm. Report and `results/QUARANTINE_MANIFEST.json` updated.

## Finding 3 — `results/v4_raw/local/` was a stale mixed scratch dir

Its contents span 2026-08-24 to 08-26 and were overwritten in place by later
sweep rounds (e.g. `local/lh01/reports_q3-compliance.md` has an 08-26 10:32
mtime, from the pw=0.6 era), and it contains stray tooling (`analyze.py`). It is
not a clean forced-local artifact set. The per-round dirs `auto_pw0.20`,
`auto_pw0.40`, `auto_pw0.60`, `auto_pw0.85`, `cloud` are the trustworthy ones.

**Action:** renamed to `results/v4_raw/local_STALE_MIXED/`. Do not cite it.
`results/v4_raw/` is gitignored, so this is a local-disk change only.

## Not affected

- `pb_top3_pw0.85_auto_v5.jsonl`, `baseline_pw0.85_auto_*`,
  `baseline_pw0.85_local_*`, `smoke_oem.jsonl` — names match contents.
- No Python script resolves any of these logs by hardcoded filename except
  `logs/_crosscheck.py` (updated); `tools/backup.py` globs `logs/baseline_*.jsonl`,
  which still matches.

---

# Grading audit — 2026-08-27 (same session)

Follow-up to the question "of the 116 OEM cases, how many were attempted and how
many produced a judgeable artifact?". Answering it surfaced two harness defects
that invalidate the published PinchBench accuracy.

## Coverage of the 116 OEM cases

| | count |
|---|---|
| attempted (a run row exists with chat_count > 0) | 67 |
| never attempted | 49 |
| produced an artifact named in their own rubric | 6 |
| produced files, but none matching their rubric (contamination only) | 11 |
| produced no files at all | 50 |

The 49 never attempted are concentrated in `pb_meeting_*` (27) and
`pb_log_{ssh,syslog}_*` (10), all `routing_expectation=cloud`.

## Defect 1 — the grader scored 1.0 when nothing was checked

`check_accuracy()` averaged each dimension with `safe_avg(lst)` returning **1.0
for an empty list**, and emitted `no_files` as a *passing* privacy check with the
detail "no output → privacy N/A". Net effect across `pb_top3_pw0.85_auto_v5.jsonl`:

- 58 rows whose only check was `no_files` → 1.0
- 26 rows with `checks: []` → 1.0
- 1 row with real assertions

Reported mean 0.988. Actual gradeable rows: **0 of 84**.

**Fixed:** empty dimension → `None`; no checks → `score: None, gradeable: False`;
"no output" is now a *failing* completeness check (`produced_output`) and privacy
reports `None` instead of a free pass. Pinned by `tests/test_grading.py` (6 tests).
All score consumers now go through `harness/scoring.py`, which also treats legacy
`score=1.0, total=0` rows as ungraded.

## Defect 2 — the workspace was not reset between tasks

`restore_workspace()` collected unlink failures into a `skipped` list that was
printed but never recorded, and a task that raised skipped restore entirely. The
next task's `find_new_outputs()` then attributed the survivors to itself:
`pb_cve_security_triage` → `global_temperature.csv`, `pb_log_hdfs_connections` →
`vulnerability_scan.json`, `pb_csv_iris_summary` → `express\lib\request.js`.

**Fixed:** a `PRISTINE` baseline is captured once per run; every task resets to it
on entry, so a crashed task cannot contaminate its successors. Each row now
records `workspace_dirty_at_start`, `restore_skipped` and `restore_leftovers`, and
the run summary prints a workspace-hygiene line. Pinned by
`tests/test_workspace_isolation.py` (4 tests).

## What survives re-scoring

`harness/regrade.py` re-scores any existing log from its persisted `checks[]`
without rerunning. Full output in `results/regrade_20260827.txt`.

| log | rows | gradeable | old | new |
|---|---|---|---|---|
| `pb_top3_pw0.85_auto_v5.jsonl` | 84 | **0** | 1.000 | n/a |
| `baseline_pw0.85_auto_lh.jsonl` | 8 | 8 | 0.600 | 0.600 |
| `baseline_pw0.85_cloud_lh.jsonl` | 8 | 8 | 1.000 | 1.000 |
| `baseline_pw0.85_local_lh.jsonl` | 8 | 8 | 1.000 | 1.000 |
| `baseline_pw0.85_*_cppm.jsonl` | 3 each | **0** | 1.000 | n/a |
| `cppm_auto_pw0{2,4,6}_rerun.jsonl` | 3 each | 3 | 0.598–0.601 | unchanged |
| `lh_auto_pw0{2,4,6}_rerun.jsonl` | 8 each | 8 | 1.000 | unchanged |

Two things to note:

- **The lh arm is real and unchanged.** Its scores were never inflated, because
  `TASK_ACCURACY` has had lh01–lh08 rules throughout. The one movement is privacy
  in the force-local arm, 1.000 → 0.750, which the `no_files` free pass had been
  hiding.
- **The Aug 20/24 cppm baselines are ungradeable for a different reason** than
  PinchBench: `TASK_ACCURACY` gained its cppm01–03 rules *after* those runs, so
  they recorded `checks: []`. The Aug 26 pw-sweep cppm runs used the newer rules
  and re-score identically (0.598–0.601) — that data is sound. The cppm baselines
  need a rerun, not a re-score.

The sweep data (`*_auto_pw*`) is unaffected by both defects: identical before and
after re-scoring, and every row gradeable.
