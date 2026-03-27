"""Tests for streamlit_app helper functions and API client."""

import os

os.environ.setdefault("azure_proxy_key", "test-key")

from unittest.mock import MagicMock, patch

import pytest
import requests

from streamlit_app import (
    ENDPOINT_MAP,
    MAX_HISTORY_MESSAGES,
    MODE_LABELS,
    _build_prompt_description,
    _state_key,
    _summarize_chat_history,
    api_generate,
    api_render,
)

# ---------------------------------------------------------------------------
# _state_key
# ---------------------------------------------------------------------------


class TestStateKey:
    """Tests for the _state_key helper."""

    def test_basic_key(self) -> None:
        assert _state_key("uml", "chat_history") == "chat_history_uml"

    def test_mindmap_key(self) -> None:
        assert _state_key("mindmap", "plantuml_code") == "plantuml_code_mindmap"

    def test_c4_key(self) -> None:
        assert _state_key("c4", "image_base64") == "image_base64_c4"

    def test_ui_mockup_key(self) -> None:
        assert _state_key("ui_mockup", "error_message") == "error_message_ui_mockup"


# ---------------------------------------------------------------------------
# _summarize_chat_history
# ---------------------------------------------------------------------------


class TestSummarizeChatHistory:
    """Tests for chat history summarization."""

    def test_empty_history(self) -> None:
        assert _summarize_chat_history([]) == ""

    def test_single_message(self) -> None:
        history = [{"role": "user", "content": "hello"}]
        result = _summarize_chat_history(history)
        assert result == "user: hello"

    def test_truncates_to_max(self) -> None:
        history = [{"role": "user", "content": f"msg {i}"} for i in range(20)]
        result = _summarize_chat_history(history)
        lines = result.strip().split("\n")
        assert len(lines) == MAX_HISTORY_MESSAGES

    def test_preserves_roles(self) -> None:
        history = [
            {"role": "user", "content": "request"},
            {"role": "assistant", "content": "response"},
        ]
        result = _summarize_chat_history(history)
        assert "user: request" in result
        assert "assistant: response" in result


# ---------------------------------------------------------------------------
# _build_prompt_description
# ---------------------------------------------------------------------------


class TestBuildPromptDescription:
    """Tests for prompt description composition."""

    def test_uml_fence_markers(self) -> None:
        result = _build_prompt_description(
            user_request="Create a class diagram",
            current_code="",
            chat_history=[],
            mode="uml",
            diagram_type="Class",
        )
        assert "@startuml and @enduml" in result
        assert "UML" in result

    def test_mindmap_fence_markers(self) -> None:
        result = _build_prompt_description(
            user_request="Create a mindmap",
            current_code="",
            chat_history=[],
            mode="mindmap",
            diagram_type="Mindmap",
        )
        assert "@startmindmap and @endmindmap" in result

    def test_salt_fence_markers(self) -> None:
        result = _build_prompt_description(
            user_request="Create a login form",
            current_code="",
            chat_history=[],
            mode="ui_mockup",
            diagram_type="salt",
        )
        assert "@startsalt and @endsalt" in result

    def test_gantt_fence_markers(self) -> None:
        result = _build_prompt_description(
            user_request="Create a gantt chart",
            current_code="",
            chat_history=[],
            mode="gantt",
            diagram_type="gantt",
        )
        assert "@startgantt and @endgantt" in result

    def test_json_fence_markers(self) -> None:
        result = _build_prompt_description(
            user_request="Create a json diagram",
            current_code="",
            chat_history=[],
            mode="json",
            diagram_type="json",
        )
        assert "@startjson and @endjson" in result

    def test_c4_fence_markers(self) -> None:
        result = _build_prompt_description(
            user_request="Create a C4 diagram",
            current_code="",
            chat_history=[],
            mode="c4",
            diagram_type="C4",
        )
        assert "C4-PlantUML includes" in result

    def test_includes_existing_code(self) -> None:
        code = "@startuml\nactor User\n@enduml"
        result = _build_prompt_description(
            user_request="Add a class",
            current_code=code,
            chat_history=[],
            mode="uml",
            diagram_type="Class",
        )
        assert "reuse and refine" in result
        assert code in result

    def test_no_code_creates_fresh(self) -> None:
        result = _build_prompt_description(
            user_request="Create a class diagram",
            current_code="",
            chat_history=[],
            mode="uml",
            diagram_type="Class",
        )
        assert "No UML diagram has been created yet" in result

    def test_includes_chat_summary(self) -> None:
        history = [{"role": "user", "content": "previous request"}]
        result = _build_prompt_description(
            user_request="followup",
            current_code="",
            chat_history=history,
            mode="uml",
            diagram_type="Class",
        )
        assert "Recent conversation" in result
        assert "previous request" in result

    def test_includes_user_request(self) -> None:
        result = _build_prompt_description(
            user_request="Draw a sequence diagram for login",
            current_code="",
            chat_history=[],
            mode="uml",
            diagram_type="Sequence",
        )
        assert "Draw a sequence diagram for login" in result


# ---------------------------------------------------------------------------
# ENDPOINT_MAP completeness
# ---------------------------------------------------------------------------


