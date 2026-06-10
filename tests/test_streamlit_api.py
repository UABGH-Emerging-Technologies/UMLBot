"""Tests for credential resolution in the streamlit testing UI API client."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_API_PATH = Path(__file__).parents[1] / "streamlit" / "Api.py"


def _load_api_module() -> ModuleType:
    """Load streamlit/Api.py by path (the installed streamlit package shadows the dir)."""
    spec = importlib.util.spec_from_file_location("umlbot_streamlit_api", _API_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestResolveCredential:
    """Tests for the _resolve_credential helper."""

    def test_prefers_manage_sensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        api = _load_api_module()
        monkeypatch.setattr(api, "manage_sensitive", lambda name: f"secret-{name}")
        monkeypatch.setenv("OPENAI_COMPATIBLE_KEY", "legacy-key")
        result = api._resolve_credential("azure_proxy_key", "OPENAI_COMPATIBLE_KEY")
        assert result == "secret-azure_proxy_key"

    def test_falls_back_to_legacy_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        api = _load_api_module()

        def _missing(name: str) -> str:
            raise KeyError(f"Secret {name} not found")

        monkeypatch.setattr(api, "manage_sensitive", _missing)
        monkeypatch.setenv("OPENAI_COMPATIBLE_KEY", "legacy-key")
        result = api._resolve_credential("azure_proxy_key", "OPENAI_COMPATIBLE_KEY")
        assert result == "legacy-key"

    def test_empty_when_nothing_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        api = _load_api_module()

        def _missing(name: str) -> str:
            raise KeyError(f"Secret {name} not found")

        monkeypatch.setattr(api, "manage_sensitive", _missing)
        monkeypatch.delenv("OPENAI_COMPATIBLE_KEY", raising=False)
        result = api._resolve_credential("azure_proxy_key", "OPENAI_COMPATIBLE_KEY")
        assert result == ""
