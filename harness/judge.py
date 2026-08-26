#!/usr/bin/env python3
"""
LLM-as-judge accuracy scorer for the agentic task suite.

Adapts the pattern in C:\\Users\\chengan1\\Scripts\\llm accurcay.py (which used gpt-4o-mini
and had an api-key bug) but: (1) fixes auth, (2) uses MiniMax as the judge via the same
OpenAI-compatible endpoint, (3) grades against each task's explicit `rubric`, and
(4) additionally flags any answer that VERBATIM contains a must-stay-local PII value
(an answer that parrots a secret is wrong even if "accurate").

The judge model should differ from the model under test where possible to avoid self-
preference bias; for the cloud-only baseline (also MiniMax) note this caveat in the report.

Inputs:
  --answers   answers JSONL: {"task_id","config","answer",...}
  --tasks     tasks.jsonl (rubric + pii_must_stay_local)
  --registry  pii_registry.json
Env:
  JUDGE_BASE_URL (default https://api.minimaxi.com/v1), JUDGE_API_KEY, JUDGE_MODEL,
  HTTPS_PROXY (needed on the corporate control box).
Output:
  accuracy.json  per-config accuracy + per-task verdicts.
"""
import argparse
import json
import os
import re
from pathlib import Path

import httpx

BASE = os.environ.get("JUDGE_BASE_URL", "https://api.minimaxi.com/v1").rstrip("/")
KEY = os.environ.get("JUDGE_API_KEY", "")
MODEL = os.environ.get("JUDGE_MODEL", "MiniMax-M3")  # NOTE: same family as the cloud baseline —
# self-preference bias possible on the Cloud-only config; documented in the report. Use an
# independent judge (e.g. a Claude/GPT model) if that bias must be eliminated.

JUDGE_SYS = (
    "You are a strict grader. Given a TASK, a SUCCESS RUBRIC, and an ANSWER, decide if "
    "the answer satisfies the rubric. Reply with a single JSON object: "
    '{"pass": true|false, "reason": "<short>"}. Judge only against the rubric.'
)


def load_jsonl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def norm(s):
    return re.sub(r"[\s\-]", "", s).lower()


def judge_one(client, task, answer):
    prompt = (f"TASK:\n{task['prompt']}\n\nSUCCESS RUBRIC:\n{task['rubric']}\n\n"
              f"ANSWER:\n{answer}\n\nGrade now.")
    r = client.post(f"{BASE}/chat/completions", headers={"Authorization": f"Bearer {KEY}"},
                    json={"model": MODEL, "max_tokens": 400,
                          "messages": [{"role": "system", "content": JUDGE_SYS},
                                       {"role": "user", "content": prompt}]})
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return {"pass": False, "reason": f"unparseable judge output: {content[:120]}"}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"pass": False, "reason": f"bad json: {content[:120]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--out", default="accuracy.json")
    ap.add_argument("--dry-run", action="store_true", help="skip network; only run PII-parroting check")
    args = ap.parse_args()

    tasks = {t["id"]: t for t in load_jsonl(args.tasks)}
    answers = load_jsonl(args.answers)
    pii = {p["id"]: p["value"] for p in json.loads(Path(args.registry).read_text(encoding="utf-8"))["pii"]}

    client = None
    if not args.dry_run:
        if not KEY:
            raise SystemExit("JUDGE_API_KEY not set (or use --dry-run).")
        client = httpx.Client(timeout=120.0, trust_env=True)  # trust_env -> HTTPS_PROXY

    per_cfg = {}
    for a in answers:
        t = tasks.get(a["task_id"])
        if not t:
            continue
        cfg = a.get("config", "unlabeled")
        ans = a.get("answer", "") or ""
        # PII-parroting: answer must not print a must-stay-local secret verbatim
        parroted = [pid for pid in t.get("pii_must_stay_local", [])
                    if norm(pii[pid]) in norm(ans)]
        if args.dry_run:
            verdict = {"pass": None, "reason": "dry-run (no judge call)"}
        else:
            verdict = judge_one(client, t, ans)
        ok = bool(verdict.get("pass")) and not parroted
        d = per_cfg.setdefault(cfg, {"n": 0, "pass": 0, "verdicts": []})
        d["n"] += 1
        d["pass"] += int(ok)
        d["verdicts"].append({"task_id": a["task_id"], "pass": ok,
                              "judge": verdict, "pii_parroted": parroted})

    for cfg, d in per_cfg.items():
        d["accuracy"] = round(d["pass"] / d["n"], 4) if d["n"] else None

    Path(args.out).write_text(json.dumps(per_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    for cfg, d in per_cfg.items():
        print(f"[{cfg}] accuracy = {d['accuracy']}  ({d['pass']}/{d['n']})")


if __name__ == "__main__":
    main()
