import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from attendance_gen.domain.models import ReportType
from attendance_gen.domain.validation import Issue
from attendance_gen.formats import ReportFormat
from attendance_gen.generation.base import BaseRenderer, safe_output_path
from attendance_gen.parsing.base_parser import Period
from attendance_gen.parsing.classifier import classify
from attendance_gen.parsing.input_check import check_pdf
from attendance_gen.parsing.ocr import pdf_to_text
from attendance_gen.transformation.base import seed_from_bytes

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    output_path: Path
    report_type: ReportType
    rows: int
    issues: tuple[Issue, ...]


class Pipeline:
    def __init__(
        self,
        formats: Sequence[ReportFormat],
        renderer: BaseRenderer,
        ocr: Callable[[Path], str] = pdf_to_text,
    ) -> None:
        types = [f.report_type for f in formats]
        if not types:
            raise ValueError("at least one report format is required")
        if len(set(types)) != len(types):
            raise ValueError("duplicate report type in formats")
        self._formats = {f.report_type: f for f in formats}
        self._renderer = renderer
        self._ocr = ocr

    def run(
        self,
        pdf_path: Path,
        output_dir: Path,
        *,
        overwrite: bool = False,
        period: Period | None = None,
    ) -> PipelineResult:
        # כשלון מהיר: קלט ויעד נבדקים לפני ה-OCR היקר
        if period is not None and not 1 <= period[1] <= 12:
            raise ValueError(f"invalid month in period: {period[1]}")
        check_pdf(pdf_path)
        destination = safe_output_path(
            output_dir, f"{pdf_path.stem}_sample", self._renderer.extension, overwrite=overwrite
        )

        text = self._ocr(pdf_path)
        parser = classify(text, [f.parser for f in self._formats.values()])
        fmt = self._formats[parser.report_type]
        parsed = fmt.parser.parse_document(pdf_path, text, period=period)

        seed = seed_from_bytes(pdf_path.read_bytes())
        report = fmt.strategy.transform(parsed, seed)

        # כתיבה אטומית: לא נשאר קובץ חלקי אם משהו נכשל באמצע
        partial = destination.with_name(destination.name + ".part")
        try:
            self._renderer.render(report, fmt.layout, partial)
            partial.replace(destination)
        except Exception:
            partial.unlink(missing_ok=True)
            raise

        # ביומן נכתבים רק מטא-נתונים, לעולם לא טקסט מהדוח
        log.info("%s -> %s (%s, %d rows)", pdf_path.name, destination.name, fmt.report_type, len(report.rows))
        return PipelineResult(destination, fmt.report_type, len(report.rows), parsed.issues)