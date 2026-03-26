"""Router for all diagram generation endpoints (tag: generate)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.v01.dependencies import get_diagram_service, security
from app.v01.schemas import DiagramGenerateRequest, DiagramResponse
from UMLBot.services.diagram_service import DiagramService

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["generate"])


def _generate_and_respond(
    body: DiagramGenerateRequest,
    api_key: str,
    service: DiagramService,
    generate_method_name: str,
) -> DiagramResponse | JSONResponse:
    """Shared logic for all generate endpoints."""
    method = getattr(service, generate_method_name)
    try:
        result = method(
            description=body.description,
            diagram_type=body.diagram_type,
            theme=body.theme,
            openai_compatible_endpoint=body.openai_compatible_endpoint,
            openai_compatible_key=api_key,
            openai_compatible_model=body.openai_compatible_model,
        )
    except Exception:
        LOGGER.exception("Generation failed for %s", generate_method_name)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error"},
        )

    if not result.plantuml_code:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": result.status_message or "Generation failed",
            },
        )

    image_base64 = service.diagram_image_to_base64(result.pil_image)
    return DiagramResponse(
        status="ok",
        plantuml_code=result.plantuml_code,
        image_base64=image_base64,
        image_url=result.image_url,
        message=result.status_message,
    )


@router.post("/generate", response_model=DiagramResponse)
async def generate_uml(
    body: DiagramGenerateRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
    service: DiagramService = Depends(get_diagram_service),
) -> DiagramResponse | JSONResponse:
    """Generate a UML diagram from a text description."""
    return _generate_and_respond(
        body, credentials.credentials, service, "generate_diagram_from_description"
    )


@router.post("/mindmap/generate", response_model=DiagramResponse)
async def generate_mindmap(
    body: DiagramGenerateRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
    service: DiagramService = Depends(get_diagram_service),
) -> DiagramResponse | JSONResponse:
    """Generate a mindmap from a text description."""
    return _generate_and_respond(
        body, credentials.credentials, service, "generate_mindmap_from_description"
    )


@router.post("/ui-mockup/generate", response_model=DiagramResponse)
async def generate_ui_mockup(
    body: DiagramGenerateRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
    service: DiagramService = Depends(get_diagram_service),
) -> DiagramResponse | JSONResponse:
    """Generate a UI mockup (SALT) from a text description."""
    return _generate_and_respond(
        body, credentials.credentials, service, "generate_ui_mockup_from_description"
    )


@router.post("/gantt/generate", response_model=DiagramResponse)
async def generate_gantt(
    body: DiagramGenerateRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
    service: DiagramService = Depends(get_diagram_service),
) -> DiagramResponse | JSONResponse:
    """Generate a Gantt chart from a text description."""
    return _generate_and_respond(
        body, credentials.credentials, service, "generate_gantt_from_description"
    )


@router.post("/erd/generate", response_model=DiagramResponse)
async def generate_erd(
    body: DiagramGenerateRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
    service: DiagramService = Depends(get_diagram_service),
) -> DiagramResponse | JSONResponse:
    """Generate an ER diagram from a text description."""
    return _generate_and_respond(
        body, credentials.credentials, service, "generate_erd_from_description"
    )


@router.post("/json/generate", response_model=DiagramResponse)
async def generate_json(
    body: DiagramGenerateRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
    service: DiagramService = Depends(get_diagram_service),
) -> DiagramResponse | JSONResponse:
    """Generate a JSON diagram from a text description."""
    return _generate_and_respond(
        body, credentials.credentials, service, "generate_json_from_description"
    )


@router.post("/c4/generate", response_model=DiagramResponse)
async def generate_c4(
    body: DiagramGenerateRequest,
    credentials: HTTPAuthorizationCredentials = Security(security),
    service: DiagramService = Depends(get_diagram_service),
) -> DiagramResponse | JSONResponse:
    """Generate a C4 diagram from a text description."""
    return _generate_and_respond(
        body, credentials.credentials, service, "generate_c4_from_description"
    )
