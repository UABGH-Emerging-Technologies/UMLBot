"""Tests for the v01 FastAPI API layer."""

import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from unittest.mock import patch, MagicMock

os.environ.setdefault("azure_proxy_key", "test-key")

from app.server import app
from UMLBot.services.diagram_service import DiagramGenerationResult


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_GENERATE_BODY = {
    "description": "Test diagram",
    "diagram_type": "class",
    "openai_compatible_endpoint": "https://api.openai.com/v1",
    "openai_compatible_model": "gpt-4o-mini",
}

AUTH_HEADER = {"Authorization": "Bearer test-api-key"}


def _fake_result(plantuml_code: str = "@startuml\n@enduml", msg: str = "ok") -> DiagramGenerationResult:
    return DiagramGenerationResult(
        plantuml_code=plantuml_code,
        pil_image=Image.new("RGB", (10, 10), color="white"),
        status_message=msg,
        image_url="",
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Generate endpoints — auth required
# ---------------------------------------------------------------------------


@patch("UMLBot.services.diagram_service.DiagramService.generate_diagram_from_description")
def test_generate_uml_success(mock_gen: MagicMock, client: TestClient) -> None:
    mock_gen.return_value = _fake_result()
    resp = client.post("/v01/generate", json=VALID_GENERATE_BODY, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["plantuml_code"].startswith("@startuml")
    assert data["image_base64"] is not None


def test_generate_uml_missing_auth(client: TestClient) -> None:
    resp = client.post("/v01/generate", json=VALID_GENERATE_BODY)
    assert resp.status_code == 401


def test_generate_uml_missing_fields(client: TestClient) -> None:
    resp = client.post(
        "/v01/generate",
        json={"description": "test"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 422


@patch("UMLBot.services.diagram_service.DiagramService.generate_mindmap_from_description")
def test_generate_mindmap_success(mock_gen: MagicMock, client: TestClient) -> None:
    mock_gen.return_value = _fake_result("@startmindmap\n@endmindmap", "Mindmap ok")
    resp = client.post("/v01/mindmap/generate", json=VALID_GENERATE_BODY, headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["plantuml_code"].startswith("@startmindmap")


def test_generate_mindmap_missing_auth(client: TestClient) -> None:
    resp = client.post("/v01/mindmap/generate", json=VALID_GENERATE_BODY)
    assert resp.status_code == 401


@patch("UMLBot.services.diagram_service.DiagramService.generate_c4_from_description")
def test_generate_c4_success(mock_gen: MagicMock, client: TestClient) -> None:
    mock_gen.return_value = _fake_result("@startuml\n!include C4\n@enduml")
    resp = client.post("/v01/c4/generate", json=VALID_GENERATE_BODY, headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Render endpoints — no auth required
# ---------------------------------------------------------------------------


@patch("UMLBot.services.diagram_service.DiagramService.render_diagram_from_code")
def test_render_uml_success(mock_render: MagicMock, client: TestClient) -> None:
    mock_render.return_value = (
        Image.new("RGB", (10, 10), color="white"),
        "Rendered",
        "",
    )
    resp = client.post("/v01/render", json={"plantuml_code": "@startuml\n@enduml"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["image_base64"] is not None


def test_render_missing_code(client: TestClient) -> None:
    resp = client.post("/v01/render", json={})
    assert resp.status_code == 422


@patch("UMLBot.services.diagram_service.DiagramService.render_diagram_from_code")
def test_render_mindmap_no_auth_needed(mock_render: MagicMock, client: TestClient) -> None:
    mock_render.return_value = (
        Image.new("RGB", (10, 10), color="white"),
        "Rendered",
        "",
    )
    resp = client.post("/v01/mindmap/render", json={"plantuml_code": "@startmindmap\n@endmindmap"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Config endpoint
# ---------------------------------------------------------------------------


def test_config_endpoint(client: TestClient) -> None:
    resp = client.get("/v01/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "diagram_types" in data
    assert "default_diagram_type" in data
    assert "fallback_templates" in data
    assert len(data["diagram_types"]) > 0
