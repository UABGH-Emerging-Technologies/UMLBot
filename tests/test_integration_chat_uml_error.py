"""
Integration tests for chat workflow, UMLDraftHandler, and GenericErrorHandler.
Mocks UI/user input and verifies end-to-end error handling and revision workflow.
"""

import pytest
from unittest.mock import Mock
from Design_Drafter.uml_draft_handler import UMLDraftHandler
from Design_Drafter.config.config import Design_DrafterConfig
from llm_utils.aiweb_common.generate.GenericErrorHandler import GenericErrorHandler

class DummyPrompt:
    def __init__(self, template):
        self.template = template
    def format_prompt(self, **kwargs):
        return f"Diagram: {kwargs.get('diagram_type')}, Desc: {kwargs.get('description')}, Theme: {kwargs.get('theme', '')}"

def test_chat_uml_revision_with_error_handler(monkeypatch):
    # Simulate a chat workflow where the first UML generation fails, then succeeds after correction
    handler = UMLDraftHandler(config=Design_DrafterConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    monkeypatch.setattr(handler, "check_content_type", lambda x: x)

    # Simulate LLM interface: first call returns error, second call returns valid UML
    llm_calls = [Exception("LLM error"), "@startuml\nclass Foo\n@enduml"]
    class MockLLM:
        def invoke(self, prompt):
            result = llm_calls.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

    def operation():
        try:
            return handler.process("class", "Foo system", "bluegray", llm_interface=MockLLM())
        except Exception as e:
            return e

    def error_predicate(result):
        return isinstance(result, Exception)

    corrections = []
    def correction_callback(attempt, last_result):
        corrections.append((attempt, str(last_result)))

    error_handler = GenericErrorHandler(
        operation=operation,
        error_predicate=error_predicate,
        correction_callback=correction_callback,
        max_retries=2,
    )
    result = error_handler.run()
    assert "@startuml" in result
    assert corrections == [(1, "LLM error")]

def test_integration_respects_retry_limit(monkeypatch):
    # Simulate repeated failures and ensure retry limit is respected
    handler = UMLDraftHandler(config=Design_DrafterConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    monkeypatch.setattr(handler, "check_content_type", lambda x: x)

    class MockLLM:
        def invoke(self, prompt):
            raise Exception("Always fails")

    def operation():
        try:
            return handler.process("class", "Foo system", "bluegray", llm_interface=MockLLM())
        except Exception as e:
            return e

    def error_predicate(result):
        return isinstance(result, Exception)

    corrections = []
    def correction_callback(attempt, last_result):
        corrections.append(attempt)

    error_handler = GenericErrorHandler(
        operation=operation,
        error_predicate=error_predicate,
        correction_callback=correction_callback,
        max_retries=3,
    )
    with pytest.raises(RuntimeError):
        error_handler.run()
    assert corrections == [1, 2, 3]