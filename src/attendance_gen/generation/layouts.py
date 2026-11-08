from collections.abc import Callable
from datetime import date, time, timedelta
from decimal import Decimal

from attendance_gen.domain.models import (
    AttendanceReport,
    AttendanceRow,
    ReportType,
    hebrew_weekday,
)
from attendance_gen.generation.layout import ColumnSpec, LayoutSpec, SummaryItem

_ZERO = Decimal(0)
_SATURDAY = 5  # weekday של Python
_MONTH_ABBR = ("ינו", "פבר", "מרץ", "אפר", "מאי", "יונ", "יול", "אוג", "ספט", "אוק", "נוב", "דצמ")


def _fixed(value: Decimal) -> str:
    return f"{value:.2f}"


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _clock(value: time) -> str:
    return value.strftime("%H:%M")


def _clock_short(value: time) -> str:
    return f"{value.hour}:{value.minute:02d}"


def _short_date(day: date) -> str:
    return f"{day.day}/{day.month}/{day:%y}"


def _shekel(value: Decimal | None) -> str:
    return "" if value is None else f"₪ {value:,.2f}"


def _duration(value: timedelta | None) -> str:
    if value is None:
        return ""
    minutes = int(value.total_seconds() // 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _day_name(row: AttendanceRow) -> str:
    return "שבת" if row.day.weekday() == 5 else f"יום {row.weekday_he}"


def _month_abbr(report: AttendanceReport) -> str:
    """"ספט-22": קיצור החודש ושתי ספרות של השנה, כמו בכותרת הכרטיס המקורי."""
    if not report.rows:
        return report.period_label
    day = report.rows[0].day
    return f"{_MONTH_ABBR[day.month - 1]}-{day:%y}"


def _sum(report: AttendanceReport, getter: Callable[[AttendanceRow], Decimal]) -> Decimal:
    return sum((getter(row) for row in report.rows), _ZERO)


def _break_total(report: AttendanceReport) -> str:
    total = sum((row.break_duration or timedelta(0) for row in report.rows), timedelta(0))
    return _duration(total)


TYPE_A_LAYOUT = LayoutSpec(
    title="דוח נוכחות",
    columns=(
        ColumnSpec("תאריך", 22, lambda r: r.day.strftime("%d/%m/%Y"), lambda rep: str(rep.days_count)),
        ColumnSpec("יום", 22, _day_name),
        ColumnSpec("מקום עבודה", 20, lambda r: r.location or ""),
        ColumnSpec("כניסה", 14, lambda r: _clock(r.clock_in)),
        ColumnSpec("יציאה", 14, lambda r: _clock(r.clock_out)),
        ColumnSpec("הפסקה", 14, lambda r: _duration(r.break_duration), _break_total),
        ColumnSpec("סה\"כ", 14, lambda r: _fixed(r.total_hours), lambda rep: _fixed(rep.total_hours)),
        ColumnSpec("100%", 13, lambda r: _fixed(r.hours_100), lambda rep: _fixed(_sum(rep, lambda r: r.hours_100))),
        ColumnSpec("125%", 13, lambda r: _fixed(r.hours_125), lambda rep: _fixed(_sum(rep, lambda r: r.hours_125))),
        ColumnSpec("150%", 13, lambda r: _fixed(r.hours_150), lambda rep: _fixed(_sum(rep, lambda r: r.hours_150))),
        ColumnSpec("שבת", 13, lambda r: _fixed(r.hours_saturday), lambda rep: _fixed(_sum(rep, lambda r: r.hours_saturday))),
    ),
    summary=(
        SummaryItem("ימים", lambda rep: str(rep.days_count)),
        SummaryItem("סה\"כ שעות", lambda rep: _plain(rep.total_hours)),
        SummaryItem("שעות 100%", lambda rep: _plain(_sum(rep, lambda r: r.hours_100))),
        SummaryItem("שעות 125%", lambda rep: _plain(_sum(rep, lambda r: r.hours_125))),
        SummaryItem("שעות 150%", lambda rep: _plain(_sum(rep, lambda r: r.hours_150))),
        SummaryItem("שבת 150%", lambda rep: _plain(_sum(rep, lambda r: r.hours_saturday))),
        SummaryItem("בונוס", lambda rep: "0"),
        SummaryItem("נסיעות", lambda rep: "0"),
    ),
    show_title=False,
)

TYPE_B_LAYOUT = LayoutSpec(
    title="כרטיס עובד לחודש:",
    columns=(
        ColumnSpec("תאריך", 25, lambda r: _short_date(r.day), blank=_short_date),
        ColumnSpec("יום בשבוע", 25, lambda r: r.weekday_he, blank=hebrew_weekday),
        ColumnSpec("שעת כניסה", 25, lambda r: _clock_short(r.clock_in)),
        ColumnSpec("שעת יציאה", 25, lambda r: _clock_short(r.clock_out)),
        ColumnSpec("סה\"כ שעות", 25, lambda r: _fixed(r.total_hours)),
        ColumnSpec("הערות", 55, lambda r: r.note or ""),
    ),
    summary=(
        SummaryItem("סה\"כ ימי עבודה לחודש", lambda rep: str(rep.days_count)),
        SummaryItem("סה\"כ שעות חודשיות", lambda rep: _fixed(rep.total_hours)),
        SummaryItem("מחיר לשעה", lambda rep: _shekel(rep.hourly_rate)),
        SummaryItem("סה\"כ לתשלום", lambda rep: _shekel(rep.total_pay)),
    ),
    summary_on_top=True,
    fill_month=True,
    shaded_weekdays=frozenset({_SATURDAY}),
    grid=True,
    summary_label_mm=50.0,
    period_text=_month_abbr,
    show_company=False,  # במקור אין שורת חברה
    employee_label="שם העובד:",
)

LAYOUTS: dict[ReportType, LayoutSpec] = {
    ReportType.TYPE_A: TYPE_A_LAYOUT,
    ReportType.TYPE_B: TYPE_B_LAYOUT,
}