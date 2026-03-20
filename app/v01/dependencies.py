"""Shared FastAPI dependencies for the v01 API."""

from fastapi import Request
from fastapi.exceptions import HTTPException

from UMLBot.services.diagram_service import DiagramService

_diagram_service: DiagramService | None = None


def get_bearer_token(request: Request) -> str:
    """Extract the bearer token from the Authorization header.

    Raises:
        HTTPException: 401 if the header is missing or malformed.
    """
    auth_header: str | None = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Bearer <api_key>",
        )
    return auth_header[len("Bearer "):]


def get_diagram_service() -> DiagramService:
    """Return a singleton DiagramService instance."""
    global _diagram_service  # noqa: PLW0603
    if _diagram_service is None:
        _diagram_service = DiagramService()
    return _diagram_service
