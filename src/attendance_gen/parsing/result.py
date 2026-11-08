from dataclasses import dataclass
from datetime import time, timedelta
from decimal import Decimal

from attendance_gen.domain.models import ReportType
from attendance_gen.domain.validation import Issue


@dataclass(frozen=True, slots=True)
class ObservedShift:
    """משמרת שנצפתה בדוח המקור. בלי תאריך, כי ה-OCR לא קורא אותו בצורה אמינה."""

    clock_in: time
    clock_out: time
    break_duration: timedelta
    line_no: int


@dataclass(frozen=True, slots=True)
class ParseResult:
    report_type: ReportType
    year: int
    month: int
    shifts: tuple[ObservedShift, ...]
    issues: tuple[Issue, ...]
    candidate_lines: int
    hourly_rate: Decimal | None = None  # רק בדוחות שמציגים מחיר לשעה (TYPE_B)
    # מספרי השורות (מ-1) בטבלה שנראו כימי עבודה, גם אם לא נקראו עד הסוף.
    # ב-TYPE_B שורה N היא היום ה-N בחודש. ריק = הפרסר לא מדווח על ימים.
    workday_lines: tuple[int, ...] = ()

    @property
    def coverage(self) -> float:
        """איזה חלק מהשורות שנראו כמו משמרות נקרא בהצלחה."""
        return len(self.shifts) / self.candidate_lines if self.candidate_lines else 0.0


class ParseError(ValueError):
    """הקריאה לא אמינה מספיק, ועדיף להיכשל מאשר לנחש."""

    def __init__(self, message: str, issues: tuple[Issue, ...] = ()) -> None:
        super().__init__(message)
        self.issues = issues