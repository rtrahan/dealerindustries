"""API routes for Menu Builder projects."""

from __future__ import annotations

from datetime import datetime, timezone

from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.menu.calculations import calc_pmp_report, calc_pvp, pmp_monthly_total
from app.menu.models import (
    CreateProjectRequest,
    MenuProject,
    UpdateProjectRequest,
)
from app.menu.pdf_exports import generate_advisor_ops_pdf, generate_parts_pull_pdf
from app.menu.template_data import WORKFLOW_STEPS
from app.menu import store

router = APIRouter(prefix="/api/menu-projects", tags=["menu-builder"])


def _touch(project: MenuProject) -> MenuProject:
    project.updated_at = datetime.now(timezone.utc).isoformat()
    return project


@router.get("")
async def api_list_projects() -> list:
    return [s.model_dump() for s in store.list_projects()]


@router.post("", status_code=201)
async def api_create_project(body: CreateProjectRequest) -> dict:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Dealership name is required.")
    project = store.create_project(name)
    return project.model_dump()


@router.get("/{project_id}")
async def api_get_project(project_id: str) -> dict:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project.model_dump()


@router.get("/{project_id}/resolved")
async def api_get_resolved_project(project_id: str) -> dict:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project.model_dump()


@router.patch("/{project_id}")
async def api_update_project(project_id: str, body: UpdateProjectRequest) -> dict:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Dealership name cannot be empty.")
        project.name = name
    if body.status is not None:
        if body.status not in {"active", "archived"}:
            raise HTTPException(status_code=400, detail="Status must be active or archived.")
        project.status = body.status
    if body.current_step is not None:
        project.current_step = max(0, min(body.current_step, len(WORKFLOW_STEPS) - 1))
    if body.steps_completed is not None:
        project.steps_completed = body.steps_completed
    if body.pricing is not None:
        project.pricing = body.pricing
    if body.products is not None:
        project.products = body.products
    if body.pmp_services is not None:
        project.pmp_services = body.pmp_services
    if body.pvp is not None:
        project.pvp = body.pvp
    if body.advisor_packages is not None:
        project.advisor_packages = body.advisor_packages
    if body.parts_pull is not None:
        project.parts_pull = body.parts_pull

    store.save_project(_touch(project))
    return project.model_dump()


@router.get("/{project_id}/calculations")
async def api_project_calculations(project_id: str) -> dict:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {
        "pmp": calc_pmp_report(project),
        "pmp_monthly_total": round(pmp_monthly_total(project), 2),
        "pvp": calc_pvp(project.pvp),
    }


@router.get("/{project_id}/advisor-ops.pdf")
async def api_advisor_ops_pdf(project_id: str) -> Response:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    pdf = generate_advisor_ops_pdf(project)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{project.name}-advisor-ops.pdf"'},
    )


@router.get("/{project_id}/parts-pull.pdf")
async def api_parts_pull_pdf(project_id: str) -> Response:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    pdf = generate_parts_pull_pdf(project)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{project.name}-parts-pull.pdf"'},
    )


@router.post("/{project_id}/duplicate", status_code=201)
async def api_duplicate_project(project_id: str) -> dict:
    source = store.get_project(project_id)
    if not source:
        raise HTTPException(status_code=404, detail="Project not found.")

    duplicate = store.create_project(f"{source.name} (Copy)")
    duplicate.pricing = source.pricing.model_copy()
    duplicate.current_step = source.current_step
    duplicate.steps_completed = list(source.steps_completed)
    duplicate.products = [p.model_copy(update={"id": str(uuid4())}) for p in source.products]
    duplicate.pmp_services = [
        s.model_copy(
            update={
                "id": str(uuid4()),
                "extra_parts": [ep.model_copy(update={"id": str(uuid4())}) for ep in s.extra_parts],
            }
        )
        for s in source.pmp_services
    ]
    duplicate.pvp = source.pvp.model_copy()
    duplicate.advisor_packages = [p.model_copy(update={"id": str(uuid4())}) for p in source.advisor_packages]
    duplicate.parts_pull = [p.model_copy(update={"id": str(uuid4())}) for p in source.parts_pull]
    store.save_project(duplicate)
    return duplicate.model_dump()
