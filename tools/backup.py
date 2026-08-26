#!/usr/bin/env python3
"""
backup.py - Snapshot a benchmark round's data and push to GitHub.

Each invocation captures the latest state of the round's output files into
``baseline_runs/<round_id>/`` (a self-contained, reproducible snapshot) and
commits/pushes that directory to the configured remote.

What gets captured (the canonical baseline payload):
  - logs/baseline_*.jsonl                       (all matching files)
  - results/v4_benchmark_aggregated.json
  - results/v4_benchmark_report.md
  - results/QUARANTINE_MANIFEST.json

A ``manifest.json`` is generated alongside the snapshot describing the files
(size, sha256, mtime, source path).

Auto-called at the end of:
  - harness/run_driver.py
  - harness/lh_automation.py

Manually runnable:
  python tools/backup.py --config hybrid --pw 0.85
  python tools/backup.py --config hybrid --pw 0.85 --no-push
  python tools/backup.py --dry-run                    # preview only
  python tools/backup.py --message "manual hotfix"    # custom commit message

Auth:
  Set ``GITHUB_TOKEN`` in env to a fine-grained PAT (Contents: Read+Write) and
  the script will inject it into the push URL. This avoids interactive prompts
  and leaves no credential on disk. The .gitconfig credential helper is left
  empty intentionally.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
RES_DIR = REPO_ROOT / "results"
SNAP_DIR = REPO_ROOT / "baseline_runs"
MANIFEST_NAME = "manifest.json"

# Files we always consider part of "the baseline payload".
# Wildcard in LOG_DIR is also scanned; this list is the explicit
# (no-wildcard) result files.
EXPLICIT_RESULT_FILES = [
    RES_DIR / "v4_benchmark_aggregated.json",
    RES_DIR / "v4_benchmark_report.md",
    RES_DIR / "QUARANTINE_MANIFEST.json",
]
LOG_WILDCARD = "baseline_*.jsonl"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_git() -> str:
    """Locate git.exe, even when the current Python's PATH doesn't include it.

    Order of resolution:
      1. ``shutil.which('git')`` on the inherited PATH
      2. Common Windows install locations
      3. ``GIT_BIN`` env var (override)
    """
    override = os.environ.get("GIT_BIN", "").strip()
    if override and Path(override).is_file():
        return override
    found = shutil.which("git")
    if found:
        return found
    candidates = [
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
    ]
    for c in candidates:
        if Path(c).is_file():
            return c
    raise FileNotFoundError(
        "git executable not found. Install Git for Windows "
        "(https://git-scm.com/download/win) or set $env:GIT_BIN."
    )


_GIT_BIN: str | None = None


def _git(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in REPO_ROOT. Returns CompletedProcess."""
    global _GIT_BIN
    if _GIT_BIN is None:
        _GIT_BIN = _find_git()
    return subprocess.run(
        [_GIT_BIN, "-C", str(REPO_ROOT), *args],
        check=check,
        capture_output=capture,
        text=True,
    )


def _round_id(config: str | None, pw: float | None, now: datetime) -> str:
    ts = now.strftime("%Y%m%d-%H%M%S")
    parts: list[str] = []
    if config:
        parts.append(config)
    if pw is not None:
        parts.append(f"pw{pw:g}")
    parts.append(ts)
    return "_".join(parts)


