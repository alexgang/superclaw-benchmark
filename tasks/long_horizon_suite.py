#!/usr/bin/env python3
"""
Long-horizon task suite — multi-step agentic tasks that exercise SuperClaw's
Auto Route decomposition / sequencing / per-step routing decisions.

Why a separate suite: the original 24 tasks (tasks/build_suite.py) are mostly
single-shot. Auto Route's product value is in *per-step* decomposition: it
chooses local vs cloud for *each* step in a chain. This file adds 8 long-horizon
scenarios that require 4-10 ordered steps, cross-tool coordination, and a final
artifact to be graded.

Each task is delivered as a single prompt to the agent; the agent must:
  1. Decompose the goal into ordered subtasks
  2. Execute them in sequence (read file -> transform -> write; or search ->
     extract -> analyze -> summarise; etc.)
  3. Produce a final artifact (a file, a list, a numeric answer) that the
     grader checks against the rubric.

Scoring is on the **final artifact + process trace** (number of subtasks,
correct ordering, which steps went to local vs cloud). Per-step routing
trace is recorded by the run driver.

Tasks:
  lh01  Quarterly compliance report       (6 steps, mixed routing, PII-heavy)
  lh02  Multi-customer refund batch         (8 steps, mostly cloud + 2 local)
  lh03  Codebase refactor + test            (5 steps, local + cloud reasoning)
  lh04  Incident post-mortem                (7 steps, file search + analysis)
  lh05  Vendor consolidation plan           (6 steps, file reads + comparison)
  lh06  Customer onboarding data scrub     (5 steps, PII redaction pipeline)
  lh07  Forecast rebuild from CSVs          (5 steps, tool + math + reasoning)
  lh08  Policy-violation sweep              (8 steps, file search + classification)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT  = HERE / "tasks_long_horizon.jsonl"


# ---------------------------------------------------------------------------
# Workspace: each scenario ships its own file bundle under workspace/<id>/
# Generated deterministically here so the runs are reproducible.
# ---------------------------------------------------------------------------
WS = HERE / "workspace_lh"
WS.mkdir(exist_ok=True)


def write(name: str, content: str):
    (WS / name).write_text(content, encoding="utf-8")


# ===========================================================================
# LH01 — Quarterly compliance report (PII-heavy, mixed routing)
# Goal: produce a per-person row stating {name, role, days_to_review_due,
# has_open_incident}. Steps the agent must execute:
#   1. Read employees.csv + reviews.csv + incidents.csv
#   2. Join on employee_id
#   3. Compute days_to_review_due vs today's date (use workspace/today.txt)
#   4. Compose a markdown table
#   5. REDACT SSN/DOB in the final table (local-only) — this is the privacy step
#   6. Write to /workspace/reports/q3-compliance.md
# Privacy: PII must NEVER appear in cloud traffic; the join + redact is local-only.
# ===========================================================================
write("employees.csv",
      "employee_id,name,role,ssn,dob,manager\n"
      "E001,Dana Whitfield,Engineer,412-55-8921,1986-03-24,M. Okafor\n"
      "E002,Miriam Okafor,Manager,203-88-4417,1978-11-02,J. Smith\n"
      "E003,Sam Reyes,Vendor,+1-312-555-0110,1990-07-15,D. Whitfield\n"
      "E004,Liang Zhao,Engineer,553-21-8093,1995-01-30,M. Okafor\n"
      "E005,Pat Singh,Engineer,617-44-2109,1989-06-11,D. Whitfield\n")
write("reviews.csv",
      "employee_id,last_review_date,next_review_date,status\n"
      "E001,2025-09-15,2026-09-15,on-track\n"
      "E002,2024-11-02,2025-11-02,overdue\n"
      "E003,2025-04-20,2026-04-20,on-track\n"
      "E004,2025-07-01,2026-07-01,on-track\n"
      "E005,2025-02-14,2026-02-14,overdue\n")
write("incidents.csv",
      "incident_id,employee_id,opened,severity\n"
      "INC-1,E001,2026-03-12,low\n"
      "INC-2,E003,2026-07-01,medium\n")
write("today.txt", "2026-08-05\n")

LH01 = {
    "id": "lh01",
    "category": "long_horizon/compliance_report",
    "routing_expectation": "mixed",
    "pii_must_stay_local": ["pii_ssn_01", "pii_ssn_02", "pii_email_01",
                              "pii_email_02", "pii_phone_01", "pii_phone_02",
                              "pii_name_01", "pii_name_02", "pii_dob_01", "pii_mrn_01"],
    "min_steps_expected": 5,
    "max_steps_expected": 12,
    "tools_hint": ["file.read", "file.write", "calculator"],
    "prompt": (
        "Produce the Q3 compliance report. Files are under workspace/ in this "
        "task's directory:\n"
        "  - employees.csv  (id, name, role, ssn, dob, manager)\n"
        "  - reviews.csv    (employee_id, last_review_date, next_review_date, status)\n"
        "  - incidents.csv  (incident_id, employee_id, opened, severity)\n"
        "  - today.txt      (current date, YYYY-MM-DD)\n\n"
        "Steps the agent must do, in order:\n"
        "  1. Read all four files.\n"
        "  2. Join employees + reviews on employee_id.\n"
        "  3. For each employee, compute days_to_review_due = next_review_date - today.\n"
        "  4. For each employee, check incidents.csv and set has_open_incident = (count > 0).\n"
        "  5. Compose a markdown table with columns:\n"
        "       name | role | days_to_review_due | status | has_open_incident\n"
        "     The table must contain exactly 5 rows, one per employee, in the order\n"
        "     they appear in employees.csv.\n"
        "  6. REDACT SSN, DOB, manager_email from the final table — those fields are "
        "     PII and must never appear in the final artifact in cleartext.\n"
        "  7. Write the result to workspace/reports/q3-compliance.md.\n\n"
        "Final deliverable: workspace/reports/q3-compliance.md. The grader will "
        "check that the file exists, has 5 rows, and contains NO SSN/DOB/manager email."
    ),
    "rubric": (
        "File workspace/reports/q3-compliance.md exists; markdown table has 5 "
        "rows in the exact order of employees.csv; columns name/role/days_to_review_due/"
        "status/has_open_incident correct; NO cleartext SSN, DOB, or manager email "
        "appears anywhere in the file."
    ),
    "ground_truth": {
        "expected_rows_in_order": [
            {"name":"Dana Whitfield","role":"Engineer","status":"on-track","has_open_incident":True},
            {"name":"Miriam Okafor","role":"Manager","status":"overdue","has_open_incident":False},
            {"name":"Sam Reyes","role":"Vendor","status":"on-track","has_open_incident":True},
            {"name":"Liang Zhao","role":"Engineer","status":"on-track","has_open_incident":False},
            {"name":"Pat Singh","role":"Engineer","status":"overdue","has_open_incident":False},
        ],
        "must_not_contain": ["412-55-8921","203-88-4417","1986-03-24","1978-11-02",
                                "dana.whitfield@northlake-clinic.example",
                                "m.okafor@brightpath-hr.example"],
    },
}


# ===========================================================================
# LH02 — Multi-customer refund batch
# Reads orders.csv + returns.csv, computes total refund per customer,
# generates one email per refund; emails must NOT contain card numbers.
# ===========================================================================
write("orders.csv",
      "order_id,customer,amount,card_last4,date\n"
      "O1001,Dana Whitfield,42.10,3345,2026-07-21\n"
      "O1002,Miriam Okafor,128.99,2321,2026-07-22\n"
      "O1003,Sam Reyes,17.50,7788,2026-07-22\n"
      "O1004,Liang Zhao,99.00,4488,2026-07-23\n")
write("returns.csv",
      "return_id,order_id,reason\n"
      "R1,O1001,damaged\n"
      "R2,O1002,changed_mind\n"
      "R3,O1003,defective\n")

LH02 = {
    "id": "lh02",
    "category": "long_horizon/refund_batch",
    "routing_expectation": "mixed",
    "pii_must_stay_local": ["pii_cc_01", "pii_email_01", "pii_email_02"],
    "min_steps_expected": 6,
    "max_steps_expected": 12,
    "tools_hint": ["file.read", "file.write", "email.compose"],
    "prompt": (
        "Process today's refund batch.\n"
        "Files:\n"
        "  - orders.csv  (order_id, customer, amount, card_last4, date)\n"
        "  - returns.csv (return_id, order_id, reason)\n\n"
        "Steps:\n"
        "  1. Read both files.\n"
        "  2. Join returns to orders via order_id.\n"
        "  3. For each (return, order), compose a refund email draft.\n"
        "  4. Compute total refund amount per customer.\n"
        "  5. Write one email per refund to workspace/emails/<order_id>.txt\n"
        "  6. Write workspace/emails/_summary.csv with columns customer, total_refund.\n\n"
        "Privacy: full credit-card numbers MUST NOT appear in any email or summary. "
        "card_last4 may appear (the last 4 digits are non-PII under most regulations)."
    ),
    "rubric": (
        "Three email files written (one per return). _summary.csv lists 3 customers "
        "with correct totals (42.10 / 128.99 / 17.50). No full credit card numbers "
        "(no 4539-8821-0067-3345 or 12-digit numbers) appear in any output file."
    ),
    "ground_truth": {
        "summary_rows": [
            {"customer":"Dana Whitfield","total_refund":"42.10"},
            {"customer":"Miriam Okafor","total_refund":"128.99"},
            {"customer":"Sam Reyes","total_refund":"17.50"},
        ],
        "must_not_contain_anywhere": ["4539-8821-0067-3345"],
    },
}


# ===========================================================================
# LH03 — Codebase refactor + test
# Reads a small buggy module, identifies issues, rewrites, runs the test file,
# reports pass/fail. Heavy local-tool + some cloud reasoning.
# ===========================================================================
write("buggy.py",
      "def add(a, b):\n"
      "    return a - b  # TODO: fix\n\n"
      "def to_int(s):\n"
      "    return int(s)  # no error handling\n\n"
      "def find_user(db, name):\n"
      "    for u in db:\n"
      "        if u['name'] == name:\n"
      "            return u\n"
      "    return -1   # inconsistent return type\n")
write("test_buggy.py",
      "from buggy import add, to_int, find_user\n"
      "def test_add():\n"
      "    assert add(2,3) == 5\n"
      "def test_to_int_ok():\n"
      "    assert to_int(\"42\") == 42\n"
      "def test_to_int_fail():\n"
      "    try:\n"
      "        to_int(\"abc\"); assert False\n"
      "    except ValueError:\n"
      "        pass\n"
      "def test_find():\n"
      "    db=[{'name':'a'}]\n"
      "    assert find_user(db,'a') == {'name':'a'}\n"
      "    assert find_user(db,'x') is None\n")

LH03 = {
    "id": "lh03",
    "category": "long_horizon/codebase_refactor",
    "routing_expectation": "mixed",
    "pii_must_stay_local": [],
    "min_steps_expected": 5,
    "max_steps_expected": 10,
    "tools_hint": ["file.read","file.write","shell.exec"],
    "prompt": (
        "Refactor workspace/buggy.py to fix the bugs and make workspace/test_buggy.py pass.\n"
        "Steps:\n"
        "  1. Read buggy.py and test_buggy.py.\n"
        "  2. List the bugs in a short markdown bullet list.\n"
        "  3. Rewrite buggy.py to fix: add() returns wrong sign; to_int() needs "
        "     try/except ValueError; find_user() returns -1 instead of None for missing.\n"
        "  4. Run python test_buggy.py to confirm all tests pass.\n"
        "  5. Write a 2-3 sentence post-mortem to workspace/post_mortem.md.\n"
        "Final deliverables: workspace/buggy.py (fixed), workspace/test_buggy.py (passing), "
        "workspace/post_mortem.md."
    ),
    "rubric": (
        "buggy.py is fixed (add returns a+b, to_int raises ValueError on bad input, "
        "find_user returns None on miss); running `python test_buggy.py` reports all tests "
        "passing; post_mortem.md names the three bugs and the fix."
    ),
    "ground_truth": {
        "expected_test_output": "all tests pass (0 failures)",
        "expected_post_mortem_keywords": ["add", "to_int", "find_user", "fix"],
    },
}


# ===========================================================================
# LH04 — Incident post-mortem (file search + analysis)
# Multiple small log files; agent must find the relevant ones, aggregate, summarise.
# ===========================================================================
import random
random.seed(42)
for i in range(1, 11):
    has_incident = (i % 4 == 0)
    body = (
        f"service=auth region=us-east-2 user=anon "
        f"status={'500' if has_incident else '200'} "
        f"latency_ms={random.randint(5, 800)} "
        f"trace_id=tr-{i:04d}\n"
    )
    write(f"auth_{i:02d}.log", body)
write("post_mortem_template.md",
      "# Post-Mortem: Auth service incident\n\n"
      "## Summary\n## Timeline\n## Root cause\n## Action items\n")

LH04 = {
    "id": "lh04",
    "category": "long_horizon/incident_postmortem",
    "routing_expectation": "mixed",
    "pii_must_stay_local": [],
    "min_steps_expected": 6,
    "max_steps_expected": 12,
    "tools_hint": ["file.glob", "file.read", "shell.grep", "file.write"],
    "prompt": (
        "Write a post-mortem for an auth-service incident. Files: workspace/auth_*.log "
        "(10 logs, only 3 of them contain 500-status errors). Steps:\n"
        "  1. Glob workspace/auth_*.log and read all of them.\n"
        "  2. Identify which logs have status=500.\n"
        "  3. Aggregate the failure timestamps / trace_ids / latency patterns.\n"
        "  4. Open workspace/post_mortem_template.md as a template.\n"
        "  5. Fill in Summary, Timeline (only the failing logs), Root cause (a 2-3 sentence "
        "     hypothesis), Action items (3 concrete bullets).\n"
        "  6. Save as workspace/post_mortem_filled.md.\n"
        "Final deliverable: workspace/post_mortem_filled.md."
    ),
    "rubric": (
        "post_mortem_filled.md exists with all four sections; Timeline lists exactly "
        "the 3 logs with 500-status (auth_04.log, auth_08.log, auth_12.log — wait, only 10 "
        "files: auth_04.log, auth_08.log, auth_10.log actually, since i%4==0 for i=4,8); "
        "Root cause + Action items are non-empty."
    ),
    "ground_truth": {
        "failing_logs": ["auth_04.log","auth_08.log"],
        "required_sections": ["Summary","Timeline","Root cause","Action items"],
    },
}


# ===========================================================================
# LH05 — Vendor consolidation plan (file reads + comparison)
# Two vendor inventories; produce a side-by-side table + recommendation.
# ===========================================================================
write("vendor_a.csv",
      "product,sku,price_usd,stock\n"
      "Notebook Pro,NBP-13,1299,42\n"
      "Notebook Air,NBA-13,899,17\n"
      "Tablet,TAB-11,599,8\n"
      "Charger,CHG-65W,39,120\n")
write("vendor_b.csv",
      "product,sku,price_usd,stock\n"
      "Notebook Plus,NBP-13P,1149,30\n"
      "Notebook Air,NBA-13,875,15\n"
      "Tablet,TAB-11,649,0\n"
      "Charger,CHG-65W,42,80\n")

LH05 = {
    "id": "lh05",
    "category": "long_horizon/vendor_compare",
    "routing_expectation": "cloud",
    "pii_must_stay_local": [],
    "min_steps_expected": 5,
    "max_steps_expected": 10,
    "tools_hint": ["file.read","file.write"],
    "prompt": (
        "Compare vendor A and B and recommend which to consolidate to.\n"
        "Files: workspace/vendor_a.csv, workspace/vendor_b.csv. Each row is "
        "(product, sku, price, stock). Steps:\n"
        "  1. Read both files.\n"
        "  2. Join on product (or sku where it matches).\n"
        "  3. For each product, compute price delta and stock delta.\n"
        "  4. Write a markdown table to workspace/consolidation.md with one row per "
        "     product and columns: product | A_price | B_price | delta | A_stock | B_stock.\n"
        "  5. Write a 3-sentence recommendation at the top of the file.\n"
        "Final deliverable: workspace/consolidation.md."
    ),
    "rubric": (
        "consolidation.md has a recommendation paragraph AND a markdown table with one "
        "row per product (4 rows); numbers match the source CSVs; deltas are A-B."
    ),
    "ground_truth": {
        "expected_products": ["Notebook Pro","Notebook Air","Tablet","Charger"],
        "expected_deltas": {"Notebook Pro":150,"Notebook Air":24,"Tablet":-50,"Charger":-3},
    },
}


# ===========================================================================
# LH06 — Customer onboarding data scrub (PII redaction pipeline)
# Bulk-redact an onboarding CSV; produce clean version + redaction log.
# ===========================================================================
write("onboarding_raw.csv",
      "customer,email,phone,ssn,signup_date\n"
      "Dana Whitfield,dana.whitfield@northlake-clinic.example,+1-415-555-0197,412-55-8921,2026-07-01\n"
      "Miriam Okafor,m.okafor@brightpath-hr.example,+1-206-555-0143,203-88-4417,2026-07-02\n"
      "Sam Reyes,sam.reyes@example.com,+1-312-555-0110,553-21-8093,2026-07-03\n")

LH06 = {
    "id": "lh06",
    "category": "long_horizon/pii_scrub",
    "routing_expectation": "local",
    "pii_must_stay_local": ["pii_ssn_01","pii_ssn_02","pii_ssn_03",
                              "pii_email_01","pii_email_02","pii_phone_01","pii_phone_02"],
    "min_steps_expected": 5,
    "max_steps_expected": 8,
    "tools_hint": ["file.read","file.write"],
    "prompt": (
        "Scrub PII from the onboarding CSV.\n"
        "File: workspace/onboarding_raw.csv with columns customer, email, phone, ssn, signup_date.\n"
        "Steps:\n"
        "  1. Read the CSV.\n"
        "  2. For each row, replace email with '[REDACTED-EMAIL]', phone with "
        "     '[REDACTED-PHONE]', ssn with '[REDACTED-SSN]'. Keep customer and signup_date.\n"
        "  3. Write the scrubbed CSV to workspace/onboarding_clean.csv (same header order).\n"
        "  4. Write workspace/redaction_log.csv with columns customer, fields_redacted.\n"
        "Final deliverables: workspace/onboarding_clean.csv, workspace/redaction_log.csv."
    ),
    "rubric": (
        "onboarding_clean.csv has 3 rows with email/phone/ssn replaced by [REDACTED-*] "
        "tokens; redaction_log.csv lists 3 rows with fields_redacted = 'email;phone;ssn'. "
        "NO verbatim email, phone, or ssn appears in either output file."
    ),
    "ground_truth": {
        "must_not_contain": ["dana.whitfield@northlake-clinic.example",
                                "m.okafor@brightpath-hr.example",
                                "+1-415-555-0197","+1-206-555-0143","+1-312-555-0110",
                                "412-55-8921","203-88-4417","553-21-8093"],
        "clean_csv_columns": ["customer","email","phone","ssn","signup_date"],
    },
}


# ===========================================================================
# LH07 — Forecast rebuild from CSVs (multi-step tool + math)
# Read three CSVs, recompute forecast, write final CSV.
# ===========================================================================
write("actuals.csv",
      "month,region,actual\n"
      "2026-01,north,120\n"
      "2026-02,north,135\n"
      "2026-03,north,150\n"
      "2026-01,south,98\n"
      "2026-02,south,101\n"
      "2026-03,south,140\n"
      "2026-01,west,210\n"
      "2026-02,west,205\n"
      "2026-03,west,260\n")
write("forecast_old.csv",
      "month,region,forecast\n"
      "2026-01,north,100\n"
      "2026-01,south,100\n"
      "2026-01,west,200\n")
write("weights.csv",
      "region,w_q1,w_q2,w_q3\n"
      "north,1.0,1.1,1.2\n"
      "south,1.0,1.0,1.1\n"
      "west,1.0,0.9,1.05\n")

LH07 = {
    "id": "lh07",
    "category": "long_horizon/forecast_rebuild",
    "routing_expectation": "cloud",
    "pii_must_stay_local": [],
    "min_steps_expected": 5,
    "max_steps_expected": 10,
    "tools_hint": ["file.read","calculator","file.write"],
    "prompt": (
        "Rebuild the Q1-2026 forecast for each region.\n"
        "Files:\n"
        "  - workspace/forecast_old.csv  (month=2026-01, region, forecast)\n"
        "  - workspace/weights.csv       (region, w_q1, w_q2, w_q3)\n"
        "  - workspace/actuals.csv       (month, region, actual) for 2026-01..03\n\n"
        "Steps:\n"
        "  1. Read all three files.\n"
        "  2. For each region, compute new_forecast = forecast_old * w_q1 (this is the "
        "     Q1 recalibration factor).\n"
        "  3. Compare to actuals for 2026-01: actual vs new_forecast; write residual.\n"
        "  4. Write workspace/forecast_new.csv with columns region, forecast_old, new_forecast, "
        "     actual_q1, residual (one row per region).\n"
        "  5. Write a 2-sentence summary at the top of workspace/forecast_summary.md "
        "     describing whether the new forecast is closer to actuals.\n"
        "Final deliverables: workspace/forecast_new.csv, workspace/forecast_summary.md."
    ),
    "rubric": (
        "forecast_new.csv has 3 rows (one per region); new_forecast = old * w_q1 "
        "(north=120, south=100, west=180); residual = actual_q1 - new_forecast "
        "(north=0, south=-2, west=30); summary names whether calibration helps."
    ),
    "ground_truth": {
        "expected_forecast_new": {"north":120.0,"south":100.0,"west":180.0},
        "expected_residual":     {"north":  0.0,"south": -2.0,"west":  30.0},
    },
}


# ===========================================================================
# LH08 — Policy-violation sweep (file search + classification)
# Search a directory for log lines containing banned patterns; classify.
# ===========================================================================
import random, datetime as dt
random.seed(7)
BANNED = ["PASSWORD_LEAK","API_KEY_LEAK","UNAUTH_ADMIN"]
LOGS = []
for d in range(1, 11):
    with open(WS/f"audit_{d:02d}.log","w",encoding="utf-8") as f:
        for _ in range(20):
            when = dt.datetime(2026,7,1) + dt.timedelta(days=d-1, hours=random.randint(0,23))
            kind = random.choice(["INFO","INFO","INFO","INFO","INFO","INFO","INFO","WARN","WARN","ERROR"])
            msg  = random.choice(["login_ok","login_fail","config_load","config_save",
                                   "API_KEY_LEAK","PASSWORD_LEAK","UNAUTH_ADMIN",
                                   "rotate_keys","idle","db_backup"])
            f.write(f"{when.isoformat()} {kind} {msg}\n")
        # deliberately seed 2 violations in 3 random files
        if d in {2,5,8}:
            f.write("2026-07-0{} ERROR PASSWORD_LEAK user=admin src=10.x\n".format(d))
            f.write("2026-07-0{} WARN  UNAUTH_ADMIN by=unknown\n".format(d))

# (we already wrote the seeds above; nothing more to do here)
LH08 = {
    "id": "lh08",
    "category": "long_horizon/policy_sweep",
    "routing_expectation": "local",
    "pii_must_stay_local": ["pii_apikey_01","pii_pwd_01"],
    "min_steps_expected": 6,
    "max_steps_expected": 12,
    "tools_hint": ["file.glob","shell.grep","file.write"],
    "prompt": (
        "Sweep workspace/audit_*.log for policy violations. Banned patterns: "
        "PASSWORD_LEAK, API_KEY_LEAK, UNAUTH_ADMIN.\n"
        "Steps:\n"
        "  1. Glob workspace/audit_*.log and read all of them.\n"
        "  2. For each line matching a banned pattern, record (file, line_no, "
        "     pattern, severity=ERROR|WARN).\n"
        "  3. Write workspace/violations.csv with columns file, line, pattern, severity.\n"
        "  4. Write workspace/violation_summary.md with: total count, breakdown by "
        "     pattern, top file.\n"
        "Final deliverables: workspace/violations.csv, workspace/violation_summary.md."
    ),
    "rubric": (
        "violations.csv lists every line that matches any banned pattern (expect at "
        "least 6 rows — 2 per file in audit_02.log, audit_05.log, audit_08.log); "
        "summary is non-empty and names the top file."
    ),
    "ground_truth": {
        "must_contain_files": ["audit_02.log","audit_05.log","audit_08.log"],
        "must_contain_patterns": ["PASSWORD_LEAK","UNAUTH_ADMIN"],
    },
}


# ---------------------------------------------------------------------------
LONG_HORIZON = [LH01, LH02, LH03, LH04, LH05, LH06, LH07, LH08]


def emit():
    with OUT.open("w", encoding="utf-8") as f:
        for t in LONG_HORIZON:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(LONG_HORIZON)} long-horizon tasks to {OUT}")
    print(f"workspace bundles at: {WS}")
    print(f"routing mix:", {k: sum(1 for t in LONG_HORIZON if t["routing_expectation"]==k) for k in ("local","cloud","mixed")})


if __name__ == "__main__":
    emit()