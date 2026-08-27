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
