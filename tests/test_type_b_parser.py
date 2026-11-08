from datetime import time
from decimal import Decimal

import pytest

from attendance_gen.parsing.result import ParseError
from attendance_gen.parsing.type_b_parser import RawRow, build_result

HEADER = "כרטיס עובד ספט-22"
SUMMARY = "21 84.00 30.65 2,574.60"


def _good_rows(count: int = 10) -> list[RawRow]:
    return [RawRow(i, "8:30", "12:00", "3.50") for i in range(1, count + 1)]


def _codes(result_issues: tuple) -> set[str]:  # type: ignore[type-arg]
    return {issue.code for issue in result_issues}


def test_happy_path() -> None:
    result = build_result(_good_rows(), HEADER, SUMMARY)
    assert (result.year, result.month) == (2022, 9)
    assert len(result.shifts) == 10
    assert result.shifts[0].clock_in == time(8, 30)
    assert result.hourly_rate == Decimal("30.65")
    assert result.issues == ()


def test_empty_rows_are_not_candidates() -> None:
    rows = [*_good_rows(), RawRow(11, "", "", "")]
    assert build_result(rows, HEADER, SUMMARY).candidate_lines == 10


def test_inconsistent_row_is_dropped() -> None:
    rows = _good_rows()
    rows[2] = RawRow(3, "3:02", "10:59", "2.95")  # 3:02 במקום 8:02
    result = build_result(rows, HEADER, SUMMARY)
    assert len(result.shifts) == 9
    assert "ROW_INCONSISTENT" in _codes(result.issues)


def test_unreadable_row_is_dropped() -> None:
    rows = _good_rows()
    rows[3] = RawRow(4, "8:30", "42:00", "3.50")
    result = build_result(rows, HEADER, SUMMARY)
    assert len(result.shifts) == 9
    assert "ROW_UNREADABLE" in _codes(result.issues)


def test_consistent_outlier_is_dropped() -> None:
    rows = [*_good_rows(8), RawRow(9, "8:30", "16:00", "7.50")]
    result = build_result(rows, HEADER, SUMMARY)
    assert len(result.shifts) == 8
    assert "ROW_OUTLIER" in _codes(result.issues)


def test_missing_period_fails() -> None:
    with pytest.raises(ParseError):
        build_result(_good_rows(), "בלי כותרת", SUMMARY)


def test_low_coverage_fails() -> None:
    bad = [RawRow(i, "8:30", "12:00", "9.99") for i in range(1, 9)]
    rows = [*bad, RawRow(9, "8:30", "12:00", "3.50"), RawRow(10, "8:30", "12:00", "3.50")]
    with pytest.raises(ParseError):
        build_result(rows, HEADER, SUMMARY)


def test_rate_not_found_is_warning_not_failure() -> None:
    result = build_result(_good_rows(), HEADER, "אין כאן מספרים")
    assert result.hourly_rate is None
    assert "RATE_NOT_FOUND" in _codes(result.issues)


def test_period_from_dates_wins_and_mismatch_is_reported() -> None:
    text = "01/09/22 02/09/22 05/09/22 אוק-22"
    result = build_result(_good_rows(), text, SUMMARY)
    assert (result.year, result.month) == (2022, 9)
    assert "PERIOD_MISMATCH" in _codes(result.issues)


def test_period_override_replaces_missing_period() -> None:
    result = build_result(_good_rows(), "בלי כותרת", SUMMARY, period_override=(2023, 1))
    assert (result.year, result.month) == (2023, 1)
    assert result.issues == ()


def test_period_override_that_differs_from_text_is_reported() -> None:
    result = build_result(_good_rows(), HEADER, SUMMARY, period_override=(2023, 1))
    assert (result.year, result.month) == (2023, 1)
    assert "PERIOD_OVERRIDDEN" in _codes(result.issues)