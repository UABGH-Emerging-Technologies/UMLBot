from __future__ import annotations

import logging

from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from Design_Drafter.services import (
    DiagramGenerationResult,
    diagram_image_to_base64,
    generate_diagram_from_description,
)


def create_api_app(
    generate_fn: Callable[[str, str, str | None], "DiagramGenerationResult"] | None = None,
) -> FastAPI:
    """Builds the FastAPI application exposing JSON endpoints for diagram generation."""
    if generate_fn is None:
        generate_fn = generate_diagram_from_description

    api_app = FastAPI(title="Design Drafter HTTP API")
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: tighten in production
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
    )

    @api_app.post("/api/generate")
    async def generate_endpoint(request: Request):
        """
        HTTP POST endpoint for diagram generation used by the Next.js frontend.
        """
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
        except Exception as exc:
            logging.exception("Unhandled exception in /api/generate")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"Exception: {exc}"},
            )

    return api_app


__all__ = ["create_api_app"]
