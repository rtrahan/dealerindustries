"""Team-level aggregates for advisor comparison pages."""

from __future__ import annotations

from dataclasses import dataclass

from app.aggregator import AdvisorReportRow, ReportData


@dataclass(frozen=True)
class TeamBenchmarks:
    advisor_count: int
    cp_ro_cnt: float
    act_hr_per_ro: float
    elr: float
    kits: float
    mp_pct: float
    pmp_hours: float
    revenue: float
    kit_avg_per_advisor: dict[str, float]


def compute_team_benchmarks(report: ReportData) -> TeamBenchmarks:
    advisors = report.advisors
    count = len(advisors)
    if not count:
        return TeamBenchmarks(
            advisor_count=0,
            cp_ro_cnt=0.0,
            act_hr_per_ro=0.0,
            elr=0.0,
            kits=0.0,
            mp_pct=0.0,
            pmp_hours=0.0,
            revenue=0.0,
            kit_avg_per_advisor={code: 0.0 for code in report.kit_codes},
        )

    team_ro = sum(r.cp_ro_cnt for r in advisors)
    kit_avg = {
        code: report.kit_column_totals.get(code, 0) / count for code in report.kit_codes
    }

    return TeamBenchmarks(
        advisor_count=count,
        cp_ro_cnt=team_ro / count,
        act_hr_per_ro=(
            sum(r.act_hr_per_ro * r.cp_ro_cnt for r in advisors) / team_ro if team_ro else 0.0
        ),
        elr=sum(r.elr * r.cp_ro_cnt for r in advisors) / team_ro if team_ro else 0.0,
        kits=sum(r.kits for r in advisors) / count,
        mp_pct=sum(r.mp_pct * r.cp_ro_cnt for r in advisors) / team_ro if team_ro else 0.0,
        pmp_hours=sum(r.pmp_hours for r in advisors) / count,
        revenue=sum(r.revenue for r in advisors) / count,
        kit_avg_per_advisor=kit_avg,
    )


def kits_rank(advisors: list[AdvisorReportRow], advisor: AdvisorReportRow) -> int:
    ordered = sorted(advisors, key=lambda r: (-r.kits, -r.revenue, r.name))
    for idx, row in enumerate(ordered, start=1):
        if row.name == advisor.name:
            return idx
    return len(advisors)


def revenue_rank(advisors: list[AdvisorReportRow], advisor: AdvisorReportRow) -> int:
    ordered = sorted(advisors, key=lambda r: (-r.revenue, -r.kits, r.name))
    for idx, row in enumerate(ordered, start=1):
        if row.name == advisor.name:
            return idx
    return len(advisors)
