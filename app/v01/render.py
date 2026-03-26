"""Router for all render endpoints (tag: render) — no auth required."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.v01.dependencies import get_diagram_service
from app.v01.schemas import RenderRequest, RenderResponse, ResponseStatus
from UMLBot.services.diagram_service import DiagramService

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["render"])


def _render_and_respond(
    body: RenderRequest,
    service: DiagramService,
) -> RenderResponse | JSONResponse:
    """Shared logic for all render endpoints."""
    try:
        pil_image, status_msg, image_url = service.render_diagram_from_code(body.plantuml_code)
        image_base64 = service.diagram_image_to_base64(pil_image)
        return RenderResponse(
            status=ResponseStatus.ok,
            image_base64=image_base64,
            image_url=image_url,
            message=status_msg,
        )
    except Exception:
        LOGGER.exception("Render failed")
        return JSONResponse(
            status_code=500,
            content={"status": ResponseStatus.error, "message": "Internal server error"},
        )


@router.post("/render", response_model=RenderResponse)
async def render_uml(
    body: RenderRequest,
    service: DiagramService = Depends(get_diagram_service),
) -> RenderResponse | JSONResponse:
    """Render PlantUML code to an image."""
    return _render_and_respond(body, service)


@router.post("/mindmap/render", response_model=RenderResponse)
async def render_mindmap(
    body: RenderRequest,
    service: DiagramService = Depends(get_diagram_service),
) -> RenderResponse | JSONResponse:
    """Render PlantUML mindmap code to an image."""
    return _render_and_respond(body, service)


@router.post("/ui-mockup/render", response_model=RenderResponse)
async def render_ui_mockup(
    body: RenderRequest,
    service: DiagramService = Depends(get_diagram_service),
) -> RenderResponse | JSONResponse:
    """Render PlantUML SALT code to an image."""
    return _render_and_respond(body, service)


@router.post("/gantt/render", response_model=RenderResponse)
async def render_gantt(
    body: RenderRequest,
    service: DiagramService = Depends(get_diagram_service),
) -> RenderResponse | JSONResponse:
    """Render PlantUML Gantt code to an image."""
    return _render_and_respond(body, service)


@router.post("/erd/render", response_model=RenderResponse)
async def render_erd(
    body: RenderRequest,
    service: DiagramService = Depends(get_diagram_service),
) -> RenderResponse | JSONResponse:
    """Render PlantUML ER diagram code to an image."""
    return _render_and_respond(body, service)


@router.post("/json/render", response_model=RenderResponse)
async def render_json(
    body: RenderRequest,
    service: DiagramService = Depends(get_diagram_service),
) -> RenderResponse | JSONResponse:
    """Render PlantUML JSON code to an image."""
    return _render_and_respond(body, service)


@router.post("/c4/render", response_model=RenderResponse)
async def render_c4(
    body: RenderRequest,
    service: DiagramService = Depends(get_diagram_service),
) -> RenderResponse | JSONResponse:
    """Render PlantUML C4 code to an image."""
    return _render_and_respond(body, service)
