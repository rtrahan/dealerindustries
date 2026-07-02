"""Default workflow template data from Workflow.xlsx."""

from __future__ import annotations

from uuid import uuid4

# Process checklist = these five spreadsheet tabs, in order.
WORKFLOW_STEPS = [
    {"id": "pricing", "sheet": "Dealership Pricing", "title": "Dealership Pricing", "subtitle": "Global assumptions and product catalog"},
    {"id": "pmp", "sheet": "PMP Profitability", "title": "PMP Profitability", "subtitle": "Kit services, margins, and pretty pricing"},
    {"id": "pvp", "sheet": "PVP Profitability", "title": "PVP Profitability", "subtitle": "Used-vehicle protection program pricing"},
    {"id": "advisor_ops", "sheet": "Advisor Ops", "title": "Advisor Ops", "subtitle": "Advisor cheat sheet by OP code"},
    {"id": "parts_pull", "sheet": "Parts Pull", "title": "Parts Pull", "subtitle": "Parts department pull sheet"},
]


def _id() -> str:
    return str(uuid4())


DEFAULT_PRODUCTS = [
    {"category": "frequently_used", "name": "Bulk Coolant"},
    {"category": "frequently_used", "name": "Full Synthetic Oil (Per qt)"},
    {"category": "frequently_used", "name": "Conventional / Semi Synthetic Oil (Per qt)"},
    {"category": "frequently_used", "name": "Oil Filter"},
    {"category": "frequently_used", "name": "Cabin air filter"},
    {"category": "frequently_used", "name": "Engine air filter"},
    {"category": "frequently_used", "name": "Wiper blades"},
    {"category": "product", "name": "Semi Synthetic Oil - 5qts", "labor_hours": 0.3, "current_sales_price": 49.95},
    {"category": "product", "name": "Full Synthetic Oil - 5qts", "labor_hours": 0.3, "current_sales_price": 69.95},
    {"category": "product", "name": "Semi Synthetic Oil - 6qts", "labor_hours": 0.3, "current_sales_price": 54.95},
    {"category": "product", "name": "Full Synthetic Oil - 6qts", "labor_hours": 0.3, "current_sales_price": 77.95},
    {"category": "product", "name": "Front Wiper Insert", "labor_hours": 0.2, "current_sales_price": 33.95},
    {"category": "product", "name": "Rear Wiper Insert", "labor_hours": 0.1, "current_sales_price": 16.95},
    {"category": "product", "name": "Front Wiper Blades", "labor_hours": 0.1, "current_sales_price": 64.95},
    {"category": "product", "name": "Rear Wiper Blades", "labor_hours": 0.5, "current_sales_price": 31.95},
    {"category": "product", "name": "Rotate Tires", "labor_hours": 0.4, "current_sales_price": 28.95},
    {"category": "product", "name": "Rotate and Balance", "labor_hours": 1.0, "current_sales_price": 69.95},
    {"category": "product", "name": "4 Wheel Alignment", "labor_hours": 1.0, "current_sales_price": 104.95},
    {"category": "product", "name": "Spark Plug (4)", "labor_hours": 0.8, "current_sales_price": 294.95},
    {"category": "product", "name": "Spark Plug (6)", "labor_hours": 1.2, "current_sales_price": 232.95},
    {"category": "product", "name": "Replace Battery", "labor_hours": 0.4, "current_sales_price": None},
    {"category": "fluid_exchange", "name": "Brake Fluid Exchange"},
    {"category": "fluid_exchange", "name": "Power Steering Fluid Exchange"},
    {"category": "fluid_exchange", "name": "Coolant Fluid Exchange"},
    {"category": "fluid_exchange", "name": "Complete Fuel Service"},
    {"category": "fluid_exchange", "name": "Minor Fuel Service"},
    {"category": "fluid_exchange", "name": "Automatic Transmission Service"},
    {"category": "fluid_exchange", "name": "CVT Transmission Service"},
    {"category": "fluid_exchange", "name": "Battery Terminal Service"},
    {"category": "fluid_exchange", "name": "Climate Control Service"},
]

