"""Portrait per-advisor performance pages — dashboard layout."""

from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, Image, Paragraph, Spacer, Table, TableStyle

from app.aggregator import AdvisorReportRow, ReportData
from app.pdf_team_stats import TeamBenchmarks, kits_rank, revenue_rank

BRAND_RED = colors.HexColor("#D31124")
BRAND_BLACK = colors.HexColor("#111111")
TEXT = colors.HexColor("#1F2937")
TEXT_MUTED = colors.HexColor("#6B7280")
WHITE = colors.white
CANVAS = colors.HexColor("#FAFAFA")
TILE_BG = colors.HexColor("#F8F9FB")
GOOD = colors.HexColor("#059669")
GOOD_BG = colors.HexColor("#D1FAE5")
BAD = colors.HexColor("#DC2626")
BAD_BG = colors.HexColor("#FEE2E2")
NEUTRAL_BG = colors.HexColor("#E5E7EB")
HEADER_BG = colors.HexColor("#0D0D0D")
BAR_TRACK = colors.HexColor("#E6EBF1")
TEAM_BAR = colors.HexColor("#A7AFBA")
CHIP_BG = colors.HexColor("#262626")
DIVIDER = colors.HexColor("#ECEEF2")
PROFILE_KIT_LIMIT = 10


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _pct(value: float) -> str:
    return f"{value:.1f}%"


def _num(value: float, decimals: int = 1) -> str:
    if decimals == 0:
        return str(int(round(value)))
    return f"{value:.{decimals}f}"


def _advisor_name_size(name: str) -> int:
    if len(name) > 24:
        return 18
    if len(name) > 18:
        return 21
    return 25


def _mp_score(advisor: AdvisorReportRow) -> float:
    return (advisor.kits / advisor.cp_ro_cnt * 100) if advisor.cp_ro_cnt else 0.0


def _mp_rating(score: float) -> tuple[str, str, colors.Color, colors.Color]:
    if score >= 70:
        return "Stellar", "70%+ penetration", GOOD, GOOD_BG
    if score >= 60:
        return "Great", "60%+ target", GOOD, GOOD_BG
    if score >= 30:
        return "Good", "30%+ target", colors.HexColor("#047857"), colors.HexColor("#ECFDF5")
    return "Coaching", "Below 30% target", BAD, BAD_BG


def _mp_rank(advisors: list[AdvisorReportRow], advisor: AdvisorReportRow) -> int:
    ordered = sorted(advisors, key=lambda r: (-_mp_score(r), -r.kits, -r.revenue, r.name))
    for idx, row in enumerate(ordered, start=1):
        if row.name == advisor.name:
            return idx
    return len(advisors)


def _delta_parts(
    advisor: float,
    team: float,
    *,
    higher_is_better: bool = True,
) -> tuple[str, colors.Color, colors.Color]:
    if team == 0:
        if advisor == 0:
            return "On par", TEXT_MUTED, NEUTRAL_BG
        positive = higher_is_better
    else:
        pct = ((advisor - team) / abs(team)) * 100
        if abs(pct) < 1.5:
            return "On par", TEXT_MUTED, NEUTRAL_BG
        above = advisor > team
        positive = above if higher_is_better else not above
        if higher_is_better:
            label = f"{'+' if above else '-'}{abs(pct):.0f}%"
        else:
            label = f"{abs(pct):.0f}% {'high' if above else 'low'}"
        text = GOOD if positive else BAD
        bg = GOOD_BG if positive else BAD_BG
        return label, text, bg

    label = "Above team" if positive else "Below team"
    text = GOOD if positive else BAD
    bg = GOOD_BG if positive else BAD_BG
    return label, text, bg


def _para(
    text: str,
    *,
    align=TA_LEFT,
    size: int = 9,
    color=TEXT,
    bold: bool = False,
    leading: int | None = None,
) -> Paragraph:
    base = getSampleStyleSheet()["Normal"]
    style = ParagraphStyle(
        "p",
        parent=base,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        textColor=color,
        alignment=align,
        leading=leading or size + 3,
    )
    return Paragraph(text, style)


