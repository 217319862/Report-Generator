"""ימי עבודה ב-TYPE_B נקבעים לפי הכרטיס המקורי: ימים ריקים נשארים ריקים."""

from datetime import date, time, timedelta
from decimal import Decimal

from attendance_gen.domain.models import ReportType
from attendance_gen.parsing.result import ObservedShift, ParseResult
from attendance_gen.parsing.type_b_parser import RawRow, build_result
from attendance_gen.transformation.type_b import TypeBStrategy


def _parsed(lines: tuple[int, ...], *, year: int = 2022, month: int = 9) -> ParseResult:
    shift = ObservedShift(time(8, 30), time(12, 0), timedelta(0), line_no=1)
    return ParseResult(
        report_type=ReportType.TYPE_B,
        year=year,
        month=month,
        shifts=(shift,),
        issues=(),
        candidate_lines=len(lines),
        hourly_rate=Decimal("30.65"),
        workday_lines=lines,
    )


def _days(lines: tuple[int, ...]) -> list[date]:
    report = TypeBStrategy().transform(_parsed(lines), seed=1)
    return [row.day for row in report.rows]


def test_empty_days_in_source_stay_empty() -> None:
    # ספטמבר 2022: ב-26 וב-27 (ראש השנה) הכרטיס המקורי ריק
    days = _days((25, 28, 29))
    assert days == [date(2022, 9, 25), date(2022, 9, 28), date(2022, 9, 29)]
    assert date(2022, 9, 26) not in days
    assert date(2022, 9, 27) not in days


def test_line_beyond_month_is_ignored() -> None:
    # הכרטיס מציג גם את 1/10, וזה לא חלק מספטמבר
    assert _days((1, 31)) == [date(2022, 9, 1)]


def test_saturday_line_is_dropped() -> None:
    # 3/9/2022 הוא שבת
    assert _days((1, 3, 4)) == [date(2022, 9, 1), date(2022, 9, 4)]


def test_parser_reports_which_lines_were_workdays() -> None:
    ok = ("8:30", "12:00", "3.50")
    rows = [
        RawRow(1, *ok),
        RawRow(2, *ok),
        RawRow(3, "", "", ""),  # יום ריק
        RawRow(4, "", "1", ""),  # רעש: תא בודד
        RawRow(5, "8:04", "40:59", "2.97"),  # יום עבודה שלא נקרא עד הסוף
        RawRow(6, *ok),
    ]
    result = build_result(rows, "ספט-22", "")
    assert result.workday_lines == (1, 2, 5, 6)
    assert result.candidate_lines == 4
