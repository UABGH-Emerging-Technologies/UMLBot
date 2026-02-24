import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

os.environ.setdefault("azure_proxy_key", "test-key")

from UMLBot.api_server import create_api_app
from UMLBot.services.diagram_service import DiagramGenerationResult


@pytest.fixture
def client():
    def fake_generate(description, diagram_type, theme=None):
        image = Image.new("RGB", (10, 10), color="white")
        return DiagramGenerationResult(
            plantuml_code="@startuml\n@enduml",
            pil_image=image,
            status_message="Diagram generated successfully",
            image_url="http://example.com/uml.png",
        )

    def fake_mindmap_generate(description, diagram_type, theme=None):
        image = Image.new("RGB", (10, 10), color="white")
        return DiagramGenerationResult(
            plantuml_code="@startmindmap\n@endmindmap",
            pil_image=image,
            status_message="Mindmap generated successfully",
            image_url="http://example.com/mindmap.png",
        )

    app = create_api_app(generate_fn=fake_generate, mindmap_generate_fn=fake_mindmap_generate)
    return TestClient(app)


def test_generate_diagram_success(client):
    resp = client.post(
        "/api/generate",
        json={"diagram_type": "class", "description": "Test diagram", "theme": "default"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["plantuml_code"].startswith("@startuml")
    assert data["image_url"] == "http://example.com/uml.png"
    assert data["image_base64"] is not None


def test_generate_diagram_missing_fields(client):
    resp = client.post("/api/generate", json={"diagram_type": "class"})
    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "error"


def test_generate_mindmap_success(client):
    resp = client.post(
        "/api/mindmap/generate",
        json={"diagram_type": "Mindmap", "description": "Test mindmap", "theme": "default"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["plantuml_code"].startswith("@startmindmap")
    assert data["image_url"] == "http://example.com/mindmap.png"
    assert data["image_base64"] is not None


def test_generate_mindmap_missing_fields(client):
    resp = client.post("/api/mindmap/generate", json={})
    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "error"


def test_render_mindmap_missing_fields(client):
    resp = client.post("/api/mindmap/render", json={})
    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "error"
