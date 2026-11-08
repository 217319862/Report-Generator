import argparse
import io
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from attendance_gen.domain.validation import Severity
from attendance_gen.formats import DEFAULT_FORMATS
from attendance_gen.generation.base import RenderError
from attendance_gen.generation.fonts import FontNotFoundError
from attendance_gen.generation.pdf_renderer import PdfRenderer
from attendance_gen.parsing.base_parser import Period
from attendance_gen.parsing.classifier import UnknownReportTypeError
from attendance_gen.parsing.input_check import InputError
from attendance_gen.parsing.ocr import OcrError
from attendance_gen.parsing.result import ParseError
from attendance_gen.pipeline import Pipeline
from attendance_gen.transformation.base import GenerationError

EXPECTED_ERRORS = (
    FileNotFoundError,
    FileExistsError,
    InputError,
    OcrError,
    ParseError,
    UnknownReportTypeError,
    GenerationError,
    RenderError,
    FontNotFoundError,
)

_MIN_YEAR = 2000
_MAX_YEAR = 2100


def _period(text: str) -> Period:
    """קורא תקופה בפורמט YYYY-MM, למשל 2023-01."""
    try:
        year_text, month_text = text.split("-")
        year, month = int(year_text), int(month_text)
    except ValueError:
        raise argparse.ArgumentTypeError("הפורמט הנדרש הוא YYYY-MM, למשל 2023-01") from None
    if not (_MIN_YEAR <= year <= _MAX_YEAR and 1 <= month <= 12):
        raise argparse.ArgumentTypeError("שנה או חודש מחוץ לטווח")
    return year, month


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="attendance_gen", description="יוצר וריאציה הגיונית של דוח נוכחות."
    )
    parser.add_argument("pdf", type=Path, help="קובץ דוח נוכחות בפורמט PDF")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("data/output"))
    parser.add_argument("--overwrite", action="store_true", help="מותר לדרוס קובץ קיים")
    parser.add_argument("--font", type=Path, default=None, help="קובץ פונט .ttf עם תמיכה בעברית")
    parser.add_argument("--company", default="חברה לדוגמה")
    parser.add_argument("--employee", default="עובד לדוגמה")
    parser.add_argument(
        "--period",
        type=_period,
        default=None,
        help="חודש הדוח בפורמט YYYY-MM, כשאי אפשר לקרוא אותו מהקובץ. משפיע רק על TYPE_B",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args(argv)


def _use_utf8() -> None:
    """מונע קריסה בהדפסת עברית בקונסולות Windows ישנות."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    _use_utf8()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    try:
        renderer = PdfRenderer(args.font, company=args.company, employee=args.employee)
        result = Pipeline(DEFAULT_FORMATS, renderer).run(
            args.pdf, args.output_dir, overwrite=args.overwrite, period=args.period
        )
    except EXPECTED_ERRORS as exc:
        print(f"שגיאה: {exc}", file=sys.stderr)
        return 2

    warnings = sum(1 for issue in result.issues if issue.severity is Severity.WARNING)
    print(f"נוצר: {result.output_path}")
    print(f"סוג דוח: {result.report_type}, שורות: {result.rows}, אזהרות קריאה: {warnings}")
    if args.verbose:
        for issue in result.issues:
            print(f"{issue.code}: {issue.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())