DEFAULT_PMP_SERVICES = [
    {
        "group_name": "COMPLETE FUEL SYSTEM SERVICE",
        "kit_name": "BD-93010 SUPERTUNE KIT",
        "labor_hours": 1.0,
        "parts_cost": 24.48,
        "pretty_price": 149.95,
        "projected_monthly_sales": 30,
        "extra_parts": [],
    },
    {
        "group_name": "BRAKE SYSTEM EXCHANGE",
        "kit_name": "BD-59136 BRAKE FLUID KIT DOT 4",
        "labor_hours": 1.0,
        "parts_cost": 17.58,
        "pretty_price": 109.95,
        "projected_monthly_sales": 30,
        "extra_parts": [],
    },
    {
        "group_name": "POWER STEERING FLUID EXCHANGE",
        "kit_name": "BD-57148 PS Kit Clear",
        "labor_hours": 1.0,
        "parts_cost": 28.62,
        "pretty_price": 139.95,
        "projected_monthly_sales": 30,
        "extra_parts": [],
    },
    {
        "group_name": "COOLANT FLUID EXCHANGE",
        "kit_name": "BD-94608 (COOLANT KIT)",
        "labor_hours": 1.0,
        "parts_cost": 14.68,
        "pretty_price": 129.95,
        "projected_monthly_sales": 30,
        "extra_parts": [{"name": "COOLANT", "parts_cost": 13.15}],
    },
    {
        "group_name": "AUTOMATIC TRANSMISSION SERVICE",
        "kit_name": "BD-93258 Automatic Transmission Kit",
        "labor_hours": 1.0,
        "parts_cost": 33.35,
        "pretty_price": 229.95,
        "projected_monthly_sales": 30,
        "extra_parts": [{"name": "BD-57074 HI Vis Transmission Fluid", "parts_cost": 76.25}],
    },
    {
        "group_name": "VEHICLE PROTECTION SERVICE",
        "kit_name": "BD-93435 3-5K Maintenance Kit",
        "labor_hours": 0.1,
        "parts_cost": 16.17,
        "pretty_price": 34.95,
        "projected_monthly_sales": 30,
        "extra_parts": [],
    },
]

DEFAULT_ADVISOR_PACKAGES = [
    {"section": "Gasoline Service Intervals", "op_code": "5K", "description": "Vin Specific Oil Change, Tire Rotation and Vehicle Protection Service", "parts": 74.81, "time": 0.7, "labor": 15.18, "total": 89.99},
    {"section": "Gasoline Service Intervals", "op_code": "15K", "description": "Vin Specific Oil Change, Tire Rotation and Balance, Vehicle Protection Service, Complete Fuel Service", "parts": 23.09, "time": 2.2, "labor": 276.90, "total": 299.99},
    {"section": "Gasoline Service Intervals", "op_code": "20K", "description": "Vin Specific Oil Change, Cabin Filter, Tire Rotation, Vehicle Protection Service, Brake Service", "parts": 153.71, "time": 1.9, "labor": 156.28, "total": 309.99},
    {"section": "Gasoline Service Intervals", "op_code": "30K", "description": "Vin Specific Oil Change, Tire Rotation and Balance, VPS, Complete Fuel Service", "parts": 122.10, "time": 2.2, "labor": 177.89, "total": 299.99},
    {"section": "Gasoline Service Intervals", "op_code": "45K", "description": "Vin Specific Oil Change, Tire Rotation and Balance, Cabin Filter, Engine Filter, Vehicle Protection Service, Brake Service, Transmission Service, Complete Fuel Service", "parts": 295.61, "time": 4.0, "labor": 369.38, "total": 664.99},
    {"section": "Gasoline Service Intervals", "op_code": "60K", "description": "Vin Specific Oil Change, Tire Rotation and Balance, 4 Wheel Alignment, VPS, Battery Service, Complete Fuel Service, Coolant Fluid Service", "parts": 115.04, "time": 4.0, "labor": 339.95, "total": 454.99},
    {"section": "Fluid Services", "op_code": "BS", "description": "Brake Service BD-59136", "parts": 25.11, "time": 1.0, "labor": 84.88, "total": 109.95},
    {"section": "Fluid Services", "op_code": "PS", "description": "Power Steering Service BD-57148", "parts": 40.89, "time": 1.0, "labor": 79.10, "total": 139.95},
    {"section": "Fluid Services", "op_code": "CS", "description": "Coolant Service BD-94608", "parts": 39.76, "time": 1.0, "labor": 73.15, "total": 129.95},
    {"section": "Fluid Services", "op_code": "ATS", "description": "Automatic Transmission Service BD-93258 and BD-57084", "parts": 125.76, "time": 1.0, "labor": 94.23, "total": 219.99},
    {"section": "Fluid Services", "op_code": "CFS", "description": "Complete Fuel Service BD-93010", "parts": 34.97, "time": 1.0, "labor": 115.02, "total": 149.95},
    {"section": "Fluid Services", "op_code": "VPS", "description": "Vehicle Protection Service BD-93435", "parts": 23.10, "time": 0.1, "labor": 6.90, "total": 34.95},
]

