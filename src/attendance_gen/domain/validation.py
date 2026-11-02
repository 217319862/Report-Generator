from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum

from attendance_gen.domain.models import AttendanceReport, AttendanceRow

TOLERANCE = Decimal("0.02")
_ZERO = Decimal(0)


class Severity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    message: str
    row_index: int | None = None
    severity: Severity = Severity.ERROR


def _hours_between(day: date, start: time, end: time) -> Decimal:
    delta = datetime.combine(day, end) - datetime.combine(day, start)
    return Decimal(int(delta.total_seconds())) / Decimal(3600)


def validate_row(row: AttendanceRow, index: int) -> list[Issue]:
    issues: list[Issue] = []
    if row.clock_out <= row.clock_in:
        issues.append(Issue("TIME_ORDER", "יציאה לא אחרי כניסה", index))
        return issues  # שאר הבדיקות לא רלוונטיות

    span = _hours_between(row.day, row.clock_in, row.clock_out)
    break_hours = (
        Decimal(int(row.break_duration.total_seconds())) / Decimal(3600)
        if row.break_duration is not None
        else _ZERO
    )
    if abs(row.total_hours - (span - break_hours)) > TOLERANCE:
        issues.append(Issue("TOTAL_MISMATCH", "סה\"כ לא תואם כניסה/יציאה/הפסקה", index))

    breakdown = row.hours_100 + row.hours_125 + row.hours_150 + row.hours_saturday
    if breakdown != _ZERO and abs(breakdown - row.total_hours) > TOLERANCE:
        issues.append(Issue("BREAKDOWN_MISMATCH", "פירוק השעות לא מסתכם לסה\"כ", index))
    return issues


def validate_report(report: AttendanceReport) -> list[Issue]:
    issues: list[Issue] = []
    for index, row in enumerate(report.rows):
        issues.extend(validate_row(row, index))

    days = [row.day for row in report.rows]
    if len(days) != len(set(days)):
        issues.append(Issue("DUPLICATE_DATE", "יש תאריכים כפולים"))
    if days != sorted(days):
        issues.append(Issue("ORDER", "התאריכים לא בסדר כרונולוגי"))
    return issues