import os
from pathlib import Path

ENV_VAR = "ATTENDANCE_FONT"
_CANDIDATES = (
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)


class FontNotFoundError(RuntimeError):
    """לא נמצא פונט שתומך בעברית."""


def find_font(explicit: Path | None = None) -> Path:
    env = os.environ.get(ENV_VAR)
    wanted = explicit or (Path(env) if env else None)
    if wanted is not None:
        if not wanted.is_file():
            raise FontNotFoundError(f"font file not found: {wanted}")
        return wanted
    for candidate in _CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FontNotFoundError(f"no Hebrew-capable font found; set {ENV_VAR} to a .ttf file")