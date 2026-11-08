from dataclasses import dataclass

from attendance_gen.domain.models import ReportType
from attendance_gen.generation.layout import LayoutSpec
from attendance_gen.generation.layouts import TYPE_A_LAYOUT, TYPE_B_LAYOUT
from attendance_gen.parsing.base_parser import BaseParser
from attendance_gen.parsing.type_a_parser import TypeAParser
from attendance_gen.parsing.type_b_parser import TypeBParser
from attendance_gen.transformation.base import BaseTransformationStrategy
from attendance_gen.transformation.type_a import TypeAStrategy
from attendance_gen.transformation.type_b import TypeBStrategy


@dataclass(frozen=True, slots=True)
class ReportFormat:
    """כל מה שצריך לדעת על סוג דוח אחד. סוג חדש = אובייקט אחד נוסף כאן."""

    parser: BaseParser
    strategy: BaseTransformationStrategy
    layout: LayoutSpec

    @property
    def report_type(self) -> ReportType:
        return self.parser.report_type


DEFAULT_FORMATS: tuple[ReportFormat, ...] = (
    ReportFormat(TypeAParser(), TypeAStrategy(), TYPE_A_LAYOUT),
    ReportFormat(TypeBParser(), TypeBStrategy(), TYPE_B_LAYOUT),
)