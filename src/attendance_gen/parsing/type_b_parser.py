import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import time, timedelta
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from statistics import median

from attendance_gen.domain.models import ReportType
from attendance_gen.domain.validation import TOLERANCE, Issue, Severity
from attendance_gen.parsing.base_parser import BaseParser, Period
from attendance_gen.parsing.cells import (
    DIGITS_AMOUNT,
    DIGITS_DATE,
    DIGITS_DECIMAL,
    DIGITS_TIME,
    read_cell,
    read_region,
)
from attendance_gen.parsing.grid import GrayImage, find_grid, render_page
from attendance_gen.parsing.result import ObservedShift, ParseError, ParseResult
from attendance_gen.parsing.table import Box, TableNotFoundError, body_cell_boxes

_SHORT_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2}\b")  # לזיהוי סוג הדוח (score)

# לקריאת החודש: תאריכים בפורמט יום/חודש/שנה בשתי ספרות, וכותרת כמו "ספט-22"
_DATE_PARTS = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{2})(?!\d)")
_HEBREW_MONTHS = {
    "ינו": 1, "פבר": 2, "מרץ": 3, "מרס": 3, "אפר": 4, "מאי": 5, "יונ": 6,
    "יול": 7, "אוג": 8, "ספט": 9, "אוק": 10, "נוב": 11, "דצמ": 12,
}  # fmt: skip
_MONTH_NAMES = "|".join(_HEBREW_MONTHS)
_HEADER_FORWARD = re.compile(rf"({_MONTH_NAMES})[א-ת]*\s*[-־–.]?\s*(\d{{2}})(?!\d)")
_HEADER_REVERSED = re.compile(rf"(?<!\d)(\d{{2}})\s*[-־–.]?\s*({_MONTH_NAMES})")

_TIME_CELL = re.compile(r"(?:[01]?\d|2[0-3]):[0-5]\d")
_TOTAL_CELL = re.compile(r"\d{1,2}\.\d{2}")
_AMOUNT = re.compile(r"(?<![\d.,])(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{1,2}(?!\d)")

_MIN_DATE_VOTES = 3
_MIN_ROWS_FOR_OUTLIERS = 5
_MIN_FILLED_CELLS = 2  # שורה עם תא בודד היא רעש של OCR, לא יום עבודה
_OUTLIER_MINUTES = 90
_PAY_TOLERANCE = Decimal("0.5")  # תשלום מעוגל, ושעות עם שתי ספרות אחרי הנקודה
_ONE = Decimal(1)  # מסנן רעש כמו "0.00"
MIN_COVERAGE = 0.5


@dataclass(frozen=True, slots=True)
class RawRow:
    """מה שנקרא (כטקסט) משלושת התאים של שורה אחת. מחרוזת ריקה = לא נקרא."""

    line_no: int
    clock_in: str
    clock_out: str
    total: str


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _row_warning(code: str, line_no: int, detail: str) -> Issue:
    return Issue(code, f"שורה {line_no}: {detail}", severity=Severity.WARNING)


def _raw_values(row: RawRow) -> str:
    """מה שה-OCR קרא בשורה, להצגה באזהרות."""
    return f"כניסה={row.clock_in!r}, יציאה={row.clock_out!r}, סה\"כ={row.total!r}"


def _parse_time(text: str) -> time | None:
    if not _TIME_CELL.fullmatch(text):
        return None
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


def _parse_total(text: str) -> Decimal | None:
    return Decimal(text) if _TOTAL_CELL.fullmatch(text) else None


def _read_row(row: RawRow) -> ObservedShift | Issue:
    clock_in = _parse_time(row.clock_in)
    clock_out = _parse_time(row.clock_out)
    total = _parse_total(row.total)
    if clock_in is None or clock_out is None or total is None:
        return _row_warning(
            "ROW_UNREADABLE", row.line_no, f"לא כל התאים נקראו ({_raw_values(row)})"
        )

    # בכרטיס הזה אין הפסקה, לכן סה"כ חייב להיות יציאה פחות כניסה
    worked = Decimal(_minutes(clock_out) - _minutes(clock_in)) / Decimal(60)
    if worked <= 0 or abs(worked - total) > TOLERANCE:
        return _row_warning(
            "ROW_INCONSISTENT",
            row.line_no,
            f"כניסה, יציאה וסה\"כ לא מתאימים ({_raw_values(row)})",
        )
    return ObservedShift(clock_in, clock_out, timedelta(0), row.line_no)


