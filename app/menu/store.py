"""JSON file persistence for Menu Builder projects."""

from __future__ import annotations

import json
from pathlib import Path

from app.menu import admin_store
from app.menu.models import MenuProject, migrate_project_data, MenuProjectSummary, new_project, to_summary

PROJECTS_DIR = Path(__file__).resolve().parents[2] / "data" / "menu_projects"


def _ensure_dir() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _path(project_id: str) -> Path:
    return PROJECTS_DIR / f"{project_id}.json"


def list_projects(*, include_archived: bool = False) -> list[MenuProjectSummary]:
    _ensure_dir()
    summaries: list[MenuProjectSummary] = []
    for file in PROJECTS_DIR.glob("*.json"):
        project = _load_file(file)
        if project.status == "archived" and not include_archived:
            continue
        summaries.append(to_summary(project))
    summaries.sort(key=lambda p: p.updated_at, reverse=True)
    return summaries


def get_project(project_id: str) -> MenuProject | None:
    path = _path(project_id)
    if not path.exists():
        return None
    return _load_file(path)


def create_project(name: str) -> MenuProject:
    _ensure_dir()
    project = new_project(name)
    save_project(project)
    return project


def save_project(project: MenuProject) -> None:
    _ensure_dir()
    _path(project.id).write_text(
        project.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _load_file(path: Path) -> MenuProject:
    data = json.loads(path.read_text(encoding="utf-8"))
    data = migrate_project_data(data)
    return apply_global_inheritance(MenuProject.model_validate(data))


def apply_global_inheritance(project: MenuProject) -> MenuProject:
    settings = admin_store.load_settings()
    for field in ["target_elr", "avg_labor_cost_per_hour", "parts_gross_pct", "spiff_amount"]:
        if field not in project.pricing.override_fields:
            setattr(project.pricing, field, getattr(settings, field))

    products = admin_store.load_products(include_inactive=False)
    existing_by_source = {p.source_product_id: p for p in project.products if p.source_product_id}
    existing_by_name = {_normalize(p.name): p for p in project.products}
    resolved_products = []
    used_ids = set()
    for admin_product in products:
        product = existing_by_source.get(admin_product.id) or existing_by_name.get(_normalize(admin_product.name))
        if product:
            product.source_product_id = admin_product.id
            _inherit_product(product, admin_product)
        else:
            from app.menu.models import ProductLine

            product = ProductLine(
                id=admin_product.id,
                source_product_id=admin_product.id,
                name=admin_product.name,
                category=admin_product.category,
                parts_cost=admin_product.parts_cost,
                parts_sale=admin_product.parts_sale,
                labor_hours=admin_product.labor_hours,
                current_sales_price=admin_product.current_sales_price,
                op_code=admin_product.op_code,
                vin_specific=admin_product.vin_specific,
                active=admin_product.active,
            )
        resolved_products.append(product)
        used_ids.add(product.id)

    # Preserve custom dealership-only rows.
    resolved_products.extend([p for p in project.products if not p.source_product_id and p.id not in used_ids])
    project.products = resolved_products

    kits = admin_store.load_pmp_kits(include_inactive=False)
    existing_kits_by_source = {s.source_kit_id: s for s in project.pmp_services if s.source_kit_id}
    existing_kits_by_name = {_normalize(s.group_name): s for s in project.pmp_services}
    resolved_kits = []
    for admin_kit in kits:
        service = existing_kits_by_source.get(admin_kit.id) or existing_kits_by_name.get(_normalize(admin_kit.group_name))
        if service:
            service.source_kit_id = admin_kit.id
            _inherit_kit(service, admin_kit)
        else:
            from app.menu.models import PmpProductItem, PmpService

            service = PmpService(
                id=admin_kit.id,
                source_kit_id=admin_kit.id,
                group_name=admin_kit.group_name,
                kit_name=admin_kit.kit_name,
                product_items=[PmpProductItem(product_id=i.product_id, quantity=i.quantity) for i in admin_kit.product_items],
                labor_hours=admin_kit.labor_hours,
                parts_cost=admin_kit.parts_cost,
                pretty_price=admin_kit.pretty_price,
                projected_monthly_sales=admin_kit.projected_monthly_sales,
            )
        resolved_kits.append(service)
    project.pmp_services = resolved_kits
    return project


def _inherit_product(product, admin_product) -> None:
    for field in [
        "name",
        "category",
        "parts_cost",
        "parts_sale",
        "labor_hours",
        "current_sales_price",
        "op_code",
        "vin_specific",
        "active",
    ]:
        if field not in product.override_fields:
            setattr(product, field, getattr(admin_product, field))


def _inherit_kit(service, admin_kit) -> None:
    for field in ["group_name", "kit_name", "labor_hours", "pretty_price", "projected_monthly_sales"]:
        if field not in service.override_fields:
            setattr(service, field, getattr(admin_kit, field))
    if "product_items" not in service.override_fields:
        from app.menu.models import PmpProductItem

        service.product_items = [PmpProductItem(product_id=i.product_id, quantity=i.quantity) for i in admin_kit.product_items]


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())
