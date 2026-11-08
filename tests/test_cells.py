import numpy as np

from attendance_gen.parsing.cells import crop_cell, is_shaded


def test_crop_removes_margin() -> None:
    image = np.zeros((100, 100), dtype=np.uint8)
    assert crop_cell(image, (10, 10, 90, 90), margin=5).shape == (70, 70)


def test_shaded_cell_is_detected() -> None:
    assert is_shaded(np.full((20, 20), 150, dtype=np.uint8))
    assert not is_shaded(np.full((20, 20), 250, dtype=np.uint8))


def test_empty_crop_is_not_shaded() -> None:
    tiny = crop_cell(np.zeros((50, 50), dtype=np.uint8), (0, 0, 8, 8))
    assert not is_shaded(tiny)