"""Gemini vision extraction for CDK printed reports."""

from __future__ import annotations

import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google import genai
from google.genai import types

from collections.abc import Callable
from typing import Any

from app.parsers.advisor import AdvisorMetrics
from app.parsers.cdk.advisor_recap import AdvisorRecapParseResult
from app.parsers.opcode import OpCodeParseResult, OpCodeRow

DEFAULT_MODEL = "gemini-2.5-flash"

_ADVISOR_PROMPT = """You are reading a photo of a CDK "SERVICE ADVISOR RECAP REPORT" dot-matrix printout.

Extract structured data and return JSON only.

Rules:
- Read through highlights, pen marks, and photo glare when possible.
- Include ONLY Customer Pay rows (labor class column = "C").
- Each advisor may have separate C, I, and W rows — we only want the C row.
- "name" is the advisor last name from SA-NAME (e.g. RAILEY, TODORA).
- "advisor_number" is the 4-digit SA-NO.
- ro_count = #ROS, bill_hours = HRS-SLD, hrs_per_ro = HRS/RO, elr = ELR column.
- period_start / period_end from the FROM ... THRU ... header as MM-DD-YYYY (assume 20YY for 2-digit years).
- store_name from the dealership header line.

Return JSON:
{
  "store_name": "string",
  "period_start": "MM-DD-YYYY or null",
  "period_end": "MM-DD-YYYY or null",
  "advisors": [
    {
      "advisor_number": "9064",
      "name": "RAILEY",
      "ro_count": 146,
      "bill_hours": 212.2,
      "hrs_per_ro": 1.45,
      "elr": 157.42
    }
  ]
}
"""

_OPCODE_PROMPT = """You are reading a photo of a CDK "OP-CODE HISTORY REPORT" page (dot-matrix printout).

Extract every data row on this page and return JSON only.

Rules:
- Read through highlights and pen marks — still extract the row if legible.
- Skip headers, footers, "***" separator lines, and column titles.
- Each row is one kit/opcode sale.
- op_code examples: 5K, 10K, 15K, BS, ATF, BATTS, etc.
- advisor_number is the 4-digit SERVICE ADVISOR column.
- labor_type is usually CEXP or CALLY.
- Include all rows on this page, not just highlighted ones.

Return JSON:
{
  "store_name": "string or null",
  "period_start": "MM-DD-YYYY or null",
  "period_end": "MM-DD-YYYY or null",
  "rows": [
    {
      "op_code": "5K",
      "tech": "5243",
      "ro": "461330",
      "date_closed": "08MAY26",
      "advisor_number": "9064",
      "vin": "KNDMB5C18G6093113",
      "labor_type": "CEXP"
    }
  ]
}
"""

_CDK_PHOTO_PROMPT = """You are reading a photo of a CDK dealership dot-matrix report printout.

First identify the report type, then extract the matching data. Return JSON only.

If this is a "SERVICE ADVISOR RECAP REPORT" (header says SERVICE ADVISOR RECAP, columns like SA-NO, SA-NAME, #ROS, ELR):
{
  "report_type": "advisor_recap",
  "store_name": "string",
  "period_start": "MM-DD-YYYY or null",
  "period_end": "MM-DD-YYYY or null",
  "advisors": [
    {
      "advisor_number": "9064",
      "name": "RAILEY",
      "ro_count": 146,
      "bill_hours": 212.2,
      "hrs_per_ro": 1.45,
      "elr": 157.42
    }
  ]
}
For advisor_recap: include ONLY Customer Pay rows (labor class = "C"). Each advisor may have C, I, W rows — only extract C.

If this is an "OP-CODE HISTORY REPORT" (header says OP-CODE HISTORY, columns like OP CODE, TECH, RO, SERVICE ADVISOR, VIN):
{
  "report_type": "opcode_history",
  "store_name": "string or null",
  "period_start": "MM-DD-YYYY or null",
  "period_end": "MM-DD-YYYY or null",
  "rows": [
    {
      "op_code": "5K",
      "tech": "5243",
      "ro": "461330",
      "date_closed": "08MAY26",
      "advisor_number": "9064",
      "vin": "KNDMB5C18G6093113",
      "labor_type": "CEXP"
    }
  ]
}
For opcode_history: extract every data row on the page, not just highlighted rows.

If the image is not a CDK report or is unreadable:
{"report_type": "unknown"}
"""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    env_path = _project_root() / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == "GEMINI_API_KEY":
                key = value.strip().strip('"').strip("'")
                if key:
                    return key
    raise ValueError(
        "GEMINI_API_KEY is not set. Add it to your environment or a .env file in the project root."
    )