class TestEndpointMap:
    """Tests for ENDPOINT_MAP configuration."""

    def test_all_modes_present(self) -> None:
        for mode_key in MODE_LABELS:
            assert mode_key in ENDPOINT_MAP, f"Missing endpoint mapping for mode: {mode_key}"

    def test_each_entry_has_three_elements(self) -> None:
        for mode_key, entry in ENDPOINT_MAP.items():
            assert len(entry) == 3, f"ENDPOINT_MAP[{mode_key}] should have 3 elements"

    def test_generate_paths_start_with_v01(self) -> None:
        for mode_key, (gen_path, _, _) in ENDPOINT_MAP.items():
            assert gen_path.startswith(
                "/v01/"
            ), f"Generate path for {mode_key} should start with /v01/"

    def test_render_paths_start_with_v01(self) -> None:
        for mode_key, (_, render_path, _) in ENDPOINT_MAP.items():
            assert render_path.startswith(
                "/v01/"
            ), f"Render path for {mode_key} should start with /v01/"


# ---------------------------------------------------------------------------
# api_generate
# ---------------------------------------------------------------------------


class TestApiGenerate:
    """Tests for the api_generate function."""

    @patch("streamlit_app.requests.post")
    def test_success(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "ok",
            "plantuml_code": "@startuml\n@enduml",
            "image_base64": "abc123",
            "image_url": "",
            "message": "Generated",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = api_generate(
            "http://localhost:8000",
            "uml",
            "test desc",
            "Class",
            openai_compatible_endpoint="https://api.openai.com/v1",
            openai_compatible_model="gpt-4o-mini",
            api_key="sk-test",
        )

        assert result["status"] == "ok"
        assert result["plantuml_code"] == "@startuml\n@enduml"
        assert result["image_base64"] == "abc123"

    @patch("streamlit_app.requests.post")
    def test_includes_credentials_in_payload(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        api_generate(
            "http://localhost:8000",
            "uml",
            "test",
            "Class",
            openai_compatible_endpoint="https://api.example.com/v1",
            openai_compatible_model="gpt-4",
            api_key="sk-test123",
        )

        called_payload = mock_post.call_args[1]["json"]
        assert called_payload["openai_compatible_endpoint"] == "https://api.example.com/v1"
        assert called_payload["openai_compatible_model"] == "gpt-4"

        called_headers = mock_post.call_args[1]["headers"]
        assert called_headers["Authorization"] == "Bearer sk-test123"

    @patch("streamlit_app.requests.post")
    def test_timeout(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.Timeout()

        result = api_generate("http://localhost:8000", "uml", "test", "Class")

        assert result["status"] == "error"
        assert "timed out" in result["message"]

    @patch("streamlit_app.requests.post")
    def test_connection_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError()

        result = api_generate("http://localhost:8000", "mindmap", "test", "Mindmap")

        assert result["status"] == "error"
        assert "Cannot connect" in result["message"]

    @patch("streamlit_app.requests.post")
    def test_http_error(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"message": "Internal server error"}
        http_error = requests.exceptions.HTTPError(response=mock_resp)
        mock_post.side_effect = http_error

        result = api_generate("http://localhost:8000", "uml", "test", "Class")

        assert result["status"] == "error"

    @patch("streamlit_app.requests.post")
    def test_uses_correct_endpoint(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        api_generate("http://localhost:8000", "gantt", "test", "gantt")

        called_url = mock_post.call_args[0][0]
        assert "/v01/gantt/generate" in called_url

    @patch("streamlit_app.requests.post")
    def test_includes_theme_when_provided(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        api_generate("http://localhost:8000", "uml", "test", "Class", theme="cerulean")

        called_payload = mock_post.call_args[1]["json"]
        assert called_payload["theme"] == "cerulean"


# ---------------------------------------------------------------------------
# api_render
# ---------------------------------------------------------------------------


class TestApiRender:
    """Tests for the api_render function."""

    @patch("streamlit_app.requests.post")
    def test_success(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "ok",
            "image_base64": "rendered_img",
            "image_url": "",
            "message": "Rendered",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = api_render("http://localhost:8000", "uml", "@startuml\n@enduml")

        assert result["status"] == "ok"
        assert result["image_base64"] == "rendered_img"
        assert result["plantuml_code"] == "@startuml\n@enduml"

    @patch("streamlit_app.requests.post")
    def test_timeout(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.Timeout()

        result = api_render("http://localhost:8000", "mindmap", "@startmindmap\n@endmindmap")

        assert result["status"] == "error"
        assert "timed out" in result["message"]

    @patch("streamlit_app.requests.post")
    def test_connection_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError()

        result = api_render("http://localhost:8000", "uml", "@startuml\n@enduml")

        assert result["status"] == "error"
        assert "Cannot connect" in result["message"]

    @patch("streamlit_app.requests.post")
    def test_uses_correct_render_endpoint(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        api_render("http://localhost:8000", "erd", "@startuml\n@enduml")

        called_url = mock_post.call_args[0][0]
        assert "/v01/erd/render" in called_url
