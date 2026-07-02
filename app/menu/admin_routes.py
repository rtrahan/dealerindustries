"""API routes for global Menu Builder administration."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.menu import admin_store
from app.menu.admin_models import AdminPmpKit, AdminProduct, AdminSettings

router = APIRouter(prefix="/api/menu-admin", tags=["menu-admin"])


@router.get("/settings")
async def api_get_settings() -> dict:
    return admin_store.load_settings().model_dump()


@router.patch("/settings")
async def api_update_settings(body: AdminSettings) -> dict:
    admin_store.save_settings(body)
    return body.model_dump()


@router.get("/products")
async def api_list_products() -> list[dict]:
    return [p.model_dump() for p in admin_store.load_products()]


@router.put("/products")
async def api_replace_products(body: list[AdminProduct]) -> list[dict]:
    admin_store.save_products(body)
    return [p.model_dump() for p in body]


@router.post("/products", status_code=201)
async def api_create_product(body: AdminProduct) -> dict:
    products = admin_store.load_products()
    product = body.model_copy(update={"id": body.id or str(uuid4())})
    if any(p.id == product.id for p in products):
        raise HTTPException(status_code=400, detail="Product ID already exists.")
    products.append(product)
    admin_store.save_products(products)
    return product.model_dump()


@router.patch("/products/{product_id}")
async def api_update_product(product_id: str, body: AdminProduct) -> dict:
    products = admin_store.load_products()
    for idx, product in enumerate(products):
        if product.id == product_id:
            updated = body.model_copy(update={"id": product_id})
            products[idx] = updated
            admin_store.save_products(products)
            return updated.model_dump()
    raise HTTPException(status_code=404, detail="Product not found.")


@router.delete("/products/{product_id}")
async def api_delete_product(product_id: str) -> dict:
    products = [p for p in admin_store.load_products() if p.id != product_id]
    admin_store.save_products(products)
    return {"deleted": product_id}


@router.get("/pmp-kits")
async def api_list_pmp_kits() -> list[dict]:
    return [k.model_dump() for k in admin_store.load_pmp_kits()]


@router.put("/pmp-kits")
async def api_replace_pmp_kits(body: list[AdminPmpKit]) -> list[dict]:
    admin_store.save_pmp_kits(body)
    return [k.model_dump() for k in body]


@router.post("/pmp-kits", status_code=201)
async def api_create_pmp_kit(body: AdminPmpKit) -> dict:
    kits = admin_store.load_pmp_kits()
    kit = body.model_copy(update={"id": body.id or str(uuid4())})
    if any(k.id == kit.id for k in kits):
        raise HTTPException(status_code=400, detail="PMP kit ID already exists.")
    kits.append(kit)
    admin_store.save_pmp_kits(kits)
    return kit.model_dump()


@router.patch("/pmp-kits/{kit_id}")
async def api_update_pmp_kit(kit_id: str, body: AdminPmpKit) -> dict:
    kits = admin_store.load_pmp_kits()
    for idx, kit in enumerate(kits):
        if kit.id == kit_id:
            updated = body.model_copy(update={"id": kit_id})
            kits[idx] = updated
            admin_store.save_pmp_kits(kits)
            return updated.model_dump()
    raise HTTPException(status_code=404, detail="PMP kit not found.")


@router.delete("/pmp-kits/{kit_id}")
async def api_delete_pmp_kit(kit_id: str) -> dict:
    kits = [k for k in admin_store.load_pmp_kits() if k.id != kit_id]
    admin_store.save_pmp_kits(kits)
    return {"deleted": kit_id}

