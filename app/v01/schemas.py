"""Pydantic request/response models for the v01 API."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DiagramGenerateRequest(BaseModel):
    """Request body for diagram generation endpoints."""

    description: str = Field(..., min_length=1)
    diagram_type: str = Field(..., min_length=1)
    theme: Optional[str] = None
    openai_compatible_endpoint: str = Field(..., min_length=1)
    openai_compatible_model: str = Field(..., min_length=1)


class RenderRequest(BaseModel):
    """Request body for render endpoints — no LLM fields needed."""

    plantuml_code: str = Field(..., min_length=1)


class DiagramResponse(BaseModel):
    """Response body for diagram generation endpoints."""

    status: str
    plantuml_code: str = ""
    image_base64: Optional[str] = None
    image_url: str = ""
    message: str = ""


class RenderResponse(BaseModel):
    """Response body for render endpoints."""

    status: str
    image_base64: Optional[str] = None
    image_url: str = ""
    message: str = ""


class ConfigResponse(BaseModel):
    """Response body for the config endpoint."""

    diagram_types: List[str]
    default_diagram_type: str
    fallback_templates: Dict[str, str]
