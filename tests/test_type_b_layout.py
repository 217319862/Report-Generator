import calendar
import re
from pathlib import Path

import pymupdf
import pytest

from attendance_gen.domain.models import AttendanceReport, ReportType
from attendance_gen.generation.fonts import FontNotFoundError, find_font
from attendance_gen.generation.layouts import LAYOUTS, TYPE_B_LAYOUT
from attendance_gen.generation.pdf_renderer import PdfRenderer
from attendance_gen.transformation.type_b import TypeBStrategy
from tests.test_type_b_transformation import make_parsed


@pytest.fixture(scope="module")
def font_path() -> Path:
    try:
        return find_font()
    except FontNotFoundError:
        pytest.skip("no Hebrew-capable font available")


def render_text(tmp_path: Path, font_path: Path) -> tuple[str, AttendanceReport]:
    report = TypeBStrategy().transform(make_parsed(), 5)
    out = PdfRenderer(font_path).render(report, TYPE_B_LAYOUT, tmp_path / "b.pdf")
    with pymupdf.open(out) as doc:  # type: ignore[no-untyped-call]
        return "".join(page.get_text() for page in doc), report


def test_layout_is_registered() -> None:
    assert LAYOUTS[ReportType.TYPE_B] is TYPE_B_LAYOUT


def test_every_day_of_the_month_is_listed(tmp_path: Path, font_path: Path) -> None:
    text, _ = render_text(tmp_path, font_path)
    days = calendar.monthrange(2022, 9)[1]
    # (?<!\d) ו-(?!\d): כדי ש-1/9/22 לא ייספר כנמצא בגלל 11/9/22
    missing = [
        d for d in range(1, days + 1) if not re.search(rf"(?<!\d){d}/9/22(?!\d)", text)
    ]
    assert missing == []


def test_summary_shows_rate_and_pay(tmp_path: Path, font_path: Path) -> None:
    text, report = render_text(tmp_path, font_path)
    assert report.total_pay is not None
    assert "30.65" in text
    assert f"{report.total_pay:,.2f}" in text