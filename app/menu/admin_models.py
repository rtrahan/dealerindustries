"""Global admin models for Menu Builder templates."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdminSettings(BaseModel):
    target_elr: float = 90.0
    avg_labor_cost_per_hour: float = 22.0
    parts_gross_pct: float = 0.30
    spiff_amount: float = 3.0


class AdminProduct(BaseModel):
    id: str = ""
    name: str
    category: str = "product"
    parts_cost: float | None = None
    parts_sale: float | None = None
    labor_hours: float | None = None
    current_sales_price: float | None = None
    op_code: str | None = None
    vin_specific: bool = False
    active: bool = True


class KitProductItem(BaseModel):
    product_id: str
    quantity: float = 1.0


class AdminPmpKit(BaseModel):
    id: str = ""
    group_name: str
    kit_name: str
    product_items: list[KitProductItem] = Field(default_factory=list)
    labor_hours: float = 1.0
    parts_cost: float = 0.0
    pretty_price: float = 0.0
    projected_monthly_sales: int = 30
    active: bool = True