class _ValueBar(Flowable):
    """Single horizontal value bar scaled to a shared max."""

    def __init__(
        self,
        value: float,
        max_value: float,
        width: float,
        *,
        fill=BRAND_RED,
        height: float = 7,
    ):
        self.value = value
        self.max_value = max(max_value, 0.001)
        self.width = width
        self.fill = fill
        self.height = height

    def wrap(self, avail_width, avail_height):
        return self.width, self.height

    def draw(self):
        c = self.canv
        y = 0
        h = self.height
        c.setFillColor(BAR_TRACK)
        c.roundRect(0, y, self.width, h, 4, fill=1, stroke=0)
        fill_w = max(3, self.width * (self.value / self.max_value)) if self.value > 0 else 0
        if fill_w:
            c.setFillColor(self.fill)
            c.roundRect(0, y, fill_w, h, 4, fill=1, stroke=0)


def _comparison_bars(advisor: float, team: float, width: float) -> Table:
    peak = max(advisor, team, 0.001)
    label_w = 0.30 * inch
    bar_w = width - label_w
    chart = Table(
        [
            [
                _para("Rep", size=5, color=BRAND_RED, bold=True),
                _ValueBar(advisor, peak, bar_w, fill=BRAND_RED, height=5),
            ],
            [
                _para("Avg", size=5, color=TEXT_MUTED, bold=True),
                _ValueBar(team, peak, bar_w, fill=TEAM_BAR, height=5),
            ],
        ],
        colWidths=[label_w, bar_w],
        rowHeights=[8, 8],
    )
    chart.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return chart