def get_gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _mime_type(image_bytes: bytes) -> str:
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


_THREAD_LOCAL = threading.local()


def _max_workers() -> int:
    raw = os.environ.get("GEMINI_MAX_WORKERS", "6").strip()
    try:
        return max(1, min(int(raw), 12))
    except ValueError:
        return 6


def _client() -> genai.Client:
    client = getattr(_THREAD_LOCAL, "client", None)
    if client is None:
        client = genai.Client(api_key=get_gemini_api_key())
        _THREAD_LOCAL.client = client
    return client


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Gemini response must be a JSON object.")
    return data


def _analyze_image(image_bytes: bytes, prompt: str) -> dict:
    response = _client().models.generate_content(
        model=get_gemini_model(),
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=image_bytes, mime_type=_mime_type(image_bytes)),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")
    return _parse_json_response(text)


def extract_advisor_recap(image_bytes: bytes) -> AdvisorRecapParseResult:
    data = _analyze_image(image_bytes, _ADVISOR_PROMPT)
    return _advisor_recap_from_data(data, require_advisors=True)


def _advisor_recap_from_data(data: dict, *, require_advisors: bool) -> AdvisorRecapParseResult:
    advisors: dict[str, AdvisorMetrics] = {}
    advisor_numbers: dict[str, str] = {}

    for item in data.get("advisors") or []:
        if not isinstance(item, dict):
            continue
        sa_no = str(item.get("advisor_number", "")).strip()
        name = re.sub(r"\s+", " ", str(item.get("name", "")).strip().upper())
        if not sa_no or not name:
            continue
        ro_count = float(item.get("ro_count") or 0)
        bill_hrs = float(item.get("bill_hours") or 0)
        hrs_per_ro = float(item.get("hrs_per_ro") or 0)
        elr = float(item.get("elr") or 0)
        if not hrs_per_ro and ro_count:
            hrs_per_ro = bill_hrs / ro_count

        advisors[name] = AdvisorMetrics(
            name=name,
            ro_count=ro_count,
            bill_hrs=bill_hrs,
            elr=elr,
            parts_gp_pct=0.0,
            hrs_per_ro=hrs_per_ro,
        )
        advisor_numbers[sa_no] = name

    if require_advisors and not advisors:
        raise ValueError("Gemini could not find Customer Pay advisor rows in the recap photo.")

    return AdvisorRecapParseResult(
        advisors=advisors,
        advisor_numbers=advisor_numbers,
        period_start=_nullable_str(data.get("period_start")),
        period_end=_nullable_str(data.get("period_end")),
        store_name=_nullable_str(data.get("store_name")),
    )


def _opcode_rows_from_data(
    data: dict,
    *,
    advisor_numbers: dict[str, str] | None,
    seen: set[tuple[str, str, str]],
) -> list[OpCodeRow]:
    rows: list[OpCodeRow] = []
    for item in data.get("rows") or []:
        if not isinstance(item, dict):
            continue
        op_code = str(item.get("op_code", "")).strip().upper()
        ro = str(item.get("ro", "")).strip()
        advisor_no = str(item.get("advisor_number", "")).strip()
        labor = str(item.get("labor_type", "CEXP")).strip().upper() or "CEXP"
        if not op_code or not ro or not advisor_no:
            continue

        key = (op_code, ro, advisor_no)
        if key in seen:
            continue
        seen.add(key)

        advisor_name = advisor_numbers.get(advisor_no, advisor_no) if advisor_numbers else advisor_no
        rows.append(
            OpCodeRow(
                part_number=op_code,
                sale_qty=1,
                service_advisor=advisor_name,
                pay_type=labor,
                source_code="",
            )
        )
    return rows


def extract_opcode_history(
    image_pages: list[bytes],
    *,
    advisor_numbers: dict[str, str] | None = None,
) -> OpCodeParseResult:
    rows: list[OpCodeRow] = []
    seen: set[tuple[str, str, str]] = set()
    store_name: str | None = None
    period_start: str | None = None
    period_end: str | None = None

    for page_bytes in image_pages:
        data = _analyze_image(page_bytes, _OPCODE_PROMPT)
        if not store_name:
            store_name = _nullable_str(data.get("store_name"))
        if not period_start:
            period_start = _nullable_str(data.get("period_start"))
        if not period_end:
            period_end = _nullable_str(data.get("period_end"))
        rows.extend(
            _opcode_rows_from_data(data, advisor_numbers=advisor_numbers, seen=seen)
        )

    if not rows:
        raise ValueError("Gemini could not find kit sale rows in the OP-Code History photos.")

    return OpCodeParseResult(
        rows=rows,
        period_start=period_start,
        period_end=period_end,
        site_name=store_name,
    )


