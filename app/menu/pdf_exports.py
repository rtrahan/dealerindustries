"""PDF exports for Menu Builder deliverables."""

from __future__ import annotations

import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.menu.models import MenuProject

BRAND_BLACK = colors.HexColor("#111111")
BORDER = colors.HexColor("#E5E7EB")
HEADER_BG = colors.HexColor("#F3F4F6")
ROW_ALT = colors.HexColor("#FAFAFA")
TEXT_MUTED = colors.HexColor("#6B7280")


def _money(value: str | float) -> str:
    if isinstance(value, (int, float)):
        return f"${value:,.2f}"
    return str(value or "")


def _num(value: float) -> str:
    return f"{value:g}"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=BRAND_BLACK,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT_MUTED,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=BRAND_BLACK,
            alignment=TA_LEFT,
        ),
        "right": ParagraphStyle(
            "right",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=BRAND_BLACK,
            alignment=TA_RIGHT,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=BRAND_BLACK,
        ),
    }


def _header(project: MenuProject, subtitle: str, width: float) -> Table:
    styles = _styles()
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "logo.png")
    logo = Image(logo_path, width=1.25 * inch, height=0.42 * inch) if os.path.exists(logo_path) else ""
    title = [
        Paragraph(project.name, styles["title"]),
        Paragraph(subtitle, styles["subtitle"]),
    ]
    table = Table([[logo, title]], colWidths=[1.45 * inch, width - 1.45 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return table


def _doc() -> tuple[SimpleDocTemplate, BytesIO, float]:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.35 * inch,
    )
    width = landscape(letter)[0] - doc.leftMargin - doc.rightMargin
    return doc, buffer, width


def generate_advisor_ops_pdf(project: MenuProject) -> bytes:
    doc, buffer, width = _doc()
    styles = _styles()
    story = [_header(project, "Advisor Ops Cheat Sheet", width), Spacer(1, 0.08 * inch)]

    data: list[list] = [["OP Code", "Description", "Parts", "Time", "Labor", "Total"]]
    last_section = None
    section_rows: list[int] = []
    for package in project.advisor_packages:
        if package.section != last_section:
            section_rows.append(len(data))
            data.append([Paragraph(package.section, styles["section"]), "", "", "", "", ""])
            last_section = package.section
        data.append(
            [
                Paragraph(package.op_code, styles["cell"]),
                Paragraph(package.description, styles["cell"]),
                Paragraph(_money(package.parts), styles["right"]),
                Paragraph(_num(package.time), styles["right"]),
                Paragraph(_money(package.labor), styles["right"]),
                Paragraph(_money(package.total), styles["right"]),
            ]
        )

    table = Table(
        data,
        colWidths=[0.8 * inch, width - 4.3 * inch, 0.85 * inch, 0.6 * inch, 0.85 * inch, 0.85 * inch],
        repeatRows=1,
    )
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_BLACK),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]
    for row in section_rows:
        commands.extend(
            [
                ("SPAN", (0, row), (-1, row)),
                ("BACKGROUND", (0, row), (-1, row), ROW_ALT),
                ("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"),
            ]
        )
    table.setStyle(TableStyle(commands))
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def generate_parts_pull_pdf(project: MenuProject) -> bytes:
    doc, buffer, width = _doc()
    styles = _styles()
    story = [_header(project, "Parts Pull Cheat Sheet", width), Spacer(1, 0.08 * inch)]

    data: list[list] = [["OP Code / Part #", "Description", "Parts Sale"]]
    package_rows: list[int] = []
    for row in project.parts_pull:
        is_package_row = row.op_code_or_part == row.section and not row.parts_sale
        if is_package_row:
            package_rows.append(len(data))
        data.append(
            [
                Paragraph(row.op_code_or_part, styles["cell"]),
                Paragraph(row.description, styles["section"] if is_package_row else styles["cell"]),
                Paragraph("" if is_package_row else _money(row.parts_sale), styles["right"]),
            ]
        )

    table = Table(data, colWidths=[1.5 * inch, width - 2.8 * inch, 1.3 * inch], repeatRows=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 1), (0, -1), "RIGHT"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    ]
    for row_idx in package_rows:
        commands.extend(
            [
                ("BACKGROUND", (0, row_idx), (-1, row_idx), ROW_ALT),
                ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold"),
                ("ALIGN", (0, row_idx), (0, row_idx), "LEFT"),
            ]
        )
    table.setStyle(TableStyle(commands))
    story.append(table)
    doc.build(story)
    return buffer.getvalue()
