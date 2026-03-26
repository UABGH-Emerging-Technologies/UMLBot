"""Pydantic request/response models for the v01 API."""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class UMLDiagramType(str, Enum):
    """Supported UML diagram sub-types for the /generate endpoint."""

    use_case = "Use Case"
    class_ = "Class"
    activity = "Activity"
    component = "Component"
    deployment = "Deployment"
    state_machine = "State Machine"
    timing = "Timing"
    sequence = "Sequence"


class ResponseStatus(str, Enum):
    """Standard response status values."""

    ok = "ok"
    error = "error"


class UMLGenerateRequest(BaseModel):
    """Request body for the UML /generate endpoint."""

    description: str = Field(..., min_length=1)
    diagram_type: UMLDiagramType
    theme: Optional[str] = None
    openai_compatible_endpoint: str = Field(..., min_length=1)
    openai_compatible_model: str = Field(..., min_length=1)


class GenerateRequest(BaseModel):
    """Request body for non-UML generate endpoints (mindmap, gantt, etc.).

    The diagram type is implied by the endpoint and hardcoded server-side.
    """

    description: str = Field(..., min_length=1)
    theme: Optional[str] = None
    openai_compatible_endpoint: str = Field(..., min_length=1)
    openai_compatible_model: str = Field(..., min_length=1)


class RenderRequest(BaseModel):
    """Request body for render endpoints — no LLM fields needed."""

    plantuml_code: str = Field(..., min_length=1)


class DiagramResponse(BaseModel):
    """Response body for diagram generation endpoints."""

    status: ResponseStatus
    plantuml_code: str = ""
    image_base64: Optional[str] = None
    image_url: str = ""
    message: str = ""


class RenderResponse(BaseModel):
    """Response body for render endpoints."""

    status: ResponseStatus
    image_base64: Optional[str] = None
    image_url: str = ""
    message: str = ""


class ConfigResponse(BaseModel):
    """Response body for the config endpoint."""

    diagram_types: List[UMLDiagramType]
    default_diagram_type: UMLDiagramType
    fallback_templates: Dict[str, str]
