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
    diagram_image_to_base64,
    generate_diagram_from_description,
    render_diagram_from_code,
)


def create_api_app(
    generate_fn: Callable[[str, str, str | None], "DiagramGenerationResult"] | None = None,
) -> FastAPI:
    """Builds the FastAPI application exposing JSON endpoints for diagram generation."""
    if generate_fn is None:
        generate_fn = generate_diagram_from_description

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

            image_base64 = diagram_image_to_base64(result.pil_image)
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

            pil_image, status_msg, image_url = render_diagram_from_code(plantuml_code)
            image_base64 = diagram_image_to_base64(pil_image)
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

    return api_app


__all__ = ["create_api_app"]
