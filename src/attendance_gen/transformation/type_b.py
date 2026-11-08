import calendar
import random
from dataclasses import replace
from datetime import date
from decimal import Decimal

from attendance_gen.domain.models import AttendanceReport, AttendanceRow, ReportType
from attendance_gen.parsing.result import ParseResult
from attendance_gen.transformation.base import (
    BaseTransformationStrategy,
    GenerationError,
    PlannedShift,
)
from attendance_gen.transformation.rules import GenerationRules

_ZERO = Decimal(0)

# weekday של Python: שני=0 ... ראשון=6. בכרטיס הזה עובדים גם בשישי (4), אף פעם בשבת (5).
TYPE_B_RULES = GenerationRules(
    work_weekdays=frozenset({6, 0, 1, 2, 3, 4}),
    max_jitter_minutes=15,
    jitter_step_minutes=5,
    max_break_minutes=0,  # אין עמודת הפסקה בכרטיס
    max_net_hours=Decimal(4),
    max_month_hours=Decimal(120),
    days_variation=0,  # ימי העבודה נקבעים לפי הכרטיס המקורי, ראו _choose_days
)


class TypeBStrategy(BaseTransformationStrategy):
    report_type = ReportType.TYPE_B

    def __init__(self, rules: GenerationRules | None = None) -> None:
        super().__init__(rules or TYPE_B_RULES)

    def _choose_days(self, parsed: ParseResult, rng: random.Random) -> list[date]:
        """ימי העבודה הם הימים שהיו עם נתונים בכרטיס המקורי.

        כך ימים ריקים במקור (חגים, ימי חופש) נשארים ריקים, בלי לוח חגים.
        ההנחה: שורה N בטבלה היא היום ה-N בחודש (הכרטיס מתחיל ב-1 לחודש).
        שורה שחורגת מהחודש, או שיום השבוע שלה אסור לפי הכללים, היא רעש ונזרקת.
        """
        if not parsed.workday_lines:
            return super()._choose_days(parsed, rng)
        del rng  # בלי אקראיות: הימים נקבעים מהמקור
        last_day = calendar.monthrange(parsed.year, parsed.month)[1]
        candidates = (
            date(parsed.year, parsed.month, line)
            for line in parsed.workday_lines
            if 1 <= line <= last_day
        )
        days = sorted(d for d in candidates if d.weekday() in self.rules.work_weekdays)
        if not days:
            raise GenerationError("אף שורה מהכרטיס המקורי לא מתאימה לימי העבודה המותרים")
        return days

    def _expected_days(self, parsed: ParseResult) -> int:
        # שורות שנפסלו בקריאה הן עדיין ימי עבודה אמיתיים בכרטיס המקורי,
        # ולכן סופרים את כל השורות הלא ריקות ולא רק את אלה שנקראו היטב
        return parsed.candidate_lines

    def _build_row(self, day: date, shift: PlannedShift, total: Decimal) -> AttendanceRow:
        # בלי הפסקה: סה"כ הוא יציאה פחות כניסה
        return AttendanceRow(
            day=day, clock_in=shift.clock_in, clock_out=shift.clock_out, total_hours=total
        )

    def _make_report(
        self, parsed: ParseResult, rows: tuple[AttendanceRow, ...]
    ) -> AttendanceReport:
        report = super()._make_report(parsed, rows)
        return replace(report, hourly_rate=parsed.hourly_rate)

    def _verify(self, report: AttendanceReport) -> None:
        super()._verify(report)
        errors: list[str] = []
        if report.hourly_rate is None or report.hourly_rate <= _ZERO:
            errors.append("מחיר לשעה חסר או לא חיובי")
        if any(row.break_duration for row in report.rows):
            errors.append("בכרטיס מסוג B אין הפסקה")
        if errors:
            raise GenerationError("; ".join(errors))