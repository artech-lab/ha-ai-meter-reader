"""Tests for the prompt and the parsing of the AI answer (pure Python)."""

import pytest

from custom_components.ai_meter_reader.const import MeterType
from custom_components.ai_meter_reader.reading import Problem, build_instructions, parse_reading


def test_digits_become_a_value() -> None:
    reading = parse_reading({"digits": "01250922", "confidence": 8})
    assert reading.value == 1250922
    assert reading.problem is None
    assert reading.digits == "01250922"


def test_decimals_are_applied_here_not_by_the_model() -> None:
    assert parse_reading({"digits": "01250922", "confidence": 8}, digits=8, decimals=3).value == 1250.922


def test_separators_and_spaces_are_ignored() -> None:
    assert parse_reading({"digits": " 0125 0.922 ", "confidence": 8}).value == 1250922


@pytest.mark.parametrize(
    "answer",
    [
        {"digits": "0125X922", "confidence": 8},
        {"digits": "x", "confidence": 9},
        {"digits": "", "confidence": 9},
        {"digits": "12a4", "confidence": 9},
        {"digits": "01250922", "confidence": 2},
        {"digits": "01250922", "confidence": "high"},
    ],
)
def test_unreadable_frames(answer: dict) -> None:
    reading = parse_reading(answer)
    assert reading.value is None
    assert reading.problem is Problem.UNREADABLE


def test_digit_count() -> None:
    assert parse_reading({"digits": "101250922", "confidence": 8}, digits=8).problem is Problem.WRONG_DIGITS
    # A dropped leading zero is harmless.
    short = parse_reading({"digits": "1250922", "confidence": 8}, digits=8)
    assert short.value == 1250922
    assert short.digits == "01250922"


def test_confidence_is_clamped() -> None:
    assert parse_reading({"digits": "1", "confidence": 42}).confidence == 10


@pytest.mark.parametrize("data", [None, "1234", {"value": 1234}])
def test_not_an_answer(data) -> None:
    with pytest.raises(ValueError):
        parse_reading(data)


def test_instructions() -> None:
    text = build_instructions(MeterType.GAS, digits=8, decimals=3, notes="  ignore the blue digit ")
    assert "gas meter" in text
    assert "exactly 8 digits" in text
    assert "last 3 digit(s) are the decimal part" in text
    assert "NOTES FROM THE OWNER (they override the rules above): ignore the blue digit" in text
    plain = build_instructions(MeterType.WATER)
    assert "exactly 8" not in plain and "decimal part" not in plain and "NOTES" not in plain
    # Rules are numbered without gaps.
    assert "\n1. " in plain and "\n4. " in plain and "\n5. " not in plain
