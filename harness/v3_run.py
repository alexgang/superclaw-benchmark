#!/usr/bin/env python3
"""v3 run driver: POSTs each task to SuperClaw gateway (127.0.0.1:18321) with
model=auto. The router decides local vs cloud. Captures TTFT + answer + route.
"""
import argparse, json, os, re, statistics, sys, time
from pathlib import Path
import httpx

WORKSPACE_INLINES = {
    "contacts.csv": "name,role,phone,email,note\nDana Whitfield,primary-care patient,+1-415-555-0197,dana.whitfield@northlake-clinic.example,annual checkup due\nMiriam Okafor,HR contact,+1-206-555-0143,m.okafor@brightpath-hr.example,\nLiang Zhao,engineering manager,,,Q3 hiring freeze\n",
    "patient_intake.txt": "Patient: Dana Whitfield\nDOB: 1986-03-24\nMRN: MRN-7742199\nSSN: 412-55-8921\nAddress: 1487 Cedar Hollow Rd, Bellevue WA 98004\nChief complaint: tachycardia on exertion, 2 weeks.\nReferral: cardiology.\n",
    "deploy_config.env": "STRIPE_API_KEY=sk-live-9f3a71bd42ee4c0e8be1770c9d2f5a6b\nDATABASE_URL=postgres://app:Hn7$mVq2!raptor@db.internal:5432/prod\nPAYMENT_PROCESSOR_CC=4539-8821-0067-3345\n",
    "payroll_note.md": "# Payroll adjustment\n\nSubject: Miriam Okafor (m.okafor@brightpath-hr.example)\nSSN-on-file: 203-88-4417\nBank IBAN: GB29 NWBK 6016 1331 9268 19\nDecision: +4% cost-of-living adjustment, back-dated to Q1.\n",
    "sales_region.csv": "region,Q1,Q2,Q3,Q4\nnorth,100,120,150,180\nsouth,90,110,140,160\neast,80,85,95,110\nwest,150,170,260,195\n",
    "meeting_notes.md": "# 2026-08-04 sync\n\nOpen: time complexity of dedup() in algo.py?\nClosed: CI green.\n",
    "algo.py": "def dedup(xs):\n    out = []\n    for x in xs:\n        if x not in out:\n            out.append(x)\n    return out\n",
}

def inline_for(prompt):
    blocks = []
    pl = prompt.lower()
    for fname, content in WORKSPACE_INLINES.items():
        stem = fname.split(".")[0]
        if stem in pl or fname in pl:
            blocks.append(content)
    return "\n".join(blocks)


def run_one(client, task, max_tokens, timeout):
    user_prompt = task["prompt"]
    ctx = inline_for(user_prompt)
    messages = []
    if ctx:
        messages.append({"role": "system", "content": ctx})
    messages.append({"role": "user", "content": user_prompt})

    payload = {"model": "auto", "messages": messages, "max_tokens": max_tokens, "stream": True}
    t0 = time.perf_counter()
    ttft = None
    chunks = 0
    text = []
    usage = None
    model_id = None
    resp = None
    try:
        resp = client.post("http://127.0.0.1:18321/v1/chat/completions", json=payload, timeout=timeout)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith("data:"):
                s = line[5:].strip()
                if s == "[DONE]":
                    break
                chunks += 1
                if ttft is None:
                    ttft = time.perf_counter() - t0
                try:
                    o = json.loads(s)
                    if o.get("model") and not model_id:
                        model_id = o["model"]
                    cs = o.get("choices") or []
                    if cs:
                        d = cs[0].get("delta", {})
                        if "content" in d and d["content"]:
                            text.append(d["content"])
                    if o.get("usage"):
                        usage = o["usage"]
                except json.JSONDecodeError:
                    pass
    except httpx.HTTPError as e:
        return {"task_id": task["id"], "answer": "", "client_ttft_s": None,
                "client_total_s": round(time.perf_counter() - t0, 4),
                "output_tokens": 0, "model": None, "route": "error", "error": f"{type(e).__name__}: {e}"}
    finally:
        if resp is not None:
            resp.close()

    total = round(time.perf_counter() - t0, 4)
    ans = _strip_think("".join(text))
    ct = (usage or {}).get("completion_tokens", 0)
    route = "local" if model_id and "qwen" in model_id.lower() else ("cloud" if model_id and ("M3" in model_id or "minimax" in model_id.lower()) else "?")
    return {"task_id": task["id"], "answer": ans,
            "client_ttft_s": round(ttft, 4) if ttft else None,
            "client_total_s": total, "output_tokens": ct,
            "model": model_id, "route": route}


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
def _strip_think(t):
    return _THINK.sub("", t or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--perf-weight", type=float, required=True)
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--tasks", default=str(Path(__file__).resolve().parent.parent / "tasks" / "tasks.jsonl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=2048)
    args = ap.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    tasks = [json.loads(l) for l in Path(args.tasks).read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"[v3] perf_weight={args.perf_weight} rep={args.rep} tasks={len(tasks)}")

    with httpx.Client() as c:
        for i, t in enumerate(tasks, 1):
            t0 = time.perf_counter()
            r = run_one(c, t, args.max_tokens, 300.0)
            dt = time.perf_counter() - t0
            print(f"  [{i:02d}/{len(tasks)}] {t['id']:>4} ({t.get('category','?')[:18]:18}) -> "
                  f"{r.get('route','?'):5} {r.get('model','?'):20} ttft={r.get('client_ttft_s')}s "
                  f"tokens={r.get('output_tokens')} ({dt:.1f}s wall)")
            with open(args.out, "a", encoding="utf-8") as f:
                f.write(json.dumps({**r, "perf_weight": args.perf_weight, "rep": args.rep,
                                    "expected_route": t.get("routing_expectation")}) + "\n")


if __name__ == "__main__":
    main()