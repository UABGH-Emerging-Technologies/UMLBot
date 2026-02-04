"""Lightweight LLM adapter abstractions used in tests."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Protocol

from UMLBot.exceptions import LLMError


class LLMCallable(Protocol):
    """Callable protocol for LLM backends used by the adapter."""

    def __call__(self, prompt: str) -> str:  # pragma: no cover - Protocol signature only
        ...


class LLMInterface(Protocol):
    """Minimal interface for LLM invocation used in the codebase and tests."""

    def invoke(self, prompt: str) -> str:
        """Invoke the LLM synchronously."""

    async def invoke_async(self, prompt: str) -> str:
        """Invoke the LLM asynchronously."""


class LangchainLLMAdapter:
    """Adapter that normalizes a callable into an LLM interface."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the adapter with a callable under ``llm_callable``."""
        llm_callable = config.get("llm_callable")
        if llm_callable is None or not callable(llm_callable):
            raise ValueError("config['llm_callable'] must be a callable.")
        self._llm_callable: LLMCallable = llm_callable

    def invoke(self, prompt: str) -> str:
        """Invoke the underlying callable and normalize errors."""
        try:
            return self._llm_callable(prompt)
        except Exception as exc:  # pragma: no cover - exception path exercised in tests
            raise LLMError(str(exc)) from exc

    async def invoke_async(self, prompt: str) -> str:
        """Invoke the callable asynchronously using a thread helper."""
        try:
            return await asyncio.to_thread(self._llm_callable, prompt)
        except Exception as exc:
            raise LLMError(str(exc)) from exc


__all__ = ["LangchainLLMAdapter", "LLMInterface"]

