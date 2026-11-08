from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

_ZERO = Decimal(0)
_CENT = Decimal("0.01")
_HEBREW_DAYS = ("ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת")


class ReportType(StrEnum):
    TYPE_A = "TYPE_A"
    TYPE_B = "TYPE_B"


def hebrew_weekday(day: date) -> str:
    # date.weekday(): שני=0 ... ראשון=6. אצלנו ראשון הוא הראשון ברשימה.
    return _HEBREW_DAYS[(day.weekday() + 1) % 7]


@dataclass(frozen=True, slots=True)
class AttendanceRow:
    """שורה אחת בדוח נוכחות. אי אפשר לשנות אותה אחרי היצירה."""

    day: date
    clock_in: time
    clock_out: time
    total_hours: Decimal
    break_duration: timedelta | None = None
    hours_100: Decimal = _ZERO
    hours_125: Decimal = _ZERO
    hours_150: Decimal = _ZERO
    hours_saturday: Decimal = _ZERO
    location: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.break_duration is not None and self.break_duration < timedelta(0):
            raise ValueError("break_duration cannot be negative")
        if self.total_hours < _ZERO:
            raise ValueError("total_hours cannot be negative")

    @property
    def weekday_he(self) -> str:
        return hebrew_weekday(self.day)


@dataclass(frozen=True, slots=True)
class AttendanceReport:
    report_type: ReportType
    rows: tuple[AttendanceRow, ...]
    period_label: str = ""
    hourly_rate: Decimal | None = None
    is_sample: bool = True

    @property
    def total_hours(self) -> Decimal:
        return sum((row.total_hours for row in self.rows), _ZERO)

    @property
    def days_count(self) -> int:
        return len({row.day for row in self.rows})

    @property
    def total_pay(self) -> Decimal | None:
        """שעות כפול מחיר לשעה, מעוגל לאגורה. None אם אין מחיר."""
        if self.hourly_rate is None:
            return None
        return (self.total_hours * self.hourly_rate).quantize(_CENT, rounding=ROUND_HALF_UP)