def process_cdk_photos(
    photos: list[bytes],
    *,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[AdvisorRecapParseResult, OpCodeParseResult]:
    """Classify and extract data from an unsorted batch of CDK report photos."""

    def emit(**event: Any) -> None:
        if on_progress:
            on_progress({"type": "progress", **event})

    if not photos:
        raise ValueError("Please upload at least one CDK report photo.")

    total = len(photos)
    workers = min(_max_workers(), total)
    parsed_pages: list[dict | None] = [None] * total
    completed = 0
    progress_lock = threading.Lock()

    def analyze(index: int, photo: bytes) -> tuple[int, dict]:
        return index, _analyze_image(photo, _CDK_PHOTO_PROMPT)

    emit(
        phase="analyze",
        current=0,
        total=total,
        percent=4,
        message=f"Analyzing {total} photos in parallel ({workers} at a time)…",
        workers=workers,
    )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(analyze, index, photo): index
            for index, photo in enumerate(photos)
        }
        for future in as_completed(futures):
            index, data = future.result()
            parsed_pages[index] = data

            report_type = str(data.get("report_type", "unknown")).strip().lower()
            if report_type == "advisor_recap":
                label = "Service Advisor Recap"
            elif report_type == "opcode_history":
                label = "OP-Code History"
            else:
                label = "Unknown report"

            with progress_lock:
                completed += 1
                emit(
                    phase="analyze",
                    current=completed,
                    total=total,
                    percent=max(4, int((completed / total) * 68)),
                    message=f"Photo {index + 1} done — {label} ({completed}/{total})",
                    report_type=report_type,
                )

    emit(phase="merge", percent=72, message="Sorting recap and opcode pages…")

    pages = [page for page in parsed_pages if page is not None]

    advisors: dict[str, AdvisorMetrics] = {}
    advisor_numbers: dict[str, str] = {}
    store_name: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    recap_pages = 0
    opcode_pages = 0

    for data in pages:
        if str(data.get("report_type", "unknown")).strip().lower() != "advisor_recap":
            continue
        recap_pages += 1
        partial = _advisor_recap_from_data(data, require_advisors=False)
        advisors.update(partial.advisors)
        advisor_numbers.update(partial.advisor_numbers)
        store_name = store_name or partial.store_name
        period_start = period_start or partial.period_start
        period_end = period_end or partial.period_end

    opcode_rows: list[OpCodeRow] = []
    seen: set[tuple[str, str, str]] = set()
    for data in pages:
        if str(data.get("report_type", "unknown")).strip().lower() != "opcode_history":
            continue
        opcode_pages += 1
        store_name = store_name or _nullable_str(data.get("store_name"))
        period_start = period_start or _nullable_str(data.get("period_start"))
        period_end = period_end or _nullable_str(data.get("period_end"))
        opcode_rows.extend(
            _opcode_rows_from_data(data, advisor_numbers=advisor_numbers, seen=seen)
        )

    if recap_pages == 0:
        raise ValueError(
            "Could not find a Service Advisor Recap photo in your upload. "
            "Make sure the recap report is included."
        )
    if opcode_pages == 0:
        raise ValueError(
            "Could not find any OP-Code History photos in your upload. "
            "Make sure all opcode pages are included."
        )
    if not advisors:
        raise ValueError("Found a recap photo but could not read any Customer Pay advisor rows.")
    if not opcode_rows:
        raise ValueError("Found OP-Code History photos but could not read any kit sale rows.")

    emit(
        phase="merge",
        percent=78,
        message=f"Found {recap_pages} recap and {opcode_pages} opcode pages",
        recap_pages=recap_pages,
        opcode_pages=opcode_pages,
    )

    recap = AdvisorRecapParseResult(
        advisors=advisors,
        advisor_numbers=advisor_numbers,
        period_start=period_start,
        period_end=period_end,
        store_name=store_name,
    )
    opcode_result = OpCodeParseResult(
        rows=opcode_rows,
        period_start=period_start,
        period_end=period_end,
        site_name=store_name,
    )
    return recap, opcode_result


def _nullable_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
