"""Parse Dynatron Service Advisor Recap Report CSV exports (RAP*.csv)."""

from __future__ import annotations

import csv
import re
from io import BytesIO, StringIO
from typing import BinaryIO, Union

from app.parsers.advisor import AdvisorMetrics
from app.parsers.cdk.advisor_recap import AdvisorRecapParseResult

Source = Union[bytes, BinaryIO]


def _decode(source: Source) -> str:
    if isinstance(source, bytes):
        raw = source
    else:
        raw = source.read()
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _parse_float(value: str | None) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if not text or text.startswith("-"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _is_data_row(sa_no: str, sa_name: str) -> bool:
    if not sa_no or not sa_name:
        return False
    if sa_no in {"----", "TOTAL", "GRAND", "RECAP"}:
        return False
    if not re.fullmatch(r"\d{3,5}", sa_no.strip()):
        return False
    return True


def parse_advisor_recap_csv(source: Source) -> AdvisorRecapParseResult:
    """Extract Customer Pay advisor metrics keyed by last name."""
    text = _decode(source)
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Advisor Recap CSV is empty.")

    headers = {name.strip(): name for name in reader.fieldnames if name}
    required = ["SA-No", "SA-Name", "CLS", "# ROs", "HRS-Sold", "HRS/RO", "ELR"]
    for field in required:
        if field not in headers:
            raise ValueError(f"Advisor Recap CSV missing column: {field}")

    advisors: dict[str, AdvisorMetrics] = {}
    advisor_numbers: dict[str, str] = {}

    for row in reader:
        pay_class = row[headers["CLS"]].strip().upper()
        if pay_class != "C":
            continue

        sa_no = row[headers["SA-No"]].strip()
        sa_name = re.sub(r"\s+", " ", row[headers["SA-Name"]].strip()).upper()
        if not _is_data_row(sa_no, sa_name):
            continue

        ro_count = _parse_float(row[headers["# ROs"]])
        bill_hrs = _parse_float(row[headers["HRS-Sold"]])
        hrs_per_ro = _parse_float(row[headers["HRS/RO"]])
        elr = _parse_float(row[headers["ELR"]])

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
        raise ValueError("No Customer Pay advisor rows found in Advisor Recap CSV.")

    return AdvisorRecapParseResult(
        advisors=advisors,
        advisor_numbers=advisor_numbers,
        period_start=None,
        period_end=None,
        store_name=None,
    )


def is_advisor_recap_csv(source: Source) -> bool:
    """Return True when bytes look like a Dynatron Service Advisor Recap CSV."""
    text = _decode(source if isinstance(source, bytes) else BytesIO(source.read()))
    if isinstance(source, BinaryIO):
        source.seek(0)
    first_line = text.splitlines()[0] if text else ""
    return "SA-No" in first_line and "SA-Name" in first_line and "CLS" in first_line
