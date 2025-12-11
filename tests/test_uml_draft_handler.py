"""
Unit tests for UMLDraftHandler (chat-based UML revision workflow).
Covers prompt construction, LLM invocation, and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from uml_draft_handler import UMLDraftHandler
from config.config import Design_DrafterConfig


class DummyPrompt:
    def __init__(self, template):
        self.template = template

    def format_prompt(self, **kwargs):
        # Simulate prompt formatting
        return f"Diagram: {kwargs.get('diagram_type')}, Desc: {kwargs.get('description')}, Theme: {kwargs.get('theme', '')}"


def test_construct_prompt_appends_context(monkeypatch):
    handler = UMLDraftHandler(config=Design_DrafterConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    prompt = handler.construct_prompt("class", "A system", "bluegray")
    assert "Diagram: class" in prompt
    assert "Desc: A system" in prompt
    assert "Theme: bluegray" in prompt


def test_process_invokes_llm_and_returns_diagram(monkeypatch):
    handler = UMLDraftHandler(config=Design_DrafterConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    mock_llm = Mock()
    mock_llm.invoke.return_value = "@startuml\nclass Foo\n@enduml"
    monkeypatch.setattr(handler, "check_content_type", lambda x: x)
    result = handler.process("class", "Foo system", "bluegray", llm_interface=mock_llm)
    assert "@startuml" in result
    assert "class Foo" in result


def test_process_raises_on_missing_llm(monkeypatch):
    handler = UMLDraftHandler(config=Design_DrafterConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    from Design_Drafter.uml_draft_handler import UMLRetryManager

    with pytest.raises(RuntimeError):
        handler.process(
            "class",
            "Foo system",
            "bluegray",
            llm_interface=None,
            retry_manager=UMLRetryManager(max_retries=1),
        )


def test_process_retries_and_surfaces_error(monkeypatch):
    handler = UMLDraftHandler(config=Design_DrafterConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))

    class AlwaysFailLLM:
        def invoke(self, prompt):
            raise Exception("LLM always fails")

    from Design_Drafter.uml_draft_handler import UMLRetryManager

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
    handler = UMLDraftHandler(config=Design_DrafterConfig())
    # Missing 'diagram_type' and 'description'
    bad_template = "Generate a {theme} diagram"
    with pytest.raises(ValueError):
        handler._validate_prompt_template(bad_template)


def test_validate_prompt_template_malformed(monkeypatch):
    handler = UMLDraftHandler(config=Design_DrafterConfig())
    # Malformed Python placeholder
    bad_template = "Generate a {123bad} diagram for: {description}"
    with pytest.raises(ValueError):
        handler._validate_prompt_template(bad_template)


def test_construct_prompt_escapes_curly_braces(monkeypatch):
    handler = UMLDraftHandler(config=Design_DrafterConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    plantuml_block = "@startuml\nskinparam {\n  BackgroundColor #EEEBDC\n}\n@enduml"
    prompt = handler.construct_prompt("class", plantuml_block, "bluegray")
    # The curly braces in the PlantUML block should be escaped
    assert "{{" in prompt and "}}" in prompt
    # The PlantUML block should still be present in the output
    assert "skinparam" in prompt
