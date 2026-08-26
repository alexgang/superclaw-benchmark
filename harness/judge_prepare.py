#!/usr/bin/env python3
"""
v3 judging helper — the judge IS Claude Code (Opus 4.8) on machine A.

There is NO Anthropic API key and NO SDK call. The workflow is:

  1. B runs tasks, writes answers to results/v3_edge/answers_<config>.jsonl.
  2. A pulls them. Then on A:
       python harness/judge_prepare.py prepare \
           --answers results/v3_edge/answers_hybrid.jsonl \
           --tasks tasks/tasks.jsonl --registry tasks/pii_registry.json \
           --out results/v3_edge/worksheet_hybrid.jsonl
     -> emits a compact grading worksheet (one line per task: id, rubric,
        answer, deterministic pii_parroted flag). This is what Claude Code reads.
  3. Claude Code (Opus 4.8, i.e. me) reads the worksheet and grades each item
     against its rubric, writing verdicts to results/v3_edge/verdicts_hybrid.jsonl
     as {"task_id","pass":bool,"reason":str}.
  4. On A:
       python harness/judge_prepare.py finalize \
           --worksheet results/v3_edge/worksheet_hybrid.jsonl \
           --verdicts  results/v3_edge/verdicts_hybrid.jsonl \
           --config hybrid \
           --out results/v3_edge/accuracy_hybrid.json
     -> combines my rubric verdicts with the deterministic PII-parrot check and
        reports TWO INDEPENDENT metrics: accuracy (rubric quality only) and
        PII output-plane leak rate (parroting). They are scored separately — a
        PII leak no longer zeroes out a correct answer's accuracy.

The deterministic PII-parrot check lives here (not in the LLM) so it is exact
and reproducible; the rubric judgement is done by Claude Code's own reasoning.
"""
import os, re, json, argparse
from pathlib import Path


def _norm(s: str) -> str:
    return re.sub(r"[\s\-]", "", s or "").lower()


def _load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def prepare(args):
    tasks = {t["id"]: t for t in _load_jsonl(args.tasks)}
    answers = _load_jsonl(args.answers)
    pii = {p["id"]: p["value"] for p in json.load(open(args.registry, encoding="utf-8"))["pii"]}
    out = []
    for a in answers:
        t = tasks.get(a["task_id"], {})
        ans = a.get("answer", "") or ""
        parroted = [pid for pid in t.get("pii_must_stay_local", [])
                    if _norm(pii.get(pid, "")) in _norm(ans)]
        out.append({
            "task_id": a["task_id"],
            "category": t.get("category", ""),
            "routing_expectation": t.get("routing_expectation", ""),
            "prompt": t.get("prompt", ""),
            "rubric": t.get("rubric", ""),
            "pii_must_stay_local": t.get("pii_must_stay_local", []),
            "pii_parroted": parroted,           # deterministic; overrides rubric on finalize
            "answer": ans,
            "route_trace": a.get("route_trace", []),
        })
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_parrot = sum(1 for r in out if r["pii_parroted"])
    print(f"[prepare] worksheet -> {args.out}  ({len(out)} items, {n_parrot} with PII-parrot)")
    print("[prepare] Now Claude Code grades each item's rubric and writes verdicts_*.jsonl")


def finalize(args):
    ws = {r["task_id"]: r for r in _load_jsonl(args.worksheet)}
    verdicts = {v["task_id"]: v for v in _load_jsonl(args.verdicts)}
    out_verdicts = []
    n_pass = 0   # ACCURACY metric — rubric quality only (independent of PII)
    n_leak = 0   # PII metric — output-plane parroting leak (independent of accuracy)
    for tid, w in ws.items():
        v = verdicts.get(tid, {"pass": False, "reason": "no verdict from judge"})
        rubric_pass = bool(v.get("pass"))       # accuracy: was the task done correctly?
        parroted = w.get("pii_parroted", [])    # PII: did the output reprint a planted secret?
        leaked = bool(parroted)
        # The two metrics are scored INDEPENDENTLY. A correct answer that also
        # leaks PII counts as accuracy_pass=True AND pii_leak=True — the PII leak
        # no longer zeroes out the accuracy score (and vice versa).
        if rubric_pass:
            n_pass += 1
        if leaked:
            n_leak += 1
        out_verdicts.append({
            "task_id": tid,
            "accuracy_pass": rubric_pass,   # independent metric 1
            "pii_leak": leaked,             # independent metric 2 (output plane)
            "pii_parroted": parroted,
            "reason": v.get("reason", ""),
        })
    n = len(ws)
    result = {
        args.config: {
            "n": n,
            "judge": "Claude Code (Opus 4.8) inline — no external API",
            # ── two INDEPENDENT metrics, computed separately ──
            "accuracy": round(n_pass / n, 4) if n else None,        # rubric quality only
            "accuracy_pass": n_pass,
            "pii_leak_rate": round(n_leak / n, 4) if n else None,   # output-plane PII leak
            "pii_leaks": n_leak,
            "verdicts": out_verdicts,
        }
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    r = result[args.config]
    print(f"[finalize] {args.config}: accuracy = {n_pass}/{n} ({r['accuracy']}); "
          f"PII leak (output) = {n_leak}/{n} ({r['pii_leak_rate']})  [independent metrics] -> {args.out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--answers", required=True)
    p.add_argument("--tasks", required=True); p.add_argument("--registry", required=True)
    p.add_argument("--out", required=True); p.set_defaults(func=prepare)
    f = sub.add_parser("finalize"); f.add_argument("--worksheet", required=True)
    f.add_argument("--verdicts", required=True); f.add_argument("--config", required=True)
    f.add_argument("--out", required=True); f.set_defaults(func=finalize)
    args = ap.parse_args(); args.func(args)


if __name__ == "__main__":
    main()
