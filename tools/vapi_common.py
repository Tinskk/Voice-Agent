"""Vapi REST API access shared by tools/ scripts.

Vapi's API surface has moved fast (Custom Functions -> the unified Tools API
in 2026) and field names can drift between the docs and what a given account
actually accepts. If a call here gets rejected with a validation error, the
fix is almost always: read the error message, adjust the JSON body being
built in the calling script to match, and record what changed in
workflows/setup_vapi_assistant.md's "Notes & learnings" so the next run
starts smarter — this is the same self-improvement loop the rest of the
project follows, not a sign something is fundamentally wrong here.

Reads VAPI_API_KEY from .env.
"""

from __future__ import annotations

import requests

from common import env, fail

BASE_URL = "https://api.vapi.ai"


def _headers() -> dict:
    api_key = env("VAPI_API_KEY", required=True)
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def request(method: str, path: str, *, json: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    response = requests.request(method, url, headers=_headers(), json=json, timeout=30)
    if not response.ok:
        fail(
            f"Vapi API {method} {path} failed: {response.status_code} {response.text}",
            hint="Check the request body shape against https://docs.vapi.ai/api-reference — Vapi's schema evolves; adjust and log the fix in workflows/setup_vapi_assistant.md.",
        )
    if not response.content:
        return {}
    return response.json()


def get(path: str) -> dict:
    return request("GET", path)


def post(path: str, body: dict) -> dict:
    return request("POST", path, json=body)


def patch(path: str, body: dict) -> dict:
    return request("PATCH", path, json=body)
