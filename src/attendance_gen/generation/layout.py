from collections.abc import Callable
from dataclasses import dataclass

from attendance_gen.domain.models import AttendanceReport, AttendanceRow


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    header: str
    width_mm: float
    value: Callable[[AttendanceRow], str]
    total: Callable[[AttendanceReport], str] | None = None


@dataclass(frozen=True, slots=True)
class SummaryItem:
    label: str
    value: Callable[[AttendanceReport], str]


@dataclass(frozen=True, slots=True)
class LayoutSpec:
    title: str
    columns: tuple[ColumnSpec, ...]  # בסדר קריאה: הראשון הוא הימני ביותר
    summary: tuple[SummaryItem, ...] = ()
    show_title: bool = True