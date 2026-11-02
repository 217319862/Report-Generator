from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from attendance_gen.domain.models import AttendanceReport
from attendance_gen.generation.layout import LayoutSpec


class RenderError(RuntimeError):
    """יצירת הקובץ נכשלה."""


class BaseRenderer(ABC):
    """Renderer לפי פורמט הפלט (PDF, HTML), לא לפי סוג הדוח."""

    extension: ClassVar[str]

    @abstractmethod
    def render(self, report: AttendanceReport, layout: LayoutSpec, destination: Path) -> Path:
        """כותב את הדוח ל-destination ומחזיר את הנתיב."""


def safe_output_path(
    output_dir: Path, stem: str, extension: str, *, overwrite: bool = False
) -> Path:
    """נתיב כתיבה בטוח: רק בתוך תיקיית הפלט, בלי '..', ובלי דריסה בטעות."""
    name = Path(stem).name
    if not name or name in {".", ".."}:
        raise RenderError(f"invalid output name: {stem!r}")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = (output_dir / f"{name}{extension}").resolve()
    if path.parent != output_dir.resolve():
        raise RenderError("output path escapes the output directory")
    if path.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {path}")
    return path