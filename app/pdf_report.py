"""Generate finalized advisor performance PDF."""

from __future__ import annotations

import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.aggregator import ReportData
from app.pdf_advisor_pages import build_advisor_page_story, build_section_divider_story
from app.pdf_team_stats import compute_team_benchmarks

# Brand palette
BRAND_RED = colors.HexColor("#D31124")
BRAND_BLACK = colors.HexColor("#111111")
ROW_ALT = colors.HexColor("#F9FAFB")
BORDER = colors.HexColor("#E5E7EB")
TEXT = colors.HexColor("#1F2937")
TEXT_MUTED = colors.HexColor("#6B7280")
WHITE = colors.white
TEAM_BG = colors.HexColor("#FEF2F2")
REF_BG = colors.HexColor("#F3F4F6")
HEADER_BG = BRAND_BLACK

LANDSCAPE_PAGE = landscape(letter)
PORTRAIT_PAGE = letter
LANDSCAPE_MARGIN = 0.45 * inch
PORTRAIT_MARGIN = 0.6 * inch


class PerformanceReportDoc(BaseDocTemplate):
    def __init__(self, buffer, advisor_names: list[str], **kwargs):
        super().__init__(buffer, **kwargs)
        self.advisor_names = advisor_names
        self.page_footer_label = "Team Overview"


class _PageLabel(Flowable):
    """Set the footer label for the current page."""

    def __init__(self, label: str):
        super().__init__()
        self.label = label

    def draw(self) -> None:
        self.canv._doctemplate.page_footer_label = self.label  # type: ignore[attr-defined]


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _pct(value: float) -> str:
    return f"{value:.2f}%"


def _num(value: float, decimals: int = 1) -> str:
    if decimals == 0:
        return str(int(round(value)))
    return f"{value:.{decimals}f}"


def _money_compact(value: float, col_width: float) -> str:
    """Shorter price string when kit columns are narrow."""
    if col_width < 0.46 * inch:
        return f"${value:,.0f}" if value >= 100 else f"${value:.0f}"
    if col_width < 0.54 * inch:
        return f"${value:,.2f}".replace(".00", "")
    return _money(value)


def _kit_qty(value: int) -> str:
    return str(value) if value else "—"


KIT_COL_MIN = 0.42 * inch
KIT_CHUNK_MAX = 16


def _max_kits_per_page(page_width: float) -> int:
    fixed = 0.38 * inch + 0.8 * inch + 0.45 * inch
    available = page_width - fixed
    from_width = int(available / KIT_COL_MIN)
    return max(1, min(from_width, KIT_CHUNK_MAX))


def _kit_chunks(num_kits: int, page_width: float) -> list[tuple[int, int]]:
    """Return (start, end) index slices for kit column groups."""
    if num_kits <= KIT_CHUNK_MAX:
        return [(0, num_kits)]
    per_page = _max_kits_per_page(page_width)
    return [(i, min(i + per_page, num_kits)) for i in range(0, num_kits, per_page)]


def _cell_para(text: str, *, size: int = 7, bold: bool = False, align=TA_CENTER, color=TEXT) -> Paragraph:
    base = getSampleStyleSheet()["Normal"]
    style = ParagraphStyle(
        "cell",
        parent=base,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        textColor=color,
        alignment=align,
        leading=size + 1,
    )
    return Paragraph(text, style)


def _kit_header_cell(label: str, price: float, hours: float, col_width: float) -> Paragraph:
    price_s = _money_compact(price, col_width)
    hour_s = _num(hours, 1)
    meta_size = 5 if col_width < 0.58 * inch else 6
    return _cell_para(
        f"<b>{label}</b><br/>"
        f"<font size='{meta_size}' color='#FFFFFF'>{price_s}</font><br/>"
        f"<font size='{meta_size}' color='#B0B7C3'>{hour_s}h</font>",
        size=meta_size + 1,
        align=TA_CENTER,
        color=WHITE,
    )


