import pytest

from attendance_gen.parsing.grid import Grid
from attendance_gen.parsing.table import TableNotFoundError, body_cell_boxes, find_body_rows

SEPT_XS = (924, 1139, 1352, 1610, 1824, 2035, 2245)
SEPT_YS = (
    396, 453, 510, 567, 622, 678, 734, 788, 845, 900, 1012, 1064, 1120, 1172, 1226, 1278,
    1332, 1387, 1439, 1493, 1547, 1602, 1654, 1707, 1760, 1812, 1867, 1918, 1972, 2026,
    2079, 2134, 2186, 2240, 2292, 2344, 2400, 2453, 2506, 2559, 2613, 2667,
)
JAN_XS = (496, 710, 925, 1163, 1376, 1588, 1799)
JAN_YS = (
    576, 633, 689, 744, 801, 857, 912, 966, 1023, 1079, 1189, 1242, 1295, 1348, 1403, 1457,
    1510, 1563, 1616, 1669, 1722, 1777, 1832, 1884, 1938, 1989, 2043, 2096, 2150, 2204,
    2256, 2309, 2361, 2414, 2468, 2521, 2575, 2629, 2683, 2734, 2788, 2840,
)


@pytest.mark.parametrize(
    ("xs", "ys", "top", "bottom"),
    [(SEPT_XS, SEPT_YS, 1012, 2667), (JAN_XS, JAN_YS, 1189, 2840)],
)
def test_finds_31_body_rows(
    xs: tuple[int, ...], ys: tuple[int, ...], top: int, bottom: int
) -> None:
    rows = find_body_rows(Grid(xs, ys))
    assert len(rows) == 31
    assert rows[0][0] == top
    assert rows[-1][1] == bottom


def test_columns_are_mapped_right_to_left() -> None:
    first = body_cell_boxes(Grid(SEPT_XS, SEPT_YS))[0]
    assert (first["date"][0], first["date"][2]) == (2035, 2245)
    assert (first["notes"][0], first["notes"][2]) == (924, 1139)


def test_wrong_column_count_is_rejected() -> None:
    with pytest.raises(TableNotFoundError):
        body_cell_boxes(Grid((0, 100, 200), SEPT_YS))


def test_page_without_lines_is_rejected() -> None:
    with pytest.raises(TableNotFoundError):
        find_body_rows(Grid((), ()))