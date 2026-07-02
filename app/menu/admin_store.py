"""JSON persistence for global Menu Builder admin templates."""

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

from app.menu.admin_models import AdminPmpKit, AdminProduct, AdminSettings, KitProductItem
from app.menu.template_data import DEFAULT_PMP_SERVICES, DEFAULT_PRODUCTS

ADMIN_DIR = Path(__file__).resolve().parents[2] / "data" / "menu_admin"
SETTINGS_FILE = ADMIN_DIR / "settings.json"
PRODUCTS_FILE = ADMIN_DIR / "products.json"
PMP_KITS_FILE = ADMIN_DIR / "pmp_kits.json"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or str(uuid4())


def _ensure_seeded() -> None:
    ADMIN_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        save_settings(AdminSettings())
    if not PRODUCTS_FILE.exists():
        save_products(_seed_products())
    if not PMP_KITS_FILE.exists():
        products = [AdminProduct.model_validate(item) for item in json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))]
        save_pmp_kits(_seed_pmp_kits(products))


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data) -> None:
    ADMIN_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_settings() -> AdminSettings:
    _ensure_seeded()
    data = _read_json(SETTINGS_FILE, {})
    return AdminSettings.model_validate(data)


def save_settings(settings: AdminSettings) -> None:
    _write_json(SETTINGS_FILE, settings.model_dump())


def load_products(include_inactive: bool = True) -> list[AdminProduct]:
    _ensure_seeded()
    data = _read_json(PRODUCTS_FILE, [])
    products = [AdminProduct.model_validate(item) for item in data]
    if not include_inactive:
        products = [p for p in products if p.active]
    return products


def save_products(products: list[AdminProduct]) -> None:
    _write_json(PRODUCTS_FILE, [p.model_dump() for p in products])


def load_pmp_kits(include_inactive: bool = True) -> list[AdminPmpKit]:
    _ensure_seeded()
    data = _read_json(PMP_KITS_FILE, [])
    kits = [AdminPmpKit.model_validate(item) for item in data]
    if not include_inactive:
        kits = [k for k in kits if k.active]
    return kits


def save_pmp_kits(kits: list[AdminPmpKit]) -> None:
    _write_json(PMP_KITS_FILE, [k.model_dump() for k in kits])


def _seed_products() -> list[AdminProduct]:
    products: list[AdminProduct] = []
    seen: set[str] = set()
    for product in DEFAULT_PRODUCTS:
        name = product["name"]
        product_id = slugify(name)
        if product_id in seen:
            continue
        seen.add(product_id)
        products.append(
            AdminProduct(
                id=product_id,
                name=name,
                category=product.get("category", "product"),
                parts_cost=product.get("parts_cost"),
                parts_sale=product.get("parts_sale"),
                labor_hours=product.get("labor_hours"),
                current_sales_price=product.get("current_sales_price"),
                op_code=product.get("op_code"),
                vin_specific="vin specific" in name.lower(),
            )
        )

    # Add kit-level Bardahl products used by the PMP profitability templates.
    for service in DEFAULT_PMP_SERVICES:
        kit_name = service["kit_name"]
        product_id = slugify(kit_name)
        if product_id not in seen:
            seen.add(product_id)
            products.append(
                AdminProduct(
                    id=product_id,
                    name=kit_name,
                    category="pmp_kit_product",
                    parts_cost=service.get("parts_cost", 0.0),
                    labor_hours=service.get("labor_hours"),
                )
            )
        for extra in service.get("extra_parts", []):
            extra_id = slugify(extra["name"])
            if extra_id in seen:
                continue
            seen.add(extra_id)
            products.append(
                AdminProduct(
                    id=extra_id,
                    name=extra["name"],
                    category="pmp_kit_product",
                    parts_cost=extra.get("parts_cost", 0.0),
                )
            )
    return products


def _seed_pmp_kits(products: list[AdminProduct]) -> list[AdminPmpKit]:
    product_by_name = {p.name.lower(): p for p in products}
    kits: list[AdminPmpKit] = []
    for service in DEFAULT_PMP_SERVICES:
        kit_name = service["kit_name"]
        product_items: list[KitProductItem] = []
        kit_product = product_by_name.get(kit_name.lower())
        if kit_product:
            product_items.append(KitProductItem(product_id=kit_product.id))
        for extra in service.get("extra_parts", []):
            extra_product = product_by_name.get(extra["name"].lower())
            if extra_product:
                product_items.append(KitProductItem(product_id=extra_product.id))
        kits.append(
            AdminPmpKit(
                id=slugify(service["group_name"]),
                group_name=service["group_name"],
                kit_name=kit_name,
                product_items=product_items,
                labor_hours=service.get("labor_hours", 1.0),
                parts_cost=service.get("parts_cost", 0.0),
                pretty_price=service.get("pretty_price", 0.0),
                projected_monthly_sales=service.get("projected_monthly_sales", 30),
            )
        )
    return kits

