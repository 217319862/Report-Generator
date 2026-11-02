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

from attendance_gen.domain.models import AttendanceReport
from attendance_gen.generation.base import BaseRenderer
from attendance_gen.generation.fonts import find_font
from attendance_gen.generation.layout import LayoutSpec
from attendance_gen.generation.text import visual

FONT_NAME = "ReportFont"
_MARGIN = 15 * mm


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
        story: list[Any] = [*self._header(report, layout), Spacer(1, 6 * mm)]
        story.append(self._main_table(report, layout))
        if layout.summary:
            story += [Spacer(1, 6 * mm), self._summary_table(report, layout)]

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

    def _header(self, report: AttendanceReport, layout: LayoutSpec) -> list[Any]:
        style = ParagraphStyle(
            "rtl", fontName=FONT_NAME, fontSize=12, leading=18, alignment=TA_RIGHT
        )
        lines = [self._company]
        if layout.show_title:
            title = f"{layout.title} {report.period_label}".strip()
            lines.append(f"{title} – דוגמה" if report.is_sample else title)
        lines.append(self._employee)
        # escape: טקסט חיצוני לא מתפרש כ-markup של reportlab
        return [Paragraph(escape(visual(line)), style) for line in lines]

    def _main_table(self, report: AttendanceReport, layout: LayoutSpec) -> Table:
        columns = tuple(reversed(layout.columns))  # עברית: הטור הראשון בצד ימין
        data = [[visual(c.header) for c in columns]]
        data += [[visual(c.value(row)) for c in columns] for row in report.rows]
        if any(c.total for c in columns):
            data.append([visual(c.total(report)) if c.total else "" for c in columns])

        table = Table(data, colWidths=[c.width_mm * mm for c in columns], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    # קווים רק סביב הכותרת, כמו במקור
                    ("BOX", (0, 0), (-1, 0), 0.8, colors.black),
                    ("INNERGRID", (0, 0), (-1, 0), 0.8, colors.black),
                ]
            )
        )
        return table
    def _summary_table(self, report: AttendanceReport, layout: LayoutSpec) -> Table:
        data = [[visual(item.value(report)), visual(item.label)] for item in layout.summary]
        table = Table(data, colWidths=[25 * mm, 35 * mm], hAlign="RIGHT")
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