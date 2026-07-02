"""Menu Builder profitability calculations."""

from __future__ import annotations

from app.menu.models import MenuProject, PmpService, PricingAssumptions, PvpData


def parts_sale_from_cost(parts_cost: float, parts_gross_pct: float) -> float:
    if parts_gross_pct >= 1:
        return parts_cost
    return parts_cost / (1 - parts_gross_pct)


def calc_pmp_service(
    service: PmpService,
    pricing: PricingAssumptions,
    project: MenuProject | None = None,
) -> dict:
    extra_cost = sum(p.parts_cost for p in service.extra_parts)
    component_cost = _component_parts_cost(service, project)
    total_parts_cost = component_cost if service.product_items else service.parts_cost + extra_cost
    total_parts_sale = parts_sale_from_cost(total_parts_cost, pricing.parts_gross_pct)

    labor_cost = service.labor_hours * pricing.avg_labor_cost_per_hour
    labor_sale = service.pretty_price - total_parts_sale
    actual_elr = labor_sale / service.labor_hours if service.labor_hours else 0.0
    target_price = (service.labor_hours * pricing.target_elr) + total_parts_sale
    labor_gross = labor_sale - labor_cost
    parts_gross = total_parts_sale - total_parts_cost
    total_gross = labor_gross + parts_gross
    meets_target = actual_elr >= pricing.target_elr if service.labor_hours else True
    monthly_gross = total_gross * service.projected_monthly_sales

    return {
        "total_parts_cost": round(total_parts_cost, 2),
        "total_parts_sale": round(total_parts_sale, 2),
        "labor_cost": round(labor_cost, 2),
        "labor_sale": round(labor_sale, 2),
        "actual_elr": round(actual_elr, 2),
        "target_price": round(target_price, 2),
        "labor_gross": round(labor_gross, 2),
        "parts_gross": round(parts_gross, 2),
        "total_gross": round(total_gross, 2),
        "meets_target": meets_target,
        "monthly_gross": round(monthly_gross, 2),
    }


def calc_pmp_report(project: MenuProject) -> list[dict]:
    return [
        {"service_id": s.id, **calc_pmp_service(s, project.pricing, project)}
        for s in project.pmp_services
    ]


def calc_pvp(pvp: PvpData, parts_gross_pct: float | None = None) -> dict:
    markup = pvp.parts_markup_pct
    parts_sale = pvp.parts_cost * (1 + markup)
    labor_sale = pvp.cp_labor_rate * pvp.labor_hours
    total = parts_sale + labor_sale
    return {
        "parts_sale": round(parts_sale, 2),
        "labor_sale": round(labor_sale, 2),
        "total": round(total, 2),
        "under_100": total < 100,
    }


def pmp_monthly_total(project: MenuProject) -> float:
    return sum(calc_pmp_service(s, project.pricing, project)["monthly_gross"] for s in project.pmp_services)


def _component_parts_cost(service: PmpService, project: MenuProject | None) -> float:
    if not project or not service.product_items:
        return service.parts_cost
    products = {p.source_product_id or p.id: p for p in project.products}
    total = 0.0
    for item in service.product_items:
        product = products.get(item.product_id)
        if product and product.parts_cost is not None:
            total += product.parts_cost * item.quantity
    return total