def _drop_outliers(shifts: list[ObservedShift]) -> tuple[list[ObservedShift], list[Issue]]:
    """משמרת שרחוקה מהחציוני של כולן היא כנראה קריאה שגויה שבמקרה עקבית."""
    if len(shifts) < _MIN_ROWS_FOR_OUTLIERS:
        return shifts, []
    typical_in = median(_minutes(s.clock_in) for s in shifts)
    typical_out = median(_minutes(s.clock_out) for s in shifts)
    kept: list[ObservedShift] = []
    issues: list[Issue] = []
    for shift in shifts:
        near_in = abs(_minutes(shift.clock_in) - typical_in) <= _OUTLIER_MINUTES
        near_out = abs(_minutes(shift.clock_out) - typical_out) <= _OUTLIER_MINUTES
        if near_in and near_out:
            kept.append(shift)
        else:
            issues.append(_row_warning("ROW_OUTLIER", shift.line_no, "רחוקה מהמשמרת האופיינית"))
    return kept, issues


def _read_shifts(rows: Sequence[RawRow]) -> tuple[list[ObservedShift], list[Issue], list[int]]:
    """(משמרות שנקראו, אזהרות, מספרי השורות שנראו כימי עבודה)."""
    shifts: list[ObservedShift] = []
    issues: list[Issue] = []
    candidates: list[int] = []
    for row in rows:
        filled = sum(1 for cell in (row.clock_in, row.clock_out, row.total) if cell)
        if filled == 0:
            continue  # שורה ריקה: שבת, חג או יום בלי עבודה
        if filled < _MIN_FILLED_CELLS:
            # תא בודד בשורה שנראית ריקה הוא כנראה שארית של קו רשת, ולא יום עבודה
            issues.append(
                _row_warning("ROW_IGNORED", row.line_no, f"נקרא תא בודד ({_raw_values(row)})")
            )
            continue
        candidates.append(row.line_no)
        outcome = _read_row(row)
        if isinstance(outcome, Issue):
            issues.append(outcome)
        else:
            shifts.append(outcome)
    kept, outlier_issues = _drop_outliers(shifts)
    return kept, issues + outlier_issues, candidates


def _find_period(text: str) -> tuple[Period | None, list[Issue]]:
    """(שנה, חודש) מהתאריכים בטקסט (הצבעה) או מכותרת כמו "ספט-22"."""
    date_votes: Counter[Period] = Counter()
    for day, month, year in _DATE_PARTS.findall(text):
        if 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
            date_votes[(2000 + int(year), int(month))] += 1

    header_votes: Counter[Period] = Counter()
    for name, year in _HEADER_FORWARD.findall(text):
        header_votes[(2000 + int(year), _HEBREW_MONTHS[name])] += 1
    for year, name in _HEADER_REVERSED.findall(text):
        header_votes[(2000 + int(year), _HEBREW_MONTHS[name])] += 1

    enough_dates = sum(date_votes.values()) >= _MIN_DATE_VOTES
    from_dates = date_votes.most_common(1)[0][0] if enough_dates else None
    from_header = header_votes.most_common(1)[0][0] if header_votes else None

    issues: list[Issue] = []
    if from_dates and from_header and from_dates != from_header:
        issues.append(
            Issue("PERIOD_MISMATCH", "החודש בכותרת שונה מהחודש בתאריכים", severity=Severity.WARNING)
        )
    return from_dates or from_header, issues


def _find_hourly_rate(summary_text: str) -> tuple[Decimal | None, list[Issue]]:
    """מחיר לשעה: האמצעי מבין שלושה מספרים שבהם שעות כפול מחיר שווה לתשלום.

    המספרים נקראים מלמעלה למטה: שעות, מחיר, תשלום (או הפוך, תלוי בכיוון הקריאה),
    ולכן המחיר תמיד באמצע. בזכות זה אין בלבול בין שעות למחיר.
    """
    numbers = [Decimal(match.replace(",", "")) for match in _AMOUNT.findall(summary_text)]
    rates = {
        middle
        for first, middle, last in combinations(numbers, 3)
        if min(first, middle, last) >= _ONE
        and len({first, middle, last}) == 3
        and (
            abs(first * middle - last) <= _PAY_TOLERANCE
            or abs(last * middle - first) <= _PAY_TOLERANCE
        )
    }
    if len(rates) == 1:
        return next(iter(rates)), []
    code = "RATE_AMBIGUOUS" if rates else "RATE_NOT_FOUND"
    return None, [Issue(code, "מחיר לשעה לא זוהה בטבלת הסיכום", severity=Severity.WARNING)]


