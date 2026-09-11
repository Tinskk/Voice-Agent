"""Push the current Menu sheet into the live Vapi assistant's system prompt.

Convenience wrapper: re-runs create_or_update_vapi_assistant.py's full flow,
which always re-renders the menu block from the sheet before building the
system prompt. That flow is idempotent (matches tools/assistant by cached ID
and PATCHes them), so re-running it just to pick up a menu edit is safe and
doesn't duplicate anything.

    python tools/refresh_menu_context.py

Run this any time the business owner edits prices/items in the Menu sheet and
wants the change to actually reach the live assistant (see the "menu is
prompt-embedded, not a live tool" design note in workflows/setup_vapi_assistant.md).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from common import emit, fail, log

TOOLS_DIR = Path(__file__).resolve().parent


def main() -> None:
    log("refreshing assistant from current Menu sheet contents...")
    result = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "create_or_update_vapi_assistant.py")],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(
            "create_or_update_vapi_assistant.py failed while refreshing the menu",
            hint=result.stdout.strip() or result.stderr.strip(),
        )

    log(result.stderr)
    emit({"refreshed": True, "underlying_result": result.stdout.strip()})


if __name__ == "__main__":
    main()
