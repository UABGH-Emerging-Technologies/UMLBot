"""Tests for the render-validate-repair loop in DiagramService."""

from unittest.mock import MagicMock, patch

from PIL import Image

from UMLBot.services.diagram_service import DiagramGenerationResult, DiagramService

RENDER_ERROR = "Diagram generated, but rendering failed: ERROR\n3\nSyntax Error? (Assumed diagram type: sequence)"


class MockLLM:
    """Minimal LLM interface that records prompts and replays responses."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> str:
        self.prompts.append(prompt)
        index = min(len(self.prompts) - 1, len(self.responses) - 1)
        return self.responses[index]


def _make_handler(original_code: str, repaired_code: str) -> MagicMock:
    handler = MagicMock()
    handler.process.return_value = original_code
    handler.llm_interface = MockLLM([repaired_code])
    handler.check_content_type.side_effect = lambda content: content
    return handler


def _generate(handler: MagicMock, mode: str = "gantt") -> DiagramGenerationResult:
    return DiagramService()._generate_from_description(
        handler=handler,
        description="A project plan",
        diagram_type="gantt",
        theme=None,
        fallback_template="@startgantt\n[Task] lasts 1 day\n@endgantt",
        failure_log="failed",
        openai_compatible_endpoint="https://api.openai.com/v1",
        openai_compatible_key="sk-test",
        openai_compatible_model="gpt-4o-mini",
        mode=mode,
    )


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_repair_after_first_failure_sets_render_ok(mock_render: MagicMock) -> None:
    mock_render.side_effect = [
        (None, RENDER_ERROR, False),
        (Image.new("RGB", (10, 10), "white"), "Diagram generated successfully using LLM.", True),
    ]
    handler = _make_handler(
        "@startuml\n[Task] lasts 1 quarter\n@enduml",
        "@startgantt\n[Task] lasts 3 months\n@endgantt",
    )

    result = _generate(handler)

    assert result.render_ok is True
    assert handler.process.call_count == 1
    assert len(handler.llm_interface.prompts) == 1
    assert mock_render.call_count == 2


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_repair_stops_after_two_attempts(mock_render: MagicMock) -> None:
    mock_render.return_value = (None, RENDER_ERROR, False)
    handler = _make_handler(
        "@startgantt\n[Task] lasts 1 day\n@endgantt",
        "@startgantt\n[Task] lasts 1 day\n@endgantt",
    )

    result = _generate(handler)

    assert result.render_ok is False
    assert len(handler.llm_interface.prompts) == 2
    assert mock_render.call_count == 3


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_repair_prompt_contains_stderr_and_offending_line(mock_render: MagicMock) -> None:
    mock_render.side_effect = [
        (None, "Diagram generated, but rendering failed: ERROR\n2\nSyntax Error here", False),
        (Image.new("RGB", (10, 10), "white"), "Diagram generated successfully using LLM.", True),
    ]
    handler = _make_handler(
        "@startgantt\nBROKEN LINE\n[Task] lasts 1 day\n@endgantt",
        "@startgantt\n[Task] lasts 1 day\n@endgantt",
    )

    _generate(handler)

    assert len(handler.llm_interface.prompts) == 1
    prompt = handler.llm_interface.prompts[0]
    assert "Syntax Error here" in prompt
    assert "BROKEN LINE" in prompt


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_no_repair_when_llm_call_failed(mock_render: MagicMock) -> None:
    mock_render.return_value = (None, "LLM error: boom. Showing fallback stub.", False)
    handler = MagicMock()
    handler.process.side_effect = RuntimeError("boom")

    result = _generate(handler)

    assert result.render_ok is False
    handler.llm_interface.invoke.assert_not_called()
    assert mock_render.call_count == 1


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_render_from_code_returns_four_tuple(mock_render: MagicMock) -> None:
    mock_render.return_value = (Image.new("RGB", (10, 10), "white"), "Re-rendered", True)
    service = DiagramService()

    image, status_msg, image_url, render_ok = service.render_diagram_from_code(
        "@startuml\n[Task] lasts 1 day\n@enduml", "gantt"
    )

    assert image is not None
    assert status_msg == "Re-rendered"
    assert image_url == ""
    assert render_ok is True


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_render_from_code_sanitizes_before_rendering(mock_render: MagicMock) -> None:
    mock_render.return_value = (Image.new("RGB", (10, 10), "white"), "Re-rendered", True)
    service = DiagramService()

    service.render_diagram_from_code("@startuml\n[Task] lasts 1 quarter\n@enduml", "gantt")

    rendered_code = mock_render.call_args.kwargs["plantuml_code"]
    assert rendered_code.startswith("@startgantt")
    assert rendered_code.endswith("@endgantt")
    assert "lasts 3 months" in rendered_code


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_render_from_code_placeholder_is_not_ok(mock_render: MagicMock) -> None:
    mock_render.return_value = (None, "PlantUML rendering failed: bad", False)
    service = DiagramService()

    image, _, _, render_ok = service.render_diagram_from_code("@startuml\n@enduml", "uml")

    assert image is not None
    assert render_ok is False
