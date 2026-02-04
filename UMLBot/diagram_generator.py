"""Diagram generator abstractions and UML implementation."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from UMLBot.prompt_manager import PromptManager
from UMLBot.retry_policy import RetryPolicy
from UMLBot.exceptions import RetryExceededError

class DiagramGenerator(ABC):
    """Abstract base class for diagram generation."""

    @abstractmethod
    def generate(
        self,
        diagram_type: str,
        description: str,
        theme: Optional[str] = None
    ) -> dict[str, Any]:
        """Generate a diagram.

        Args:
            diagram_type (str): Type of diagram.
            description (str): Description of diagram.
            theme (Optional[str]): Optional theme.

        Returns:
            dict[str, Any]: Diagram code and metadata.

        Raises:
            GenerationError: If generation fails.
        """
        pass

class UMLDiagramGenerator(DiagramGenerator):
    """Generates UML diagrams using PromptManager, QueryInterface, and RetryPolicy."""

    def __init__(
        self,
        prompt_manager: PromptManager,
        llm: object,  # Must provide .invoke(prompt: str) -> str
        retry: RetryPolicy
    ) -> None:
        """Initialize the UML diagram generator."""
        self.prompt_manager = prompt_manager
        self.llm = llm
        self.retry = retry

    def generate(
        self,
        diagram_type: str,
        description: str,
        theme: Optional[str] = None
    ) -> dict[str, Any]:
        """Generate a UML diagram with retry logic.

        Args:
            diagram_type (str): Type of diagram.
            description (str): Description of diagram.
            theme (Optional[str]): Optional theme.

        Returns:
            dict[str, Any]: {"diagram_code": str, "metadata": dict}

        Raises:
            GenerationError: If generation fails.
            RetryExceededError: If retries are exhausted.
        """
        variables = {
            "diagram_type": diagram_type,
            "description": description,
            "theme": theme or ""
        }
        prompt = self.prompt_manager.render(variables)
        self.retry.reset()
        while True:
            try:
                diagram_code = self.llm.invoke(prompt)
                return {
                    "diagram_code": diagram_code,
                    "metadata": {
                        "diagram_type": diagram_type,
                        "description": description,
                        "theme": theme
                    }
                }
            except Exception as e:
                self.retry.record_error(e)
                if self.retry.should_retry():
                    if self.retry.backoff_seconds > 0:
                        import time
                        time.sleep(self.retry.backoff_seconds)
                    continue
                else:
                    raise RetryExceededError(
                        self.retry.error_context_list()
                    )
