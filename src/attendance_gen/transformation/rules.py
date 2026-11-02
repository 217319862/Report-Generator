from dataclasses import dataclass
from datetime import time
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class GenerationRules:
    """הכללים שקובעים מהי וריאציה הגיונית. כולם נתונים, וקל לשנות אותם."""

    work_weekdays: frozenset[int] = frozenset({6, 0, 1, 2, 3})  # ראשון עד חמישי (weekday של Python)
    earliest_start: time = time(6, 0)
    latest_end: time = time(20, 0)
    max_jitter_minutes: int = 30
    jitter_step_minutes: int = 15
    max_break_minutes: int = 60
    max_net_hours: Decimal = Decimal(10)
    max_month_hours: Decimal = Decimal(220)
    days_variation: int = 2
    location_label: str = "אתר לדוגמה"