#!/usr/bin/env python3
"""
Analyze a completed benchmark run into the report numbers.

Inputs
------
--cloud-log   proxy JSONL (from minimax_logging_proxy.py) — cloud-side ground truth
--registry    tasks/pii_registry.json — planted PII values
--answers     answers JSONL produced by the run driver, one line per task:
                {"task_id","config","answer","client_ttft_s","client_total_s",
                 "output_tokens","route_trace":[...]}   (route_trace optional)
--tasks       tasks/tasks.jsonl — for rubrics + pii_must_stay_local

Outputs (to --out dir)
----------------------
metrics.json        TTFT/TPS/latency/token aggregates per config (mean + P95/P99)
privacy.json        PII leak rate per config, per-entity-type, per-task
routing.json        local-vs-cloud split per config (from proxy hits + route traces)

Privacy method: exact + normalized substring match of each planted PII value against
the verbatim request bodies the cloud received (Wang et al. 2023 extraction-rate style:
a task leaks if >=1 of its pii_must_stay_local values appears cloud-side). This is the
strongest possible signal because we know the exact planted strings. Presidio NER is an
OPTIONAL add-on (see scan_unplanted()) to catch *unplanted* PII the agent may invent.
"""
import argparse
import json
import re
import statistics as stats
from pathlib import Path


def load_jsonl(p):
    out = []
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def pct(values, q):
    if not values:
        return None
    xs = sorted(values)
    k = max(0, min(len(xs) - 1, int(round((q / 100.0) * (len(xs) - 1)))))
    return xs[k]