def _build_kit_chunk_table(
    report: ReportData,
    start: int,
    end: int,
    page_width: float,
    *,
    chunk_index: int,
    chunk_count: int,
) -> Table:
    codes = report.kit_codes[start:end]
    labels = report.kit_labels[start:end]
    prices = report.kit_prices[start:end]
    hours_list = report.kit_hours[start:end]
    num_kits = len(codes)

    id_width = 0.38 * inch
    advisor_width = 0.8 * inch
    totals_width = 0.45 * inch
    kit_width = (page_width - id_width - advisor_width - totals_width) / num_kits
    kit_col_widths = [id_width, advisor_width] + [kit_width] * num_kits + [totals_width]

    totals_label = "TOTAL" if chunk_index == chunk_count - 1 else "SUB"
    header_cells = [
        _cell_para("ID", size=7, bold=True, color=WHITE),
        _cell_para("ADVISOR", size=7, bold=True, color=WHITE),
    ] + [
        _kit_header_cell(label, price, hour, kit_width)
        for label, price, hour in zip(labels, prices, hours_list)
    ] + [_cell_para(totals_label, size=6, bold=True, color=WHITE)]
    kit_data_rows = [header_cells]
    data_start_row = 1

    data_size = 7 if kit_width < 0.58 * inch else 8
    for row in report.advisors:
        counts = [_kit_qty(row.kit_counts.get(code, 0)) for code in codes]
        if chunk_index == chunk_count - 1:
            row_total = row.kits
        else:
            row_total = sum(row.kit_counts.get(code, 0) for code in codes)
        kit_data_rows.append([
            _cell_para(str(row.advisor_id), size=data_size, align=TA_CENTER),
            _cell_para(row.name, size=data_size, align=TA_LEFT),
        ] + [
            _cell_para(c, size=data_size, align=TA_CENTER) for c in counts
        ] + [
            _cell_para(str(row_total), size=data_size, bold=True, align=TA_CENTER),
        ])

    totals_row_idx = len(kit_data_rows)
    totals_counts = [_kit_qty(report.kit_column_totals.get(code, 0)) for code in codes]
    if chunk_index == chunk_count - 1:
        chunk_kit_total = report.total_kits
    else:
        chunk_kit_total = sum(report.kit_column_totals.get(code, 0) for code in codes)
    kit_data_rows.append([
        "",
        _cell_para("TOTALS", size=data_size, bold=True, align=TA_LEFT),
    ] + [
        _cell_para(c, size=data_size, bold=True, align=TA_CENTER) for c in totals_counts
    ] + [
        _cell_para(str(chunk_kit_total), size=data_size, bold=True, align=TA_CENTER),
    ])

    pad = 5 if kit_width < 0.58 * inch else 7
    row_heights = [40] + [22] * (len(kit_data_rows) - 1)
    kit_style = [
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BRAND_RED),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LEFTPADDING", (1, 1), (1, -1), 6),
        ("FONTNAME", (0, totals_row_idx), (-1, totals_row_idx), "Helvetica-Bold"),
        ("BACKGROUND", (0, totals_row_idx), (-1, totals_row_idx), TEAM_BG),
        ("TEXTCOLOR", (0, totals_row_idx), (-1, totals_row_idx), BRAND_BLACK),
    ]

    for i in range(data_start_row, totals_row_idx):
        if (i - data_start_row) % 2 == 1:
            kit_style.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))

    kit_table = Table(kit_data_rows, colWidths=kit_col_widths, rowHeights=row_heights, repeatRows=data_start_row)
    kit_table.setStyle(TableStyle(kit_style))
    return kit_table


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "store": ParagraphStyle(
            "store",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=BRAND_BLACK,
        ),
        "period": ParagraphStyle(
            "period",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=TEXT_MUTED,
            alignment=TA_RIGHT,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=BRAND_BLACK,
            spaceBefore=12,
            spaceAfter=8,
        ),
    }


