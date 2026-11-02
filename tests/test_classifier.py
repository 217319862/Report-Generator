from pathlib import Path

import pytest

from attendance_gen.domain.models import ReportType
from attendance_gen.parsing.classifier import UnknownReportTypeError, classify
from attendance_gen.parsing.type_a_parser import TypeAParser
from attendance_gen.parsing.type_b_parser import TypeBParser

FIXTURES = Path(__file__).parent / "fixtures"
PARSERS = (TypeAParser(), TypeBParser())


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a_r_25.txt", ReportType.TYPE_A),
        ("a_r_25_v2.txt", ReportType.TYPE_A),
        ("n_r_5_n.txt", ReportType.TYPE_B),
        ("n_r_5_n_v2.txt", ReportType.TYPE_B),
    ],
)
def test_classify_real_ocr_output(name: str, expected: ReportType) -> None:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    assert classify(text, PARSERS).report_type == expected


def test_garbage_text_is_rejected() -> None:
    with pytest.raises(UnknownReportTypeError):
        classify("שלום עולם", PARSERS)