"""Data models for Menu Builder projects."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from app.menu.template_data import (
    WORKFLOW_STEPS,
    apply_template_defaults,
    build_default_advisor_packages,
    build_default_parts_pull,
    build_default_pmp_services,
    build_default_products,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PricingAssumptions(BaseModel):
    target_elr: float = 90.0
    avg_labor_cost_per_hour: float = 22.0
    parts_gross_pct: float = 0.30
    spiff_amount: float = 3.0
    override_fields: list[str] = Field(default_factory=list)


class ProductLine(BaseModel):
    id: str
    source_product_id: str | None = None
    name: str
    category: str = "product"
    parts_cost: float | None = None
    parts_sale: float | None = None
    labor_hours: float | None = None
    current_sales_price: float | None = None
    op_code: str | None = None
    vin_specific: bool = False
    active: bool = True
    override_fields: list[str] = Field(default_factory=list)


class PmpExtraPart(BaseModel):
    id: str
    name: str
    parts_cost: float = 0.0


class PmpProductItem(BaseModel):
    product_id: str
    quantity: float = 1.0


class PmpService(BaseModel):
    id: str
    source_kit_id: str | None = None
    group_name: str
    kit_name: str
    product_items: list[PmpProductItem] = Field(default_factory=list)
    labor_hours: float = 1.0
    parts_cost: float = 0.0
    pretty_price: float = 0.0
    projected_monthly_sales: int = 30
    extra_parts: list[PmpExtraPart] = Field(default_factory=list)
    override_fields: list[str] = Field(default_factory=list)


class PvpData(BaseModel):
    parts_cost: float = 58.55
    parts_markup_pct: float = 0.20
    cp_labor_rate: float = 90.0
    labor_hours: float = 0.2


class AdvisorPackage(BaseModel):
    id: str
    section: str
    op_code: str
    description: str
    parts: float = 0.0
    time: float = 0.0
    labor: float = 0.0
    total: float = 0.0


class PartsPullRow(BaseModel):
    id: str
    section: str = ""
    op_code_or_part: str
    description: str
    parts_sale: str | float = ""


class MenuProject(BaseModel):
    id: str
    name: str
    status: str = "active"
    created_at: str
    updated_at: str
    current_step: int = 0
    steps_completed: list[bool] = Field(default_factory=lambda: [False] * len(WORKFLOW_STEPS))
    pricing: PricingAssumptions = Field(default_factory=PricingAssumptions)
    products: list[ProductLine] = Field(default_factory=list)
    pmp_services: list[PmpService] = Field(default_factory=list)
    pvp: PvpData = Field(default_factory=PvpData)
    advisor_packages: list[AdvisorPackage] = Field(default_factory=list)
    parts_pull: list[PartsPullRow] = Field(default_factory=list)


class MenuProjectSummary(BaseModel):
    id: str
    name: str
    status: str
    created_at: str
    updated_at: str
    steps_completed: int
    steps_total: int


class CreateProjectRequest(BaseModel):
    name: str


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    current_step: int | None = None
    steps_completed: list[bool] | None = None
    pricing: PricingAssumptions | None = None
    products: list[ProductLine] | None = None
    pmp_services: list[PmpService] | None = None
    pvp: PvpData | None = None
    advisor_packages: list[AdvisorPackage] | None = None
    parts_pull: list[PartsPullRow] | None = None


def new_project(name: str) -> MenuProject:
    from app.menu import admin_store

    now = _now_iso()
    settings = admin_store.load_settings()
    products = [
        ProductLine(
            id=p.id,
            source_product_id=p.id,
            name=p.name,
            category=p.category,
            parts_cost=p.parts_cost,
            parts_sale=p.parts_sale,
            labor_hours=p.labor_hours,
            current_sales_price=p.current_sales_price,
            op_code=p.op_code,
            vin_specific=p.vin_specific,
            active=p.active,
        )
        for p in admin_store.load_products(include_inactive=False)
    ]
    pmp_services = [
        PmpService(
            id=k.id,
            source_kit_id=k.id,
            group_name=k.group_name,
            kit_name=k.kit_name,
            product_items=[PmpProductItem(product_id=i.product_id, quantity=i.quantity) for i in k.product_items],
            labor_hours=k.labor_hours,
            parts_cost=k.parts_cost,
            pretty_price=k.pretty_price,
            projected_monthly_sales=k.projected_monthly_sales,
        )
        for k in admin_store.load_pmp_kits(include_inactive=False)
    ]
    return MenuProject(
        id=str(uuid4()),
        name=name.strip(),
        created_at=now,
        updated_at=now,
        pricing=PricingAssumptions(
            target_elr=settings.target_elr,
            avg_labor_cost_per_hour=settings.avg_labor_cost_per_hour,
            parts_gross_pct=settings.parts_gross_pct,
            spiff_amount=settings.spiff_amount,
        ),
        products=products,
        pmp_services=pmp_services,
        pvp=PvpData(),
        advisor_packages=[AdvisorPackage(**p) for p in build_default_advisor_packages()],
        parts_pull=[PartsPullRow(**p) for p in build_default_parts_pull()],
    )


def to_summary(project: MenuProject) -> MenuProjectSummary:
    steps_done = sum(1 for s in project.steps_completed if s)
    return MenuProjectSummary(
        id=project.id,
        name=project.name,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        steps_completed=steps_done,
        steps_total=len(WORKFLOW_STEPS),
    )


def migrate_project_data(data: dict) -> dict:
    return apply_template_defaults(data)
