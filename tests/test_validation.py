from datetime import date, time, timedelta
from decimal import Decimal

from attendance_gen.domain.models import AttendanceRow
from attendance_gen.domain.validation import validate_row


def make_row(total: str = "7.50", out: time = time(16, 0)) -> AttendanceRow:
    return AttendanceRow(
        day=date(2023, 2, 1),
        clock_in=time(8, 0),
        clock_out=out,
        total_hours=Decimal(total),
        break_duration=timedelta(minutes=30),
        hours_100=Decimal(total),
    )


def test_valid_row_has_no_issues() -> None:
    assert validate_row(make_row(), 0) == []


def test_wrong_total_is_flagged() -> None:
    issues = validate_row(make_row(total="6.50"), 0)
    assert [i.code for i in issues] == ["TOTAL_MISMATCH", "BREAKDOWN_MISMATCH"] or \
        "TOTAL_MISMATCH" in [i.code for i in issues]


def test_exit_before_entry_is_flagged() -> None:
    issues = validate_row(make_row(out=time(7, 0)), 0)
    assert issues[0].code == "TIME_ORDER"