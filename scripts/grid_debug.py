import sys
from pathlib import Path

import cv2

from attendance_gen.parsing.grid import draw_grid, find_grid, render_page


def main(pdf: Path, fraction: float) -> None:
    gray = render_page(pdf)
    grid = find_grid(gray, min_fraction=fraction)
    print(f"גודל תמונה: {gray.shape[1]}x{gray.shape[0]}")
    print(f"קווים אנכיים ({len(grid.xs)}): {grid.xs}")
    print(f"קווים אופקיים ({len(grid.ys)}): {grid.ys}")
    print(f"תאים: {grid.rows} שורות x {grid.cols} עמודות")
    out = Path("data/output") / f"{pdf.stem}_grid.png"
    cv2.imwrite(str(out), draw_grid(gray, grid))
    print(f"נשמר: {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else 0.6)