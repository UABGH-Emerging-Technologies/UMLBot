"""
Integration tests for chat workflow, UMLDraftHandler, and GenericErrorHandler.
Mocks UI/user input and verifies end-to-end error handling and revision workflow.
"""

import os

os.environ.setdefault("azure_proxy_key", "test-key")

import pytest
from unittest.mock import Mock
from UMLBot.diagram_handlers.uml_draft_handler import UMLDraftHandler
from UMLBot.config.config import UMLBotConfig
from aiweb_common.generate.GenericErrorHandler import GenericErrorHandler


class DummyPrompt:
    def __init__(self, template):
        self.template = template

    def format_prompt(self, **kwargs):
        return f"Diagram: {kwargs.get('diagram_type')}, Desc: {kwargs.get('description')}, Theme: {kwargs.get('theme', '')}"


def test_chat_uml_revision_with_error_handler(monkeypatch):
    """UMLRetryManager inside process() handles transient LLM failures internally.

    The first invoke() raises; process() retries and the second invoke() succeeds.
    GenericErrorHandler never sees an error because process() resolves it.
    """
    handler = UMLDraftHandler(config=UMLBotConfig())
    monkeypatch.setattr(handler, "load_prompty", lambda: DummyPrompt("template"))
    monkeypatch.setattr(handler, "check_content_type", lambda x: x)

    llm_calls = [Exception("LLM error"), "@startuml\nclass Foo\n@enduml"]

    class MockLLM:
        def invoke(self, prompt):
            result = llm_calls.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

    from UMLBot.diagram_handlers.uml_draft_handler import UMLRetryManager

    result = handler.process(
        "class",
        "Foo system",
        "bluegray",
        llm_interface=MockLLM(),
        retry_manager=UMLRetryManager(max_retries=2),
    )
    assert "@startuml" in result
    assert "class Foo" in result


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
            from UMLBot.diagram_handlers.uml_draft_handler import UMLRetryManager

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
