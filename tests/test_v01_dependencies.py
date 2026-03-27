"""Tests for app.v01.dependencies — bearer token extraction and service singleton."""

import os

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock

os.environ.setdefault("azure_proxy_key", "test-key")

from app.v01.dependencies import get_bearer_token, get_diagram_service


class TestGetBearerToken:
    """Tests for bearer token extraction."""

    def _make_request(self, auth_header: str | None = None) -> MagicMock:
        request = MagicMock()
        headers = {}
        if auth_header is not None:
            headers["Authorization"] = auth_header
        request.headers = headers
        return request

    def test_valid_bearer_token(self) -> None:
        request = self._make_request("Bearer sk-abc123")
        assert get_bearer_token(request) == "sk-abc123"

    def test_missing_header_raises_401(self) -> None:
        request = self._make_request(None)
        with pytest.raises(HTTPException) as exc_info:
            get_bearer_token(request)
        assert exc_info.value.status_code == 401

    def test_malformed_header_raises_401(self) -> None:
        request = self._make_request("Basic dXNlcjpwYXNz")
        with pytest.raises(HTTPException) as exc_info:
            get_bearer_token(request)
        assert exc_info.value.status_code == 401

    def test_empty_bearer_raises_401(self) -> None:
        request = self._make_request("Token abc")
        with pytest.raises(HTTPException) as exc_info:
            get_bearer_token(request)
        assert exc_info.value.status_code == 401


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