def _chip(text: str, *, fg=WHITE, bg=CHIP_BG, width: float | None = None) -> Table:
    w = width or 0.9 * inch
    chip = Table(
        [[_para(text, align=TA_CENTER, size=7, color=fg, bold=True)]],
        colWidths=[w],
        rowHeights=[22],
    )
    chip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("ROUNDEDCORNERS", [11, 11, 11, 11]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return chip


def _label_pill(text: str, *, width: float = 1.28 * inch) -> Table:
    pill = Table(
        [[_para(text, align=TA_CENTER, size=7, color=WHITE, bold=True)]],
        colWidths=[width],
        rowHeights=[17],
    )
    pill.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_RED),
        ("ROUNDEDCORNERS", [9, 9, 9, 9]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return pill


def _delta_chip(advisor: float, team: float, *, higher_is_better: bool = True) -> Table:
    label, text_color, bg = _delta_parts(advisor, team, higher_is_better=higher_is_better)
    return _chip(label, fg=text_color, bg=bg, width=0.74 * inch)


def _kpi_cell(
    label: str,
    value: str,
    advisor: float,
    team: float,
    *,
    higher_is_better: bool = True,
) -> Table:
    delta, text_color, bg = _delta_parts(advisor, team, higher_is_better=higher_is_better)
    value_size = 15 if len(value) > 7 else 21
    return Table(
        [
            [_para(label.upper(), align=TA_CENTER, size=7, color=TEXT_MUTED, bold=True)],
            [_para(f"<font size='{value_size}'><b>{value}</b></font>", align=TA_CENTER, size=value_size, bold=True, leading=value_size + 2)],
            [_para(
                f"<font color='#{text_color.hexval()[2:]}'><b>{delta}</b></font>",
                align=TA_CENTER,
                size=8,
                bold=True,
            )],
        ],
        style=TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )


def _kpi_strip(
    kits_val: str,
    kits_a: float,
    kits_t: float,
    rev_val: str,
    rev_a: float,
    rev_t: float,
    ro_val: str,
    ro_a: float,
    ro_t: float,
    width: float,
) -> Table:
    col = width / 3
    strip = Table(
        [[
            _kpi_cell("Total Kits", kits_val, kits_a, kits_t),
            _kpi_cell("Revenue", rev_val, rev_a, rev_t),
            _kpi_cell("CP RO Count", ro_val, ro_a, ro_t, higher_is_better=True),
        ]],
        colWidths=[col, col, col],
        rowHeights=[68],
    )
    strip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("ROUNDEDCORNERS", [10, 10, 10, 10]),
        ("LINEAFTER", (0, 0), (0, 0), 1, DIVIDER),
        ("LINEAFTER", (1, 0), (1, 0), 1, DIVIDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return strip


def _report_card_cell(title: str, value: str, detail: str, *, accent=TEXT, bg=WHITE) -> Table:
    cell = Table(
        [
            [_para(title.upper(), align=TA_CENTER, size=6, color=TEXT_MUTED, bold=True)],
            [_para(f"<font color='#{accent.hexval()[2:]}'><b>{value}</b></font>", align=TA_CENTER, size=15, bold=True, leading=18)],
            [_para(detail, align=TA_CENTER, size=6, color=TEXT_MUTED)],
        ],
        colWidths=[1.58 * inch],
        rowHeights=[10, 20, 10],
    )
    cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return cell


def _mp_report_card(report: ReportData, advisor: AdvisorReportRow, width: float) -> Table:
    score = _mp_score(advisor)
    rating, rating_detail, rating_color, rating_bg = _mp_rating(score)
    rank = _mp_rank(report.advisors, advisor)
    card = Table(
        [[
            _report_card_cell("MP Score", _pct(score), f"{advisor.kits} kits / {_num(advisor.cp_ro_cnt, 0)} CP ROs", accent=BRAND_BLACK),
            _report_card_cell("Rating", rating, rating_detail, accent=rating_color, bg=rating_bg),
            _report_card_cell("Team Rank", f"#{rank}", f"of {len(report.advisors)} advisors", accent=BRAND_RED),
        ]],
        colWidths=[width / 3] * 3,
        rowHeights=[52],
    )
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("ROUNDEDCORNERS", [10, 10, 10, 10]),
        ("BOX", (0, 0), (-1, -1), 0.5, DIVIDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return card


def _metric_tile(
    label: str,
    display_adv: str,
    display_team: str,
    advisor: float,
    team: float,
    *,
    higher_is_better: bool,
    width: float,
) -> Table:
    delta, text_color, bg = _delta_parts(advisor, team, higher_is_better=higher_is_better)
    bar_w = width - 28
    return Table(
        [
            [
                Table(
                    [[
                        _para(label, size=8, color=TEXT_MUTED, bold=True),
                        _delta_chip(advisor, team, higher_is_better=higher_is_better),
                    ]],
                    colWidths=[width - 82, 78],
                )
            ],
            [_para(f"<font size='18'><b>{display_adv}</b></font>", size=18, bold=True, leading=22)],
            [_para(f"Team avg {display_team}", size=7, color=TEXT_MUTED)],
            [_comparison_bars(advisor, team, bar_w)],
        ],
        colWidths=[width],
        rowHeights=[28, 27, 13, 25],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), TILE_BG),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (0, 0), 11),
            ("TOPPADDING", (0, 1), (-1, 1), 4),
            ("TOPPADDING", (0, 2), (-1, 2), 0),
            ("TOPPADDING", (0, 3), (-1, 3), 4),
            ("BOTTOMPADDING", (0, 3), (-1, 3), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]),
    )


def _section_heading(title: str, subtitle: str) -> list:
    return [
        _para(title, size=13, bold=True, color=BRAND_BLACK),
        Spacer(1, 2),
        _para(subtitle, size=8, color=TEXT_MUTED),
        Spacer(1, 6),
    ]


