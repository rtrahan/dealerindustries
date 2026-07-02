"""End-to-end CDK photo → PDF report pipeline."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.aggregator import ReportData, build_report
from app.config import load_config
from app.parsers.cdk.gemini_vision import process_cdk_photos
from app.pdf_report import generate_pdf


ProgressCallback = Callable[[dict[str, Any]], None]


def _emit(on_progress: ProgressCallback | None, **event: Any) -> None:
    if on_progress:
        on_progress({"type": "progress", **event})


def build_report_from_cdk_photos(
    photos: list[bytes],
    *,
    config_name: str = "classic_kia_carrollton",
    period_override: str | None = None,
    store_name_override: str | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[ReportData, bytes]:
    """Use Gemini vision on CDK printout photos, then generate the standard PDF."""
    recap, opcode_result = process_cdk_photos(photos, on_progress=on_progress)

    _emit(on_progress, phase="build", percent=82, message="Building advisor report…")

    try:
        config = load_config(config_name)
    except FileNotFoundError:
        config = load_config("default")

    store_name = (
        store_name_override
        or recap.store_name
        or opcode_result.site_name
        or config.store_name
    )
    period = period_override or recap.period_end or opcode_result.period_end

    report = build_report(
        advisor_source=None,
        opcode_source=None,
        config=config,
        period_override=period,
        store_name_override=store_name,
        advisor_metrics=recap.advisors,
        opcode_result=opcode_result,
    )

    _emit(on_progress, phase="pdf", percent=92, message="Generating PDF…")
    return report, generate_pdf(report)
