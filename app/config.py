"""Load dealership kit configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@dataclass(frozen=True)
class KitDefinition:
    code: str
    label: str
    part_numbers: tuple[str, ...]
    price: float
    hours: float


@dataclass(frozen=True)
class DealershipConfig:
    store_name: str
    source_codes: tuple[str, ...]
    pay_types: tuple[str, ...]
    maintenance_elr: float
    kits: tuple[KitDefinition, ...]
    part_to_kit: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict) -> DealershipConfig:
        kits = []
        part_to_kit: dict[str, str] = {}
        for item in data["kits"]:
            normalized_parts = tuple(
                normalize_part_number(p) for p in item.get("part_numbers", [])
            )
            kit = KitDefinition(
                code=item["code"],
                label=item.get("label", item["code"]),
                part_numbers=normalized_parts,
                price=float(item.get("price", 0)),
                hours=float(item.get("hours", 0)),
            )
            kits.append(kit)
            for part in normalized_parts:
                part_to_kit[part] = kit.code
        return cls(
            store_name=data.get("store_name", "Dealership"),
            source_codes=tuple(data.get("source_codes", [])),
            pay_types=tuple(data.get("pay_types", ["CUSTOMER_PAY"])),
            maintenance_elr=float(data.get("maintenance_elr", 90)),
            kits=tuple(kits),
            part_to_kit=part_to_kit,
        )


def load_config(name: str = "default") -> DealershipConfig:
    path = CONFIG_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as f:
        return DealershipConfig.from_dict(json.load(f))


def normalize_part_number(part: str) -> str:
    part = part.replace("-", "").strip().upper()
    if part.startswith("BD"):
        part = part[2:]
    return part
