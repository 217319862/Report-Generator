from abc import ABC, abstractmethod
from typing import ClassVar

from attendance_gen.domain.models import ReportType
from attendance_gen.parsing.result import ParseResult


class BaseParser(ABC):
    report_type: ClassVar[ReportType]

    @abstractmethod
    def score(self, text: str) -> float:
        """ציון בין 0 ל-1: כמה הטקסט דומה לפורמט הזה."""

    @abstractmethod
    def parse(self, text: str) -> ParseResult:
        """מוציא מהטקסט את מה שאפשר לסמוך עליו, ומתעד את השאר."""