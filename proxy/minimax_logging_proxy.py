#!/usr/bin/env python3
"""
MiniMax logging reverse-proxy (OpenAI-compatible) for the SuperClaw hybrid benchmark.

This is the single choke point between SuperClaw's cloud slot (and the cloud-only
baseline client) and the real MiniMax endpoint. Every request/response is appended
to a JSONL log so we get, per cloud call, the GROUND TRUTH of:
  - exact payload the cloud received  -> privacy leak detection (planted PII scan)
  - token usage (prompt/completion)   -> cloud-token-volume comparison
  - server-side timing                -> TTFT (first SSE chunk) and TPS (cloud segment)

It forwards /v1/chat/completions (streaming and non-streaming) unchanged, so any
OpenAI-compatible client works. It is transport-only: it does NOT mask, alter, or
drop anything, so whatever SuperClaw sends is faithfully recorded and forwarded.

Usage:
    UPSTREAM_BASE_URL=https://api.minimaxi.com/v1 \
    UPSTREAM_API_KEY=sk-... \
    PROXY_LOG=../logs/cloud_calls.jsonl \
    python minimax_logging_proxy.py --host 0.0.0.0 --port 8900

Point clients at:  http://<proxy-host>:8900/v1  (model id = whatever M3 is called)

Dependencies: fastapi, uvicorn, httpx   (pip install fastapi uvicorn httpx)
Stdlib-only fallback is intentionally avoided; streaming passthrough needs async I/O.
"""
import argparse
import json
import os
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

UPSTREAM_BASE_URL = os.environ.get("UPSTREAM_BASE_URL", "https://api.minimaxi.com/v1").rstrip("/")
UPSTREAM_API_KEY = os.environ.get("UPSTREAM_API_KEY", "")
# Config label lets us tag whether the traffic came from the Hybrid or Cloud-only run.
CONFIG_LABEL = os.environ.get("CONFIG_LABEL", "unlabeled")
LOG_PATH = Path(os.environ.get("PROXY_LOG", "cloud_calls.jsonl"))
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MiniMax logging proxy")
_client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=15.0))

# monotonic-based id so log lines can be correlated across request/response halves
_seq = {"n": 0}


def _next_id() -> int:
    _seq["n"] += 1
    return _seq["n"]


def _log(record: dict) -> None:
    """Append one JSON record. Flushed each call so a crash never loses the trace."""
    record["ts"] = time.time()
    record["config"] = CONFIG_LABEL
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def _upstream_headers(req: Request) -> dict:
    # Forward everything except hop-by-hop / host; force our upstream auth.
    drop = {"host", "content-length", "authorization", "accept-encoding"}
    headers = {k: v for k, v in req.headers.items() if k.lower() not in drop}
    if UPSTREAM_API_KEY:
        headers["Authorization"] = f"Bearer {UPSTREAM_API_KEY}"
    return headers


@app.get("/__health")
async def health():
    return JSONResponse({
        "ok": True,
        "upstream": UPSTREAM_BASE_URL,
        "has_key": bool(UPSTREAM_API_KEY),
        "config": CONFIG_LABEL,
        "log": str(LOG_PATH),
    })


@app.api_route("/{full_path:path}", methods=["POST", "GET"])
async def proxy(full_path: str, request: Request):
    call_id = _next_id()
    body = await request.body()
    # Collapse a duplicated /v1 so clients may target either the proxy root or /v1.
    url = f"{UPSTREAM_BASE_URL}/{full_path}".replace("/v1/v1/", "/v1/")
    headers = _upstream_headers(request)

    # Parse the request body so the log is human-readable and PII-scannable.
    parsed_req = None
    is_stream = False
    if body:
        try:
            parsed_req = json.loads(body)
            is_stream = bool(parsed_req.get("stream"))
        except (json.JSONDecodeError, AttributeError):
            parsed_req = {"_raw": body.decode("utf-8", "replace")}

    _log({
        "call_id": call_id,
        "half": "request",
        "path": full_path,
        "stream": is_stream,
        # full request body is the privacy ground truth -> keep it verbatim
        "request_body": parsed_req,
    })

    t0 = time.perf_counter()

    if is_stream:
        # Stream passthrough while timing first chunk (server TTFT) and counting chunks.
        async def event_stream():
            first_token_dt = None
            chunk_count = 0
            collected = []
            usage = None
            req_stream = _client.stream("POST", url, headers=headers, content=body)
            async with req_stream as upstream:
                async for raw in upstream.aiter_bytes():
                    if raw:
                        chunk_count += 1
                        if first_token_dt is None:
                            first_token_dt = time.perf_counter() - t0
                        collected.append(raw)
                        # try to sniff usage out of the final SSE data frame
                        text = raw.decode("utf-8", "replace")
                        for line in text.splitlines():
                            if line.startswith("data:") and '"usage"' in line:
                                try:
                                    usage = json.loads(line[5:].strip()).get("usage")
                                except json.JSONDecodeError:
                                    pass
                    yield raw
            total_dt = time.perf_counter() - t0
            body_text = b"".join(collected).decode("utf-8", "replace")
            _log({
                "call_id": call_id,
                "half": "response",
                "stream": True,
                "server_ttft_s": first_token_dt,
                "server_total_s": total_dt,
                "sse_chunks": chunk_count,
                "usage": usage,
                # verbatim response so PII the cloud *returned* is also captured
                "response_raw": body_text,
            })
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # Non-streaming
    resp = await _client.post(url, headers=headers, content=body)
    total_dt = time.perf_counter() - t0
    try:
        parsed_resp = resp.json()
        usage = parsed_resp.get("usage")
    except (json.JSONDecodeError, ValueError):
        parsed_resp = {"_raw": resp.text}
        usage = None
    _log({
        "call_id": call_id,
        "half": "response",
        "stream": False,
        "server_total_s": total_dt,
        "status": resp.status_code,
        "usage": usage,
        "response_body": parsed_resp,
    })
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8900)
    args = ap.parse_args()
    if not UPSTREAM_API_KEY:
        print("[warn] UPSTREAM_API_KEY is empty — set it before real runs.")
    print(f"[proxy] {args.host}:{args.port} -> {UPSTREAM_BASE_URL} (config={CONFIG_LABEL}) log={LOG_PATH}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
