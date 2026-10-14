"""Tests for the v01 FastAPI API layer."""

import base64
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

os.environ.setdefault("azure_proxy_key", "test-key")

from app.server import app
from UMLBot.services.diagram_service import DiagramGenerationResult, _render_plantuml_jar


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UML_GENERATE_BODY = {
    "description": "Test diagram",
    "diagram_type": "Class",
    "openai_compatible_endpoint": "https://api.openai.com/v1",
    "openai_compatible_model": "gpt-4o-mini",
}

NON_UML_GENERATE_BODY = {
    "description": "Test diagram",
    "openai_compatible_endpoint": "https://api.openai.com/v1",
    "openai_compatible_model": "gpt-4o-mini",
}

AUTH_HEADER = {"Authorization": "Bearer test-api-key"}


def _fake_result(
    plantuml_code: str = "@startuml\n@enduml", msg: str = "ok"
) -> DiagramGenerationResult:
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
    resp = client.post("/v01/generate", json=UML_GENERATE_BODY, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["plantuml_code"].startswith("@startuml")
    assert data["image_base64"] is not None
    assert data["plan_warnings"] == []


def test_generate_uml_missing_auth(client: TestClient) -> None:
    resp = client.post("/v01/generate", json=UML_GENERATE_BODY)
    assert resp.status_code in (401, 403)


def test_generate_uml_missing_fields(client: TestClient) -> None:
    resp = client.post(
        "/v01/generate",
        json={"description": "test"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 422


def test_generate_uml_invalid_diagram_type(client: TestClient) -> None:
    body = {**UML_GENERATE_BODY, "diagram_type": "InvalidType"}
    resp = client.post("/v01/generate", json=body, headers=AUTH_HEADER)
    assert resp.status_code == 422


@patch("UMLBot.services.diagram_service.DiagramService.generate_mindmap_from_description")
def test_generate_mindmap_success(mock_gen: MagicMock, client: TestClient) -> None:
    mock_gen.return_value = _fake_result("@startmindmap\n@endmindmap", "Mindmap ok")
    resp = client.post("/v01/mindmap/generate", json=NON_UML_GENERATE_BODY, headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["plantuml_code"].startswith("@startmindmap")


def test_generate_mindmap_missing_auth(client: TestClient) -> None:
    resp = client.post("/v01/mindmap/generate", json=NON_UML_GENERATE_BODY)
    assert resp.status_code in (401, 403)


@patch("UMLBot.services.diagram_service.DiagramService.generate_c4_from_description")
def test_generate_c4_success(mock_gen: MagicMock, client: TestClient) -> None:
    mock_gen.return_value = _fake_result("@startuml\n!include C4\n@enduml")
    resp = client.post("/v01/c4/generate", json=NON_UML_GENERATE_BODY, headers=AUTH_HEADER)
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
        True,
        "@startuml\n@enduml",
        [],
    )
    resp = client.post("/v01/render", json={"plantuml_code": "@startuml\n@enduml"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["image_base64"] is not None
    assert data["plantuml_code"] == "@startuml\n@enduml"


def test_render_missing_code(client: TestClient) -> None:
    resp = client.post("/v01/render", json={})
    assert resp.status_code == 422


@patch("UMLBot.services.diagram_service.DiagramService.render_diagram_from_code")
def test_render_mindmap_no_auth_needed(mock_render: MagicMock, client: TestClient) -> None:
    mock_render.return_value = (
        Image.new("RGB", (10, 10), color="white"),
        "Rendered",
        "",
        True,
        "@startmindmap\n@endmindmap",
        [],
    )
    resp = client.post("/v01/mindmap/render", json={"plantuml_code": "@startmindmap\n@endmindmap"})
    assert resp.status_code == 200


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
@patch("UMLBot.services.diagram_service.GanttDraftHandler")
def test_gantt_render_sanitizes_and_never_calls_llm(
    mock_handler: MagicMock, mock_render: MagicMock, client: TestClient
) -> None:
    mock_render.return_value = (
        Image.new("RGB", (10, 10), color="white"),
        "Re-rendered",
        True,
    )
    resp = client.post(
        "/v01/gantt/render",
        json={"plantuml_code": "@startgantt\n[Task] lasts 1 quarter\n@endgantt"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "lasts 13 weeks" in data["plantuml_code"]
    assert data["plan_warnings"]
    mock_handler.assert_not_called()


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
    assert len(data["diagram_types"]) == 8
    assert data["default_diagram_type"] == "Use Case"


# ---------------------------------------------------------------------------
# SVG output tests
# ---------------------------------------------------------------------------


@patch("UMLBot.services.diagram_service.DiagramService.render_diagram_from_code")
def test_render_svg_success(mock_render: MagicMock, client: TestClient) -> None:
    mock_render.return_value = (
        "<svg xmlns='http://www.w3.org/2000/svg'><rect/></svg>",
        "Rendered",
        "",
        True,
        "@startuml\n@enduml",
        [],
    )
    resp = client.post(
        "/v01/render",
        json={"plantuml_code": "@startuml\n@enduml", "format": "svg"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["image_base64"] is None
    assert data["svg_base64"] is not None
    decoded = base64.b64decode(data["svg_base64"])
    assert decoded.startswith(b"<?xml") or decoded.startswith(b"<svg")


def test_render_invalid_format(client: TestClient) -> None:
    resp = client.post(
        "/v01/render",
        json={"plantuml_code": "@startuml\n@enduml", "format": "pdf"},
    )
    assert resp.status_code == 422


@patch("UMLBot.services.diagram_service.DiagramService.generate_diagram_from_description")
def test_generate_svg_success(mock_gen: MagicMock, client: TestClient) -> None:
    mock_gen.return_value = DiagramGenerationResult(
        plantuml_code="@startuml\n@enduml",
        pil_image=None,
        status_message="ok",
        image_url="",
        svg_text="<svg xmlns='http://www.w3.org/2000/svg'></svg>",
    )
    resp = client.post(
        "/v01/generate",
        json={**UML_GENERATE_BODY, "format": "svg"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["image_base64"] is None
    assert data["svg_base64"] is not None


@patch("UMLBot.services.diagram_service.DiagramService.render_diagram_from_code")
def test_render_default_format_is_png(mock_render: MagicMock, client: TestClient) -> None:
    mock_render.return_value = (
        Image.new("RGB", (10, 10), color="white"),
        "Rendered",
        "",
        True,
        "@startuml\n@enduml",
        [],
    )
    resp = client.post("/v01/render", json={"plantuml_code": "@startuml\n@enduml"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["image_base64"] is not None
    assert data["svg_base64"] is None


@patch("UMLBot.services.diagram_service.Image.open")
@patch("UMLBot.services.diagram_service.subprocess.run")
def test_render_plantuml_jar_svg(mock_run: MagicMock, mock_image_open: MagicMock) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout=b"<svg/>")
    svg_text, status_msg, render_ok = _render_plantuml_jar("test", "msg", fmt="svg")
    assert svg_text == "<svg/>"
    assert isinstance(svg_text, str)
    assert status_msg == "msg"
    assert render_ok is True
    argv = mock_run.call_args[0][0]
    assert "-tsvg" in argv
    mock_image_open.assert_not_called()


def test_gantt_render_runs_plan_check_once(client: TestClient) -> None:
    from UMLBot.services import diagram_service as ds

    calls: list[int] = []
    real_check = ds.check_gantt_plan

    def counting_check(*args: object, **kwargs: object) -> list[str]:
        calls.append(1)
        return real_check(*args, **kwargs)

    with (
        patch.object(ds, "check_gantt_plan", counting_check),
        patch.object(
            ds,
            "_render_plantuml_jar",
            lambda **_: (Image.new("RGB", (10, 10), "white"), "Rendered", True),
        ),
    ):
        resp = client.post(
            "/v01/gantt/render",
            json={
                "plantuml_code": "@startgantt\n[A task] starts D+0\n[A tsk] ends D+90\n@endgantt"
            },
        )

    assert resp.status_code == 200
    assert len(calls) == 1
    assert resp.json()["plan_warnings"], "the typo should still be reported"
