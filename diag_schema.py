import sqlite3
db = r'C:\Users\Trekker-PTL\AppData\Local\SuperClaw\llmrouter_manager\llmrouter_manager.db'
con = sqlite3.connect(db)
cur = con.cursor()

# schema for config + bundle_lifecycle
for tbl in ['config', 'bundle_lifecycle', 'model_verifications']:
    print(f"\n=== schema {tbl} ===")
    for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall():
        print(r)

print("\n=== config rows ===")
for r in cur.execute("SELECT * FROM config").fetchall():
    print(r)

print("\n=== bundle_lifecycle rows (full) ===")
for r in cur.execute("SELECT * FROM bundle_lifecycle").fetchall():
    print(r)