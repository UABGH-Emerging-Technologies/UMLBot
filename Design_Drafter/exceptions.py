"""Custom exceptions for Design_Drafter modules."""

class TemplateError(Exception):
    """Raised when a prompt template is invalid or cannot be rendered."""

class LLMError(Exception):
    """Raised when an LLM invocation fails."""

class GenerationError(Exception):
    """Raised when diagram generation fails."""

class RetryExceededError(Exception):
    """Raised when retry attempts are exhausted."""