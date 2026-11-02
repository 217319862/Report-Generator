import re

from attendance_gen.domain.models import ReportType
from attendance_gen.parsing.base_parser import BaseParser
from attendance_gen.parsing.result import ParseResult

_SHORT_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2}\b")


class TypeBParser(BaseParser):
    report_type = ReportType.TYPE_B

    def score(self, text: str) -> float:
        hits = len(_SHORT_DATE.findall(text)) + 3 * text.count("₪")
        return min(hits / 10, 1.0)

    def parse(self, text: str) -> ParseResult:
        raise NotImplementedError