"""Render a ReportResult to PDF, Excel or CSV."""
import csv
import io
from datetime import datetime

from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HEADER_BG = colors.HexColor("#1f3a5f")


def to_pdf(result) -> bytes:
    buf = io.BytesIO()
    size = landscape(A4) if result.landscape else A4
    doc = SimpleDocTemplate(buf, pagesize=size, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title=result.title)
    styles = getSampleStyleSheet()
    cell = styles["BodyText"].clone("cell", fontSize=8, leading=10)
    head = cell.clone("head", textColor=colors.white, fontName="Helvetica-Bold")
    story = [
        Paragraph(settings.HRMS_ORG_NAME, styles["Heading3"]),
        Paragraph(result.title, styles["Title"]),
    ]
    if result.subtitle:
        story.append(Paragraph(result.subtitle, styles["Italic"]))
    story.append(Spacer(1, 4 * mm))
    data = [[Paragraph(str(c), head) for c in result.columns]]
    data += [[Paragraph(str(v), cell) for v in row] for row in result.rows] or [[Paragraph("No records.", cell)] + [""] * (len(result.columns) - 1)]
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b8c2cc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f8")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(12 * mm, 8 * mm, f"Generated {datetime.now():%d %b %Y %H:%M} - Enterprise HRMS (demo data)")
        canvas.drawRightString(size[0] - 12 * mm, 8 * mm, f"Page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def to_xlsx(result) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = result.title[:31]
    ws.append([settings.HRMS_ORG_NAME])
    ws.append([result.title])
    ws["A1"].font = Font(bold=True)
    ws["A2"].font = Font(bold=True, size=14)
    if result.subtitle:
        ws.append([result.subtitle])
    ws.append([])
    ws.append(result.columns)
    header_row = ws.max_row
    for c in ws[header_row]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3A5F")
        c.alignment = Alignment(vertical="center")
    for row in result.rows:
        ws.append(row)
    for i, col in enumerate(result.columns, 1):
        width = max([len(str(col))] + [len(str(r[i - 1])) for r in result.rows if i - 1 < len(r)])
        ws.column_dimensions[get_column_letter(i)].width = min(width + 2, 45)
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_csv(result) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(result.columns)
    w.writerows(result.rows)
    return buf.getvalue().encode("utf-8-sig")
