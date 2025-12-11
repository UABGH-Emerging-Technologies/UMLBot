import pytest
from retry_policy import RetryPolicy

def test_initial_state():
    rp = RetryPolicy(max_retries=2)
    assert rp.attempts == 0
    assert rp.errors == []
    assert rp.should_retry() is True

def test_record_error_and_retry():
    rp = RetryPolicy(max_retries=2)
    rp.record_error(ValueError("fail1"))
    assert rp.attempts == 1
    assert len(rp.errors) == 1
    assert rp.should_retry() is True
    rp.record_error(RuntimeError("fail2"))
    assert rp.attempts == 2
    assert len(rp.errors) == 2
    assert rp.should_retry() is False

def test_error_context():
    rp = RetryPolicy(max_retries=2)
    rp.record_error(ValueError("fail1"))
    rp.record_error(RuntimeError("fail2"))
    ctx = rp.error_context()
    assert "ValueError: fail1" in ctx
    assert "RuntimeError: fail2" in ctx

def test_reset():
    rp = RetryPolicy(max_retries=2)
    rp.record_error(ValueError("fail1"))
    rp.reset()
    assert rp.attempts == 0
    assert rp.errors == []
    assert rp.should_retry() is True