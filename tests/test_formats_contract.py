from datetime import date, time
from decimal import Decimal
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from attendance_gen.domain.models import AttendanceReport, AttendanceRow, ReportType
from attendance_gen.formats import DEFAULT_FORMATS, ReportFormat
from attendance_gen.generation.fonts import FontNotFoundError, find_font
from attendance_gen.generation.layouts import LAYOUTS
from attendance_gen.generation.pdf_renderer import _MARGIN, PdfRenderer

FORMAT_IDS = [fmt.report_type.value for fmt in DEFAULT_FORMATS]


@pytest.fixture(scope="module")
def renderer() -> PdfRenderer:
    try:
        return PdfRenderer(find_font())
    except FontNotFoundError:
        pytest.skip("no Hebrew-capable font available")


def sample_report(report_type: ReportType) -> AttendanceReport:
    rows = tuple(
        AttendanceRow(
            day=date(2022, 9, number),
            clock_in=time(8, 30),
            clock_out=time(12, 0),
            total_hours=Decimal("3.5"),
        )
        for number in (4, 5, 6)
    )
    return AttendanceReport(
        report_type=report_type,
        rows=rows,
        period_label="09/2022",
        hourly_rate=Decimal("30.65"),
    )


def test_every_report_type_has_exactly_one_format() -> None:
    types = [fmt.report_type for fmt in DEFAULT_FORMATS]
    assert sorted(types) == sorted(ReportType)


@pytest.mark.parametrize("fmt", DEFAULT_FORMATS, ids=FORMAT_IDS)
def test_layout_is_registered(fmt: ReportFormat) -> None:
    assert LAYOUTS[fmt.report_type] is fmt.layout


@pytest.mark.parametrize("fmt", DEFAULT_FORMATS, ids=FORMAT_IDS)
def test_score_is_between_zero_and_one(fmt: ReportFormat) -> None:
    for text in ("", "שלום עולם", "1/9/22 ₪ 8:30 12:00 3.50"):
        assert 0.0 <= fmt.parser.score(text) <= 1.0


@pytest.mark.parametrize("fmt", DEFAULT_FORMATS, ids=FORMAT_IDS)
def test_columns_fit_within_page_margins(fmt: ReportFormat) -> None:
    usable_mm = (A4[0] - 2 * _MARGIN) / mm
    assert sum(column.width_mm for column in fmt.layout.columns) <= usable_mm + 0.01


@pytest.mark.parametrize("fmt", DEFAULT_FORMATS, ids=FORMAT_IDS)
def test_every_cell_is_text(fmt: ReportFormat) -> None:
    report = sample_report(fmt.report_type)
    row = report.rows[0]
    for column in fmt.layout.columns:
        assert isinstance(column.value(row), str)
        assert isinstance(column.blank(row.day), str)
        if column.total is not None:
            assert isinstance(column.total(report), str)
    for item in fmt.layout.summary:
        assert isinstance(item.value(report), str)


@pytest.mark.parametrize("fmt", DEFAULT_FORMATS, ids=FORMAT_IDS)
def test_layout_renders_a_minimal_report(
    fmt: ReportFormat, renderer: PdfRenderer, tmp_path: Path
) -> None:
    report = sample_report(fmt.report_type)
    out = renderer.render(report, fmt.layout, tmp_path / "out.pdf")
    assert out.read_bytes().startswith(b"%PDF")