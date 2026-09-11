"""FastAPI webhook receiver for Vapi's custom tool calls.

Local dev:
    uvicorn main:app --reload --app-dir app       # from the project root
    # or: cd app && uvicorn main:app --reload

Production: deployed to Render — see workflows/deploy_agent_server.md.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import agent_tools
import config
import store
import vapi_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_agent")

app = FastAPI(title=f"{config.BUSINESS_NAME} Voice Agent")

_FALLBACK_MESSAGE = "Sorry, I'm having trouble checking that right now — could you give me just a moment, or should I have someone call you back?"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/vapi/tool-calls")
async def tool_calls(request: Request):
    secret = request.headers.get(vapi_client.SECRET_HEADER)
    if not vapi_client.verify_secret(secret):
        logger.warning("rejected tool-call webhook: bad/missing secret")
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    payload = await request.json()
    calls = vapi_client.parse_tool_calls(payload)
    call_ctx = vapi_client.parse_call_context(payload)

    if not calls:
        logger.info("tool-call webhook with no recognizable toolCallList — ignoring")
        return vapi_client.build_results_response([])

    results: list[tuple[str, dict]] = []
    for call in calls:
        tool_call_id = call["id"]
        name = call["name"]

        cached = store.get_cached_result(tool_call_id)
        if cached is not None:
            logger.info("tool call %s (%s) already handled — returning cached result", tool_call_id, name)
            results.append((tool_call_id, cached))
            continue

        try:
            result = agent_tools.dispatch(name, call["arguments"], call_ctx)
        except Exception:
            logger.exception("tool call %s (%s) failed", tool_call_id, name)
            result = {"error": "tool_failed", "message": _FALLBACK_MESSAGE}

        store.cache_result(tool_call_id, result)
        results.append((tool_call_id, result))

    return vapi_client.build_results_response(results)


@app.post("/vapi/events")
async def events(request: Request):
    """Log-only stub for call-lifecycle webhooks (end-of-call-report,
    status-update). Not required for v1 functionality — cheap to extend later
    for transcript-driven prompt iteration (see workflows build order)."""
    payload = await request.json()
    logger.info("vapi event: %s", payload.get("message", {}).get("type"))
    return {"status": "received"}
