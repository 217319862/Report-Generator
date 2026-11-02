from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path

import pymupdf
import pytest

from attendance_gen.domain.models import AttendanceReport, AttendanceRow, ReportType
from attendance_gen.generation.base import RenderError, safe_output_path
from attendance_gen.generation.fonts import FontNotFoundError, find_font
from attendance_gen.generation.layouts import TYPE_A_LAYOUT
from attendance_gen.generation.pdf_renderer import PdfRenderer


@pytest.fixture(scope="module")
def font_path() -> Path:
    try:
        return find_font()
    except FontNotFoundError:
        pytest.skip("no Hebrew-capable font available")


def make_report() -> AttendanceReport:
    rows = tuple(
        AttendanceRow(
            day=date(2023, 2, d),
            clock_in=time(8, 0),
            clock_out=time(16, 0),
            total_hours=Decimal("7.50"),
            break_duration=timedelta(minutes=30),
            hours_100=Decimal("7.50"),
            location="אתר לדוגמה",
        )
        for d in (1, 2, 5)
    )
    return AttendanceReport(ReportType.TYPE_A, rows, period_label="02/2023")


def test_creates_valid_pdf_with_totals(tmp_path: Path, font_path: Path) -> None:
    out = PdfRenderer(font_path).render(make_report(), TYPE_A_LAYOUT, tmp_path / "x.pdf")
    assert out.read_bytes().startswith(b"%PDF")
    with pymupdf.open(out) as doc:  # type: ignore[no-untyped-call]
        text = "".join(page.get_text() for page in doc)
    assert "22.50" in text  # סה"כ שעות
    assert "01:30" in text  # סה"כ הפסקות


def test_untrusted_text_does_not_break_rendering(tmp_path: Path, font_path: Path) -> None:
    renderer = PdfRenderer(font_path, company="<b>evil</i> & co", employee="<unclosed")
    out = renderer.render(make_report(), TYPE_A_LAYOUT, tmp_path / "x.pdf")
    assert out.exists()


def test_output_path_cannot_escape_directory(tmp_path: Path) -> None:
    path = safe_output_path(tmp_path, "../../evil", ".pdf")
    assert path.parent == tmp_path.resolve()
    assert path.name == "evil.pdf"


def test_existing_output_is_not_overwritten(tmp_path: Path) -> None:
    (tmp_path / "a.pdf").write_bytes(b"x")
    with pytest.raises(FileExistsError):
        safe_output_path(tmp_path, "a", ".pdf")
    assert safe_output_path(tmp_path, "a", ".pdf", overwrite=True).name == "a.pdf"


def test_empty_name_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RenderError):
        safe_output_path(tmp_path, "..", ".pdf")