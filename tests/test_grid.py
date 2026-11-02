import cv2
import numpy as np

from attendance_gen.parsing.grid import GrayImage, find_grid

XS = (20, 120, 220, 320)
YS = (20, 70, 120, 170, 220)


def synthetic_table() -> GrayImage:
    image = np.full((260, 360), 255, dtype=np.uint8)
    for x in XS:
        cv2.line(image, (x, YS[0]), (x, YS[-1]), 0, 3)
    for y in YS:
        cv2.line(image, (XS[0], y), (XS[-1], y), 0, 3)
    return image


def test_finds_all_lines() -> None:
    grid = find_grid(synthetic_table())
    assert len(grid.xs) == len(XS)
    assert len(grid.ys) == len(YS)
    assert all(abs(found - real) <= 3 for found, real in zip(grid.xs, XS, strict=True))
    assert all(abs(found - real) <= 3 for found, real in zip(grid.ys, YS, strict=True))
    assert (grid.rows, grid.cols) == (4, 3)


def test_blank_page_has_no_grid() -> None:
    grid = find_grid(np.full((200, 200), 255, dtype=np.uint8))
    assert (grid.rows, grid.cols) == (0, 0)