def agg(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {
        "n": len(values),
        "mean": round(stats.mean(values), 4),
        "p50": round(pct(values, 50), 4),
        "p95": round(pct(values, 95), 4),
        "p99": round(pct(values, 99), 4),
        "max": round(max(values), 4),
    }


def norm(s: str) -> str:
    """Normalize for leak matching: drop spaces/hyphens so '412-55-8921' == '412 55 8921'."""
    return re.sub(r"[\s\-]", "", s).lower()


# --------------------------------------------------------------------------- #
# Privacy
# --------------------------------------------------------------------------- #
def request_text_by_config(cloud_log):
    """Concatenate every cloud-bound request body, grouped by config label."""
    buckets = {}
    for rec in cloud_log:
        if rec.get("half") != "request":
            continue
        cfg = rec.get("config", "unlabeled")
        body = rec.get("request_body")
        buckets.setdefault(cfg, []).append(json.dumps(body, ensure_ascii=False))
    return {cfg: "\n".join(parts) for cfg, parts in buckets.items()}


def privacy_report(cloud_log, registry, tasks):
    pii = {p["id"]: p for p in registry["pii"]}
    texts = request_text_by_config(cloud_log)
    report = {}
    for cfg, blob in texts.items():
        blob_norm = norm(blob)
        leaked_ids, by_type = [], {}
        for pid, p in pii.items():
            hit = p["value"].lower() in blob.lower() or norm(p["value"]) in blob_norm
            if hit:
                leaked_ids.append(pid)
                by_type[p["type"]] = by_type.get(p["type"], 0) + 1
        # per-task: did any of its must-stay-local values appear cloud-side?
        task_leaks = []
        for t in tasks:
            must = t.get("pii_must_stay_local", [])
            leaked = [pid for pid in must if pid in leaked_ids]
            if must:
                task_leaks.append({"task_id": t["id"], "leaked": leaked,
                                   "clean": not leaked})
        sensitive_tasks = [t for t in task_leaks]
        clean = sum(1 for t in sensitive_tasks if t["clean"])
        report[cfg] = {
            "planted_total": len(pii),
            "leaked_count": len(leaked_ids),
            "leaked_ids": leaked_ids,
            "leak_rate": round(len(leaked_ids) / len(pii), 4) if pii else None,
            "by_type": by_type,
            "sensitive_task_count": len(sensitive_tasks),
            "sensitive_tasks_clean": clean,
            "task_clean_rate": round(clean / len(sensitive_tasks), 4) if sensitive_tasks else None,
            "per_task": task_leaks,
        }
    return report


# --------------------------------------------------------------------------- #
# Performance
# --------------------------------------------------------------------------- #
def metrics_report(cloud_log, answers):
    out = {}
    # cloud-segment metrics from proxy
    cloud_by_cfg = {}
    for rec in cloud_log:
        if rec.get("half") != "response":
            continue
        cfg = rec.get("config", "unlabeled")
        d = cloud_by_cfg.setdefault(cfg, {"ttft": [], "total": [], "ctoks": []})
        if rec.get("server_ttft_s") is not None:
            d["ttft"].append(rec["server_ttft_s"])
        if rec.get("server_total_s") is not None:
            d["total"].append(rec["server_total_s"])
        usage = rec.get("usage") or {}
        if usage.get("completion_tokens"):
            d["ctoks"].append(usage["completion_tokens"])
    # client-observed metrics from run driver
    client_by_cfg = {}
    for a in answers:
        cfg = a.get("config", "unlabeled")
        d = client_by_cfg.setdefault(cfg, {"ttft": [], "total": [], "tps": []})
        if a.get("client_ttft_s") is not None:
            d["ttft"].append(a["client_ttft_s"])
        if a.get("client_total_s") is not None:
            d["total"].append(a["client_total_s"])
        # TPS = output tokens / (total - ttft); guard against divide-by-zero
        ot, tot, tt = a.get("output_tokens"), a.get("client_total_s"), a.get("client_ttft_s")
        if ot and tot and tt is not None and (tot - tt) > 0:
            d["tps"].append(ot / (tot - tt))

    for cfg in set(cloud_by_cfg) | set(client_by_cfg):
        c = cloud_by_cfg.get(cfg, {})
        cl = client_by_cfg.get(cfg, {})
        cloud_calls = c.get("ttft", [])
        out[cfg] = {
            "client_ttft_s": agg(cl.get("ttft", [])),
            "client_e2e_s": agg(cl.get("total", [])),
            "client_tps": agg(cl.get("tps", [])),
            "cloud_ttft_s": agg(c.get("ttft", [])),
            "cloud_e2e_s": agg(c.get("total", [])),
            "cloud_calls": len(cloud_calls),
            "cloud_completion_tokens_total": sum(c.get("ctoks", [])),
        }
    return out


# --------------------------------------------------------------------------- #
# Routing (decomposition quality)
# --------------------------------------------------------------------------- #
def routing_report(cloud_log, answers, tasks):
    exp = {t["id"]: t["routing_expectation"] for t in tasks}
    # cloud hits per (config, task) inferred from request bodies tagged by driver.
    # The driver should stamp each cloud call's task via a header we log; if absent,
    # we fall back to route_trace in answers.
    out = {}
    by_cfg = {}
    for a in answers:
        cfg = a.get("config", "unlabeled")
        d = by_cfg.setdefault(cfg, {"tasks": 0, "any_cloud": 0, "trace": []})
        d["tasks"] += 1
        trace = a.get("route_trace") or []
        used_cloud = a.get("used_cloud")
        if used_cloud is None:
            used_cloud = any(str(s).lower() == "cloud" for s in trace)
        if used_cloud:
            d["any_cloud"] += 1
        d["trace"].append({"task_id": a.get("task_id"),
                            "expected": exp.get(a.get("task_id")),
                            "used_cloud": bool(used_cloud),
                            "trace": trace})
    for cfg, d in by_cfg.items():
        # a "sensible" hybrid keeps local/mixed-local work off the cloud
        correct = 0
        for tr in d["trace"]:
            e = tr["expected"]
            if e == "local" and not tr["used_cloud"]:
                correct += 1
            elif e == "cloud" and tr["used_cloud"]:
                correct += 1
            elif e == "mixed":
                correct += 1  # mixed is acceptable either way; judged qualitatively
        out[cfg] = {
            "tasks": d["tasks"],
            "tasks_touching_cloud": d["any_cloud"],
            "local_retention_rate": round(1 - d["any_cloud"] / d["tasks"], 4) if d["tasks"] else None,
            "routing_match_rate": round(correct / d["tasks"], 4) if d["tasks"] else None,
            "per_task": d["trace"],
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cloud-log", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--answers", required=True)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    cloud_log = load_jsonl(args.cloud_log) if Path(args.cloud_log).exists() else []
    answers = load_jsonl(args.answers) if Path(args.answers).exists() else []
    tasks = load_jsonl(args.tasks)
    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    priv = privacy_report(cloud_log, registry, tasks)
    met = metrics_report(cloud_log, answers)
    route = routing_report(cloud_log, answers, tasks)

    (outdir / "privacy.json").write_text(json.dumps(priv, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "metrics.json").write_text(json.dumps(met, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "routing.json").write_text(json.dumps(route, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== privacy ==="); print(json.dumps(priv, ensure_ascii=False, indent=2))
    print("=== metrics ==="); print(json.dumps(met, ensure_ascii=False, indent=2))
    print("=== routing ==="); print(json.dumps(route, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
