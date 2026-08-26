import sqlite3, sys
db = r'C:\Users\Trekker-PTL\AppData\Local\SuperClaw\llmrouter_manager\llmrouter_manager.db'
con = sqlite3.connect(db)
cur = con.cursor()
print("=== tables ===")
for r in cur.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall():
    print(r[0])

def show(q, label):
    print(f"\n=== {label} ===")
    try:
        for row in cur.execute(q).fetchall():
            print(row)
    except Exception as e:
        print(f"err: {e}")

show("SELECT key, value FROM config", "config (all)")
show("SELECT * FROM bundle_lifecycle", "bundle_lifecycle")
show("SELECT * FROM model_verifications", "model_verifications")
show("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%boot%'", "boot_* tables")
show("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%router%'", "router_* tables")