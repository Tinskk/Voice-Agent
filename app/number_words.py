"""Convert whole-naira amounts to spoken English words.

Exists because instructing the LLM to "say this number in words" is not
reliable enough on a live call — it kept reading amounts digit-by-digit
(e.g. "three, two, zero, zero") despite explicit system-prompt instructions.
Handing it a pre-worded string to read verbatim instead of a number to
convert on the fly is deterministic and doesn't depend on model behavior.
"""

from __future__ import annotations

_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _three_digits(n: int) -> str:
    parts = []
    if n >= 100:
        parts.append(f"{_ONES[n // 100]} hundred")
        n %= 100
        if n:
            parts.append("and")
    if n >= 20:
        tens_word = _TENS[n // 10]
        ones_digit = n % 10
        parts.append(f"{tens_word}-{_ONES[ones_digit]}" if ones_digit else tens_word)
    elif n > 0:
        parts.append(_ONES[n])
    return " ".join(parts)


def number_to_words(n: int) -> str:
    if n == 0:
        return "zero"

    negative = n < 0
    n = abs(n)

    chunks = []
    for divisor, name in ((1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")):
        if n >= divisor:
            chunks.append(f"{_three_digits(n // divisor)} {name}")
            n %= divisor
    if n > 0 or not chunks:
        chunks.append(_three_digits(n))

    words = " ".join(chunks)
    return f"negative {words}" if negative else words


def naira_words(amount: float) -> str:
    """Rounds to the nearest whole naira — spoken amounts don't need kobo precision."""
    return f"{number_to_words(round(amount))} naira"
