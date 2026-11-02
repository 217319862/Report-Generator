from decimal import Decimal

from attendance_gen.transformation.pay_bands import split_pay_bands


def test_regular_day() -> None:
    bands = split_pay_bands(Decimal("7.50"), saturday=False)
    assert bands.hours_100 == Decimal("7.50")
    assert bands.hours_125 == bands.hours_150 == 0


def test_overtime_tiers() -> None:
    bands = split_pay_bands(Decimal(11), saturday=False)
    assert (bands.hours_100, bands.hours_125, bands.hours_150) == (
        Decimal(8),
        Decimal(2),
        Decimal(1),
    )


def test_saturday_goes_to_its_own_column() -> None:
    bands = split_pay_bands(Decimal("6.50"), saturday=True)
    assert bands.hours_saturday == Decimal("6.50")
    assert bands.hours_100 == 0