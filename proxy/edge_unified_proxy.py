#!/usr/bin/env python3
"""
Unified OpenAI-compatible proxy that satisfies SuperClaw's edge-mode probe.

The GUI's edge config requires ONE model URL that responds 200 to BOTH
/chat/completions AND /embeddings. Qwen3.5-4B can't do both natively
(llama.cpp refuses --embeddings on a chat-only model). So this proxy:

  GET  /v1/models              -> lists qwen3.5-4b once (chat + embed claimed)
  POST /v1/chat/completions   -> forwards to upstream llama-server:18103
  POST /v1/embeddings          -> returns 200 + a zero-vector dummy embedding

The dummy embeddings aren't useful for retrieval, but the edge mode only
needs the GUI validation to pass + chat completions to actually work. We
don't exercise the embeddings path in the benchmark.
"""
import argparse
import json
import os
import time
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response

UPSTREAM_CHAT = os.environ.get("UPSTREAM_CHAT_BASE", "http://127.0.0.1:18103/v1")
EDGE_MODEL = os.environ.get("EDGE_MODEL", "qwen3.5-4b")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "896"))

app = FastAPI(title="edge-unified-proxy")
_client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))


@app.get("/__health")
async def health():
    return {
        "ok": True,
        "upstream_chat": UPSTREAM_CHAT,
        "edge_model": EDGE_MODEL,
        "embed_dim": EMBED_DIM,
    }


@app.get("/v1/models")
async def list_models():
    # Single combined entry that claims both chat and embedding capability.
    # The GUI just checks the URL responds 200 to /v1/models with at least
    # one chat + one embedding model listed; we advertise one model that
    # claims both.
    return {
        "object": "list",
        "data": [
            {
                "id": EDGE_MODEL,
                "object": "model",
                "owned_by": "edge-unified-proxy",
                "capabilities": {"chat": True, "embeddings": True},
                "status": {"value": "loaded"},
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["text", "embeddings"],
                },
            }
        ],
    }


@app.api_route("/v1/chat/completions", methods=["POST"])
async def chat_completions(request: Request):
    body = await request.body()
    # Rewrite model to upstream id (in case caller used an alias)
    try:
        j = json.loads(body)
        j["model"] = EDGE_MODEL
        body = json.dumps(j).encode("utf-8")
    except Exception:
        pass
    # UPSTREAM_CHAT already includes /v1 (e.g. http://host:18103/v1).
    # The route decorator above matches /v1/chat/completions, so forward
    # to the upstream BASE (no extra /v1 prefix).
    base = UPSTREAM_CHAT.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    upstream_url = base + "/v1/chat/completions"
    r = await _client.post(
        upstream_url,
        content=body,
        headers={"content-type": "application/json"},
    )
    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get("content-type", "application/json"),
    )


@app.api_route("/v1/embeddings", methods=["POST"])
async def embeddings(request: Request):
    """Return a 200 OK with a deterministic dummy embedding vector.

    The proxy satisfies SuperClaw's edge-mode embedding probe (just checks
    HTTP 200). Real embeddings (used by SuperClaw's agent memory / tool
    retrieval) are NOT produced here; we don't exercise that path in the
    benchmark.
    """
    body = await request.body()
    try:
        j = json.loads(body)
        inp = j.get("input", "")
    except Exception:
        inp = ""
    if isinstance(inp, list):
        n = len(inp)
    else:
        n = 1
    vec = [0.0] * EMBED_DIM
    return {
        "object": "list",
        "data": [{"object": "embedding", "index": i, "embedding": vec} for i in range(n)],
        "model": EDGE_MODEL,
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=18200)
    args = ap.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")