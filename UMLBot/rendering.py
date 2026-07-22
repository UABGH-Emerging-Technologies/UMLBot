"""Pure PlantUML rendering helpers.

This module intentionally depends only on the standard library and ``requests`` so it
can be imported without pulling in the LLM stack, application config, or ``aiweb_common``.
Everything here is side-effect free at import time, which lets a lightweight MCP server
render PlantUML without a fully provisioned environment.
"""

from __future__ import annotations

import base64
import zlib

import requests

# Default local PlantUML server (``plantuml/plantuml-server`` on port 8080). Callers may
# override via the ``server_url_template`` argument or a higher-level config value.
DEFAULT_PLANTUML_SERVER_URL_TEMPLATE = "http://localhost:8080/png/{encoded}"

# Timeout (seconds) for a single render request against the PlantUML server.
_RENDER_TIMEOUT_SECONDS = 10


def _plantuml_encode(text: str) -> str:
    """Encode PlantUML source text for the PlantUML server URL format.

    Uses raw DEFLATE (``wbits=-15``) followed by base64 with PlantUML's custom alphabet.
    """
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(text.encode("utf-8")) + compressor.flush()
    b64 = base64.b64encode(compressed).decode("utf-8")
    translation = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_",
    )
    return b64.translate(translation)


def _build_plantuml_url(template: str, encoded: str) -> str:
    """Build a render URL, supporting both ``{encoded}`` templates and bare base URLs."""
    if "{encoded}" in template:
        return template.format(encoded=encoded)
    base = template.rstrip("/")
    return f"{base}/{encoded}"


def build_plantuml_image_url(
    plantuml_code: str,
    server_url_template: str = DEFAULT_PLANTUML_SERVER_URL_TEMPLATE,
) -> str:
    """Build a PlantUML render URL for the given diagram code."""
    encoded = _plantuml_encode(plantuml_code)
    return _build_plantuml_url(server_url_template, encoded)


def render_plantuml_png_bytes(
    plantuml_code: str,
    server_url_template: str = DEFAULT_PLANTUML_SERVER_URL_TEMPLATE,
) -> bytes:
    """Render PlantUML source to PNG bytes via a PlantUML server.

    Args:
        plantuml_code: A full ``@startuml ... @enduml`` document.
        server_url_template: URL template (with ``{encoded}``) or base URL of the server.

    Returns:
        The raw PNG bytes returned by the PlantUML server.

    Raises:
        requests.RequestException: If the HTTP request fails or returns an error status.
        RuntimeError: If the server responds with a non-PNG content type.
    """
    image_url = build_plantuml_image_url(plantuml_code, server_url_template)
    resp = requests.get(image_url, timeout=_RENDER_TIMEOUT_SECONDS)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    if not content_type.startswith("image/png"):
        raise RuntimeError(
            f"PlantUML server returned unexpected content-type {content_type!r}. "
            "Check that the PlantUML source is valid."
        )
    return resp.content
