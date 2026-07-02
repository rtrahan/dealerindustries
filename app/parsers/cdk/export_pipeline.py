"""Dynatron export files → PDF report pipeline."""

from __future__ import annotations

from app.aggregator import ReportData, build_report
from app.config import load_config
from app.parsers.cdk.advisor_recap_csv import parse_advisor_recap_csv
from app.parsers.cdk.opcode_analysis import parse_opcode_analysis_report
from app.pdf_report import generate_pdf


def build_report_from_dynatron_exports(
    opcode_source: bytes,
    recap_source: bytes,
    *,
    config_name: str = "dynatron_bardahl",
    period_override: str | None = None,
    store_name_override: str | None = None,
) -> tuple[ReportData, bytes]:
    """Build the standard advisor PDF from Dynatron Op Code Analysis + Recap exports."""
    recap = parse_advisor_recap_csv(recap_source)
    opcode_result = parse_opcode_analysis_report(opcode_source)

    try:
        config = load_config(config_name)
    except FileNotFoundError:
        config = load_config("dynatron_bardahl")

    store_name = (
        store_name_override
        or opcode_result.site_name
        or recap.store_name
        or config.store_name
    )
    period = period_override or opcode_result.period_end or recap.period_end

    report = build_report(
        advisor_source=None,
        opcode_source=None,
        config=config,
        period_override=period,
        store_name_override=store_name,
        advisor_metrics=recap.advisors,
        opcode_result=opcode_result,
    )
    return report, generate_pdf(report)


# Backward-compatible alias
build_report_from_cdk_exports = build_report_from_dynatron_exports
