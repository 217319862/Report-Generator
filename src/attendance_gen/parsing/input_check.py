from pathlib import Path

import pymupdf

MAX_BYTES = 20 * 1024 * 1024
MAX_PAGES = 5


class InputError(ValueError):
    """קובץ הקלט לא תקין או חורג מהמגבלות."""


def check_pdf(path: Path, *, max_bytes: int = MAX_BYTES, max_pages: int = MAX_PAGES) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise InputError("הקובץ חייב להיות בסיומת .pdf")
    size = path.stat().st_size
    if size == 0 or size > max_bytes:
        raise InputError(f"גודל הקובץ לא תקין ({size} בתים, מקסימום {max_bytes})")
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise InputError("הקובץ אינו PDF תקין")
    try:
        with pymupdf.open(path) as doc:  # type: ignore[no-untyped-call]
            pages = doc.page_count
    except (RuntimeError, ValueError) as exc:
        raise InputError("לא ניתן לפתוח את ה-PDF") from exc
    if not 0 < pages <= max_pages:
        raise InputError(f"מספר עמודים לא נתמך: {pages} (מקסימום {max_pages})")