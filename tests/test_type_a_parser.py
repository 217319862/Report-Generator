from datetime import time, timedelta
from pathlib import Path

import pytest

from attendance_gen.parsing.result import ParseError
from attendance_gen.parsing.type_a_parser import TypeAParser

FIXTURES = Path(__file__).parent / "fixtures"
PARSER = TypeAParser()


def _text(*lines: str) -> str:
    return "\n".join(("01/02/2023", *lines))


@pytest.mark.parametrize("name", ["a_r_25.txt", "a_r_25_v2.txt"])
def test_real_ocr_output(name: str) -> None:
    result = PARSER.parse((FIXTURES / name).read_text(encoding="utf-8"))
    assert (result.year, result.month) == (2023, 2)
    assert len(result.shifts) == 15
    assert result.coverage == 1.0
    assert any(s.clock_in == time(9, 0) and s.clock_out == time(17, 0) for s in result.shifts)


@pytest.mark.parametrize("line", ["08:00 16:00 00:30 7.50", "7.50 00:30 16:00 08:00"])
def test_column_order_does_not_matter(line: str) -> None:
    shift = PARSER.parse(_text(line)).shifts[0]
    assert (shift.clock_in, shift.clock_out) == (time(8, 0), time(16, 0))
    assert shift.break_duration == timedelta(minutes=30)


def test_long_break_is_rejected_and_reported() -> None:
    result = PARSER.parse(
        _text("08:00 16:00 00:30", "08:00 16:00 01:30", "09:00 17:00 00:30")
    )
    assert len(result.shifts) == 2
    assert "LONG_BREAK" in {issue.code for issue in result.issues}


def test_unconfirmed_total_is_reported_but_row_is_kept() -> None:
    result = PARSER.parse(_text("08:00 16:00 00:30 6.00"))
    assert len(result.shifts) == 1
    assert "TOTAL_NOT_CONFIRMED" in {issue.code for issue in result.issues}


def test_unreadable_text_fails_instead_of_guessing() -> None:
    with pytest.raises(ParseError):
        PARSER.parse(_text("08:00 16:00"))


def test_missing_period_fails() -> None:
    with pytest.raises(ParseError):
        PARSER.parse("08:00 16:00 00:30 7.50")