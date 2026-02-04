"""
Integration tests for chat workflow, UMLDraftHandler, and GenericErrorHandler.
Mocks UI/user input and verifies end-to-end error handling and revision workflow.
"""

import pytest
from unittest.mock import Mock
from UMLBot.uml_draft_handler import UMLDraftHandler
from UMLBot.config.config import UMLBotConfig
from llm_utils.aiweb_common.generate.GenericErrorHandler import GenericErrorHandler


class DummyPrompt:
    def __init__(self, template):
        self.template = template

    def format_prompt(self, **kwargs):
        return f"Diagram: {kwargs.get('diagram_type')}, Desc: {kwargs.get('description')}, Theme: {kwargs.get('theme', '')}"


def test_chat_history_scrollable_and_persistent(monkeypatch):
    """
    Verifies that the chat history is preserved and all messages (user, assistant, system, error)
    are present and accessible for scrolling in the Gradio UI.
    """
    from gradio_app import format_chat_history

    # Simulate a session with multiple message types
    chat_history = [
        {"role": "user", "content": "First question"},
        {"role": "system", "content": "System info"},
        {"role": "assistant", "content": "Assistant reply"},
        {"role": "error", "content": "Error occurred"},
        {"role": "user", "content": "Second question"},
        {"role": "assistant", "content": "Second reply"},
    ]
    formatted = format_chat_history(chat_history)
    # All messages should be present and in order
    assert len(formatted) == len(chat_history)
    # Check error/system formatting
    assert formatted[1]["content"].startswith("ℹ️")
    assert formatted[3]["content"].startswith("❌")
    # Check scrollable property via elem_classes
    # (UI test: would require selenium or gradio test client for full scroll test)
    # Here, we check the formatting and presence only


def test_chat_uml_revision_with_error_handler(monkeypatch):
    # Simulate a chat workflow where the first UML generation fails, then succeeds after correction
    handler = UMLDraftHandler(config=UMLBotConfig())
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
            from UMLBot.uml_draft_handler import UMLRetryManager

            return handler.process(
                "class",
                "Foo system",
                "bluegray",
                llm_interface=MockLLM(),
                retry_manager=UMLRetryManager(max_retries=2),
            )
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
    # Defensive: result may be Exception or str
    if isinstance(result, Exception):
        assert False, f"Expected UML string, got Exception: {result}"
    assert "@startuml" in str(result)
    assert corrections == [(1, "LLM error")]


def test_integration_respects_retry_limit(monkeypatch):
    # Simulate repeated failures and ensure retry limit is respected
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    monkeypatch.setattr(handler, "check_content_type", lambda x: x)

    class MockLLM:
        def invoke(self, prompt):
            raise Exception("Always fails")

    def operation():
        try:
            from UMLBot.uml_draft_handler import UMLRetryManager

            return handler.process(
                "class",
                "Foo system",
                "bluegray",
                llm_interface=MockLLM(),
                retry_manager=UMLRetryManager(max_retries=3),
            )
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
