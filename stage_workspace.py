#!/usr/bin/env python3
"""
Stage a task's workspace files into an isolated run directory (run ON machine B).

The run driver calls stage(task, run_dir) before sending the prompt, so the agent
sees exactly the files the task expects at the right relative paths.

Sources:
  - Original suite (tasks.jsonl): files already live in tasks/workspace/ (flat).
  - Long-horizon (tasks_long_horizon.jsonl): files live in tasks/workspace_lh/.
  - PinchBench (tasks_pinchbench.jsonl): files mapped by pinchbench/_staging_manifest.json
    (external data in pinchbench/data/, inline content in pinchbench/data/inline/).

Usage (library):
    from stage_workspace import stage
    stage(task_dict, "/path/to/run_workspace")

Usage (CLI, to pre-stage every task into results/workspaces/<id>/ for inspection):
    python stage_workspace.py --all --out results/workspaces
"""
import json, os, shutil, sys, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
PB_MANIFEST = os.path.join(HERE, "pinchbench", "_staging_manifest.json")


def _copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def stage(task: dict, run_dir: str):
    """Place all files a task needs into run_dir. Returns list of dest paths staged."""
    os.makedirs(run_dir, exist_ok=True)
    tid = task.get("id", "")
    staged = []

    # PinchBench: use the staging manifest (handles external + inline)
    if tid.startswith("pb_") and os.path.exists(PB_MANIFEST):
        man = json.load(open(PB_MANIFEST, encoding="utf-8"))
        for e in man.get(tid, []):
            src = os.path.join(HERE, e["local_source"]) if not os.path.isabs(e["local_source"]) else e["local_source"]
            dst = os.path.join(run_dir, e["dest"].replace("/", os.sep))
            if os.path.exists(src):
                _copy(src, dst); staged.append(e["dest"])
            else:
                print(f"  [warn] missing source for {tid}: {src}", file=sys.stderr)
        return staged

    # Long-horizon: copy the whole per-suite workspace bundle (tasks reference workspace/<file>)
    if tid.startswith("lh"):
        srcdir = os.path.join(HERE, "tasks", "workspace_lh")
        if os.path.isdir(srcdir):
            dstdir = os.path.join(run_dir, "workspace")
            for root, _, files in os.walk(srcdir):
                rel = os.path.relpath(root, srcdir)
                for fn in files:
                    _copy(os.path.join(root, fn), os.path.join(dstdir, rel, fn))
                    staged.append(os.path.join("workspace", rel, fn))
        return staged

    # Original suite: copy tasks/workspace/ (flat file set)
    srcdir = os.path.join(HERE, "tasks", "workspace")
    if os.path.isdir(srcdir):
        dstdir = os.path.join(run_dir, "workspace")
        for fn in os.listdir(srcdir):
            sp = os.path.join(srcdir, fn)
            if os.path.isfile(sp):
                _copy(sp, os.path.join(dstdir, fn)); staged.append(f"workspace/{fn}")
    return staged


def _load_all_tasks():
    tasks = []
    for f in ("tasks/tasks.jsonl","tasks/tasks_long_horizon.jsonl",
              "tasks/tasks_pinchbench.jsonl","tasks/tasks_industry.jsonl"):
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            tasks += [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    return tasks


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="pre-stage every task")
    ap.add_argument("--out", default="results/workspaces")
    args = ap.parse_args()
    if args.all:
        tasks = _load_all_tasks()
        n = 0
        for t in tasks:
            rd = os.path.join(HERE, args.out, t.get("id","unknown"))
            staged = stage(t, rd)
            if staged: n += 1
        print(f"pre-staged workspaces for {n}/{len(tasks)} tasks under {args.out}")
    else:
        print("use --all to pre-stage; or import stage() from the run driver")
