from dataclasses import replace
from datetime import time, timedelta
from decimal import Decimal

import pytest

from attendance_gen.domain.models import AttendanceReport, ReportType
from attendance_gen.domain.validation import Severity, validate_report
from attendance_gen.parsing.result import ObservedShift, ParseResult
from attendance_gen.transformation.base import GenerationError
from attendance_gen.transformation.type_b import TYPE_B_RULES, TypeBStrategy

RATE = Decimal("30.65")
_SATURDAY = 5
_FRIDAY = 4


def make_parsed(
    count: int = 20,
    *,
    candidates: int | None = None,
    rate: Decimal | None = RATE,
    report_type: ReportType = ReportType.TYPE_B,
) -> ParseResult:
    shifts = tuple(
        ObservedShift(time(8, 30), time(12, 0), timedelta(0), i) for i in range(count)
    )
    return ParseResult(
        report_type, 2022, 9, shifts, (), candidates or count, hourly_rate=rate
    )


def test_same_seed_gives_same_report() -> None:
    strategy = TypeBStrategy()
    assert strategy.transform(make_parsed(), 7) == strategy.transform(make_parsed(), 7)


def test_report_is_valid_and_within_rules() -> None:
    report = TypeBStrategy().transform(make_parsed(), 3)
    errors = [i for i in validate_report(report) if i.severity is Severity.ERROR]
    assert errors == []
    assert all(row.day.weekday() in TYPE_B_RULES.work_weekdays for row in report.rows)
    assert all(row.break_duration is None for row in report.rows)
    assert all(row.total_hours <= TYPE_B_RULES.max_net_hours for row in report.rows)
    assert report.hourly_rate == RATE
    assert report.total_pay is not None
    assert abs(report.total_pay - report.total_hours * RATE) <= Decimal("0.005")


def test_fridays_are_used_and_saturdays_never() -> None:
    days = {
        row.day
        for seed in range(5)
        for row in TypeBStrategy().transform(make_parsed(), seed).rows
    }
    assert all(day.weekday() != _SATURDAY for day in days)
    assert any(day.weekday() == _FRIDAY for day in days)


def test_day_count_follows_candidate_lines_not_parsed_shifts() -> None:
    parsed = make_parsed(10, candidates=20)
    report = TypeBStrategy().transform(parsed, 1)
    assert 19 <= report.days_count <= 21


def test_missing_rate_fails_closed() -> None:
    with pytest.raises(GenerationError):
        TypeBStrategy().transform(make_parsed(rate=None), 1)


def test_wrong_report_type_is_rejected() -> None:
    with pytest.raises(GenerationError):
        TypeBStrategy().transform(make_parsed(report_type=ReportType.TYPE_A), 1)


def test_impossible_rules_fail_closed() -> None:
    strict = replace(TYPE_B_RULES, max_month_hours=Decimal(1))
    with pytest.raises(GenerationError):
        TypeBStrategy(strict).transform(make_parsed(), 1)


def test_total_pay_is_none_without_rate() -> None:
    assert AttendanceReport(ReportType.TYPE_B, ()).total_pay is None