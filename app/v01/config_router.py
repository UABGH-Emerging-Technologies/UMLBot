"""Router for configuration endpoint."""

from fastapi import APIRouter

from app.v01.schemas import ConfigResponse, UMLDiagramType
from UMLBot.config.config import UMLBotConfig

router = APIRouter(tags=["config"])


@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Return supported diagram types and fallback templates."""
    return ConfigResponse(
        diagram_types=list(UMLDiagramType),
        default_diagram_type=UMLDiagramType(UMLBotConfig.DEFAULT_DIAGRAM_TYPE),
        fallback_templates={
            "uml": UMLBotConfig.FALLBACK_PLANTUML_TEMPLATE,
            "mindmap": UMLBotConfig.FALLBACK_MINDMAP_TEMPLATE,
            "ui_mockup": UMLBotConfig.FALLBACK_SALT_TEMPLATE,
            "gantt": UMLBotConfig.FALLBACK_GANTT_TEMPLATE,
            "erd": UMLBotConfig.FALLBACK_ERD_TEMPLATE,
            "json": UMLBotConfig.FALLBACK_JSON_TEMPLATE,
            "c4": UMLBotConfig.FALLBACK_C4_TEMPLATE,
        },
    )