def _collect_sources() -> list[Path]:
    """Return all baseline-payload files that exist on disk, deduplicated."""
    sources: list[Path] = []
    sources.extend(sorted(LOG_DIR.glob(LOG_WILDCARD)))
    for p in EXPLICIT_RESULT_FILES:
        if p.exists():
            sources.append(p)
    seen: set[str] = set()
    out: list[Path] = []
    for p in sources:
        key = str(p.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--config", help="Run config (hybrid / cloud_only / local)")
    ap.add_argument("--pw", type=float, help="perf_weight used in this round")
    ap.add_argument("--message", help="Override the default commit message")
    ap.add_argument("--no-push", action="store_true", help="Commit only, do not push")
    ap.add_argument("--dry-run", action="store_true", help="Preview without mutating git or copying files")
    ap.add_argument("--allow-empty", action="store_true", help="Make a commit even if no changes")
    ap.add_argument("--branch", default="main", help="Target branch on the remote (default: main)")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    rid = _round_id(args.config, args.pw, now)
    snap_subdir = SNAP_DIR / rid

    sources = _collect_sources()
    if not sources and not args.dry_run and not args.allow_empty:
        print(f"[backup] no baseline/result files found under {LOG_DIR} and {RES_DIR}; nothing to do")
        return 0

    if not args.dry_run:
        snap_subdir.mkdir(parents=True, exist_ok=True)

    # Mirror each source into baseline_runs/<rid>/<relpath>; record manifest entry.
    manifest: dict = {
        "round_id": rid,
        "captured_at_utc": now.isoformat(timespec="seconds"),
        "config": args.config,
        "perf_weight": args.pw,
        "files": [],
    }
    for src in sources:
        rel = src.relative_to(REPO_ROOT)
        if not args.dry_run:
            dst = snap_subdir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        stat = src.stat()
        manifest["files"].append({
            "src": str(rel).replace("\\", "/"),
            "size": stat.st_size,
            "sha256": _sha256(src),
            "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
        })

    if not args.dry_run:
        (snap_subdir / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # Human-readable summary (always)
    print(f"[backup] round_id={rid}")
    print(f"[backup] captured {len(manifest['files'])} file(s) into {snap_subdir.relative_to(REPO_ROOT)}")
    for f in manifest["files"]:
        sha = f["sha256"][:12] if f["sha256"] else "?"
        print(f"  {f['src']}  size={f['size']}  sha={sha}...")

    if args.dry_run:
        print("[backup] --dry-run set; skipping copy/git/commit/push")
        return 0

    # ---- Stage: snapshot dir + canonical baseline/result files (so the
    # authoritative results/ and logs/baseline_*.jsonl in the repo always
    # reflect the latest run, not a 1-round-stale snapshot). ----
    add_targets: list[str] = [
        str((SNAP_DIR / rid).relative_to(REPO_ROOT)).replace("\\", "/"),
    ]
    # Canonical files (whitelist; explicit so we never accidentally pick up junk)
    canonical_globs: list[str] = [
        "logs/baseline_*.jsonl",
        "results/v4_benchmark_aggregated.json",
        "results/v4_benchmark_report.md",
        "results/QUARANTINE_MANIFEST.json",
    ]
    # Resolve globs against the working tree (the .gitignore allows exactly these)
    for pat in canonical_globs:
        for p in REPO_ROOT.glob(pat):
            rel = p.relative_to(REPO_ROOT).as_posix()
            if rel not in add_targets:
                add_targets.append(rel)
    r = _git("add", "--", *add_targets)
    if r.returncode != 0:
        print(f"[backup] git add failed:\n{r.stderr}", file=sys.stderr)
        return r.returncode

    # Detect "no changes" before opening the editor
    status = _git("status", "--porcelain")
    if not status.stdout.strip() and not args.allow_empty:
        print("[backup] snapshot identical to previous round; nothing to commit")
        # Still leave the (now redundant) dir on disk? Remove to keep tree clean.
        try:
            shutil.rmtree(snap_subdir)
        except OSError:
            pass
        return 0

    # ---- Commit ----
    msg = args.message or f"[backup] {rid}"
    r = _git("commit", "-m", msg)
    if r.returncode != 0:
        print(f"[backup] git commit failed:\n{r.stderr}", file=sys.stderr)
        return r.returncode
    print(f"[backup] committed: {r.stdout.strip()}")

    if args.no_push:
        print("[backup] --no-push set; local commit only")
        return 0

    # ---- Push ----
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        r = _git("config", "--get", "remote.origin.url")
        if r.returncode != 0:
            print(f"[backup] no remote 'origin' configured: {r.stderr.strip()}", file=sys.stderr)
            return r.returncode
        original = r.stdout.strip()
        if original.startswith("https://"):
            u = urlparse(original)
            netloc = f"x-access-token:{token}@{u.netloc}"
            authed = urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))
        else:
            print(f"[backup] non-HTTPS remote '{original}'; cannot inject token", file=sys.stderr)
            return 1
        r = _git("push", authed, f"HEAD:{args.branch}")
        if r.returncode != 0:
            print(f"[backup] git push failed:\n{r.stderr}", file=sys.stderr)
            return r.returncode
        print(f"[backup] pushed HEAD -> {args.branch} (HTTPS, token in URL)")
    else:
        r = _git("push", "origin", f"HEAD:{args.branch}")
        if r.returncode != 0:
            print(f"[backup] git push failed:\n{r.stderr}", file=sys.stderr)
            return r.returncode
        # Auth: SSH (key in ~/.ssh/config) or HTTPS (cached creds / GCM)
        remote_url = _git("config", "--get", "remote.origin.url").stdout.strip()
        if remote_url.startswith("git@") or remote_url.startswith("ssh://"):
            print(f"[backup] pushed HEAD -> {args.branch} (SSH key)")
        else:
            print(f"[backup] pushed HEAD -> {args.branch} (HTTPS, cached creds)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
