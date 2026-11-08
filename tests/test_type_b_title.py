"""כותרת TYPE_B: קיצור חודש כמו במקור, ושם העובד בטבלת הסיכום."""

from datetime import date, time
from decimal import Decimal

import pytest

from attendance_gen.domain.models import AttendanceReport, AttendanceRow, ReportType
from attendance_gen.generation.layouts import TYPE_A_LAYOUT, TYPE_B_LAYOUT


def _report(day: date) -> AttendanceReport:
    row = AttendanceRow(day, time(8, 30), time(12, 0), Decimal("3.50"))
    return AttendanceReport(ReportType.TYPE_B, (row,), period_label="ignored")


@pytest.mark.parametrize(
    ("day", "expected"),
    [(date(2022, 9, 1), "ספט-22"), (date(2023, 1, 5), "ינו-23"), (date(2023, 3, 2), "מרץ-23")],
)
def test_month_label_matches_original_card(day: date, expected: str) -> None:
    assert TYPE_B_LAYOUT.period_text(_report(day)) == expected


def test_type_b_has_employee_in_summary_and_no_company_line() -> None:
    assert TYPE_B_LAYOUT.employee_label == "שם העובד:"
    assert not TYPE_B_LAYOUT.show_company


def test_type_a_header_is_unchanged() -> None:
    assert TYPE_A_LAYOUT.show_company
    assert TYPE_A_LAYOUT.employee_label is None
