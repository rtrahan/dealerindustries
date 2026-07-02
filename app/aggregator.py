"""Aggregate advisor and kit data into report model."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import DealershipConfig, normalize_part_number
from app.parsers.advisor import AdvisorMetrics, parse_advisor_report
from app.parsers.opcode import OpCodeParseResult, parse_opcode_report


@dataclass
class AdvisorReportRow:
    advisor_id: int
    name: str
    cp_ro_cnt: float
    act_hr_per_ro: float
    elr: float
    kits: int
    mp_pct: float
    pmp_hours: float
    revenue: float
    kit_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class ReportData:
    store_name: str
    period_label: str
    kit_codes: list[str]
    kit_labels: list[str]
    kit_prices: list[float]
    kit_hours: list[float]
    advisors: list[AdvisorReportRow]
    kit_column_totals: dict[str, int]
    total_kits: int
    total_revenue: float


def _kit_price_map(config: DealershipConfig) -> dict[str, float]:
    return {kit.code: kit.price for kit in config.kits}


def _kit_hours_map(config: DealershipConfig) -> dict[str, float]:
    return {kit.code: kit.hours for kit in config.kits}


def _empty_kit_counts(config: DealershipConfig) -> dict[str, int]:
    return {kit.code: 0 for kit in config.kits}


def _filter_opcode_row(row, config: DealershipConfig) -> bool:
    if config.pay_types and row.pay_type not in config.pay_types:
        return False
    if config.source_codes and row.source_code not in config.source_codes:
        return False
    return True


def build_report(
    advisor_source=None,
    opcode_source=None,
    config: DealershipConfig | None = None,
    period_override: str | None = None,
    store_name_override: str | None = None,
    *,
    advisor_metrics: dict[str, AdvisorMetrics] | None = None,
    opcode_result: OpCodeParseResult | None = None,
) -> ReportData:
    if config is None:
        raise ValueError("Dealership config is required.")
    if advisor_metrics is None:
        if advisor_source is None:
            raise ValueError("Advisor report source or parsed metrics required.")
        advisor_metrics = parse_advisor_report(advisor_source)
    if opcode_result is None:
        if opcode_source is None:
            raise ValueError("OP Code report source or parsed rows required.")
        opcode_result = parse_opcode_report(opcode_source)

    kit_prices = _kit_price_map(config)
    kit_hours = _kit_hours_map(config)
    advisor_kit_counts: dict[str, dict[str, int]] = {}

    for row in opcode_result.rows:
        if not _filter_opcode_row(row, config):
            continue
        part_key = normalize_part_number(row.part_number)
        kit_code = config.part_to_kit.get(part_key)
        if not kit_code:
            continue
        advisor = row.service_advisor.strip()
        if not advisor:
            continue
        counts = advisor_kit_counts.setdefault(advisor, _empty_kit_counts(config))
        counts[kit_code] += row.sale_qty

    # Advisors with at least one kit sale
    kit_advisors = sorted(
        advisor_kit_counts.keys(),
        key=lambda name: (-sum(advisor_kit_counts[name].values()), name),
    )

    advisors: list[AdvisorReportRow] = []
    column_totals = _empty_kit_counts(config)

    for idx, name in enumerate(kit_advisors, start=1):
        counts = advisor_kit_counts[name]
        total_kits = sum(counts.values())
        pmp_hours = sum(counts[code] * kit_hours.get(code, 0) for code in counts)
        revenue = sum(counts[code] * kit_prices.get(code, 0) for code in counts)

        metrics = advisor_metrics.get(name)
        if metrics:
            cp_ro = metrics.ro_count
            act_hr_ro = metrics.hrs_per_ro
            elr = metrics.elr
        else:
            cp_ro = 0.0
            act_hr_ro = 0.0
            elr = 0.0
        mp_pct = (total_kits / cp_ro * 100) if cp_ro else 0.0

        for code, qty in counts.items():
            column_totals[code] += qty

        advisors.append(
            AdvisorReportRow(
                advisor_id=idx,
                name=name,
                cp_ro_cnt=cp_ro,
                act_hr_per_ro=act_hr_ro,
                elr=elr,
                kits=total_kits,
                mp_pct=mp_pct,
                pmp_hours=pmp_hours,
                revenue=revenue,
                kit_counts=counts,
            )
        )

    total_kits = sum(column_totals.values())
    total_revenue = sum(row.revenue for row in advisors)

    if period_override:
        period_label = period_override
    elif opcode_result.period_end:
        period_label = opcode_result.period_end
    else:
        period_label = "—"

    return ReportData(
        store_name=store_name_override or config.store_name,
        period_label=period_label,
        kit_codes=[kit.code for kit in config.kits],
        kit_labels=[kit.label for kit in config.kits],
        kit_prices=[kit.price for kit in config.kits],
        kit_hours=[kit.hours for kit in config.kits],
        advisors=advisors,
        kit_column_totals=column_totals,
        total_kits=total_kits,
        total_revenue=total_revenue,
    )