def _kit_leaderboard_row(
    label: str,
    count: int,
    team_avg: float,
    *,
    width: float,
) -> Table:
    bar_w = width - 1.92 * inch
    delta_chip = _delta_chip(float(count), team_avg, higher_is_better=True)
    row = Table(
        [[
            _chip(label, fg=BRAND_RED, bg=colors.HexColor("#FEF2F2"), width=0.50 * inch),
            _comparison_bars(float(count), team_avg, bar_w),
            _para(
                f"<font size='13'><b>{count}</b></font><br/>"
                f"<font size='6' color='#6B7280'>avg {_num(team_avg, 1)}</font>",
                align=TA_RIGHT,
                size=13,
                bold=True,
                leading=10,
            ),
            delta_chip,
        ]],
        colWidths=[0.56 * inch, bar_w + 6, 0.48 * inch, 0.76 * inch],
        rowHeights=[28],
    )
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return row


def _kit_sales_grid(sold_kits: list[tuple[str, int, float]], page_width: float) -> list:
    shown = sold_kits[:PROFILE_KIT_LIMIT]
    gap = 8
    col_w = (page_width - gap) / 2
    story: list = []

    for idx in range(0, len(shown), 2):
        left = _kit_leaderboard_row(shown[idx][0], shown[idx][1], shown[idx][2], width=col_w)
        if idx + 1 < len(shown):
            right = _kit_leaderboard_row(shown[idx + 1][0], shown[idx + 1][1], shown[idx + 1][2], width=col_w)
        else:
            right = Spacer(col_w, 1)

        row = Table([[left, right]], colWidths=[col_w, col_w])
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (1, 0), (1, 0), gap),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(row)

    return story


def build_section_divider_story(page_width: float) -> list:
    base = getSampleStyleSheet()
    return [
        Spacer(1, 1.9 * inch),
        Table(
            [[_para("<font size='28'><b>Advisor Profiles</b></font>", align=TA_CENTER, size=28, bold=True, color=BRAND_BLACK)]],
            colWidths=[page_width],
            style=TableStyle([
                ("LINEBELOW", (0, 0), (-1, -1), 4, BRAND_RED),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]),
        ),
        Spacer(1, 0.2 * inch),
        Paragraph(
            "<font size='10' color='#6B7280'>Individual performance dashboards — one page per advisor.</font>",
            ParagraphStyle("div_sub", parent=base["Normal"], alignment=TA_CENTER, leading=14),
        ),
    ]


