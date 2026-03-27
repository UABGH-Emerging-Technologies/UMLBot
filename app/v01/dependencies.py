"""Shared FastAPI dependencies for the v01 API."""

from fastapi.security import HTTPBearer

from UMLBot.services.diagram_service import DiagramService

_diagram_service: DiagramService | None = None

security: HTTPBearer = HTTPBearer()


def get_diagram_service() -> DiagramService:
    """Return a singleton DiagramService instance."""
    global _diagram_service  # noqa: PLW0603
    if _diagram_service is None:
        _diagram_service = DiagramService()
    return _diagram_service