DEFAULT_PARTS_PULL = [
    {"section": "5K", "op_code_or_part": "5K", "description": "Oil Change, Filter, Tire Rotation and VPS", "parts_sale": ""},
    {"section": "5K", "op_code_or_part": "Vin Specific", "description": "Oil and Oil Filter", "parts_sale": "Vin Specific"},
    {"section": "5K", "op_code_or_part": "93435", "description": "VPS - Vehicle Protection Service", "parts_sale": 23.10},
    {"section": "15K", "op_code_or_part": "15K", "description": "Oil Change and Filter, Tire Rotation and Balance, Complete Fuel Service, and Vehicle Protection Service", "parts_sale": ""},
    {"section": "15K", "op_code_or_part": "Vin Specific", "description": "Oil and Oil Filter", "parts_sale": "Vin Specific"},
    {"section": "15K", "op_code_or_part": "93010", "description": "Complete Fuel Service", "parts_sale": 34.97},
    {"section": "15K", "op_code_or_part": "93435", "description": "VPS - Vehicle Protection Service", "parts_sale": 23.10},
    {"section": "20K", "op_code_or_part": "20K", "description": "Oil Change and Filter, Cabin Filter, Tire Rotation, Vehicle Protection Service, and Brake Fluid Service", "parts_sale": ""},
    {"section": "20K", "op_code_or_part": "Vin Specific", "description": "Oil and Oil Filter", "parts_sale": "Vin Specific"},
    {"section": "20K", "op_code_or_part": "Vin Specific", "description": "Cabin Filter", "parts_sale": "Vin Specific"},
    {"section": "20K", "op_code_or_part": "93435", "description": "VPS - Vehicle Protection Service", "parts_sale": 23.10},
    {"section": "20K", "op_code_or_part": "59136", "description": "Brake Fluid Service", "parts_sale": 25.11},
    {"section": "30K", "op_code_or_part": "30K", "description": "Oil Change and Filter, Tire Rotation and Balance, Complete Fuel Service, and Vehicle Protection Service", "parts_sale": ""},
    {"section": "30K", "op_code_or_part": "Vin Specific", "description": "Oil and Oil Filter", "parts_sale": "Vin Specific"},
    {"section": "30K", "op_code_or_part": "93010", "description": "Complete Fuel Service", "parts_sale": 34.97},
    {"section": "30K", "op_code_or_part": "93435", "description": "VPS - Vehicle Protection Service", "parts_sale": 23.10},
    {"section": "45K", "op_code_or_part": "45K", "description": "Oil Change and Filter, Tire Rotation and Balance, Replace Cabin Air Filter, Replace Engine Air Filter, Brake Fluid Service, Transmission Fluid Service, Complete Fuel Service and Vehicle Protection Service", "parts_sale": ""},
    {"section": "45K", "op_code_or_part": "Vin Specific", "description": "Oil and Oil Filter", "parts_sale": "Vin Specific"},
    {"section": "45K", "op_code_or_part": "Vin Specific", "description": "Cabin Filter", "parts_sale": "Vin Specific"},
    {"section": "45K", "op_code_or_part": "Vin Specific", "description": "Engine Air", "parts_sale": "Vin Specific"},
    {"section": "45K", "op_code_or_part": "93435", "description": "VPS - Vehicle Protection Service", "parts_sale": 23.10},
    {"section": "45K", "op_code_or_part": "59136", "description": "Brake Fluid Service", "parts_sale": 25.11},
    {"section": "45K", "op_code_or_part": "93258", "description": "Transmission Fluid Service", "parts_sale": 47.64},
    {"section": "45K", "op_code_or_part": "BD-57074 or BD-57084", "description": "See Spec Sheet", "parts_sale": 108.93},
    {"section": "45K", "op_code_or_part": "93010", "description": "Complete Fuel Service", "parts_sale": 34.97},
    {"section": "60K", "op_code_or_part": "60K", "description": "Oil Change and Filter, Tire Rotation and Balance, 4 Wheel Alignment, Complete Fuel Service, Coolant Fluid Service and Vehicle Protection Service", "parts_sale": ""},
    {"section": "60K", "op_code_or_part": "Vin Specific", "description": "Oil and Oil Filter", "parts_sale": "Vin Specific"},
    {"section": "60K", "op_code_or_part": "93010", "description": "Complete Fuel Service", "parts_sale": 34.97},
    {"section": "60K", "op_code_or_part": "94608", "description": "Coolant Fluid Service Kit", "parts_sale": 20.97},
    {"section": "60K", "op_code_or_part": "Vin Specific", "description": "Bulk Coolant", "parts_sale": "Vin Specific"},
    {"section": "60K", "op_code_or_part": "93435", "description": "VPS - Vehicle Protection Service", "parts_sale": 23.10},
    {"section": "BS", "op_code_or_part": "BS", "description": "Brake Fluid Service", "parts_sale": ""},
    {"section": "BS", "op_code_or_part": "59136", "description": "Brake Fluid Service Kit", "parts_sale": 25.11},
    {"section": "PS", "op_code_or_part": "PS", "description": "Power Steering Fluid Service", "parts_sale": ""},
    {"section": "PS", "op_code_or_part": "57148", "description": "Power Steering Fluid Service Kit - Clear", "parts_sale": 40.89},
    {"section": "CS", "op_code_or_part": "CS", "description": "Coolant Fluid Service", "parts_sale": ""},
    {"section": "CS", "op_code_or_part": "94608", "description": "Coolant Fluid Service Kit", "parts_sale": 20.97},
    {"section": "CS", "op_code_or_part": "Vin Specific", "description": "Bulk Coolant", "parts_sale": "Vin Specific"},
    {"section": "ATS", "op_code_or_part": "ATS", "description": "Transmission Fluid Service", "parts_sale": ""},
    {"section": "ATS", "op_code_or_part": "93258", "description": "Transmission Fluid Service Kit", "parts_sale": 47.64},
    {"section": "ATS", "op_code_or_part": "BD-57074 or BD-57084", "description": "See Spec Sheet", "parts_sale": 108.93},
    {"section": "CFS", "op_code_or_part": "CFS", "description": "Complete Fuel Service", "parts_sale": ""},
    {"section": "CFS", "op_code_or_part": "93010", "description": "Complete Fuel Service Kit", "parts_sale": 34.97},
    {"section": "VPS", "op_code_or_part": "VPS", "description": "Vehicle Protection Service", "parts_sale": ""},
    {"section": "VPS", "op_code_or_part": "93435", "description": "3-5K Vehicle Protection Service Kit", "parts_sale": 23.10},
]