def build_result(
    rows: Sequence[RawRow],
    text: str,
    summary_text: str,
    *,
    period_override: Period | None = None,
) -> ParseResult:
    """הלוגיקה של הפרסור, בלי תמונות ובלי OCR, כדי שאפשר יהיה לבדוק אותה."""
    period, period_issues = _find_period(text)
    if period_override is not None:
        if period is not None and period != period_override:
            period_issues.append(
                Issue(
                    "PERIOD_OVERRIDDEN",
                    "התקופה שנקבעה ידנית שונה מהתקופה שנקראה",
                    severity=Severity.WARNING,
                )
            )
        period = period_override

    shifts, row_issues, candidate_lines = _read_shifts(rows)
    issues = period_issues + row_issues

    if period is None:
        raise ParseError("לא נמצאו חודש ושנה בטקסט. אפשר לציין אותם ידנית", tuple(issues))
    if not shifts or len(shifts) / len(candidate_lines) < MIN_COVERAGE:
        raise ParseError(
            f"נקראו {len(shifts)} שורות מתוך {len(candidate_lines)}", tuple(issues)
        )

    rate, rate_issues = _find_hourly_rate(summary_text)
    return ParseResult(
        report_type=ReportType.TYPE_B,
        year=period[0],
        month=period[1],
        shifts=tuple(shifts),
        issues=tuple(issues + rate_issues),
        candidate_lines=len(candidate_lines),
        hourly_rate=rate,
        workday_lines=tuple(candidate_lines),
    )


def _read_rows(gray: GrayImage, boxes: Sequence[Mapping[str, Box]]) -> list[RawRow]:
    return [
        RawRow(
            line_no=index,
            clock_in=read_cell(gray, box["entry"], whitelist=DIGITS_TIME),
            clock_out=read_cell(gray, box["exit"], whitelist=DIGITS_TIME),
            total=read_cell(gray, box["total"], whitelist=DIGITS_DECIMAL),
        )
        for index, box in enumerate(boxes, start=1)
    ]


def _read_date_cells(gray: GrayImage, boxes: Sequence[Mapping[str, Box]]) -> str:
    """תאי התאריך, תא אחרי תא. גיבוי כשה-OCR של העמוד כולו לא מוצא חודש."""
    # עמודת התאריך אפורה במקור, ולכן לא מדלגים על תאים אפורים
    cells = (
        read_cell(gray, box["date"], whitelist=DIGITS_DATE, skip_shaded=False)
        for box in boxes
    )
    return "\n".join(cell for cell in cells if cell)


def _read_summary(gray: GrayImage, top: int) -> str:
    """טבלת הסיכום שמעל הטבלה הראשית, נקראת תא אחרי תא (מלמעלה למטה).

    קריאה של כל האזור בבת אחת נכשלת בגלל התאים האפורים המנוקדים והתוויות
    בעברית, אבל תא בודד עם ערך מספרי נקרא היטב.
    """
    header = gray[:top, :]
    grid = find_grid(header)
    cells = (
        read_region(header, grid.cell_box(row, col), whitelist=DIGITS_AMOUNT)
        for row in range(grid.rows)
        for col in range(grid.cols)
    )
    return "\n".join(cell for cell in cells if cell)


class TypeBParser(BaseParser):
    report_type = ReportType.TYPE_B

    def score(self, text: str) -> float:
        hits = len(_SHORT_DATE.findall(text)) + 3 * text.count("₪")
        return min(hits / 10, 1.0)

    def parse(self, text: str) -> ParseResult:
        raise NotImplementedError("TYPE_B צריך את קובץ ה-PDF: קראו ל-parse_document")

    def parse_document(
        self, pdf_path: Path, text: str, *, period: Period | None = None
    ) -> ParseResult:
        gray = render_page(pdf_path)
        try:
            boxes = body_cell_boxes(find_grid(gray))
        except TableNotFoundError as error:
            raise ParseError(f"לא נמצאה טבלת נתונים: {error}") from error

        # טבלת הסיכום נמצאת מעל השורה הראשונה של טבלת הנתונים
        top = boxes[0]["date"][1]
        summary = _read_summary(gray, top)
        rows = _read_rows(gray, boxes)

        # גיבוי: אם הטקסט הכללי לא נותן חודש ולא נקבע ידנית, קוראים את תאי התאריך
        if period is None and _find_period(text)[0] is None:
            text = f"{text}\n{_read_date_cells(gray, boxes)}"
        return build_result(rows, text, summary, period_override=period)
