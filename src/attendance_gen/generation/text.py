import re

from bidi import get_display

_HEBREW = re.compile(r"[\u0590-\u05FF]")


def visual(text: str) -> str:
    """הופך טקסט עברי לסדר ויזואלי (משמאל לימין) לצורך ציור ב-PDF."""
    return get_display(text) if _HEBREW.search(text) else text