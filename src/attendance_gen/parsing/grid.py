from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from numpy.typing import NDArray

GrayImage = NDArray[np.uint8]

_LINE_LENGTH_DIVISOR = 30
_CLUSTER_GAP = 3
_DEFAULT_MIN_FRACTION = 0.6


@dataclass(frozen=True, slots=True)
class Grid:


    xs: tuple[int, ...]
    ys: tuple[int, ...]

    @property
    def rows(self) -> int:
        return max(len(self.ys) - 1, 0)

    @property
    def cols(self) -> int:
        return max(len(self.xs) - 1, 0)

    def cell_box(self, row: int, col: int) -> tuple[int, int, int, int]:
        """(x0, y0, x1, y1) של תא."""
        return self.xs[col], self.ys[row], self.xs[col + 1], self.ys[row + 1]


def render_page(pdf_path: Path, *, dpi: int = 300, page_index: int = 0) -> GrayImage:
    with pymupdf.open(pdf_path) as doc:  # type: ignore[no-untyped-call]
        pixmap = doc[page_index].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        raw = np.frombuffer(pixmap.samples, dtype=np.uint8)
        return raw.reshape(pixmap.height, pixmap.stride)[:, : pixmap.width].copy()


def _binarize(gray: GrayImage) -> GrayImage:
    """הופך את התמונה לשחור-לבן כשהקווים והטקסט לבנים."""
    return cv2.adaptiveThreshold(  # type: ignore[no-any-return]
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 15
    )


def _extract_lines(binary: GrayImage, *, horizontal: bool) -> GrayImage:
    height, width = binary.shape
    size = max((width if horizontal else height) // _LINE_LENGTH_DIVISOR, 10)
    shape = (size, 1) if horizontal else (1, size)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, shape)
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)  # type: ignore[no-any-return]


def _positions(mask: GrayImage, *, axis: int, min_fraction: float) -> tuple[int, ...]:
    profile = mask.sum(axis=axis, dtype=np.int64) / 255
    peak = profile.max()
    if peak == 0:
        return ()
    hits = np.flatnonzero(profile >= peak * min_fraction)
    groups = np.split(hits, np.flatnonzero(np.diff(hits) > _CLUSTER_GAP) + 1)
    return tuple(int(group.mean()) for group in groups if len(group))


def find_grid(gray: GrayImage, *, min_fraction: float = _DEFAULT_MIN_FRACTION) -> Grid:
    binary = _binarize(gray)
    horizontal = _extract_lines(binary, horizontal=True)
    vertical = _extract_lines(binary, horizontal=False)
    return Grid(
        xs=_positions(vertical, axis=0, min_fraction=min_fraction),
        ys=_positions(horizontal, axis=1, min_fraction=min_fraction),
    )


def draw_grid(gray: GrayImage, grid: Grid) -> NDArray[np.uint8]:

    image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    height, width = gray.shape
    for x in grid.xs:
        cv2.line(image, (x, 0), (x, height), (0, 0, 255), 2)
    for y in grid.ys:
        cv2.line(image, (0, y), (width, y), (255, 0, 0), 2)
    return image  # type: ignore[no-any-return]