from dataclasses import FrozenInstanceError
from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from attendance_gen.domain.models import AttendanceReport, AttendanceRow, ReportType


def make_row(day: date, hours: str = "7.50") -> AttendanceRow:
    return AttendanceRow(
        day=day,
        clock_in=time(8, 0),
        clock_out=time(16, 0),
        break_duration=timedelta(minutes=30),
        total_hours=Decimal(hours),
        hours_100=Decimal(hours),
    )


def test_row_is_immutable() -> None:
    row = make_row(date(2023, 2, 1))
    with pytest.raises(FrozenInstanceError):
        setattr(row, "total_hours", Decimal(1))  # noqa: B010


def test_weekday_in_hebrew() -> None:
    assert make_row(date(2023, 2, 1)).weekday_he == "רביעי"


def test_report_totals() -> None:
    report = AttendanceReport(
        report_type=ReportType.TYPE_A,
        rows=(make_row(date(2023, 2, 1)), make_row(date(2023, 2, 2))),
    )
    assert report.total_hours == Decimal("15.00")
    assert report.days_count == 2