def _landscape_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(TEXT_MUTED)
    width, _ = LANDSCAPE_PAGE
    label = getattr(doc, "page_footer_label", "Team Overview")
    canvas.drawString(LANDSCAPE_MARGIN, 0.28 * inch, label)
    canvas.drawRightString(width - LANDSCAPE_MARGIN, 0.28 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _portrait_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(TEXT_MUTED)
    width, _ = PORTRAIT_PAGE
    label = "Individual Advisor Report"
    canvas.drawString(PORTRAIT_MARGIN, 0.28 * inch, label)
    canvas.drawRightString(width - PORTRAIT_MARGIN, 0.28 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _build_overview_story(report: ReportData, page_width: float) -> list:
    sty = _styles()
    story: list = []

    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        logo._restrictSize(2.5 * inch, 0.6 * inch)
    else:
        logo = Paragraph(f"<b>{report.store_name}</b>", sty["store"])

    header_right = Paragraph(
        f"<font size='14' color='#111111'><b>{report.store_name}</b></font><br/>"
        f"<font size='10' color='#6B7280'>Period ending {report.period_label}</font>",
        sty["period"],
    )

    header_table = Table(
        [[logo, header_right]],
        colWidths=[page_width * 0.5, page_width * 0.5],
    )
    header_table.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LINEBELOW", (0, 0), (-1, -1), 2, BRAND_RED),
        ])
    )
    story.append(header_table)
    story.append(Paragraph("SERVICE ADVISOR PERFORMANCE", sty["section"]))

    summary_header = [
        "SERVICE ADVISOR", "CP RO CNT", "ACT HR/RO", "ELR",
        "KITS", "MP %", "PMP HOURS", "REVENUE",
    ]
    summary_rows = [summary_header]
    for row in report.advisors:
        summary_rows.append([
            f"{row.advisor_id} — {row.name}",
            _num(row.cp_ro_cnt, 0),
            _num(row.act_hr_per_ro, 1),
            _num(row.elr, 2),
            _num(row.kits, 0),
            _pct(row.mp_pct),
            _num(row.pmp_hours, 2),
            _money(row.revenue),
        ])

    team_row_idx = None
    if report.advisors:
        team_ro = sum(r.cp_ro_cnt for r in report.advisors)
        team_kits = sum(r.kits for r in report.advisors)
        team_pmp = sum(r.pmp_hours for r in report.advisors)
        team_rev = sum(r.revenue for r in report.advisors)
        team_hr_ro = (
            sum(r.act_hr_per_ro * r.cp_ro_cnt for r in report.advisors) / team_ro if team_ro else 0
        )
        team_elr = sum(r.elr * r.cp_ro_cnt for r in report.advisors) / team_ro if team_ro else 0
        team_mp = sum(r.mp_pct * r.cp_ro_cnt for r in report.advisors) / team_ro if team_ro else 0

        summary_rows.append([
            "TEAM SUMMARY",
            _num(team_ro, 0),
            _num(team_hr_ro, 1),
            _num(team_elr, 2),
            _num(team_kits, 0),
            _pct(team_mp),
            _num(team_pmp, 2),
            _money(team_rev),
        ])
        team_row_idx = len(summary_rows) - 1

    summary_widths = [
        page_width * 0.28, page_width * 0.09, page_width * 0.09, page_width * 0.09,
        page_width * 0.08, page_width * 0.09, page_width * 0.11, page_width * 0.17,
    ]

    summary_style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BRAND_RED),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]

    for i in range(1, len(summary_rows)):
        if i == team_row_idx:
            summary_style.append(("BACKGROUND", (0, i), (-1, i), TEAM_BG))
            summary_style.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))
            summary_style.append(("TEXTCOLOR", (0, i), (-1, i), BRAND_BLACK))
        elif i % 2 == 0:
            summary_style.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))

    summary_table = Table(summary_rows, colWidths=summary_widths, repeatRows=1)
    summary_table.setStyle(TableStyle(summary_style))
    story.append(summary_table)

    story.append(Paragraph("KIT BREAKDOWN BY ADVISOR", sty["section"]))

    chunks = _kit_chunks(len(report.kit_codes), page_width)
    for chunk_idx, (start, end) in enumerate(chunks):
        if chunk_idx > 0:
            story.append(PageBreak())
        if len(chunks) > 1:
            story.append(
                Paragraph(
                    f"<font size='8' color='#6B7280'>Kits {start + 1}–{end} of {len(report.kit_codes)}</font>",
                    ParagraphStyle(
                        "kit_chunk",
                        parent=sty["section"],
                        fontSize=8,
                        textColor=TEXT_MUTED,
                        spaceBefore=0,
                        spaceAfter=6,
                    ),
                )
            )
        story.append(
            _build_kit_chunk_table(
                report,
                start,
                end,
                page_width,
                chunk_index=chunk_idx,
                chunk_count=len(chunks),
            )
        )

    story.append(Spacer(1, 0.2 * inch))

    footer_table = Table(
        [[
            "Total Kits Per Store",
            str(report.total_kits),
            "Total Revenue Generated",
            _money(report.total_revenue),
        ]],
        colWidths=[page_width * 0.25] * 4,
        hAlign="CENTER",
    )
    footer_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), REF_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LINEABOVE", (0, 0), (-1, 0), 2, BRAND_RED),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "RIGHT"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("ALIGN", (3, 0), (3, 0), "LEFT"),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (0, 0), TEXT_MUTED),
            ("TEXTCOLOR", (2, 0), (2, 0), TEXT_MUTED),
            ("TEXTCOLOR", (1, 0), (1, 0), BRAND_BLACK),
            ("TEXTCOLOR", (3, 0), (3, 0), BRAND_BLACK),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (0, 0), 15),
            ("RIGHTPADDING", (2, 0), (2, 0), 15),
            ("LEFTPADDING", (1, 0), (1, 0), 15),
            ("LEFTPADDING", (3, 0), (3, 0), 15),
        ])
    )
    story.append(footer_table)

    story.append(Spacer(1, 0.12 * inch))
    story.append(
        Paragraph(
            "<font size='9' color='#6B7280'><i>Individual advisor portrait pages follow the section divider.</i></font>",
            ParagraphStyle(
                "overview_note",
                parent=_styles()["section"],
                fontName="Helvetica-Oblique",
                fontSize=9,
                textColor=TEXT_MUTED,
                alignment=TA_CENTER,
                spaceBefore=0,
                spaceAfter=0,
            ),
        )
    )
    return story


