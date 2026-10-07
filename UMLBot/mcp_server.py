"""FastMCP server exposing UMLBot's PlantUML capabilities to MCP clients.

Two tools are provided:

* ``render_plantuml`` - render caller-authored PlantUML to a PNG. This is the light path:
  it imports only :mod:`UMLBot.rendering` (stdlib + ``requests``) and works even without the
  LLM stack / application config provisioned.
* ``generate_diagram`` - run UMLBot's full natural-language -> PlantUML pipeline (prompty
  template + retry + cleaning) and return the source plus a rendered PNG. The heavy chain
  (config/.env, langchain, ``aiweb_common``) is imported lazily inside the tool so it only
  loads when the tool is actually invoked. LLM credentials are resolved at call time from the
  shared secret locations (``manage_sensitive``) with ``OPENAI_COMPATIBLE_*`` env fallbacks.

Run as a stdio server: ``python -m UMLBot.mcp_server`` (or the ``umlbot-mcp`` console script).
"""

from __future__ import annotations

import io
import os

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from UMLBot.rendering import (
    DEFAULT_PLANTUML_SERVER_URL_TEMPLATE,
    render_plantuml_png_bytes,
)

mcp = FastMCP("umlbot-render")


def _server_url_template() -> str:
    """Resolve the PlantUML server URL template from the environment (falling back to local)."""
    return os.getenv(
        "UMLBOT_PLANTUML_SERVER_URL_TEMPLATE",
        DEFAULT_PLANTUML_SERVER_URL_TEMPLATE,
    )


def _resolve_llm_credentials() -> tuple[str, str, str]:
    """Resolve LLM credentials, mirroring the frontend's ``_resolve_credential`` precedence.

    Each secret is read from :func:`aiweb_common.WorkflowHandler.manage_sensitive` first (which
    checks ``/run/secrets``, the devcontainer secrets directory, the team secrets mount, then a
    matching env var) and falls back to the legacy ``OPENAI_COMPATIBLE_*`` environment variables.
    The model defaults to ``"o3"``.

    ``aiweb_common`` is imported lazily inside this helper so the module stays importable without
    the heavy LLM/config stack.

    Returns:
        A ``(endpoint, key, model)`` tuple.
    """
    from aiweb_common.WorkflowHandler import manage_sensitive

    def _resolve(secret_name: str, legacy_env_var: str) -> str:
        try:
            return manage_sensitive(secret_name)
        except KeyError:
            return os.environ.get(legacy_env_var, "")

    endpoint = _resolve("azure_proxy_endpoint", "OPENAI_COMPATIBLE_ENDPOINT")
    key = _resolve("azure_proxy_key", "OPENAI_COMPATIBLE_KEY")
    model = os.environ.get("OPENAI_COMPATIBLE_MODEL", "o3")
    return endpoint, key, model


@mcp.tool
def render_plantuml(code: str) -> Image:
    """Render PlantUML source to a PNG image and return it inline.

    Args:
        code: A complete PlantUML document, i.e. ``@startuml`` ... ``@enduml``.

    Returns:
        The rendered diagram as a PNG image.
    """
    try:
        png_bytes = render_plantuml_png_bytes(code, _server_url_template())
    except Exception as exc:  # noqa: BLE001 - surface any failure as a tool error
        raise ToolError(
            f"PlantUML rendering failed: {exc}. Ensure a PlantUML server is reachable "
            f"at {_server_url_template()!r} (e.g. run "
            "`docker run -d -p 8080:8080 plantuml/plantuml-server`)."
        ) from exc
    return Image(data=png_bytes, format="png")


@mcp.tool
def generate_diagram(
    description: str,
    diagram_type: str,
    theme: str | None = None,
):
    """Generate a PlantUML diagram from a natural-language description via UMLBot's LLM.

    Prefer authoring PlantUML yourself and calling ``render_plantuml`` when you already know
    the design; use this tool for a one-shot draft from a description.

    Args:
        description: Natural-language description of the system/behavior to diagram.
        diagram_type: One of UMLBot's supported types (e.g. "Sequence", "Class", "Use Case",
            "Activity", "Component", "Deployment", "State Machine", "Timing").
        theme: Optional PlantUML theme name.

    Returns:
        A list containing the generated PlantUML source (text) and the rendered PNG image. If
        the local PlantUML JAR is unavailable, the image is produced via the PlantUML HTTP server;
        if that also fails, the second element is a message explaining why rendering was unavailable.
    """
    # Lazy imports: pull in config/.env, the LLM stack and the diagram service only when invoked.
    from UMLBot.config.config import UMLBotConfig
    from UMLBot.services.diagram_service import DiagramService

    valid_types = list(UMLBotConfig.DIAGRAM_TYPES)
    if diagram_type not in valid_types:
        raise ToolError(
            f"Unsupported diagram_type {diagram_type!r}. Choose one of: " + ", ".join(valid_types)
        )

    endpoint, key, model = _resolve_llm_credentials()
    if not key or not endpoint:
        raise ToolError(
            "Missing LLM credentials. Provide the 'azure_proxy_key' and 'azure_proxy_endpoint' "
            "secrets (or set the OPENAI_COMPATIBLE_KEY / OPENAI_COMPATIBLE_ENDPOINT environment "
            "variables)."
        )

    result = DiagramService().generate_diagram_from_description(
        description,
        diagram_type,
        theme,
        openai_compatible_endpoint=endpoint,
        openai_compatible_key=key,
        openai_compatible_model=model,
    )
    if not result.plantuml_code:
        # Empty code means the LLM step could not run (e.g. missing API key/base) or failed.
        raise ToolError(result.status_message or "Diagram generation failed")

    contents: list = [result.plantuml_code]
    if result.pil_image is not None:
        buf = io.BytesIO()
        result.pil_image.save(buf, format="PNG")
        contents.append(Image(data=buf.getvalue(), format="png"))
    else:
        # The local JAR render failed (e.g. Java not installed); fall back to the PlantUML HTTP
        # server used by ``render_plantuml`` before reporting the failure as text.
        try:
            png_bytes = render_plantuml_png_bytes(result.plantuml_code, _server_url_template())
            contents.append(Image(data=png_bytes, format="png"))
        except Exception as exc:  # noqa: BLE001 - surface any render failure as text
            reason = str(exc) or result.status_message or "unknown error"
            contents.append(f"(diagram render unavailable: {reason})")
    return contents


def main() -> None:
    """Console entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
