from collections.abc import Mapping
from statistics import median

from attendance_gen.parsing.grid import Grid

Box = tuple[int, int, int, int]  # (x0, y0, x1, y1)

# משמאל לימין, כפי שהעמודות מופיעות בתמונה (העברית נקראת מימין)
TYPE_B_COLUMNS = ("notes", "total", "exit", "entry", "weekday", "date")

_HEIGHT_TOLERANCE = 0.3
_MIN_ROWS = 5


class TableNotFoundError(ValueError):
    """לא נמצאה טבלת נתונים במבנה הצפוי."""


def find_body_rows(grid: Grid) -> tuple[tuple[int, int], ...]:
    """(y0, y1) לכל שורת נתונים: הרצף הארוך ביותר של שורות בגובה דומה."""
    heights = [bottom - top for top, bottom in zip(grid.ys, grid.ys[1:], strict=False)]
    if not heights:
        raise TableNotFoundError("לא זוהו שורות בדף")
    typical = median(heights)

    runs: list[tuple[int, int]] = []  # (אינדקס התחלה, אורך)
    start: int | None = None
    for index, height in enumerate(heights):
        similar = abs(height - typical) <= typical * _HEIGHT_TOLERANCE
        if similar and start is None:
            start = index
        elif not similar and start is not None:
            runs.append((start, index - start))
            start = None
    if start is not None:
        runs.append((start, len(heights) - start))

    if not runs:
        raise TableNotFoundError("לא נמצאו שורות בגובה אחיד")
    first, length = max(runs, key=lambda run: run[1])
    if length < _MIN_ROWS:
        raise TableNotFoundError(f"נמצאו רק {length} שורות בגובה אחיד")
    return tuple((grid.ys[i], grid.ys[i + 1]) for i in range(first, first + length))


def body_cell_boxes(
    grid: Grid, columns: tuple[str, ...] = TYPE_B_COLUMNS
) -> tuple[Mapping[str, Box], ...]:
    """לכל שורת נתונים: מיפוי משם עמודה לתיבת התא שלה."""
    if grid.cols != len(columns):
        raise TableNotFoundError(f"צפויות {len(columns)} עמודות, נמצאו {grid.cols}")
    return tuple(
        {
            name: (grid.xs[col], top, grid.xs[col + 1], bottom)
            for col, name in enumerate(columns)
        }
        for top, bottom in find_body_rows(grid)
    )