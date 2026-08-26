"""
v3.5 fix — reconcile SuperClaw state so GUI shows Local + Auto (not just Cloud).

Root cause:
  1. bundle_lifecycle.primary_bundle JSON says local-4b but bundle_revision=3,
     while the global singleton.bundle_revision counter is 6 → lrm_bundle_revision_conflict
     blocks the switch; profile-state.json stays at local-0-8b.
  2. config.local_provider = "edge" but edge.configured=false; active_provider="llamacpp".
     GUI dropdown hides Local + Auto because it thinks the local provider is "edge"
     (and edge is unset).

Fix:
  - Read current global counter (6).
  - Re-write primary_bundle JSON with bundle_revision = global counter (6).
  - Update config.local_provider = "llamacpp".
  - Overwrite servicehub/capability/profile-state.json so primary_bundle points at local-4b.
  - Tell user to restart SuperClaw so the WebView refreshes.

After restart, /v1/models should still list auto + local-model + cloud-model and
the GUI's routing mode dropdown should show Local + Cloud + Auto.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

DB_PATH = os.path.expandvars(r"%LOCALAPPDATA%\SuperClaw\llmrouter_manager\llmrouter_manager.db")
PROFILE_PATH = os.path.expandvars(
    r"%LOCALAPPDATA%\SuperClaw\servicehub\capability\profile-state.json"
)


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # 1. Read current state
    cur.execute("SELECT bundle_revision, primary_bundle FROM bundle_lifecycle WHERE singleton=1")
    row = cur.fetchone()
    global_rev, primary_bundle_json = row
    pb = json.loads(primary_bundle_json)
    print(f"[read] global bundle_revision = {global_rev}")
    print(f"[read] primary_bundle.bundle_id = {pb['bundle_id']}")
    print(f"[read] primary_bundle.bundle_revision = {pb['bundle_revision']}")

    # 2. Fix: bump local-4b JSON's bundle_revision to match global counter
    if pb["bundle_id"] == "local-4b" and pb["bundle_revision"] != global_rev:
        old_rev = pb["bundle_revision"]
        pb["bundle_revision"] = global_rev
        new_json = json.dumps(pb)
        cur.execute("UPDATE bundle_lifecycle SET primary_bundle=? WHERE singleton=1", (new_json,))
        print(f"[fix] local-4b bundle_revision {old_rev} -> {global_rev}")
    elif pb["bundle_id"] == "local-4b":
        print(f"[ok] local-4b bundle_revision already matches global counter ({global_rev})")
    else:
        print(f"[err] primary_bundle is NOT local-4b (it's {pb['bundle_id']}); aborting")
        return 1

    # 3. Fix local_provider
    cur.execute("SELECT value FROM config WHERE key='local_provider'")
    cur_lp = cur.fetchone()
    cur_lp_str = json.loads(cur_lp[0]) if cur_lp else None
    print(f"[read] config.local_provider = {cur_lp_str!r}")
    if cur_lp_str != "llamacpp":
        cur.execute("UPDATE config SET value=? WHERE key='local_provider'", ('"llamacpp"',))
        print(f"[fix] local_provider 'edge' -> 'llamacpp'")
    else:
        print(f"[ok] local_provider already 'llamacpp'")

    con.commit()

    # 4. Verify
    cur.execute("SELECT bundle_revision, primary_bundle FROM bundle_lifecycle WHERE singleton=1")
    row = cur.fetchone()
    pb2 = json.loads(row[1])
    cur.execute("SELECT value FROM config WHERE key='local_provider'")
    lp2 = json.loads(cur.fetchone()[0])
    print(f"\n[verify] bundle_revision={row[0]}  primary={pb2['bundle_id']}/rev={pb2['bundle_revision']}/state={pb2['state']}")
    print(f"[verify] local_provider={lp2!r}")

    con.close()

    # 5. DELETE profile-state.json so servicehub regenerates it cleanly.
    #    Important: do NOT hand-edit it. The pydantic validator checks
    #    `target_fingerprint` (a hash) matches the new `primary_bundle`, and
    #    also keeps `active.snapshot.profile_revision` consistent. Hand-editing
    #    any of these triggers ProfileStoreCorruptionError → saga_recovery_required.
    if Path(PROFILE_PATH).exists():
        Path(PROFILE_PATH).unlink()
        print(f"\n[fix] deleted {PROFILE_PATH} (servicehub will regenerate on next boot)")
    else:
        print(f"[ok] {PROFILE_PATH} already absent")

    print("\n[DONE] Now restart SuperClaw.exe so the WebView reloads.")
    print("  Stop:  taskkill /F /IM SuperClaw.exe")
    print("  Start: 'C:\\Program Files\\Intel\\SuperClaw\\SuperClaw.exe'")
    print("  Verify: curl 127.0.0.1:18321/v1/models should show auto + local-model + cloud-model")
    return 0


if __name__ == "__main__":
    sys.exit(main())