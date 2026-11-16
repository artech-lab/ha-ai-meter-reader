# SPDX-License-Identifier: GPL-3.0-or-later
"""Prompt, output schema and parsing of one meter reading.

Pure Python, no Home Assistant imports besides the constants. The prompt is in
English on purpose: it is short, numbered and asks for digits only, which small
local vision models follow best. The model never does arithmetic: it copies the
digits it sees, and the decimal point and every check are applied here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Any

from .const import MIN_CONFIDENCE, MeterType


class Problem(StrEnum):
    """Why a frame did not give a usable number."""

    UNREADABLE = "unreadable"  # a digit was marked unreadable, or nothing was read
    WRONG_DIGITS = "wrong_digits"  # more digits than the counter has


_METER_NAMES = {MeterType.WATER: "water", MeterType.GAS: "gas", MeterType.ENERGY: "electricity or heat"}
UNREADABLE_MARK = "X"

STRUCTURE: dict[str, Any] = {
    # No minimum/maximum on numbers: some providers reject them in structured
    # output schemas. The range is enforced by parse_reading().
    "digits": {
        "description": "Counter digits left to right, leading zeros included, X for an unreadable digit",
        "required": True,
        "selector": {"text": {}},
    },
    "confidence": {
        "description": "0-10: how sure you are of every single digit",
        "required": True,
        "selector": {"number": {"mode": "box"}},
    },
}


def build_instructions(meter_type: MeterType, digits: int = 0, decimals: int = 0, notes: str = "") -> str:
    """The instructions sent to the AI Task entity with one camera frame."""
    rules = ["Include leading zeros. No spaces, separators, units or decimal point."]
    if digits:
        rules.append(f"The counter has exactly {digits} digits: write all {digits}.")
    if decimals:
        rules.append(
            f"The last {decimals} digit(s) are the decimal part (often red, or on a coloured background): "
            "include them, without a decimal point."
        )
    rules += [
        "A wheel caught between two numbers: write the LOWER one (between 9 and 0, write 9).",
        f"A digit that is blurred, hidden, reflected or not clearly readable: write {UNREADABLE_MARK} in its place. "
        f"Never guess a digit. If you cannot find the counter at all, write {UNREADABLE_MARK}.",
        "Ignore serial numbers, labels, barcodes, small dials and pointers.",
    ]
    numbered = "\n".join(f"{n}. {rule}" for n, rule in enumerate(rules, 1))
    owner = (
        f"\nNOTES FROM THE OWNER (they override the rules above): {notes.strip()}\n" if notes and notes.strip() else ""
    )
    return f"""You read the counter of a {_METER_NAMES[meter_type]} meter from ONE photo, like a meter reader \
would. Copy the digits you see; never calculate, never estimate.

TASK: write the digits of the counter (the row of number wheels or the display) from left to right, exactly as \
printed.

RULES:
{numbered}
{owner}
IMAGE BASELINE: small meter cameras give dim, noisy, colour-tinted close-ups with a bright flash spot. Such an \
image IS readable when the digits are sharp.

CONFIDENCE 0-10: how sure you are of every single digit. 0-3 digits not readable, 5-6 some doubt, \
7-8 typical clear frame, 9-10 every digit unmistakable."""


@dataclass(frozen=True)
class Reading:
    """Parsed output of one frame."""

    digits: str  # as returned, cleaned of separators and spaces
    value: float | None  # None when the frame gave no usable number
    confidence: int
    problem: Problem | None


def _score(value: Any) -> int:
    """Clamp a 0-10 score; anything non-numeric counts as 0."""
    try:
        number = round(float(value))
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(10, number))


def parse_reading(data: Any, digits: int = 0, decimals: int = 0) -> Reading:
    """Validate the structured output of the AI. Raises ValueError if it is not an answer at all."""
    if not isinstance(data, dict) or "digits" not in data:
        raise ValueError("the AI response has no digits")
    raw = re.sub(r"[\s.,'_\-]", "", str(data.get("digits") or "")).upper()
    confidence = _score(data.get("confidence"))
    if not raw or not raw.isdigit() or confidence < MIN_CONFIDENCE:
        # Any X, a stray letter or a low confidence: nothing in this frame is trusted.
        return Reading(raw, None, confidence, Problem.UNREADABLE)
    if digits and len(raw) > digits:
        return Reading(raw, None, confidence, Problem.WRONG_DIGITS)
    # Fewer digits than expected are dropped leading zeros: harmless. A dropped
    # inner digit gives a far smaller number, which the validator rejects.
    value = int(raw) / 10**decimals if decimals else float(int(raw))
    return Reading(raw.zfill(digits) if digits else raw, round(value, decimals), confidence, None)
