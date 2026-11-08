from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from attendance_gen.domain.models import AttendanceReport, AttendanceRow


def _empty(_day: date) -> str:
    return ""


def _default_period(report: AttendanceReport) -> str:
    return report.period_label


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    header: str
    width_mm: float
    value: Callable[[AttendanceRow], str]
    total: Callable[[AttendanceReport], str] | None = None
    blank: Callable[[date], str] = _empty  # מה מציגים ביום בלי משמרת (כש-fill_month פעיל)


@dataclass(frozen=True, slots=True)
class SummaryItem:
    label: str
    value: Callable[[AttendanceReport], str]


@dataclass(frozen=True, slots=True)
class LayoutSpec:
    title: str
    columns: tuple[ColumnSpec, ...]  # בסדר קריאה: הראשון הוא הימני ביותר
    summary: tuple[SummaryItem, ...] = ()
    show_title: bool = True
    summary_on_top: bool = False  # טבלת הסיכום מעל הטבלה הראשית
    fill_month: bool = False  # מציג את כל ימי החודש, גם בלי משמרת
    shaded_weekdays: frozenset[int] = frozenset()  # weekday של Python; השורה נצבעת באפור
    grid: bool = False  # קווי רשת לכל התאים
    summary_label_mm: float = 35.0
    period_text: Callable[[AttendanceReport], str] = _default_period  # החודש בפס הכותרת
    show_company: bool = True  # שורת שם החברה מעל הדוח
    # אם קבוע: שם העובד הוא השורה הראשונה בטבלת הסיכום, עם התווית הזו, ולא שורה בכותרת
    employee_label: str | None = None