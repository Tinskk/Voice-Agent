"""Retry transient Google API failures (rate limits, brief network blips)
instead of failing the whole tool call on the first hiccup.

Added after a real test call: two orders placed seconds apart succeeded, but
a third right after failed with no row written at all and no logged
exception content visible without digging into Render's logs — consistent
with a brief Google Sheets/Calendar rate limit or network error that a single
retry would likely have absorbed. Low risk of a double-write: these failures
happen before Google returns a success response, not after, so a retry is
retrying a call that didn't actually take effect the first time.
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def with_retries(fn: Callable[[], T], *, attempts: int = 3, base_delay: float = 0.75) -> T:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any transient API/network error
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(base_delay * (2**attempt))
    assert last_exc is not None
    raise last_exc
