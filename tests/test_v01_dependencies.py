"""Tests for app.v01.dependencies — security scheme and service singleton."""

import os

os.environ.setdefault("azure_proxy_key", "test-key")

from fastapi.security import HTTPBearer

from app.v01.dependencies import get_diagram_service, security


class TestSecurity:
    """Tests for the HTTPBearer security instance."""

    def test_security_is_http_bearer(self) -> None:
        assert isinstance(security, HTTPBearer)


class TestGetDiagramService:
    """Tests for the diagram service singleton."""

    def test_returns_diagram_service(self) -> None:
        service = get_diagram_service()
        from UMLBot.services.diagram_service import DiagramService

        assert isinstance(service, DiagramService)

    def test_returns_same_instance(self) -> None:
        s1 = get_diagram_service()
        s2 = get_diagram_service()
        assert s1 is s2
