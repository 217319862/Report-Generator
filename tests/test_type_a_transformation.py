from datetime import time, timedelta
from pathlib import Path

import pytest

from attendance_gen.domain.models import ReportType
from attendance_gen.domain.validation import Severity, validate_report
from attendance_gen.parsing.result import ObservedShift, ParseResult
from attendance_gen.parsing.type_a_parser import TypeAParser
from attendance_gen.transformation.base import GenerationError, seed_from_bytes
from attendance_gen.transformation.rules import GenerationRules
from attendance_gen.transformation.type_a import TypeAStrategy

FIXTURES = Path(__file__).parent / "fixtures"


def make_parsed(count: int = 15, report_type: ReportType = ReportType.TYPE_A) -> ParseResult:
    shifts = tuple(
        ObservedShift(time(8, 0), time(16, 0), timedelta(minutes=30), i) for i in range(count)
    )
    return ParseResult(report_type, 2023, 2, shifts, (), count)


def test_same_seed_gives_same_report() -> None:
    strategy = TypeAStrategy()
    assert strategy.transform(make_parsed(), 7) == strategy.transform(make_parsed(), 7)


def test_different_seed_gives_different_report() -> None:
    strategy = TypeAStrategy()
    assert strategy.transform(make_parsed(), 1) != strategy.transform(make_parsed(), 2)


def test_report_is_valid_and_within_rules() -> None:
    rules = GenerationRules()
    report = TypeAStrategy(rules).transform(make_parsed(), 3)
    errors = [i for i in validate_report(report) if i.severity is Severity.ERROR]
    assert errors == []
    assert all(row.day.month == 2 and row.day.year == 2023 for row in report.rows)
    assert all(row.day.weekday() in rules.work_weekdays for row in report.rows)
    days = [row.day for row in report.rows]
    assert days == sorted(set(days))


def test_from_real_ocr_output() -> None:
    text = (FIXTURES / "a_r_25.txt").read_text(encoding="utf-8")
    parsed = TypeAParser().parse(text)
    seed = seed_from_bytes(text.encode())
    report = TypeAStrategy().transform(parsed, seed)
    assert report.is_sample
    assert 1 <= report.days_count <= 20


def test_wrong_report_type_is_rejected() -> None:
    with pytest.raises(GenerationError):
        TypeAStrategy().transform(make_parsed(report_type=ReportType.TYPE_B), 1)


def test_impossible_rules_fail_closed() -> None:
    strict = GenerationRules(max_month_hours=GenerationRules().max_month_hours / 100)
    with pytest.raises(GenerationError):
        TypeAStrategy(strict).transform(make_parsed(), 1)