"""Tests for the render-validate-repair loop in DiagramService."""

from datetime import date
from unittest.mock import MagicMock, patch

from PIL import Image

from UMLBot.services.diagram_service import (
    DiagramGenerationResult,
    DiagramService,
    _build_repair_prompt,
    _gantt_syntax_hint,
)
from UMLBot.utils.gantt_planning import quarter_table

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
    handler.plan_start = None
    handler.plan_quarters = None
    handler.plan_max_quarters = None
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
        "@startgantt\n[Task] starts D+0\n[Task] ends D+90\n@endgantt",
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
        "@startgantt\n[Task] starts D+0\n[Task] ends D+90\n@endgantt",
        "@startgantt\n[Task] starts D+0\n[Task] ends D+90\n@endgantt",
    )

    result = _generate(handler)

    assert result.render_ok is False
    assert len(handler.llm_interface.prompts) == 2
    assert mock_render.call_count == 3


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_repair_prompt_contains_stderr_and_offending_line(mock_render: MagicMock) -> None:
    mock_render.side_effect = [
        (None, "Diagram generated, but rendering failed: ERROR\n1\nSyntax Error here", False),
        (Image.new("RGB", (10, 10), "white"), "Diagram generated successfully using LLM.", True),
    ]
    handler = _make_handler(
        "@startgantt\nBROKEN LINE\n[Task] starts D+0\n@endgantt",
        "@startgantt\n[Task] starts D+0\n[Task] ends D+90\n@endgantt",
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
def test_render_from_code_returns_five_tuple(mock_render: MagicMock) -> None:
    mock_render.return_value = (Image.new("RGB", (10, 10), "white"), "Re-rendered", True)
    service = DiagramService()

    image, status_msg, image_url, render_ok, rendered_code, _ = service.render_diagram_from_code(
        "@startuml\n[Task] starts D+0\n[Task] ends D+90\n@enduml", "gantt"
    )

    assert image is not None
    assert status_msg == "Re-rendered"
    assert image_url == ""
    assert render_ok is True
    assert rendered_code.startswith("@startgantt")


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_render_from_code_sanitizes_before_rendering(mock_render: MagicMock) -> None:
    mock_render.return_value = (Image.new("RGB", (10, 10), "white"), "Re-rendered", True)
    service = DiagramService()

    service.render_diagram_from_code("@startuml\n[Task] lasts 1 quarter\n@enduml", "gantt")

    rendered_code = mock_render.call_args.kwargs["plantuml_code"]
    assert rendered_code.startswith("@startgantt")
    assert rendered_code.endswith("@endgantt")
    assert "lasts 13 weeks" in rendered_code


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_render_from_code_gantt_appends_plan_warning(mock_render: MagicMock) -> None:
    # A hand-edited label typo is still reported on manual re-render...
    mock_render.return_value = (Image.new("RGB", (10, 10), "white"), "Re-rendered", True)
    service = DiagramService()

    _, status_msg, _, render_ok, _, _ = service.render_diagram_from_code(
        "@startgantt\n[A task] starts D+0\n[A tsk] ends D+90\n@endgantt", "gantt"
    )

    assert render_ok is True
    assert "Plan check:" in status_msg


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_render_from_code_gantt_allows_hand_edited_dates(mock_render: MagicMock) -> None:
    # ...but dates a person typed by hand are theirs to choose.
    mock_render.return_value = (Image.new("RGB", (10, 10), "white"), "Re-rendered", True)
    service = DiagramService()

    _, status_msg, _, _, _, _ = service.render_diagram_from_code(
        "@startgantt\nProject starts 2027-07-01\n[A] starts 2027-07-15\n[A] ends 2027-08-20\n@endgantt",
        "gantt",
    )

    assert "Plan check:" not in status_msg


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_render_from_code_placeholder_is_not_ok(mock_render: MagicMock) -> None:
    mock_render.return_value = (None, "PlantUML rendering failed: bad", False)
    service = DiagramService()

    image, _, _, render_ok, _, _ = service.render_diagram_from_code("@startuml\n@enduml", "uml")

    assert image is not None
    assert render_ok is False


def test_gantt_syntax_hint_dated_lists_allowed_dates() -> None:
    start = date(2027, 7, 1)
    hint = _gantt_syntax_hint(start, quarter_table(start, 20))
    assert "2027-07-01" in hint
    assert "2027-09-30" in hint


def test_gantt_syntax_hint_undated_uses_offsets() -> None:
    hint = _gantt_syntax_hint(None, None)
    assert "No calendar dates" in hint
    assert "D+N" in hint


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_plan_check_failure_triggers_repair(mock_render: MagicMock) -> None:
    mock_render.return_value = (
        Image.new("RGB", (10, 10), "white"),
        "Diagram generated successfully using LLM.",
        True,
    )
    handler = MagicMock()
    handler.process.return_value = (
        "@startgantt\n[A] starts 2027-08-15\n[A] ends 2027-09-30\n@endgantt"
    )
    handler.llm_interface = MockLLM(
        ["@startgantt\n[A] starts 2027-07-01\n[A] ends 2027-09-30\n@endgantt"]
    )
    handler.check_content_type.side_effect = lambda content: content
    handler.plan_start = date(2027, 7, 1)
    handler.plan_quarters = quarter_table(date(2027, 7, 1), 20)
    handler.plan_max_quarters = None

    result = _generate(handler)

    assert "PLAN CHECK FAILED" in handler.llm_interface.prompts[0]
    assert result.plan_warnings == []
    assert result.render_ok is True


@patch("UMLBot.services.diagram_service._render_plantuml_jar")
def test_plan_check_persistent_warning(mock_render: MagicMock) -> None:
    mock_render.return_value = (
        Image.new("RGB", (10, 10), "white"),
        "Diagram generated successfully using LLM.",
        True,
    )
    bad_code = "@startgantt\n[A] starts 2027-08-15\n[A] ends 2027-09-30\n@endgantt"
    handler = MagicMock()
    handler.process.return_value = bad_code
    handler.llm_interface = MockLLM([bad_code])
    handler.check_content_type.side_effect = lambda content: content
    handler.plan_start = date(2027, 7, 1)
    handler.plan_quarters = quarter_table(date(2027, 7, 1), 20)
    handler.plan_max_quarters = None

    result = _generate(handler)

    assert result.plan_warnings
    assert "Plan check:" in result.status_message
    assert result.render_ok is True


def test_repair_prompt_includes_syntax_hint_when_given() -> None:
    prompt = _build_repair_prompt(
        "@startgantt\nX\n@endgantt", "ERROR\n2\nSyntax Error?", "GANTT RULES"
    )
    assert "GANTT RULES" in prompt


def test_repair_prompt_omits_hint_by_default() -> None:
    prompt = _build_repair_prompt("@startuml\nX\n@enduml", "ERROR\n2\nSyntax Error?")
    assert "rules" not in prompt.lower()


def test_repair_prompt_uses_plantuml_zero_based_line_numbers() -> None:
    # Real jar output: BADLINE is the 3rd line of the source and PlantUML reports "2".
    code = "@startgantt\nProject starts 2024-01-01\nBADLINE\n@endgantt"
    prompt = _build_repair_prompt(code, "ERROR\n2\nSyntax Error? (Assumed diagram type: gantt)")
    assert "Offending line: BADLINE" in prompt
