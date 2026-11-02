"""ניסוי: איזו הגדרת OCR נותנת הכי הרבה שורות קריאות בכרטיס."""

import itertools
import re
import sys
from pathlib import Path

from attendance_gen.parsing.ocr import pdf_to_text

DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2}\b")
TIME = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?!\d)")


def good_lines(text: str) -> int:
    """שורה טובה: תאריך ולפחות שתי שעות (כניסה ויציאה)."""
    return sum(1 for line in text.splitlines() if DATE.search(line) and len(TIME.findall(line)) >= 2)


def main(path: Path) -> None:
    results: list[tuple[int, int, int, int, int]] = []
    for psm, threshold, dpi in itertools.product((4, 6, 11), (140, 170, 200), (200, 300, 400)):
        text = pdf_to_text(path, psm=psm, threshold=threshold, dpi=dpi)
        results.append((good_lines(text), len(TIME.findall(text)), psm, threshold, dpi))
    print("שורות טובות | שעות | psm | סף | dpi")
    for row in sorted(results, reverse=True)[:8]:
        print(" | ".join(f"{value:>5}" for value in row))


if __name__ == "__main__":
    main(Path(sys.argv[1]))