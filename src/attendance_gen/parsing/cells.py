import numpy as np
import pytesseract
from PIL import Image

from attendance_gen.parsing.grid import GrayImage
from attendance_gen.parsing.table import Box

DIGITS_DATE = "0123456789/"
DIGITS_TIME = "0123456789:"
DIGITS_DECIMAL = "0123456789."
DIGITS_AMOUNT = "0123456789.,"

_MARGIN = 6  # חותכים את קווי התא עצמם
_PADDING = 20
_SHADED_MEAN = 210.0  # תא שהבהירות הממוצעת שלו נמוכה מזה הוא אפור
_TIMEOUT_SECONDS = 10
_REGION_TIMEOUT_SECONDS = 30
_PSM_LINE = 7  # שורה אחת
_PSM_BLOCK = 6  # בלוק טקסט אחיד


def crop_cell(gray: GrayImage, box: Box, *, margin: int = _MARGIN) -> GrayImage:
    x0, y0, x1, y1 = box
    return gray[y0 + margin : y1 - margin, x0 + margin : x1 - margin]


def is_shaded(cell: GrayImage, *, threshold: float = _SHADED_MEAN) -> bool:
    return cell.size > 0 and float(cell.mean()) < threshold


def _ocr(image: GrayImage, *, whitelist: str, psm: int, timeout: int) -> str:
    padded = np.pad(image, _PADDING, constant_values=255)
    config = f"--psm {psm} -c tessedit_char_whitelist={whitelist}"
    text: str = pytesseract.image_to_string(Image.fromarray(padded), config=config, timeout=timeout)
    return text.strip()


def read_cell(
    gray: GrayImage,
    box: Box,
    *,
    whitelist: str,
    timeout: int = _TIMEOUT_SECONDS,
    skip_shaded: bool = True,
) -> str:
    """skip_shaded=False לעמודות שהרקע שלהן אפור תמיד (למשל עמודת התאריך)."""
    cell = crop_cell(gray, box)
    if cell.size == 0 or (skip_shaded and is_shaded(cell)):
        return ""
    return _ocr(cell, whitelist=whitelist, psm=_PSM_LINE, timeout=timeout)


def read_region(
    gray: GrayImage, box: Box, *, whitelist: str, timeout: int = _REGION_TIMEOUT_SECONDS
) -> str:
    """OCR לאזור שלם עם כמה שורות (למשל טבלת הסיכום). בלי בדיקת אפור ובלי שוליים."""
    x0, y0, x1, y1 = box
    region = gray[y0:y1, x0:x1]
    if region.size == 0:
        return ""
    return _ocr(region, whitelist=whitelist, psm=_PSM_BLOCK, timeout=timeout)