#!/usr/bin/env python3
"""
Swap SuperClaw's primary_bundle from local-0-8b to local-4b.

The router's registry (bundles.builtin.json + models.builtin.json) already knows
about qwen3.5-4b. We just need:
  1. The GGUF on disk at the expected path (already there from manual download).
  2. The DB row for bundle_lifecycle.primary_bundle to point at local-4b.
  3. The DB row for model_verifications to have the qwen3.5-4b entry (SHA + size).
  4. The config.active_chat_model_id to say "qwen3.5-4b".

Then kill llmrouter_manager (servicehub will restart it) and the router will
load the new bundle on boot, writing a fresh llama-router.ini with the MTP
extra_args, spawning a child llama-server on a free port.

Idempotent: re-running just confirms the rows are correct.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time

DB_PATH = os.path.expandvars(r"%LOCALAPPDATA%\SuperClaw\llmrouter_manager\llmrouter_manager.db")
MODEL_DIR = os.path.expandvars(
    r"%LOCALAPPDATA%\SuperClaw\llmrouter_manager\models\qwen3.5-4b"
)
GGUF_NAME = "Qwen3.5-4B-Q4_K_M.gguf"
EXPECTED_SHA = "3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630"
EXPECTED_SIZE = 2_834_975_040


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            c = f.read(8 * 1024 * 1024)
            if not c:
                break
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Actually write to the DB. Without this, dry-run only.")
    ap.add_argument("--skip-verify", action="store_true",
                    help="Skip SHA256 verification (for testing only).")
    args = ap.parse_args()

    gguf_path = os.path.join(MODEL_DIR, GGUF_NAME)

    # 1. Sanity-check the GGUF
    if not os.path.exists(gguf_path):
        print(f"[err] GGUF not found at {gguf_path}", file=sys.stderr)
        return 1
    size = os.path.getsize(gguf_path)
    print(f"[info] GGUF size = {size} bytes (expected {EXPECTED_SIZE})")
    if size != EXPECTED_SIZE:
        print(f"[err] size mismatch", file=sys.stderr)
        return 1

    if not args.skip_verify:
        sha = sha256_of(gguf_path)
        print(f"[info] SHA256 = {sha}")
        if sha != EXPECTED_SHA:
            print(f"[err] SHA mismatch (expected {EXPECTED_SHA})", file=sys.stderr)
            return 1
        print("[ok] SHA matches registry")

    # 2. Open DB (read-only first to inspect; reopen for write if --apply)
    ro = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rc = ro.cursor()

    print("[info] current config.active_chat_model_id:")
    rc.execute("SELECT value FROM config WHERE key='active_chat_model_id'")
    print(" ", rc.fetchone())

    print("[info] current bundle_lifecycle.primary_bundle (singleton=1):")
    rc.execute("SELECT primary_bundle FROM bundle_lifecycle WHERE singleton=1")
    cur = rc.fetchone()
    print(" ", cur)
    ro.close()

    new_bundle_json = json.dumps({
        "backend": "llama",
        "bundle_id": "local-4b",
        "bundle_revision": 1,
        "capability_contract_version": 1,
        "capability_grade": "minimal",
        "chat_model_id": "qwen3.5-4b",
        "embedding_model_id": "KaLM-embedding-v2.5",
        "registry_version": 1,
        "state": "ready",
    }, separators=(", ", ": "))

    print("\n[plan] will write:")
    print(f"  config.active_chat_model_id -> '\"qwen3.5-4b\"'")
    print(f"  bundle_lifecycle.primary_bundle (singleton=1) -> {new_bundle_json}")
    st = os.stat(gguf_path)
    mtime_ns = st.st_mtime_ns
    ctime_ns = st.st_ctime_ns
    print(f"  model_verifications row for qwen3.5-4b (sha={EXPECTED_SHA[:16]}..., size={size}, mtime_ns={mtime_ns}, ctime_ns={ctime_ns})")

    if not args.apply:
        print("\n[dry-run] pass --apply to write changes")
        return 0

    # 3. Apply edits in a write transaction
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        cur.execute("UPDATE config SET value=? WHERE key='active_chat_model_id'",
                    ('"qwen3.5-4b"',))
        cur.execute("UPDATE bundle_lifecycle SET primary_bundle=? WHERE singleton=1",
                    (new_bundle_json,))
        cur.execute("""INSERT OR REPLACE INTO model_verifications
                       (asset_id, expected_sha256, filename, size_bytes, mtime_ns, ctime_ns)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    ("qwen3.5-4b", EXPECTED_SHA, GGUF_NAME, size, mtime_ns, ctime_ns))
        con.commit()
        print("[ok] DB updates committed")
    except Exception as e:
        con.rollback()
        print(f"[err] transaction failed: {e}", file=sys.stderr)
        return 1
    finally:
        con.close()

    # 4. Verify
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT value FROM config WHERE key='active_chat_model_id'")
    print("[verify] config.active_chat_model_id =", cur.fetchone()[0])
    cur.execute("SELECT primary_bundle FROM bundle_lifecycle WHERE singleton=1")
    print("[verify] bundle_lifecycle.primary_bundle =", cur.fetchone()[0])
    cur.execute("SELECT asset_id, size_bytes FROM model_verifications WHERE asset_id='qwen3.5-4b'")
    print("[verify] model_verifications[qwen3.5-4b] =", cur.fetchone())
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())