def generate_pdf(report: ReportData) -> bytes:
    if not report.advisors:
        buffer = BytesIO()
        page_width = LANDSCAPE_PAGE[0] - 2 * LANDSCAPE_MARGIN
        doc = SimpleDocTemplate(
            buffer,
            pagesize=LANDSCAPE_PAGE,
            leftMargin=LANDSCAPE_MARGIN,
            rightMargin=LANDSCAPE_MARGIN,
            topMargin=0.4 * inch,
            bottomMargin=0.4 * inch,
        )
        doc.build(_build_overview_story(report, page_width))
        return buffer.getvalue()

    buffer = BytesIO()
    landscape_width, landscape_height = LANDSCAPE_PAGE
    portrait_width, portrait_height = PORTRAIT_PAGE
    advisor_names = [row.name for row in report.advisors]

    doc = PerformanceReportDoc(
        buffer,
        advisor_names,
        pagesize=LANDSCAPE_PAGE,
        leftMargin=LANDSCAPE_MARGIN,
        rightMargin=LANDSCAPE_MARGIN,
        topMargin=0.4 * inch,
        bottomMargin=0.5 * inch,
    )
    doc.page_footer_label = "Team Overview"

    landscape_frame = Frame(
        LANDSCAPE_MARGIN,
        0.5 * inch,
        landscape_width - 2 * LANDSCAPE_MARGIN,
        landscape_height - 0.9 * inch,
        id="landscape_frame",
    )
    portrait_frame = Frame(
        PORTRAIT_MARGIN,
        0.5 * inch,
        portrait_width - 2 * PORTRAIT_MARGIN,
        portrait_height - 0.9 * inch,
        id="portrait_frame",
    )
    doc.addPageTemplates([
        PageTemplate(
            id="landscape",
            frames=[landscape_frame],
            pagesize=LANDSCAPE_PAGE,
            onPage=_landscape_footer,
        ),
        PageTemplate(
            id="portrait",
            frames=[portrait_frame],
            pagesize=PORTRAIT_PAGE,
            onPage=_portrait_footer,
        ),
    ])

    story = _build_overview_story(report, landscape_width - 2 * LANDSCAPE_MARGIN)
    story.insert(0, _PageLabel("Team Overview · Team summary"))
    team = compute_team_benchmarks(report)
    content_width = portrait_width - 2 * PORTRAIT_MARGIN

    story.append(NextPageTemplate("portrait"))
    story.append(PageBreak())
    story.append(_PageLabel("Individual Advisor Reports · Section start"))
    story.extend(build_section_divider_story(content_width))
    story.append(PageBreak())

    for index, advisor in enumerate(report.advisors):
        story.append(_PageLabel(f"{advisor.name} · Advisor {advisor.advisor_id}"))
        story.extend(build_advisor_page_story(report, advisor, team, content_width))
        if index < len(report.advisors) - 1:
            story.append(PageBreak())

    doc.build(story)
    return buffer.getvalue()
