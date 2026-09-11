"""Shared helpers for tools/.

Every tool in this directory is a standalone CLI that speaks the same contract:

    stdout  -> exactly one JSON object (the result). Nothing else.
    stderr  -> human/agent-readable logs and errors.
    exit 0  -> success. exit 1 -> handled failure. exit 2 -> bad arguments.

That contract is what lets the agent layer call a tool and parse the outcome
without guessing. Print logs with log(); print the result with emit().
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp"

load_dotenv(ROOT / ".env")


# --------------------------------------------------------------------------
# Output contract
# --------------------------------------------------------------------------

def log(message: str) -> None:
    """Progress/diagnostics. Goes to stderr so stdout stays parseable."""
    print(message, file=sys.stderr, flush=True)


def emit(data: Any, *, ok: bool = True) -> None:
    """Print the single JSON result object to stdout and exit 0."""
    print(json.dumps({"ok": ok, "data": data}, indent=2, default=str))
    sys.exit(0)


def fail(message: str, *, hint: str | None = None, code: int = 1):
    """Print a structured failure to stdout, the message to stderr, and exit.

    `hint` should say what the agent can do about it — which env var is
    missing, which argument was wrong, whether a retry is worth trying.
    """
    log(f"ERROR: {message}" + (f"\nHINT: {hint}" if hint else ""))
    print(json.dumps({"ok": False, "error": message, "hint": hint}, indent=2))
    sys.exit(code)


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def env(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    """Read a variable from .env. Fails with a usable hint when required and unset."""
    value = os.getenv(name, default)
    if required and not value:
        fail(
            f"Missing required environment variable: {name}",
            hint=f"Add {name}=... to .env (see .env.example). Never hardcode it in a tool.",
        )
    return value


# --------------------------------------------------------------------------
# Intermediates
# --------------------------------------------------------------------------

def tmp_path(name: str, *, subdir: str | None = None) -> Path:
    """Path inside .tmp/ for a disposable intermediate. Creates parent dirs."""
    target = TMP / subdir if subdir else TMP
    target.mkdir(parents=True, exist_ok=True)
    return target / name


def stamp() -> str:
    """UTC timestamp safe for filenames: 20260813T142530Z."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    log(f"wrote {path.relative_to(ROOT)}")
    return path


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    log(f"wrote {path.relative_to(ROOT)}")
    return path
