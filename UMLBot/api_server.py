"""FastAPI app factory for the UMLBot HTTP API."""

from __future__ import annotations

import logging

from collections.abc import Callable
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from UMLBot.config.config import UMLBotConfig
from UMLBot.services import (
    DiagramGenerationResult,
    DiagramService,
)


def create_api_app(
    generate_fn: Callable[[str, str, str | None], "DiagramGenerationResult"] | None = None,
    mindmap_generate_fn: Callable[[str, str, str | None], "DiagramGenerationResult"] | None = None,
    ui_mockup_generate_fn: Callable[[str, str, str | None], "DiagramGenerationResult"] | None = None,
    gantt_generate_fn: Callable[[str, str, str | None], "DiagramGenerationResult"] | None = None,
    erd_generate_fn: Callable[[str, str, str | None], "DiagramGenerationResult"] | None = None,
    service: DiagramService | None = None,
) -> FastAPI:
    """Builds the FastAPI application exposing JSON endpoints for diagram generation."""
    diagram_service = service or DiagramService()
    if generate_fn is None:
        generate_fn = diagram_service.generate_diagram_from_description
    if mindmap_generate_fn is None:
        mindmap_generate_fn = diagram_service.generate_mindmap_from_description
    if ui_mockup_generate_fn is None:
        ui_mockup_generate_fn = diagram_service.generate_ui_mockup_from_description
    if gantt_generate_fn is None:
        gantt_generate_fn = diagram_service.generate_gantt_from_description
    if erd_generate_fn is None:
        erd_generate_fn = diagram_service.generate_erd_from_description

    api_app = FastAPI(title="UMLBot HTTP API")
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=UMLBotConfig.CORS_ALLOW_ORIGINS,
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
    )

    @api_app.post("/api/generate")
    async def generate_endpoint(request: Request):
        """Handle diagram generation requests from the frontend."""
        try:
            data = await request.json()
            description = data.get("description")
            diagram_type = data.get("diagram_type")
            theme = data.get("theme")

            if not description or not diagram_type:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required fields: description, diagram_type",
                    },
                )

            result = generate_fn(description, diagram_type, theme)
            if not result.plantuml_code:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": result.status_message or "Generation failed",
                    },
                )

            image_base64 = diagram_service.diagram_image_to_base64(result.pil_image)
            return {
                "status": "ok",
                "plantuml_code": result.plantuml_code,
                "image_base64": image_base64,
                "image_url": result.image_url,
                "message": result.status_message,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/generate")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    @api_app.post("/api/render")
    async def render_endpoint(request: Request):
        """Render a PlantUML snippet into an image for client previews."""
        try:
            data = await request.json()
            plantuml_code = data.get("plantuml_code") or data.get("code")
            if not plantuml_code:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required field: plantuml_code",
                    },
                )

            pil_image, status_msg, image_url = diagram_service.render_diagram_from_code(
                plantuml_code
            )
            image_base64 = diagram_service.diagram_image_to_base64(pil_image)
            return {
                "status": "ok",
                "image_base64": image_base64,
                "image_url": image_url,
                "message": status_msg,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/render")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    @api_app.post("/api/mindmap/generate")
    async def mindmap_generate_endpoint(request: Request):
        """Handle mindmap generation requests from the frontend."""
        try:
            data = await request.json()
            description = data.get("description")
            diagram_type = data.get("diagram_type") or "Mindmap"
            theme = data.get("theme")

            if not description:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required field: description",
                    },
                )

            result = mindmap_generate_fn(description, diagram_type, theme)
            if not result.plantuml_code:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": result.status_message or "Generation failed",
                    },
                )

            image_base64 = diagram_service.diagram_image_to_base64(result.pil_image)
            return {
                "status": "ok",
                "plantuml_code": result.plantuml_code,
                "image_base64": image_base64,
                "image_url": result.image_url,
                "message": result.status_message,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/mindmap/generate")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    @api_app.post("/api/mindmap/render")
    async def mindmap_render_endpoint(request: Request):
        """Render a PlantUML mindmap snippet into an image for client previews."""
        try:
            data = await request.json()
            plantuml_code = data.get("plantuml_code") or data.get("code")
            if not plantuml_code:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required field: plantuml_code",
                    },
                )

            pil_image, status_msg, image_url = diagram_service.render_diagram_from_code(
                plantuml_code
            )
            image_base64 = diagram_service.diagram_image_to_base64(pil_image)
            return {
                "status": "ok",
                "image_base64": image_base64,
                "image_url": image_url,
                "message": status_msg,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/mindmap/render")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    @api_app.post("/api/ui-mockup/generate")
    async def ui_mockup_generate_endpoint(request: Request):
        """Handle UI mockup (SALT) generation requests from the frontend."""
        try:
            data = await request.json()
            description = data.get("description")
            diagram_type = data.get("diagram_type") or "salt"
            theme = data.get("theme")

            if not description:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required field: description",
                    },
                )

            result = ui_mockup_generate_fn(description, diagram_type, theme)
            if not result.plantuml_code:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": result.status_message or "Generation failed",
                    },
                )

            image_base64 = diagram_service.diagram_image_to_base64(result.pil_image)
            return {
                "status": "ok",
                "plantuml_code": result.plantuml_code,
                "image_base64": image_base64,
                "image_url": result.image_url,
                "message": result.status_message,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/ui-mockup/generate")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    @api_app.post("/api/ui-mockup/render")
    async def ui_mockup_render_endpoint(request: Request):
        """Render a PlantUML SALT snippet into an image for client previews."""
        try:
            data = await request.json()
            plantuml_code = data.get("plantuml_code") or data.get("code")
            if not plantuml_code:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required field: plantuml_code",
                    },
                )

            pil_image, status_msg, image_url = diagram_service.render_diagram_from_code(
                plantuml_code
            )
            image_base64 = diagram_service.diagram_image_to_base64(pil_image)
            return {
                "status": "ok",
                "image_base64": image_base64,
                "image_url": image_url,
                "message": status_msg,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/ui-mockup/render")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    @api_app.post("/api/gantt/generate")
    async def gantt_generate_endpoint(request: Request):
        """Handle Gantt chart generation requests from the frontend."""
        try:
            data = await request.json()
            description = data.get("description")
            diagram_type = data.get("diagram_type") or "gantt"
            theme = data.get("theme")

            if not description:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required field: description",
                    },
                )

            result = gantt_generate_fn(description, diagram_type, theme)
            if not result.plantuml_code:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": result.status_message or "Generation failed",
                    },
                )

            image_base64 = diagram_service.diagram_image_to_base64(result.pil_image)
            return {
                "status": "ok",
                "plantuml_code": result.plantuml_code,
                "image_base64": image_base64,
                "image_url": result.image_url,
                "message": result.status_message,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/gantt/generate")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    @api_app.post("/api/gantt/render")
    async def gantt_render_endpoint(request: Request):
        """Render a PlantUML Gantt snippet into an image for client previews."""
        try:
            data = await request.json()
            plantuml_code = data.get("plantuml_code") or data.get("code")
            if not plantuml_code:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required field: plantuml_code",
                    },
                )

            pil_image, status_msg, image_url = diagram_service.render_diagram_from_code(
                plantuml_code
            )
            image_base64 = diagram_service.diagram_image_to_base64(pil_image)
            return {
                "status": "ok",
                "image_base64": image_base64,
                "image_url": image_url,
                "message": status_msg,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/gantt/render")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    @api_app.post("/api/erd/generate")
    async def erd_generate_endpoint(request: Request):
        """Handle ER diagram generation requests from the frontend."""
        try:
            data = await request.json()
            description = data.get("description")
            diagram_type = data.get("diagram_type") or "ERD"
            theme = data.get("theme")

            if not description:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required field: description",
                    },
                )

            result = erd_generate_fn(description, diagram_type, theme)
            if not result.plantuml_code:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": result.status_message or "Generation failed",
                    },
                )

            image_base64 = diagram_service.diagram_image_to_base64(result.pil_image)
            return {
                "status": "ok",
                "plantuml_code": result.plantuml_code,
                "image_base64": image_base64,
                "image_url": result.image_url,
                "message": result.status_message,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/erd/generate")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    @api_app.post("/api/erd/render")
    async def erd_render_endpoint(request: Request):
        """Render a PlantUML ER diagram snippet into an image for client previews."""
        try:
            data = await request.json()
            plantuml_code = data.get("plantuml_code") or data.get("code")
            if not plantuml_code:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Missing required field: plantuml_code",
                    },
                )

            pil_image, status_msg, image_url = diagram_service.render_diagram_from_code(
                plantuml_code
            )
            image_base64 = diagram_service.diagram_image_to_base64(pil_image)
            return {
                "status": "ok",
                "image_base64": image_base64,
                "image_url": image_url,
                "message": status_msg,
            }
        except Exception:
            logging.exception("Unhandled exception in /api/erd/render")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

    return api_app


__all__ = ["create_api_app"]
