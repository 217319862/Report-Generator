import re
from collections import Counter
from datetime import time, timedelta
from decimal import Decimal

from attendance_gen.domain.models import ReportType
from attendance_gen.domain.validation import Issue, Severity
from attendance_gen.parsing.base_parser import BaseParser
from attendance_gen.parsing.result import ObservedShift, ParseError, ParseResult

_LONG_DATE = re.compile(r"(?<!\d)(\d{2})/(\d{2})/(\d{4})(?!\d)")
_PERCENT = re.compile(r"\b1(?:00|25|50)%")
_TIME = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3]):[0-5]\d(?!\d)")
_DECIMAL = re.compile(r"(?<![\d.])\d{1,3}\.\d{2}(?!\d)")

_BREAK_SEARCH_LIMIT = time(3, 0)  # שעה קטנה מזו נחשבת הפסקה
_LONG_BREAK_MINUTES = 60
_MAX_SHIFT_MINUTES = 12 * 60
MIN_COVERAGE = 0.5


def _to_time(text: str) -> time:
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _warning(code: str, line_no: int, detail: str) -> Issue:
    return Issue(code, f"שורה {line_no}: {detail}", severity=Severity.WARNING)


def _find_period(text: str) -> tuple[int, int] | None:
    """החודש והשנה הנפוצים ביותר בתאריכים שנקראו."""
    counts: Counter[tuple[int, int]] = Counter()
    for day, month, year in _LONG_DATE.findall(text):
        if 1 <= int(day) <= 31 and 1 <= int(month) <= 12 and 2000 <= int(year) <= 2100:
            counts[(int(year), int(month))] += 1
    return counts.most_common(1)[0][0] if counts else None


def _read_shift(
    line_no: int, line: str, raw_times: list[str]
) -> tuple[ObservedShift | None, list[Issue]]:
    if len(raw_times) != 3:
        return None, [_warning("TIMES_COUNT", line_no, f"נמצאו {len(raw_times)} שעות במקום 3")]

    # לא מסתמכים על סדר העמודות: הקטנה היא ההפסקה, ואחריה כניסה ויציאה
    break_time, clock_in, clock_out = sorted(_to_time(item) for item in raw_times)
    if break_time >= _BREAK_SEARCH_LIMIT:
        return None, [_warning("BREAK_NOT_FOUND", line_no, "לא זוהתה הפסקה")]

    break_minutes = _minutes(break_time)
    if break_minutes > _LONG_BREAK_MINUTES:
        return None, [_warning("LONG_BREAK", line_no, "הפסקה ארוכה משעה, לא משמשת כדוגמה")]

    worked = _minutes(clock_out) - _minutes(clock_in) - break_minutes
    if not 0 < worked <= _MAX_SHIFT_MINUTES:
        return None, [_warning("IMPLAUSIBLE_DURATION", line_no, "משך משמרת לא סביר")]

    issues: list[Issue] = []
    total = f"{Decimal(worked) / Decimal(60):.2f}"
    if total not in _DECIMAL.findall(line):
        issues.append(_warning("TOTAL_NOT_CONFIRMED", line_no, f"הסכום המחושב {total} לא נקרא ב-OCR"))

    shift = ObservedShift(clock_in, clock_out, timedelta(minutes=break_minutes), line_no)
    return shift, issues


class TypeAParser(BaseParser):
    report_type = ReportType.TYPE_A

    def score(self, text: str) -> float:
        hits = len(_LONG_DATE.findall(text)) + 3 * len(_PERCENT.findall(text))
        return min(hits / 10, 1.0)

    def parse(self, text: str) -> ParseResult:
        period = _find_period(text)
        shifts: list[ObservedShift] = []
        issues: list[Issue] = []
        candidates = 0

        for line_no, line in enumerate(text.splitlines(), start=1):
            raw_times = _TIME.findall(line)
            if len(raw_times) < 2:
                continue  # כותרת או שורת סיכום
            candidates += 1
            shift, line_issues = _read_shift(line_no, line, raw_times)
            issues.extend(line_issues)
            if shift is not None:
                shifts.append(shift)

        if period is None:
            raise ParseError("לא נמצאו חודש ושנה בטקסט", tuple(issues))
        if not shifts or len(shifts) / candidates < MIN_COVERAGE:
            raise ParseError(f"נקראו {len(shifts)} שורות מתוך {candidates}", tuple(issues))

        return ParseResult(
            report_type=self.report_type,
            year=period[0],
            month=period[1],
            shifts=tuple(shifts),
            issues=tuple(issues),
            candidate_lines=candidates,
        )