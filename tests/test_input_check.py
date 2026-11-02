from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from attendance_gen.parsing.input_check import InputError, check_pdf


def make_pdf(path: Path, pages: int = 1) -> Path:
    pdf = canvas.Canvas(str(path))
    for _ in range(pages):
        pdf.drawString(50, 750, "x")
        pdf.showPage()
    pdf.save()
    return path


def test_valid_pdf_passes(tmp_path: Path) -> None:
    check_pdf(make_pdf(tmp_path / "ok.pdf"))


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        check_pdf(tmp_path / "nope.pdf")


def test_wrong_extension(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_bytes(b"%PDF-1.4")
    with pytest.raises(InputError):
        check_pdf(path)


def test_fake_pdf_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "fake.pdf"
    path.write_bytes(b"not a pdf at all")
    with pytest.raises(InputError):
        check_pdf(path)


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"")
    with pytest.raises(InputError):
        check_pdf(path)


def test_size_limit(tmp_path: Path) -> None:
    with pytest.raises(InputError):
        check_pdf(make_pdf(tmp_path / "big.pdf"), max_bytes=10)


def test_page_limit(tmp_path: Path) -> None:
    with pytest.raises(InputError):
        check_pdf(make_pdf(tmp_path / "long.pdf", pages=3), max_pages=2)