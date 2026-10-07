"""Unit tests for the pure PlantUML rendering helpers (no network required)."""

import base64
import zlib

import pytest
import requests

from UMLBot import rendering

SAMPLE = "@startuml\nAlice -> Bob: hello\n@enduml"


def _plantuml_decode(encoded: str) -> str:
    """Reverse of ``rendering._plantuml_encode`` (used to verify encoding correctness)."""
    reverse = str.maketrans(
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
    )
    compressed = base64.b64decode(encoded.translate(reverse))
    return zlib.decompress(compressed, -15).decode("utf-8")


class _FakeResponse:
    def __init__(self, content: bytes, content_type: str, status_ok: bool = True):
        self.content = content
        self.headers = {"Content-Type": content_type}
        self._status_ok = status_ok

    def raise_for_status(self) -> None:
        if not self._status_ok:
            raise requests.HTTPError("500 Server Error")


def test_encode_is_deterministic_and_reversible():
    """Encoding is stable and decodes back to the original PlantUML source."""
    first = rendering._plantuml_encode(SAMPLE)
    second = rendering._plantuml_encode(SAMPLE)
    assert first == second
    assert _plantuml_decode(first) == SAMPLE


def test_encode_uses_plantuml_alphabet():
    """Encoded output uses PlantUML's custom alphabet (plus base64 '=' padding)."""
    allowed = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_=")
    assert set(rendering._plantuml_encode(SAMPLE)) <= allowed


def test_build_url_with_encoded_template():
    """A template containing ``{encoded}`` is filled with the encoded payload."""
    url = rendering.build_plantuml_image_url(SAMPLE, "http://localhost:8080/png/{encoded}")
    encoded = rendering._plantuml_encode(SAMPLE)
    assert url == f"http://localhost:8080/png/{encoded}"


def test_build_url_with_base_url_template():
    """A bare base URL (no ``{encoded}``) has the payload appended after a slash."""
    url = rendering.build_plantuml_image_url(SAMPLE, "http://plantuml:8080/png/")
    encoded = rendering._plantuml_encode(SAMPLE)
    assert url == f"http://plantuml:8080/png/{encoded}"


def test_build_url_defaults_to_local_server():
    """Without an explicit template, the local default server is used."""
    url = rendering.build_plantuml_image_url(SAMPLE)
    assert url.startswith("http://localhost:8080/png/")


def test_render_png_bytes_success(monkeypatch):
    """A successful PNG response returns the raw image bytes."""
    png = b"\x89PNG\r\n\x1a\nfake"
    captured = {}

    def fake_get(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return _FakeResponse(png, "image/png")

    monkeypatch.setattr(rendering.requests, "get", fake_get)
    result = rendering.render_plantuml_png_bytes(SAMPLE)
    assert result == png
    assert captured["url"].startswith("http://localhost:8080/png/")


def test_render_png_bytes_rejects_non_png(monkeypatch):
    """A non-PNG content type raises RuntimeError (e.g. PlantUML error page)."""
    monkeypatch.setattr(
        rendering.requests,
        "get",
        lambda url, timeout: _FakeResponse(b"<html>error</html>", "text/html"),
    )
    with pytest.raises(RuntimeError, match="unexpected content-type"):
        rendering.render_plantuml_png_bytes(SAMPLE)


def test_render_png_bytes_propagates_http_error(monkeypatch):
    """An HTTP error status propagates as requests.HTTPError."""
    monkeypatch.setattr(
        rendering.requests,
        "get",
        lambda url, timeout: _FakeResponse(b"", "image/png", status_ok=False),
    )
    with pytest.raises(requests.HTTPError):
        rendering.render_plantuml_png_bytes(SAMPLE)
