"""
Unit tests for GenericErrorHandler.
Covers error detection, correction callback, and retry limit enforcement.
"""

import pytest
from llm_utils.aiweb_common.generate.GenericErrorHandler import GenericErrorHandler

def test_successful_operation():
    # Operation always succeeds
    handler = GenericErrorHandler(
        operation=lambda: "ok",
        error_predicate=lambda result: False,
        correction_callback=lambda attempt, last_result: None,
        max_retries=3,
    )
    assert handler.run() == "ok"

def test_error_detection_and_correction(monkeypatch):
    # Operation fails first, then succeeds
    results = [Exception("fail"), "success"]
    def operation():
        return results.pop(0)
    correction_calls = []
    def error_predicate(result):
        return isinstance(result, Exception)
    def correction_callback(attempt, last_result):
        correction_calls.append((attempt, last_result))
    handler = GenericErrorHandler(
        operation=operation,
        error_predicate=error_predicate,
        correction_callback=correction_callback,
        max_retries=2,
    )
    assert handler.run() == "success"
    assert correction_calls == [(1, Exception("fail"))]

def test_retry_limit_enforced():
    # Operation always fails
    def operation():
        return Exception("fail")
    def error_predicate(result):
        return isinstance(result, Exception)
    correction_calls = []
    def correction_callback(attempt, last_result):
        correction_calls.append(attempt)
    handler = GenericErrorHandler(
        operation=operation,
        error_predicate=error_predicate,
        correction_callback=correction_callback,
        max_retries=2,
    )
    with pytest.raises(RuntimeError):
        handler.run()
    assert correction_calls == [1, 2]