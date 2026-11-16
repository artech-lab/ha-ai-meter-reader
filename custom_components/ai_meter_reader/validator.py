# SPDX-License-Identifier: GPL-3.0-or-later
"""Plausibility check of the readings: pure Python, no Home Assistant imports.

A meter counter only grows, and only so fast. ``ReadingValidator`` keeps the
last accepted value and decides what to do with each new reading:

- growth up to the allowed increase → accepted;
- a decrease → rejected (a misread digit or a wheel between two numbers);
- growth above the allowed increase → held back until the next readings
  confirm it (``CONFIRMATIONS`` in a row, each consistent with the previous
  one). A single misread digit never reaches the statistics, while a real jump
  (a long camera outage, heavy use) is accepted after a short delay. The first
  reading of a new meter goes through the same confirmation.

The allowed increase is the "maximum increase per reading" scaled by the time
elapsed, so readings missed for a while do not lock the counter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from .const import CONFIRMATIONS

_EPSILON = 1e-9


class Outcome(StrEnum):
    """Result of the last reading, as shown by the last result sensor."""

    ACCEPTED = "accepted"
    UNCONFIRMED = "unconfirmed"  # larger than allowed: waiting for confirmation
    DECREASE = "decrease"
    UNREADABLE = "unreadable"
    WRONG_DIGITS = "wrong_digits"
    ERROR = "error"  # camera or AI failure
    CORRECTED = "corrected"  # set by hand with the set_reading action

    @property
    def failed(self) -> bool:
        """Counts towards a problem."""
        return self in (Outcome.DECREASE, Outcome.UNREADABLE, Outcome.WRONG_DIGITS, Outcome.ERROR)


@dataclass
class _Point:
    value: float
    at: datetime


class ReadingValidator:
    """Holds the accepted value and the readings waiting for confirmation."""

    def __init__(self) -> None:
        """Start without a value."""
        self.value: float | None = None
        self.value_at: datetime | None = None
        self.pending: list[_Point] = []

    @staticmethod
    def allowed(max_increase: float, elapsed: timedelta, interval: timedelta) -> float:
        """Largest plausible growth over ``elapsed``: at least one interval's worth."""
        periods = max(1.0, elapsed / interval) if interval.total_seconds() > 0 else 1.0
        return max_increase * periods

    def check(self, value: float, now: datetime, max_increase: float, interval: timedelta) -> Outcome:
        """Judge a new reading and update the accepted value."""
        if self.value is not None and self.value_at is not None:
            diff = value - self.value
            if diff < -_EPSILON:
                self.pending = []
                return Outcome.DECREASE
            if diff <= self.allowed(max_increase, now - self.value_at, interval) + _EPSILON:
                self._accept(value, now)
                return Outcome.ACCEPTED

        last = self.pending[-1] if self.pending else None
        if last is not None and -_EPSILON <= value - last.value <= (
            self.allowed(max_increase, now - last.at, interval) + _EPSILON
        ):
            self.pending.append(_Point(value, now))
        else:
            self.pending = [_Point(value, now)]
        if len(self.pending) >= CONFIRMATIONS:
            self._accept(value, now)
            return Outcome.ACCEPTED
        return Outcome.UNCONFIRMED

    def set(self, value: float, now: datetime) -> None:
        """Set the value by hand (meter replaced, first setup, correction)."""
        self._accept(value, now)

    def _accept(self, value: float, now: datetime) -> None:
        self.value = value
        self.value_at = now
        self.pending = []

    @property
    def pending_value(self) -> float | None:
        """The last reading waiting for confirmation."""
        return self.pending[-1].value if self.pending else None

    def as_dict(self) -> dict[str, Any]:
        """Serialisable state."""
        return {
            "value": self.value,
            "value_at": self.value_at.isoformat() if self.value_at else None,
            "pending": [[p.value, p.at.isoformat()] for p in self.pending],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ReadingValidator:
        """Restore from ``as_dict``; anything malformed starts empty."""
        validator = cls()
        if not isinstance(data, dict):
            return validator
        try:
            if data.get("value") is not None and data.get("value_at"):
                validator.value = float(data["value"])
                validator.value_at = datetime.fromisoformat(data["value_at"])
            validator.pending = [_Point(float(v), datetime.fromisoformat(t)) for v, t in data.get("pending") or []]
        except (TypeError, ValueError):
            return cls()
        return validator
