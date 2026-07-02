"""Parse CDK OP-Code History Report OCR text."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.parsers.opcode import OpCodeParseResult, OpCodeRow

_VIN_RE = re.compile(r"[A-HJ-NPR-Z0-9]{17}")
_DATE_RE = re.compile(r"(\d{2}[A-Z]{3}\d{2})")
_BEFORE_VIN_RE = re.compile(
    r"(?P<opcode>[A-Z0-9]{1,5})\s+"
    r"(?P<tech>\d{4})\s+"
    r"(?P<ro>\d{6})\s+"
    r"(?P<date>\d{2}[A-Z]{3}\d{2})\s+"
    r"(?P<advisor>\d{4})\s*$"
)

_KNOWN_OPCODES = {
    "5K", "10K", "15K", "20K", "25K", "30K", "35K", "40K", "45K", "50K",
    "55K", "60K", "65K", "70K", "75K", "80K", "85K", "90K", "95K", "100K", "105K",
    "BS", "PS", "CS", "ATF", "CFS", "VPS", "CCS", "BAT", "BATTS", "TS",
}

_OCR_OPCODE_FIXES = {
    "SK": "5K",
    "BK": "5K",
    "1OK": "10K",
    "IOK": "10K",
    "2OK": "20K",
    "3OK": "30K",
}


def _normalize_opcode(token: str) -> str:
    token = token.upper().strip()
    return _OCR_OPCODE_FIXES.get(token, token)


def _normalize_date(token: str) -> str:
    token = token.upper()
    token = token.replace("OB", "08").replace("O1", "01").replace("O2", "02")
    token = token.replace("O3", "03").replace("O4", "04").replace("O5", "05")
    token = token.replace("O6", "06").replace("O7", "07").replace("O9", "09")
    return token


@dataclass
class _ParsedOpcodeLine:
    row: OpCodeRow
    ro_number: str


def _parse_opcode_line(line: str) -> _ParsedOpcodeLine | None:
    upper = line.upper()
    if "***" in upper or "OP-CODE" in upper or "PAGE" in upper:
        return None
    if "SERIAL NUMBER" in upper or "TECH" in upper and "RO" in upper:
        return None

    vin_match = _VIN_RE.search(upper)
    if not vin_match:
        return None

    vin = vin_match.group()
    before = upper[: vin_match.start()].strip()
    before = re.sub(r"[^A-Z0-9\s]", " ", before)
    before = re.sub(r"\s+", " ", before).strip()

    match = _BEFORE_VIN_RE.search(before)
    if not match:
        # Fallback: pull tokens from the end of the prefix
        tokens = before.split()
        if len(tokens) < 5:
            return None
        advisor, date, ro, tech = tokens[-1], tokens[-2], tokens[-3], tokens[-4]
        opcode = _normalize_opcode(tokens[0])
        if not re.fullmatch(r"\d{4}", advisor):
            return None
        if not re.fullmatch(r"\d{6}", ro):
            return None
        if not re.fullmatch(r"\d{4}", tech):
            return None
        if not _DATE_RE.fullmatch(date):
            date_match = _DATE_RE.search(before)
            date = date_match.group(1) if date_match else date
    else:
        opcode = _normalize_opcode(match.group("opcode"))
        tech = match.group("tech")
        ro = match.group("ro")
        date = _normalize_date(match.group("date"))
        advisor = match.group("advisor")

    if opcode not in _KNOWN_OPCODES:
        return None

    after = upper[vin_match.end() :].strip().split()
    labor = after[0] if after else "CEXP"
    if labor not in {"CEXP", "CALLY", "IWAR", "IINT"}:
        labor = "CEXP"

    row = OpCodeRow(
        part_number=opcode,
        sale_qty=1,
        service_advisor=advisor,
        pay_type=labor,
        source_code="",
    )
    return _ParsedOpcodeLine(row=row, ro_number=ro)


def parse_opcode_history_text(
    text: str,
    *,
    advisor_numbers: dict[str, str] | None = None,
) -> OpCodeParseResult:
    """Parse OCR text from one or more OP-Code History pages."""
    rows: list[OpCodeRow] = []
    seen: set[tuple[str, str, str]] = set()

    for raw_line in text.splitlines():
        parsed = _parse_opcode_line(raw_line)
        if not parsed:
            continue
        row = parsed.row
        key = (row.part_number, parsed.ro_number, row.service_advisor)
        if key in seen:
            continue
        seen.add(key)

        if advisor_numbers and row.service_advisor in advisor_numbers:
            row = OpCodeRow(
                part_number=row.part_number,
                sale_qty=row.sale_qty,
                service_advisor=advisor_numbers[row.service_advisor],
                pay_type=row.pay_type,
                source_code=row.source_code,
            )
        rows.append(row)

    if not rows:
        raise ValueError("No kit sale rows found in OP-Code History photos.")

    period_start, period_end = _parse_period(text)
    store_name = _parse_store_name(text)
    return OpCodeParseResult(
        rows=rows,
        period_start=period_start,
        period_end=period_end,
        site_name=store_name,
    )


def _parse_period(text: str) -> tuple[str | None, str | None]:
    match = re.search(r":?\s*(\d{1,2})\.(\d{1,2})\s+THRU\s+(\d{1,2})\.(\d{1,2})", text, re.IGNORECASE)
    if not match:
        return None, None
    sm, sd, em, ed = match.groups()
    return f"{int(sm):02d}-{int(sd):02d}-2026", f"{int(em):02d}-{int(ed):02d}-2026"


def _parse_store_name(text: str) -> str | None:
    if "CLASSIC KIA" in text.upper() and "CARROLLTON" in text.upper():
        return "Classic Kia of Carrollton"
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line.strip().upper())
        if "OP-CODE HISTORY" in cleaned or ("PAGE" in cleaned and "REPORT" not in cleaned):
            continue
        if len(cleaned) < 8:
            continue
        if "CLASSIC KIA" in cleaned and "CARROLLTON" in cleaned:
            return "Classic Kia of Carrollton"
    return None