def build_default_products() -> list[dict]:
    return [{"id": _id(), **p} for p in DEFAULT_PRODUCTS]


def _normalize_product_name(name: str) -> str:
    return " ".join(name.lower().split())


def merge_default_products(existing_products: list[dict]) -> list[dict]:
    """Backfill pricing sections while preserving existing edits by product name."""
    existing_by_name = {
        _normalize_product_name(str(product.get("name", ""))): product
        for product in existing_products
    }
    merged: list[dict] = []
    for default in build_default_products():
        existing = existing_by_name.get(_normalize_product_name(default["name"]))
        if existing:
            item = {**default, **existing}
            item["category"] = default.get("category", item.get("category", "product"))
            merged.append(item)
        else:
            merged.append(default)
    return merged


def build_default_pmp_services() -> list[dict]:
    services = []
    for s in DEFAULT_PMP_SERVICES:
        services.append({
            "id": _id(),
            "group_name": s["group_name"],
            "kit_name": s["kit_name"],
            "labor_hours": s["labor_hours"],
            "parts_cost": s["parts_cost"],
            "pretty_price": s["pretty_price"],
            "projected_monthly_sales": s["projected_monthly_sales"],
            "extra_parts": [{"id": _id(), **ep} for ep in s["extra_parts"]],
        })
    return services


