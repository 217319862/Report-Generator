from pathlib import Path

import pymupdf
import pytest

from attendance_gen.__main__ import main
from attendance_gen.domain.models import ReportType
from attendance_gen.formats import DEFAULT_FORMATS
from attendance_gen.generation.fonts import FontNotFoundError, find_font
from attendance_gen.generation.pdf_renderer import PdfRenderer
from attendance_gen.parsing.classifier import UnknownReportTypeError
from attendance_gen.pipeline import Pipeline
from tests.test_input_check import make_pdf

FIXTURES = Path(__file__).parent / "fixtures"
REAL_TEXT = (FIXTURES / "a_r_25.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def renderer() -> PdfRenderer:
    try:
        return PdfRenderer(find_font())
    except FontNotFoundError:
        pytest.skip("no Hebrew-capable font available")


def pdf_text(path: Path) -> str:
    with pymupdf.open(path) as doc:  # type: ignore[no-untyped-call]
        return "".join(page.get_text() for page in doc)


def test_end_to_end(tmp_path: Path, renderer: PdfRenderer) -> None:
    source = make_pdf(tmp_path / "in.pdf")
    result = Pipeline(DEFAULT_FORMATS, renderer, ocr=lambda _: REAL_TEXT).run(source, tmp_path / "out")
    assert result.report_type is ReportType.TYPE_A
    assert result.output_path.name == "in_sample.pdf"
    assert result.output_path.read_bytes().startswith(b"%PDF")
    assert not list((tmp_path / "out").glob("*.part"))


def test_same_input_gives_same_content(tmp_path: Path, renderer: PdfRenderer) -> None:
    source = make_pdf(tmp_path / "in.pdf")
    pipeline = Pipeline(DEFAULT_FORMATS, renderer, ocr=lambda _: REAL_TEXT)
    first = pipeline.run(source, tmp_path / "one")
    second = pipeline.run(source, tmp_path / "two")
    assert pdf_text(first.output_path) == pdf_text(second.output_path)


def test_existing_output_is_not_overwritten(tmp_path: Path, renderer: PdfRenderer) -> None:
    source = make_pdf(tmp_path / "in.pdf")
    pipeline = Pipeline(DEFAULT_FORMATS, renderer, ocr=lambda _: REAL_TEXT)
    pipeline.run(source, tmp_path / "out")
    with pytest.raises(FileExistsError):
        pipeline.run(source, tmp_path / "out")
    pipeline.run(source, tmp_path / "out", overwrite=True)


def test_unknown_type_leaves_no_output(tmp_path: Path, renderer: PdfRenderer) -> None:
    source = make_pdf(tmp_path / "in.pdf")
    pipeline = Pipeline(DEFAULT_FORMATS, renderer, ocr=lambda _: "שלום עולם")
    with pytest.raises(UnknownReportTypeError):
        pipeline.run(source, tmp_path / "out")
    assert not list((tmp_path / "out").glob("*"))


def test_duplicate_formats_are_rejected(renderer: PdfRenderer) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        Pipeline([DEFAULT_FORMATS[0], DEFAULT_FORMATS[0]], renderer)


def test_cli_returns_error_code_for_missing_file(tmp_path: Path) -> None:
    assert main([str(tmp_path / "nope.pdf")]) == 2


def test_invalid_period_is_rejected_before_any_work(tmp_path: Path, renderer: PdfRenderer) -> None:
    source = make_pdf(tmp_path / "in.pdf")
    pipeline = Pipeline(DEFAULT_FORMATS, renderer, ocr=lambda _: REAL_TEXT)
    with pytest.raises(ValueError, match="invalid month"):
        pipeline.run(source, tmp_path / "out", period=(2023, 13))
    assert not (tmp_path / "out").exists()


def test_period_is_ignored_by_type_a(tmp_path: Path, renderer: PdfRenderer) -> None:
    source = make_pdf(tmp_path / "in.pdf")
    pipeline = Pipeline(DEFAULT_FORMATS, renderer, ocr=lambda _: REAL_TEXT)
    result = pipeline.run(source, tmp_path / "out", period=(2023, 1))
    assert result.report_type is ReportType.TYPE_A


def test_cli_rejects_malformed_period(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as info:
        main([str(tmp_path / "in.pdf"), "--period", "2023-13"])
    assert info.value.code == 2