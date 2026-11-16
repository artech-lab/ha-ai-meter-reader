"""Tests for the plausibility check (pure Python)."""

from datetime import UTC, datetime, timedelta

from custom_components.ai_meter_reader.validator import Outcome, ReadingValidator

T0 = datetime(2026, 1, 1, tzinfo=UTC)
INTERVAL = timedelta(minutes=15)


def _at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _validator(value: float = 1000) -> ReadingValidator:
    validator = ReadingValidator()
    validator.set(value, T0)
    return validator


def test_normal_growth_is_accepted() -> None:
    validator = _validator()
    assert validator.check(1000, _at(15), 300, INTERVAL) is Outcome.ACCEPTED
    assert validator.check(1250, _at(30), 300, INTERVAL) is Outcome.ACCEPTED
    assert validator.value == 1250
    assert validator.value_at == _at(30)


def test_a_decrease_is_rejected() -> None:
    validator = _validator()
    assert validator.check(999, _at(15), 300, INTERVAL) is Outcome.DECREASE
    assert validator.value == 1000


def test_a_single_misread_digit_never_passes() -> None:
    validator = _validator(1250922)
    assert validator.check(1950922, _at(15), 300, INTERVAL) is Outcome.UNCONFIRMED
    assert validator.value == 1250922
    assert validator.pending_value == 1950922
    # The next reading is the real one: accepted, and the misread is forgotten.
    assert validator.check(1250950, _at(30), 300, INTERVAL) is Outcome.ACCEPTED
    assert validator.pending_value is None


def test_a_real_jump_is_accepted_once_confirmed() -> None:
    validator = _validator()
    # The camera was offline for a while, but only one interval passed since the last value.
    assert validator.check(2000, _at(15), 300, INTERVAL) is Outcome.UNCONFIRMED
    assert validator.check(2010, _at(30), 300, INTERVAL) is Outcome.ACCEPTED
    assert validator.value == 2010


def test_inconsistent_jumps_restart_the_confirmation() -> None:
    validator = _validator()
    assert validator.check(5000, _at(15), 300, INTERVAL) is Outcome.UNCONFIRMED
    assert validator.check(9000, _at(30), 300, INTERVAL) is Outcome.UNCONFIRMED
    assert validator.check(4000, _at(45), 300, INTERVAL) is Outcome.UNCONFIRMED  # lower than 9000: restart
    assert validator.check(4100, _at(60), 300, INTERVAL) is Outcome.ACCEPTED
    assert validator.value == 4100


def test_the_allowed_increase_grows_with_the_time_elapsed() -> None:
    validator = _validator()
    # Two hours without readings: up to 8 intervals' worth is plausible.
    assert validator.allowed(300, timedelta(hours=2), INTERVAL) == 2400
    assert validator.allowed(300, timedelta(minutes=1), INTERVAL) == 300
    assert validator.check(3300, _at(120), 300, INTERVAL) is Outcome.ACCEPTED


def test_the_first_reading_needs_confirmation() -> None:
    validator = ReadingValidator()
    assert validator.check(1000, _at(0), 300, INTERVAL) is Outcome.UNCONFIRMED
    assert validator.value is None
    assert validator.check(1001, _at(15), 300, INTERVAL) is Outcome.ACCEPTED
    assert validator.value == 1001


def test_decimals_do_not_suffer_from_float_rounding() -> None:
    validator = _validator(1250.922)
    assert validator.check(1251.222, _at(15), 0.3, INTERVAL) is Outcome.ACCEPTED


def test_round_trip() -> None:
    validator = _validator()
    validator.check(5000, _at(15), 300, INTERVAL)
    restored = ReadingValidator.from_dict(validator.as_dict())
    assert restored.as_dict() == validator.as_dict()
    assert ReadingValidator.from_dict({"value": "x", "value_at": "nope"}).value is None
    assert ReadingValidator.from_dict(None).value is None


def test_failed_outcomes() -> None:
    assert {o for o in Outcome if o.failed} == {
        Outcome.DECREASE,
        Outcome.UNREADABLE,
        Outcome.WRONG_DIGITS,
        Outcome.ERROR,
    }
