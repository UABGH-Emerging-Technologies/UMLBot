"""Unit tests for the UMLBot MCP server tools.

These tests never touch the network, an LLM, or a local Java/PlantUML JAR: the
diagram service, credential resolver and HTTP renderer are all stubbed with
monkeypatch.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image
from PIL import Image as PILImage

from UMLBot import mcp_server
from UMLBot.services import diagram_service
from UMLBot.services.diagram_service import DiagramGenerationResult

_REPO_ROOT = Path(__file__).parents[1]


def _tool_fn(tool):
    """Return the underlying callable from a fastmcp tool (version-tolerant)."""
    return getattr(tool, "fn", tool)


generate_diagram = _tool_fn(mcp_server.generate_diagram)


def _png_bytes() -> bytes:
    """A tiny valid PNG produced in-memory (no disk, no network)."""
    buf = io.BytesIO()
    PILImage.new("RGB", (4, 4), color="white").save(buf, format="PNG")
    return buf.getvalue()


def _install_fake_service(monkeypatch: pytest.MonkeyPatch, result):
    """Patch ``diagram_service.DiagramService`` with a recording stub.

    Returns the list of constructed stub instances so callers can assert whether the
    service was constructed and inspect the arguments it received.
    """
    created: list = []

    class _FakeDiagramService:
        def __init__(self) -> None:
            created.append(self)

        def generate_diagram_from_description(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            return result

    monkeypatch.setattr(diagram_service, "DiagramService", _FakeDiagramService)
    return created


def _result(
    plantuml_code: str = "@startuml\nAlice -> Bob: hi\n@enduml",
    pil_image: PILImage.Image | None = None,
    status_message: str = "ok",
) -> DiagramGenerationResult:
    return DiagramGenerationResult(
        plantuml_code=plantuml_code,
        pil_image=pil_image,
        status_message=status_message,
        image_url="",
    )


# --- a. missing credentials -------------------------------------------------


@pytest.mark.parametrize(
    ("endpoint", "key"),
    [
        ("", ""),
        ("http://endpoint", ""),
        ("", "key"),
    ],
)
def test_missing_credentials_raises_before_service(monkeypatch, endpoint, key):
    """A missing key/endpoint raises ToolError and never constructs DiagramService."""
    created = _install_fake_service(monkeypatch, _result())
    monkeypatch.setattr(mcp_server, "_resolve_llm_credentials", lambda: (endpoint, key, "o3"))

    with pytest.raises(ToolError, match="credentials"):
        generate_diagram("A system", "Class")

    assert created == []


# --- b. invalid diagram type ------------------------------------------------


def test_invalid_diagram_type_raises_before_credentials(monkeypatch):
    """An unsupported diagram_type raises ToolError before any credential/service work."""
    created = _install_fake_service(monkeypatch, _result())
    monkeypatch.setattr(
        mcp_server,
        "_resolve_llm_credentials",
        lambda: pytest.fail("credentials should not be resolved for an invalid diagram type"),
    )

    with pytest.raises(ToolError, match="Unsupported diagram_type"):
        generate_diagram("A system", "NotARealType")

    assert created == []


# --- c. success with a PIL image already present -----------------------------


def test_success_with_pil_image_passes_credentials(monkeypatch):
    """A generated image is returned and the resolved creds reach the service call."""
    pil = PILImage.new("RGB", (8, 8), color="red")
    code = "@startuml\nA -> B: go\n@enduml"
    created = _install_fake_service(monkeypatch, _result(plantuml_code=code, pil_image=pil))
    monkeypatch.setattr(
        mcp_server,
        "_resolve_llm_credentials",
        lambda: ("http://endpoint", "secret-key", "custom-model"),
    )

    out = generate_diagram("A system", "Class", theme="plain")

    assert out[0] == code
    assert isinstance(out[1], Image)
    assert len(created) == 1
    assert created[0].args == ("A system", "Class", "plain")
    assert created[0].kwargs == {
        "openai_compatible_endpoint": "http://endpoint",
        "openai_compatible_key": "secret-key",
        "openai_compatible_model": "custom-model",
    }


# --- d. no PIL image -> HTTP fallback succeeds ------------------------------


def test_pil_image_none_falls_back_to_http_render(monkeypatch):
    """When the JAR render yields no image, the HTTP renderer's bytes are returned."""
    png = _png_bytes()
    code = "@startuml\nA -> B\n@enduml"
    _install_fake_service(monkeypatch, _result(plantuml_code=code, pil_image=None))
    monkeypatch.setattr(mcp_server, "_resolve_llm_credentials", lambda: ("ep", "key", "o3"))

    calls: list = []

    def fake_render(plantuml_code, server_url_template):
        calls.append((plantuml_code, server_url_template))
        return png

    monkeypatch.setattr(mcp_server, "render_plantuml_png_bytes", fake_render)

    out = generate_diagram("A system", "Class")

    assert out[0] == code
    assert isinstance(out[1], Image)
    assert out[1].data == png
    assert calls == [(code, mcp_server._server_url_template())]


