from dataclasses import dataclass
from decimal import Decimal

_ZERO = Decimal(0)
_STANDARD_HOURS = Decimal(8)
_TIER_125_HOURS = Decimal(2)


@dataclass(frozen=True, slots=True)
class PayBands:
    hours_100: Decimal = _ZERO
    hours_125: Decimal = _ZERO
    hours_150: Decimal = _ZERO
    hours_saturday: Decimal = _ZERO


def split_pay_bands(total: Decimal, *, saturday: bool) -> PayBands:
    """מפרק שעות יום לפי אחוזי תשלום. ההנחה: 8 שעות רגילות, שעתיים ב-125%, השאר ב-150%."""
    if saturday:
        return PayBands(hours_saturday=total)
    return PayBands(
        hours_100=min(total, _STANDARD_HOURS),
        hours_125=min(max(total - _STANDARD_HOURS, _ZERO), _TIER_125_HOURS),
        hours_150=max(total - _STANDARD_HOURS - _TIER_125_HOURS, _ZERO),
    )