def build_advisor_page_story(
    report: ReportData,
    advisor: AdvisorReportRow,
    team: TeamBenchmarks,
    page_width: float,
) -> list:
    story: list = []

    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        logo._restrictSize(1.35 * inch, 0.34 * inch)
    else:
        logo = _para("<b>Dealer Industries</b>", bold=True)

    header = Table(
        [[
            logo,
            _para(
                f"<b>{report.store_name}</b><br/><font color='#9CA3AF'>Period ending {report.period_label}</font>",
                align=TA_RIGHT,
                size=10,
                leading=13,
            ),
        ]],
        colWidths=[page_width * 0.55, page_width * 0.45],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.1 * inch))

    k_rank = kits_rank(report.advisors, advisor)
    r_rank = revenue_rank(report.advisors, advisor)
    chip_gap = 5
    chip_w = 0.88 * inch

    hero = Table(
        [[
            Table(
                [
                    [_label_pill("SERVICE ADVISOR")],
                    [
                        _para(
                            f"<font size='{_advisor_name_size(advisor.name)}'><b>{advisor.name}</b></font>",
                            color=WHITE,
                            size=_advisor_name_size(advisor.name),
                            leading=_advisor_name_size(advisor.name) + 5,
                            bold=True,
                        )
                    ],
                    [
                        _para(
                            f"Advisor {advisor.advisor_id}",
                            color=colors.HexColor("#B7BDC7"),
                            size=9,
                            leading=12,
                        )
                    ],
                ],
                colWidths=[page_width * 0.50],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (0, 0), 9),
                    ("BOTTOMPADDING", (0, 1), (0, 1), 4),
                ]),
            ),
            Table(
                [[
                    _chip(f"#{k_rank} Kits", width=chip_w),
                    _chip(f"#{r_rank} Revenue", width=chip_w),
                    _chip(f"{team.advisor_count} Advisors", width=chip_w),
                ]],
                colWidths=[chip_w, chip_w, chip_w],
                style=TableStyle([
                    ("LEFTPADDING", (1, 0), (1, 0), chip_gap),
                    ("LEFTPADDING", (2, 0), (2, 0), chip_gap),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]),
            ),
        ]],
        colWidths=[page_width * 0.56, page_width * 0.44],
    )
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG),
        ("LEFTPADDING", (0, 0), (0, -1), 20),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LINEBELOW", (0, 0), (-1, -1), 2, BRAND_RED),
        ("ROUNDEDCORNERS", [12, 12, 12, 12]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(hero)
    story.append(Spacer(1, 0.10 * inch))

    story.append(_kpi_strip(
        _num(advisor.kits, 0), advisor.kits, team.kits,
        _money(advisor.revenue), advisor.revenue, team.revenue,
        _num(advisor.cp_ro_cnt, 0), advisor.cp_ro_cnt, team.cp_ro_cnt,
        page_width,
    ))
    story.append(Spacer(1, 0.08 * inch))

    story.append(_mp_report_card(report, advisor, page_width))
    story.append(Spacer(1, 0.10 * inch))

    story.extend(_section_heading("Efficiency", "Rep bar in red; team average in gray"))

    tile_gap = 8
    tile_w = (page_width - tile_gap) / 2
    perf_metrics = [
        ("Act HR / RO", advisor.act_hr_per_ro, team.act_hr_per_ro, _num(advisor.act_hr_per_ro, 1), _num(team.act_hr_per_ro, 1), False),
        ("ELR", advisor.elr, team.elr, _num(advisor.elr, 2), _num(team.elr, 2), True),
        ("MP %", _mp_score(advisor), team.mp_pct, _pct(_mp_score(advisor)), _pct(team.mp_pct), True),
        ("PMP Hours", advisor.pmp_hours, team.pmp_hours, _num(advisor.pmp_hours, 2), _num(team.pmp_hours, 2), True),
    ]
    for i in range(0, len(perf_metrics), 2):
        left = perf_metrics[i]
        right = perf_metrics[i + 1] if i + 1 < len(perf_metrics) else None
        row_cells = [
            _metric_tile(left[0], left[3], left[4], left[1], left[2], higher_is_better=left[5], width=tile_w),
        ]
        if right:
            row_cells.append(
                _metric_tile(right[0], right[3], right[4], right[1], right[2], higher_is_better=right[5], width=tile_w)
            )
        else:
            row_cells.append(Spacer(tile_w, 1))
        grid = Table([row_cells], colWidths=[tile_w, tile_w])
        grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (1, 0), (1, 0), tile_gap),
        ]))
        story.append(grid)
        if i + 2 < len(perf_metrics):
            story.append(Spacer(1, 7))

    sold_kits = sorted(
        (
            (label, advisor.kit_counts.get(code, 0), team.kit_avg_per_advisor.get(code, 0))
            for code, label in zip(report.kit_codes, report.kit_labels)
            if advisor.kit_counts.get(code, 0) > 0
        ),
        key=lambda x: x[1],
        reverse=True,
    )

    if sold_kits:
        story.append(Spacer(1, 0.10 * inch))
        kit_subtitle = "Sold count with rep vs. team average"
        if len(sold_kits) > PROFILE_KIT_LIMIT:
            kit_subtitle = f"Top {PROFILE_KIT_LIMIT} kit types shown; {len(sold_kits) - PROFILE_KIT_LIMIT} more sold"
        story.extend(_section_heading("Kit Sales", kit_subtitle))

        story.extend(_kit_sales_grid(sold_kits, page_width))

    return story
