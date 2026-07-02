"""Parse CDK Service Advisor Recap Report OCR text."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.parsers.advisor import AdvisorMetrics

# 9064 RAILEY C 146 237 212.20 1.45 ... 157.42
_ROW_RE = re.compile(
    r"^(?P<sa_no>\d{4})\s+"
    r"(?P<sa_name>[A-Z][A-Z\s\-']+?)\s+"
    r"(?P<pay_class>[CIW\[\(])\s*"
    r"(?P<ros>\d+)\s+"
    r"(?P<ops>\d+)\s+"
    r"(?P<hrs_sld>[\d.]+)\s+"
    r"(?P<hrs_ro>[\d.]+)\s+"
    r"(?P<rest>.+)$"
)

_PERIOD_RE = re.compile(
    r"FROM\s+(\d{2}/\d{2}/\d{2})\s+THRU\s+(\d{2}/\d{2}/\d{2})",
    re.IGNORECASE,
)
_STORE_RE = re.compile(r"^([A-Z][A-Z0-9\s&\-\.]+OF[A-Z\s]+)$", re.MULTILINE)


@dataclass
class AdvisorRecapParseResult:
    advisors: dict[str, AdvisorMetrics]
    advisor_numbers: dict[str, str]
    period_end: str | None
    period_start: str | None
    store_name: str | None


def _parse_period(text: str) -> tuple[str | None, str | None]:
    match = _PERIOD_RE.search(text)
    if not match:
        return None, None
    start_raw, end_raw = match.groups()
    return _mmddyy(start_raw), _mmddyy(end_raw)


def _mmddyy(value: str) -> str:
    parts = value.strip().split("/")
    if len(parts) != 3:
        return value
    mm, dd, yy = parts
    return f"{mm}-{dd}-20{yy}"


def _parse_store_name(text: str) -> str | None:
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line.strip().upper())
        if any(skip in cleaned for skip in ("RECAP REPORT", "PAGE", "SERVICE ADVISOR", "FROM ", "THRU ")):
            continue
        if "CLASSIC KIA" in cleaned and "CARROLLTON" in cleaned:
            return "Classic Kia of Carrollton"
        if len(cleaned) < 8 or re.search(r"\d{2}/\d{2}", cleaned):
            continue
        if "KIA" in cleaned or cleaned.endswith("OF CARROLLTON"):
            return cleaned.title()
    return None


def _parse_money_token(token: str) -> float:
    token = token.replace("$", "").replace(",", "").strip()
    if not token:
        return 0.0
    try:
        return float(token)
    except ValueError:
        return 0.0


def parse_advisor_recap_text(text: str) -> AdvisorRecapParseResult:
    """Extract Customer Pay advisor metrics keyed by last name."""
    advisors: dict[str, AdvisorMetrics] = {}
    advisor_numbers: dict[str, str] = {}

    for raw_line in text.splitlines():
        line = raw_line.upper().strip()
        if not line or line.startswith("TOTAL"):
            continue
        line = line.replace("WASHINGTO N", "WASHINGTON")
        line = line.replace("WASHINGTO", "WASHINGTON")
        line = re.sub(r"\s+", " ", line)
        match = _ROW_RE.match(line)
        if not match:
            continue
        pay_class = match.group("pay_class").upper()
        if pay_class not in {"C", "["}:
            continue

        sa_no = match.group("sa_no")
        sa_name = re.sub(r"\s+", " ", match.group("sa_name").strip())
        ro_count = float(match.group("ros"))
        bill_hrs = float(match.group("hrs_sld"))
        hrs_per_ro = float(match.group("hrs_ro"))

        rest_tokens = match.group("rest").split()
        elr = _parse_money_token(rest_tokens[-1]) if rest_tokens else 0.0

        advisors[sa_name] = AdvisorMetrics(
            name=sa_name,
            ro_count=ro_count,
            bill_hrs=bill_hrs,
            elr=elr,
            parts_gp_pct=0.0,
            hrs_per_ro=hrs_per_ro if hrs_per_ro else (bill_hrs / ro_count if ro_count else 0.0),
        )
        advisor_numbers[sa_no] = sa_name

    if not advisors:
        raise ValueError("No Customer Pay advisor rows found in Service Advisor Recap.")

    period_start, period_end = _parse_period(text)
    return AdvisorRecapParseResult(
        advisors=advisors,
        advisor_numbers=advisor_numbers,
        period_start=period_start,
        period_end=period_end,
        store_name=_parse_store_name(text),
    )
