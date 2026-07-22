"""FastMCP server exposing UMLBot's PlantUML capabilities to MCP clients.

Two tools are provided:

* ``render_plantuml`` - render caller-authored PlantUML to a PNG. This is the light path:
  it imports only :mod:`UMLBot.rendering` (stdlib + ``requests``) and works even without the
  LLM stack / application config provisioned.
* ``generate_diagram`` - run UMLBot's full natural-language -> PlantUML pipeline (prompty
  template + retry + cleaning) and return the source plus a rendered PNG. The heavy chain
  (config/.env, langchain, ``aiweb_common``) is imported lazily inside the tool so it only
  loads when the tool is actually invoked.

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
        A list containing the generated PlantUML source (text) and the rendered PNG image.
    """
    # Lazy import: pulls in config/.env, langchain and aiweb_common only when invoked.
    from UMLBot.config.config import UMLBotConfig
    from UMLBot.services.diagram_service import generate_diagram_from_description

    valid_types = list(UMLBotConfig.DIAGRAM_TYPES)
    if diagram_type not in valid_types:
        raise ToolError(
            f"Unsupported diagram_type {diagram_type!r}. Choose one of: " + ", ".join(valid_types)
        )

    result = generate_diagram_from_description(description, diagram_type, theme)
    if not result.plantuml_code:
        # Empty code means the LLM step could not run (e.g. missing API key/base) or failed.
        raise ToolError(result.status_message or UMLBotConfig.API_KEY_MISSING_MSG)

    contents: list = [result.plantuml_code]
    if result.pil_image is not None:
        buf = io.BytesIO()
        result.pil_image.save(buf, format="PNG")
        contents.append(Image(data=buf.getvalue(), format="png"))
    else:
        # Code was generated but the render failed; report why instead of a broken image.
        contents.append(f"(diagram render unavailable: {result.status_message})")
    return contents


def main() -> None:
    """Console entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
