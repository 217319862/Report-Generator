from attendance_gen.parsing.type_b_parser import RawRow, build_result


def test_period_is_read_from_date_cells_text() -> None:
    rows = [RawRow(number, "8:00", "11:00", "3.00") for number in range(1, 6)]
    cells_text = "\n".join(f"{day}/1/23" for day in range(1, 6))
    result = build_result(rows, cells_text, "")
    assert (result.year, result.month) == (2023, 1)