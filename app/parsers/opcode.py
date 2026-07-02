"""Parse Tekion OP Code History Report (csv)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO, StringIO
from typing import BinaryIO, Union

Source = Union[bytes, BinaryIO]


def _as_binary(source: Source) -> BinaryIO:
    if isinstance(source, bytes):
        return BytesIO(source)
    return source


@dataclass
class OpCodeRow:
    part_number: str
    sale_qty: int
    service_advisor: str
    pay_type: str
    source_code: str


@dataclass
class OpCodeParseResult:
    rows: list[OpCodeRow]
    period_end: str | None
    period_start: str | None
    site_name: str | None


def _decode(source: Source) -> str:
    stream = _as_binary(source)
    raw = stream.read()
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _parse_filter_dates(text: str) -> tuple[str | None, str | None]:
    """Extract date range from Tekion filter preamble."""
    start, end = None, None
    for line in text.splitlines()[:10]:
        if "Date Modified" in line or "BETWEEN" in line:
            match = re.search(
                r"([A-Za-z]{3}\s+\d{1,2}\s+\d{4})\s*;\s*([A-Za-z]{3}\s+\d{1,2}\s+\d{4})",
                line,
            )
            if match:
                start = _format_tekion_date(match.group(1))
                end = _format_tekion_date(match.group(2))
                break
    return start, end


def _format_tekion_date(value: str) -> str:
    try:
        dt = datetime.strptime(value.strip(), "%b %d %Y")
        return dt.strftime("%m-%d-%Y")
    except ValueError:
        return value.strip()


def parse_opcode_report(source: Source) -> OpCodeParseResult:
    text = _decode(source)
    period_start, period_end = _parse_filter_dates(text)

    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Part Number"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("OP Code CSV missing 'Part Number' header row.")

    reader = csv.reader(StringIO("\n".join(lines[header_idx:])))
    headers = [h.strip() for h in next(reader)]
    col = {name.strip(): i for i, name in enumerate(headers)}

    required = ["Part Number", "Sale Qty", "Service Advisor", "Pay Type", "Source Code", "Site Name"]
    for field in required:
        if field not in col:
            raise ValueError(f"OP Code CSV missing column: {field}")

    rows: list[OpCodeRow] = []
    site_name = None
    for row in reader:
        if not row or not row[col["Part Number"]].strip():
            continue
        part = row[col["Part Number"]].strip()
        if part.lower().startswith("total"):
            continue
        
        # Some Tekion exports use weird internal IDs for Site Name like "-1_6197"
        # We want to skip those and look for a real name, or fallback to it if it's all we have
        row_site = row[col["Site Name"]].strip()
        if row_site:
            if not site_name or (site_name.startswith("-1_") and not row_site.startswith("-1_")):
                site_name = row_site
            
        advisor = row[col["Service Advisor"]].strip()
        pay_type = row[col["Pay Type"]].strip().upper()
        source_code = str(row[col["Source Code"]]).strip()
        qty_raw = row[col["Sale Qty"]].strip()
        try:
            qty = int(float(qty_raw))
        except ValueError:
            qty = 1
        rows.append(
            OpCodeRow(
                part_number=part,
                sale_qty=qty,
                service_advisor=advisor,
                pay_type=pay_type,
                source_code=source_code,
            )
        )

    if not rows:
        raise ValueError("No kit sale rows found in OP Code CSV.")
    return OpCodeParseResult(
        rows=rows,
        period_start=period_start,
        period_end=period_end,
        site_name=site_name,
    )
