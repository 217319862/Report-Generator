from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

DEFAULT_LANGS = "heb+eng"
DEFAULT_DPI = 300
DEFAULT_PSM = 6
DEFAULT_THRESHOLD = 170
DEFAULT_TIMEOUT_SECONDS = 60


class OcrError(RuntimeError):
    """נזרקת כשקריאת הקובץ נכשלת"""


def ensure_tesseract() -> None:
    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrError(
            "Tesseract OCR is not installed or not on PATH. See README for setup."
        ) from exc


def _prepare(image: Image.Image, threshold: int) -> Image.Image:
    """שחור-לבן: כל פיקסל בהיר מהסף הופך ללבן, השאר לשחור."""
    gray = image.convert("L")
    return gray.point(lambda p: 255 if p > threshold else 0)


def pdf_to_text(
    pdf_path: Path,
    *,
    lang: str = DEFAULT_LANGS,
    dpi: int = DEFAULT_DPI,
    psm: int = DEFAULT_PSM,
    threshold: int = DEFAULT_THRESHOLD,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """ממיר כל עמוד ב-PDF לתמונה, מריץ עליו OCR ומחזיר את הטקסט הגולמי."""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    ensure_tesseract()

    pages: list[str] = []
    try:
        with pymupdf.open(pdf_path) as doc:  # type: ignore[no-untyped-call]
            for page in doc:
                pixmap = page.get_pixmap(dpi=dpi)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                prepared = _prepare(image, threshold)
                pages.append(
                    pytesseract.image_to_string(
                        prepared, lang=lang, config=f"--psm {psm}", timeout=timeout
                    )
                )
    except RuntimeError as exc:  # כולל TesseractError ו-timeout
        raise OcrError(f"OCR failed for {pdf_path.name}: {exc}") from exc

    return "\n".join(pages)