# --- e. no PIL image -> HTTP fallback fails ---------------------------------


def test_pil_image_none_http_fallback_failure_reports_text(monkeypatch):
    """When both render paths fail, the second element is an explanatory string."""
    _install_fake_service(
        monkeypatch,
        _result(plantuml_code="@startuml\n@enduml", pil_image=None, status_message="jar failed"),
    )
    monkeypatch.setattr(mcp_server, "_resolve_llm_credentials", lambda: ("ep", "key", "o3"))

    def boom(plantuml_code, server_url_template):
        raise RuntimeError("no PlantUML server reachable")

    monkeypatch.setattr(mcp_server, "render_plantuml_png_bytes", boom)

    out = generate_diagram("A system", "Class")

    assert isinstance(out[1], str)
    assert "diagram render unavailable" in out[1]
    assert "no PlantUML server reachable" in out[1]


# --- f. empty PlantUML code -------------------------------------------------


def test_empty_plantuml_code_raises(monkeypatch):
    """An empty plantuml_code surfaces the service status message as ToolError."""
    _install_fake_service(monkeypatch, _result(plantuml_code="", status_message="LLM failed"))
    monkeypatch.setattr(mcp_server, "_resolve_llm_credentials", lambda: ("ep", "key", "o3"))

    with pytest.raises(ToolError, match="LLM failed"):
        generate_diagram("A system", "Class")


# --- g. credential resolution ----------------------------------------------


def test_resolve_llm_credentials_falls_back_to_env(monkeypatch):
    """KeyError from manage_sensitive falls back to OPENAI_COMPATIBLE_* env vars."""
    import aiweb_common.WorkflowHandler as workflow_handler

    def _missing(name):
        raise KeyError(name)

    monkeypatch.setattr(workflow_handler, "manage_sensitive", _missing)
    monkeypatch.setenv("OPENAI_COMPATIBLE_KEY", "env-key")
    monkeypatch.setenv("OPENAI_COMPATIBLE_ENDPOINT", "http://env-endpoint")
    monkeypatch.delenv("OPENAI_COMPATIBLE_MODEL", raising=False)

    assert mcp_server._resolve_llm_credentials() == ("http://env-endpoint", "env-key", "o3")


def test_resolve_llm_credentials_prefers_manage_sensitive(monkeypatch):
    """manage_sensitive values win over the env fallbacks; model comes from the env."""
    import aiweb_common.WorkflowHandler as workflow_handler

    secrets = {
        "azure_proxy_key": "secret-key",
        "azure_proxy_endpoint": "http://secret-endpoint",
    }

    monkeypatch.setattr(workflow_handler, "manage_sensitive", lambda name: secrets[name])
    monkeypatch.setenv("OPENAI_COMPATIBLE_KEY", "env-key")
    monkeypatch.setenv("OPENAI_COMPATIBLE_ENDPOINT", "http://env-endpoint")
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL", "custom-model")

    assert mcp_server._resolve_llm_credentials() == (
        "http://secret-endpoint",
        "secret-key",
        "custom-model",
    )


# --- h. import isolation ----------------------------------------------------


def test_import_does_not_pull_aiweb_common():
    """Importing the module must not import aiweb_common (checked in a subprocess)."""
    code = "import sys, UMLBot.mcp_server; assert 'aiweb_common' not in sys.modules"
    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        cwd=str(_REPO_ROOT),
    )
