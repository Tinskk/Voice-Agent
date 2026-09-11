"""Starting point for a new tool. Copy, rename, delete what you don't need.

    python tools/_template.py --input "hello" --limit 3

A tool does one deterministic job: an API call, a transform, a file operation.
It makes no judgment calls — that's the agent's job. Keep it boring.
"""

from __future__ import annotations

import argparse

from common import emit, fail, log, stamp, tmp_path, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="One-line description of the job.")
    parser.add_argument("--input", required=True, help="What this operates on.")
    parser.add_argument("--limit", type=int, default=10, help="Cap on items processed.")
    parser.add_argument("--save", action="store_true", help="Persist raw output to .tmp/.")
    args = parser.parse_args()

    if args.limit < 1:
        fail("--limit must be at least 1", hint="Pass a positive integer.", code=2)

    log(f"processing {args.input!r} (limit={args.limit})")

    # --- real work goes here -------------------------------------------------
    items = [{"index": i, "value": args.input} for i in range(args.limit)]
    # -------------------------------------------------------------------------

    if args.save:
        write_json(tmp_path(f"template_{stamp()}.json"), items)

    emit({"count": len(items), "items": items})


if __name__ == "__main__":
    main()
