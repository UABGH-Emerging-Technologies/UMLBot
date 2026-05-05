"""
Unit tests for UMLDraftHandler (chat-based UML revision workflow).
Covers prompt construction, LLM invocation, and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from UMLBot.uml_draft_handler import UMLDraftHandler
from UMLBot.config.config import UMLBotConfig


class DummyPrompt:
    def __init__(self, template):
        self.template = template

    def format_prompt(self, **kwargs):
        # Simulate prompt formatting
        return f"Diagram: {kwargs.get('diagram_type')}, Desc: {kwargs.get('description')}, Theme: {kwargs.get('theme', '')}"


def test_construct_prompt_appends_context(monkeypatch):
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    prompt = handler.construct_prompt("class", "A system", "bluegray")
    assert "Diagram: class" in prompt
    assert "Desc: A system" in prompt
    assert "Theme: bluegray" in prompt


def test_process_invokes_llm_and_returns_diagram(monkeypatch):
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    mock_llm = Mock()
    mock_llm.invoke.return_value = "@startuml\nclass Foo\n@enduml"
    monkeypatch.setattr(handler, "check_content_type", lambda x: x)
    result = handler.process("class", "Foo system", "bluegray", llm_interface=mock_llm)
    assert "@startuml" in result
    assert "class Foo" in result


def test_process_raises_on_missing_llm(monkeypatch):
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))

    with pytest.raises(ValueError, match="LLM interface must be provided"):
        handler.process(
            "class",
            "Foo system",
            "bluegray",
            llm_interface=None,
        )


def test_process_retries_and_surfaces_error(monkeypatch):
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))

    class AlwaysFailLLM:
        def invoke(self, prompt):
            raise Exception("LLM always fails")

    from UMLBot.uml_draft_handler import UMLRetryManager

    retry_manager = UMLRetryManager(max_retries=3)
    with pytest.raises(RuntimeError) as excinfo:
        handler.process(
            "class",
            "Foo system",
            "bluegray",
            llm_interface=AlwaysFailLLM(),
            retry_manager=retry_manager,
        )
    assert "UML diagram generation failed after 3 attempts" in str(excinfo.value)
    assert "LLM always fails" in str(excinfo.value)


def test_validate_prompt_template_missing_required(monkeypatch):
    handler = UMLDraftHandler(config=UMLBotConfig())
    # Missing 'diagram_type' and 'description'
    bad_template = "Generate a {theme} diagram"
    with pytest.raises(ValueError):
        handler._validate_prompt_template(bad_template)


def test_validate_prompt_template_malformed(monkeypatch):
    handler = UMLDraftHandler(config=UMLBotConfig())
    # Malformed Python placeholder
    bad_template = "Generate a {123bad} diagram for: {description}"
    with pytest.raises(ValueError):
        handler._validate_prompt_template(bad_template)


def test_process_validates_plantuml_and_retries_with_feedback(monkeypatch):
    """When LLM returns text missing @startuml, process() retries with a correction prompt."""
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))

    responses = [
        "Here is a class diagram:\nclass Foo",
        "@startuml\nclass Foo\n@enduml",
    ]
    invocations = []

    class MockLLM:
        def invoke(self, prompt):
            invocations.append(prompt)
            return responses.pop(0)

    monkeypatch.setattr(handler, "check_content_type", lambda x: x)
    result = handler.process("class", "Foo system", llm_interface=MockLLM())
    assert "@startuml" in result
    assert len(invocations) == 2
    assert "did not contain valid PlantUML" in invocations[1]


def test_process_infra_error_retries_with_original_prompt(monkeypatch):
    """Infrastructure errors (network, etc.) retry with the original prompt, not a correction."""
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))

    call_count = [0]
    invocations = []

    class MockLLM:
        def invoke(self, prompt):
            invocations.append(prompt)
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("Network timeout")
            return "@startuml\nclass Foo\n@enduml"

    monkeypatch.setattr(handler, "check_content_type", lambda x: x)
    result = handler.process("class", "Foo system", llm_interface=MockLLM())
    assert "@startuml" in result
    assert invocations[0] == invocations[1]


def test_process_returns_extracted_plantuml(monkeypatch):
    """process() strips markdown wrappers and explanatory text, returning only the PlantUML block."""
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))

    class MockLLM:
        def invoke(self, prompt):
            return (
                "Sure! Here is your diagram:\n"
                "```plantuml\n@startuml\nclass Foo\n@enduml\n```\n"
                "Hope this helps!"
            )

    monkeypatch.setattr(handler, "check_content_type", lambda x: x)
    result = handler.process("class", "Foo system", llm_interface=MockLLM())
    assert result.startswith("@startuml")
    assert result.endswith("@enduml")
    assert "Hope this helps" not in result


def test_construct_prompt_escapes_curly_braces(monkeypatch):
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    plantuml_block = "@startuml\nskinparam {\n  BackgroundColor #EEEBDC\n}\n@enduml"
    prompt = handler.construct_prompt("class", plantuml_block, "bluegray")
    # The curly braces in the PlantUML block should be escaped
    assert "{{" in prompt and "}}" in prompt
    # The PlantUML block should still be present in the output
    assert "skinparam" in prompt
