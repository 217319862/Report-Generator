from pathlib import Path

import pytest

from attendance_gen.parsing.ocr import pdf_to_text


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        pdf_to_text(tmp_path / "nope.pdf")