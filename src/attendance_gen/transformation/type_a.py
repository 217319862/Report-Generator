from datetime import date
from decimal import Decimal

from attendance_gen.domain.models import AttendanceRow, ReportType
from attendance_gen.transformation.base import BaseTransformationStrategy, PlannedShift
from attendance_gen.transformation.pay_bands import split_pay_bands


class TypeAStrategy(BaseTransformationStrategy):
    report_type = ReportType.TYPE_A

    def _build_row(self, day: date, shift: PlannedShift, total: Decimal) -> AttendanceRow:
        bands = split_pay_bands(total, saturday=day.weekday() == 5)
        return AttendanceRow(
            day=day,
            clock_in=shift.clock_in,
            clock_out=shift.clock_out,
            total_hours=total,
            break_duration=shift.break_duration,
            hours_100=bands.hours_100,
            hours_125=bands.hours_125,
            hours_150=bands.hours_150,
            hours_saturday=bands.hours_saturday,
            location=self.rules.location_label,
        )