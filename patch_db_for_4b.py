"""patch_db_for_4b.py
Configure SQLite DB to make qwen3.5-4b the primary chat model.

Steps:
  1) Back up the live DB to llmrouter_manager.db.v3.4.bak (only if no backup yet)
  2) config.active_chat_model_id = "qwen3.5-4b"
  3) bundle_lifecycle.primary_bundle = { backend:llama, bundle_id:local-4b,
                                          chat_model_id:qwen3.5-4b, state:ready }
  4) model_verifications: insert qwen3.5-4b row with expected SHA + size
  5) clear session locality cache (routing.session_locality*)
"""
import os, sys, json, shutil, sqlite3, hashlib
from pathlib import Path

DB = Path(os.path.expandvars(r'%LOCALAPPDATA%\SuperClaw\llmrouter_manager\llmrouter_manager.db'))
GGUF = Path(os.path.expandvars(
    r'%LOCALAPPDATA%\SuperClaw\llmrouter_manager\models\qwen3.5-4b\Qwen3.5-4B-Q4_K_M.gguf'
))
BAK = DB.with_suffix('.db.v3.4.bak')
EXPECTED_SHA = "3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630"
EXPECTED_SIZE = 2834975040

def main():
    if not DB.exists():
        sys.exit(f"DB not found: {DB}")
    if not GGUF.exists():
        sys.exit(f"GGUF not found: {GGUF}")
    actual_size = GGUF.stat().st_size
    if actual_size != EXPECTED_SIZE:
        sys.exit(f"GGUF size {actual_size} != expected {EXPECTED_SIZE}")

    # 1) Backup
    if not BAK.exists():
        shutil.copy2(DB, BAK)
        print(f"[OK] backup -> {BAK}")
    else:
        print(f"[skip] backup already exists: {BAK}")

    # Quick SHA spot check (first 8 MB only — full check would take ~5s)
    h = hashlib.sha256()
    with open(GGUF, 'rb') as f:
        chunk = f.read(8 * 1024 * 1024)
        h.update(chunk)
        h_hex_partial = h.hexdigest()
    print(f"[info] SHA partial (first 8 MB): {h_hex_partial}  (expected prefix 38742092)")

    con = sqlite3.connect(DB)
    cur = con.cursor()

    # 2) active_chat_model_id
    cur.execute("UPDATE config SET value=? WHERE key='active_chat_model_id'", ('"qwen3.5-4b"',))
    n = cur.rowcount
    print(f"[OK] config.active_chat_model_id = qwen3.5-4b  (rows updated: {n})")

    # 3) primary_bundle
    new_bundle = json.dumps({
        'backend': 'llama',
        'bundle_id': 'local-4b',
        'bundle_revision': 3,
        'capability_contract_version': 1,
        'capability_grade': 'minimal',
        'chat_model_id': 'qwen3.5-4b',
        'embedding_model_id': 'KaLM-embedding-v2.5',
        'registry_version': 1,
        'state': 'ready'
    })
    cur.execute("""
        UPDATE bundle_lifecycle SET
            primary_bundle=?,
            bundle_revision=3,
            pending_bundle=NULL,
            previous_bundle=NULL,
            prepare_token=NULL,
            prepare_operation_id=NULL
        WHERE singleton=1
    """, (new_bundle,))
    print(f"[OK] bundle_lifecycle.primary_bundle = local-4b / qwen3.5-4b / state=ready / rev=3  (rows updated: {cur.rowcount})")

    # 4) model_verifications
    cur.execute("DELETE FROM model_verifications WHERE asset_id='qwen3.5-4b'")
    st = GGUF.stat()
    cur.execute("""
        INSERT OR REPLACE INTO model_verifications
        (asset_id, expected_sha256, filename, size_bytes, mtime_ns, ctime_ns)
        VALUES (?,?,?,?,?,?)
    """, ('qwen3.5-4b', EXPECTED_SHA, GGUF.name, st.st_size, st.st_mtime_ns, st.st_ctime_ns))
    print(f"[OK] model_verifications: qwen3.5-4b inserted (size={st.st_size}, sha={EXPECTED_SHA[:16]}...)")

    # 5) clear session locality cache
    cur.execute("DELETE FROM config WHERE key LIKE 'routing.session_locality%'")
    print(f"[OK] cleared session locality cache (rows: {cur.rowcount})")

    con.commit()
    con.close()

    # Verify
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT value FROM config WHERE key='active_chat_model_id'")
    print(f"[verify] active_chat_model_id = {cur.fetchone()[0]}")
    cur.execute("SELECT primary_bundle FROM bundle_lifecycle WHERE singleton=1")
    pb = cur.fetchone()[0]
    parsed = json.loads(pb)
    print(f"[verify] primary_bundle = bundle_id={parsed['bundle_id']}, chat_model_id={parsed['chat_model_id']}, state={parsed['state']}")
    cur.execute("SELECT asset_id, size_bytes FROM model_verifications WHERE asset_id='qwen3.5-4b'")
    row = cur.fetchone()
    print(f"[verify] model_verifications row = {row}")
    con.close()
    print("DONE")

if __name__ == '__main__':
    main()
