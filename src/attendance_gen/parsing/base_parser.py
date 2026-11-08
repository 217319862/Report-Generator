from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from attendance_gen.domain.models import ReportType
from attendance_gen.parsing.result import ParseResult

Period = tuple[int, int]  # (שנה, חודש)


class BaseParser(ABC):
    report_type: ClassVar[ReportType]

    @abstractmethod
    def score(self, text: str) -> float:
        """ציון בין 0 ל-1: כמה הטקסט דומה לפורמט הזה."""

    @abstractmethod
    def parse(self, text: str) -> ParseResult:
        """מוציא מהטקסט את מה שאפשר לסמוך עליו, ומתעד את השאר."""

    def parse_document(
        self, pdf_path: Path, text: str, *, period: Period | None = None
    ) -> ParseResult:
        """פרסור שיכול להשתמש גם בקובץ עצמו, ובתקופה שנקבעה ידנית.

        ברירת המחדל מפרסרת מטקסט בלבד ומתעלמת מהתקופה, כי פרסר כזה קורא אותה
        בעצמו. פרסר שלא יכול (TYPE_B) דורס את המתודה הזאת.
        """
        del pdf_path, period
        return self.parse(text)