import calendar
import hashlib
import random
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal
from typing import ClassVar

from attendance_gen.domain.models import AttendanceReport, AttendanceRow, ReportType
from attendance_gen.domain.validation import Severity, validate_report
from attendance_gen.parsing.result import ObservedShift, ParseResult
from attendance_gen.transformation.rules import GenerationRules

_CENT = Decimal("0.01")
_ZERO = Decimal(0)


class GenerationError(ValueError):
    """הדוח שנוצר לא עבר אימות, ולכן לא מוחזר."""


@dataclass(frozen=True, slots=True)
class PlannedShift:
    clock_in: time
    clock_out: time
    break_duration: timedelta

    @property
    def net_hours(self) -> Decimal:
        minutes = _minutes(self.clock_out) - _minutes(self.clock_in)
        minutes -= int(self.break_duration.total_seconds() // 60)
        return (Decimal(minutes) / Decimal(60)).quantize(_CENT)


def seed_from_bytes(data: bytes) -> int:
    """זרע קבוע שנגזר מתוכן הקלט: אותו קובץ נותן תמיד אותו דוח."""
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "big")


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _to_time(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)


class BaseTransformationStrategy(ABC):
    report_type: ClassVar[ReportType]

    def __init__(self, rules: GenerationRules | None = None) -> None:
        self.rules = rules or GenerationRules()

    def transform(self, parsed: ParseResult, seed: int) -> AttendanceReport:
        if parsed.report_type != self.report_type:
            raise GenerationError(f"strategy for {self.report_type}, got {parsed.report_type}")
        rng = random.Random(seed)
        days = self._choose_days(parsed, rng)
        rows = tuple(self._make_row(day, self._plan_shift(rng, parsed.shifts)) for day in days)
        report = AttendanceReport(
            report_type=self.report_type,
            rows=rows,
            period_label=f"{parsed.month:02d}/{parsed.year}",
        )
        self._verify(report)
        return report

    @abstractmethod
    def _build_row(self, day: date, shift: PlannedShift, total: Decimal) -> AttendanceRow:
        """החלק שמשתנה בין סוגי דוחות: אילו שדות ממלאים וכיצד."""

    def _make_row(self, day: date, shift: PlannedShift) -> AttendanceRow:
        return self._build_row(day, shift, shift.net_hours)

    def _workdays(self, year: int, month: int) -> list[date]:
        last = calendar.monthrange(year, month)[1]
        days = (date(year, month, d) for d in range(1, last + 1))
        return [d for d in days if d.weekday() in self.rules.work_weekdays]

    def _choose_days(self, parsed: ParseResult, rng: random.Random) -> list[date]:
        workdays = self._workdays(parsed.year, parsed.month)
        variation = self.rules.days_variation
        wanted = len(parsed.shifts) + rng.randint(-variation, variation)
        count = max(1, min(wanted, len(workdays)))
        return sorted(rng.sample(workdays, count))

    def _plan_shift(self, rng: random.Random, observed: Sequence[ObservedShift]) -> PlannedShift:
        rules = self.rules
        base = rng.choice(observed)
        start, end = _minutes(base.clock_in), _minutes(base.clock_out)
        break_minutes = min(int(base.break_duration.total_seconds() // 60), rules.max_break_minutes)

        jitter = rng.randrange(
            -rules.max_jitter_minutes, rules.max_jitter_minutes + 1, rules.jitter_step_minutes
        )
        if start + jitter < _minutes(rules.earliest_start) or end + jitter > _minutes(rules.latest_end):
            jitter = 0
        start, end = start + jitter, end + jitter

        max_net_minutes = int(rules.max_net_hours * 60)
        if end - start - break_minutes > max_net_minutes:
            end = start + break_minutes + max_net_minutes
        return PlannedShift(_to_time(start), _to_time(end), timedelta(minutes=break_minutes))

    def _verify(self, report: AttendanceReport) -> None:
        rules = self.rules
        errors = [i.message for i in validate_report(report) if i.severity is Severity.ERROR]
        for row in report.rows:
            label = row.day.isoformat()
            if row.day.weekday() not in rules.work_weekdays:
                errors.append(f"{label}: יום שאינו יום עבודה")
            if row.clock_in < rules.earliest_start or row.clock_out > rules.latest_end:
                errors.append(f"{label}: שעות מחוץ לטווח המותר")
            if row.total_hours > rules.max_net_hours:
                errors.append(f"{label}: יותר מדי שעות ביום")
            if (row.break_duration or timedelta(0)) > timedelta(minutes=rules.max_break_minutes):
                errors.append(f"{label}: הפסקה ארוכה מדי")
        if report.total_hours > rules.max_month_hours:
            errors.append("סה\"כ שעות חודשי חורג מהמותר")
        if errors:
            raise GenerationError("; ".join(errors))