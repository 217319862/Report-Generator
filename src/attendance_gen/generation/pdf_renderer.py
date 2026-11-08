import calendar
from datetime import date
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from attendance_gen.domain.models import AttendanceReport, AttendanceRow
from attendance_gen.generation.base import BaseRenderer
from attendance_gen.generation.fonts import find_font
from attendance_gen.generation.layout import LayoutSpec
from attendance_gen.generation.text import visual

FONT_NAME = "ReportFont"
_MARGIN = 15 * mm
_SUMMARY_VALUE_MM = 25
_TITLE_PERIOD_MM = 38
_TITLE_LABEL_MM = 42
_SHADED = colors.Color(0.85, 0.85, 0.85)


def _display_rows(
    report: AttendanceReport, layout: LayoutSpec
) -> list[tuple[date, AttendanceRow | None]]:
    """השורות להצגה. עם fill_month: כל ימי החודש, ובימים בלי משמרת השורה היא None."""
    if not (layout.fill_month and report.rows):
        return [(row.day, row) for row in report.rows]
    by_day = {row.day: row for row in report.rows}
    first = report.rows[0].day
    last = calendar.monthrange(first.year, first.month)[1]
    days = (date(first.year, first.month, number) for number in range(1, last + 1))
    return [(day, by_day.get(day)) for day in days]


class PdfRenderer(BaseRenderer):
    extension = ".pdf"

    def __init__(
        self,
        font_path: Path | None = None,
        *,
        company: str = "חברה לדוגמה",
        employee: str = "עובד לדוגמה",
        watermark: str | None = "דוגמה",
    ) -> None:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(find_font(font_path))))
        self._company = company
        self._employee = employee
        self._watermark = watermark

    def render(self, report: AttendanceReport, layout: LayoutSpec, destination: Path) -> Path:
        header = self._header(layout)
        story: list[Any] = [*header, Spacer(1, 6 * mm)] if header else []
        summary = self._summary_table(report, layout) if layout.summary else None
        if summary is not None and layout.summary_on_top:
            story += [summary, Spacer(1, 6 * mm)]
        if layout.show_title:
            story += [self._title_bar(report, layout), Spacer(1, 3 * mm)]
        story.append(self._main_table(report, layout))
        if summary is not None and not layout.summary_on_top:
            story += [Spacer(1, 6 * mm), summary]

        doc = SimpleDocTemplate(
            str(destination),
            pagesize=A4,
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=_MARGIN,
            bottomMargin=_MARGIN,
            title="Attendance report (sample)",
            author="attendance-gen",
            invariant=1,
        )
        doc.build(story, onFirstPage=self._stamp, onLaterPages=self._stamp)
        return destination

    def _header(self, layout: LayoutSpec) -> list[Any]:
        style = ParagraphStyle(
            "rtl", fontName=FONT_NAME, fontSize=12, leading=18, alignment=TA_RIGHT
        )
        lines: list[str] = []
        if layout.show_company:
            lines.append(self._company)
        if layout.employee_label is None:
            lines.append(self._employee)
        # escape: טקסט חיצוני לא מתפרש כ-markup של reportlab
        return [Paragraph(escape(visual(line)), style) for line in lines]

    def _title_bar(self, report: AttendanceReport, layout: LayoutSpec) -> Table:
        """פס כותרת מוצל מעל הטבלה: התווית מימין והחודש משמאלה."""
        period = layout.period_text(report)
        if report.is_sample:
            period = f"{period} – דוגמה"
        table = Table(
            [[visual(period), visual(layout.title)]],
            colWidths=[_TITLE_PERIOD_MM * mm, _TITLE_LABEL_MM * mm],
            hAlign="RIGHT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BACKGROUND", (0, 0), (-1, -1), _SHADED),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.8, colors.black),
                ]
            )
        )
        return table

    def _main_table(self, report: AttendanceReport, layout: LayoutSpec) -> Table:
        columns = tuple(reversed(layout.columns))  # עברית: הטור הראשון בצד ימין
        days = _display_rows(report, layout)
        data = [[visual(c.header) for c in columns]]
        for day, row in days:
            data.append([visual(c.value(row) if row else c.blank(day)) for c in columns])
        if any(c.total for c in columns):
            data.append([visual(c.total(report)) if c.total else "" for c in columns])

        commands: list[tuple[Any, ...]] = [
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
        if layout.grid:
            commands.append(("GRID", (0, 0), (-1, -1), 0.5, colors.black))
        else:
            # קווים רק סביב הכותרת, כמו במקור
            commands += [
                ("BOX", (0, 0), (-1, 0), 0.8, colors.black),
                ("INNERGRID", (0, 0), (-1, 0), 0.8, colors.black),
            ]
        for index, (day, _row) in enumerate(days, start=1):
            if day.weekday() in layout.shaded_weekdays:
                commands.append(("BACKGROUND", (0, index), (-1, index), _SHADED))

        table = Table(data, colWidths=[c.width_mm * mm for c in columns], repeatRows=1)
        table.setStyle(TableStyle(commands))
        return table

    def _summary_table(self, report: AttendanceReport, layout: LayoutSpec) -> Table:
        data = [[visual(item.value(report)), visual(item.label)] for item in layout.summary]
        if layout.employee_label is not None:
            data.insert(0, [visual(self._employee), visual(layout.employee_label)])
        widths = [_SUMMARY_VALUE_MM * mm, layout.summary_label_mm * mm]
        table = Table(data, colWidths=widths, hAlign="RIGHT")
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ]
            )
        )
        return table

    def _stamp(self, canvas: Any, doc: Any) -> None:
        """סימן מים 'דוגמה' מאחורי התוכן."""
        if not self._watermark:
            return
        canvas.saveState()
        canvas.setFont(FONT_NAME, 70)
        canvas.setFillColorRGB(0.88, 0.88, 0.88)
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, visual(self._watermark))
        canvas.restoreState()