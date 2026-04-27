"""Tests for GPT-5 Responses API migration: model detection and flag wiring."""

from unittest.mock import MagicMock, patch

import pytest

from UMLBot.config.config import UMLBotConfig, is_responses_api_model

# ---------------------------------------------------------------------------
# is_responses_api_model
# ---------------------------------------------------------------------------


class TestIsResponsesApiModel:
    """Tests for the GPT-5 model detection helper."""

    def test_gpt5_matches(self) -> None:
        assert is_responses_api_model("gpt-5") is True

    def test_gpt5_mini_matches(self) -> None:
        assert is_responses_api_model("gpt-5-mini") is True

    def test_gpt5_nano_matches(self) -> None:
        assert is_responses_api_model("gpt-5-nano") is True

    def test_gpt5_no_dash_matches(self) -> None:
        assert is_responses_api_model("gpt5") is True

    def test_gpt5_case_insensitive(self) -> None:
        assert is_responses_api_model("GPT-5") is True

    def test_gpt5_dot_variant_matches(self) -> None:
        assert is_responses_api_model("gpt-5.2") is True

    def test_gpt4o_does_not_match(self) -> None:
        assert is_responses_api_model("gpt-4o") is False

    def test_gpt4o_mini_does_not_match(self) -> None:
        assert is_responses_api_model("gpt-4o-mini") is False

    def test_empty_string(self) -> None:
        assert is_responses_api_model("") is False

    def test_other_model(self) -> None:
        assert is_responses_api_model("claude-3-opus") is False


# ---------------------------------------------------------------------------
# REASONING_EFFORT config
# ---------------------------------------------------------------------------


class TestReasoningEffortConfig:
    """Verify REASONING_EFFORT is present and has a valid default."""

    def test_default_value(self) -> None:
        assert UMLBotConfig.REASONING_EFFORT in ("none", "minimal", "low", "medium", "high", None)


# ---------------------------------------------------------------------------
# _generate_from_description passes Responses API flags
# ---------------------------------------------------------------------------


class TestResponsesApiWiring:
    """Verify that _generate_from_description passes the correct flags to _init_openai."""

    @patch("UMLBot.services.diagram_service._render_plantuml_jar")
    def test_gpt5_model_sets_responses_api_flag(self, mock_render: MagicMock) -> None:
        from UMLBot.services.diagram_service import DiagramService

        mock_render.return_value = (None, "rendered")
        service = DiagramService()

        handler = MagicMock()
        handler.process.return_value = "@startuml\n@enduml"

        service._generate_from_description(
            handler=handler,
            description="test",
            diagram_type="Class",
            theme=None,
            fallback_template="@startuml\n@enduml",
            failure_log="fail",
            openai_compatible_endpoint="https://api.openai.com/v1",
            openai_compatible_key="sk-test",
            openai_compatible_model="gpt-5-mini",
        )

        handler._init_openai.assert_called_once()
        call_kwargs = handler._init_openai.call_args[1]
        assert call_kwargs["use_responses_api"] is True
        assert call_kwargs["reasoning_effort"] is not None

    @patch("UMLBot.services.diagram_service._render_plantuml_jar")
    def test_gpt4o_model_does_not_set_responses_api_flag(self, mock_render: MagicMock) -> None:
        from UMLBot.services.diagram_service import DiagramService

        mock_render.return_value = (None, "rendered")
        service = DiagramService()

        handler = MagicMock()
        handler.process.return_value = "@startuml\n@enduml"

        service._generate_from_description(
            handler=handler,
            description="test",
            diagram_type="Class",
            theme=None,
            fallback_template="@startuml\n@enduml",
            failure_log="fail",
            openai_compatible_endpoint="https://api.openai.com/v1",
            openai_compatible_key="sk-test",
            openai_compatible_model="gpt-4o-mini",
        )

        handler._init_openai.assert_called_once()
        call_kwargs = handler._init_openai.call_args[1]
        assert call_kwargs["use_responses_api"] is False
        assert call_kwargs["reasoning_effort"] is None