def build_default_advisor_packages() -> list[dict]:
    return [{"id": _id(), **p} for p in DEFAULT_ADVISOR_PACKAGES]


def build_default_parts_pull() -> list[dict]:
    return [{"id": _id(), **p} for p in DEFAULT_PARTS_PULL]


def _migrate_steps(data: dict) -> None:
    """Normalize step progress to the 5-tab checklist."""
    step_count = len(WORKFLOW_STEPS)
    steps = list(data.get("steps_completed") or [])

    if len(steps) == 6:
        steps = steps[1:]
        current = int(data.get("current_step") or 0)
        data["current_step"] = max(0, current - 1) if current > 0 else 0

    while len(steps) < step_count:
        steps.append(False)
    data["steps_completed"] = steps[:step_count]

    current = int(data.get("current_step") or 0)
    data["current_step"] = max(0, min(current, step_count - 1))


def apply_template_defaults(data: dict) -> dict:
    """Backfill workflow fields for projects created before the wizard."""
    data.setdefault("current_step", 0)
    _migrate_steps(data)
    data.pop("launch_tasks", None)
    pricing = data.get("pricing")
    if isinstance(pricing, dict) and "override_fields" not in pricing:
        pricing["override_fields"] = [
            "target_elr",
            "avg_labor_cost_per_hour",
            "parts_gross_pct",
            "spiff_amount",
        ]
    for product in data.get("products", []):
        if "override_fields" not in product and not product.get("source_product_id"):
            product["override_fields"] = [
                field for field in [
                    "name",
                    "category",
                    "parts_cost",
                    "parts_sale",
                    "labor_hours",
                    "current_sales_price",
                    "op_code",
                ]
                if product.get(field) is not None
            ]
    for service in data.get("pmp_services", []):
        if "override_fields" not in service and not service.get("source_kit_id"):
            service["override_fields"] = [
                field for field in [
                    "group_name",
                    "kit_name",
                    "labor_hours",
                    "parts_cost",
                    "pretty_price",
                    "projected_monthly_sales",
                ]
                if service.get(field) is not None
            ]
    if (
        not data.get("products")
        or not any(p.get("category") == "frequently_used" for p in data.get("products", []))
        or not any(p.get("category") == "fluid_exchange" for p in data.get("products", []))
    ):
        data["products"] = merge_default_products(data.get("products", []))
    if not data.get("pmp_services"):
        data["pmp_services"] = build_default_pmp_services()
    if not data.get("pvp"):
        data["pvp"] = {
            "parts_cost": 58.55,
            "parts_markup_pct": 0.20,
            "cp_labor_rate": 90.0,
            "labor_hours": 0.2,
        }
    if not data.get("advisor_packages"):
        data["advisor_packages"] = build_default_advisor_packages()
    if not data.get("parts_pull") or len(data.get("parts_pull", [])) < len(DEFAULT_PARTS_PULL):
        data["parts_pull"] = build_default_parts_pull()
    return data
