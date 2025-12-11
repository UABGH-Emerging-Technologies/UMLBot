from pathlib import Path
from typing import Any, Dict

from Design_Drafter.exceptions import TemplateError

class PromptManager:
    """Manages prompt templates for diagram generation.

    Args:
        template_path (Path): Path to the prompt template file.

    Raises:
        TemplateError: If template validation fails.
    """

    REQUIRED_PLACEHOLDERS = {"diagram_type", "description"}

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        self._template: str | None = None

    def load_template(self) -> str:
        """Loads the template from file.

        Returns:
            str: The template string.

        Raises:
            TemplateError: If the template file cannot be read.
        """
        try:
            self._template = self.template_path.read_text(encoding="utf-8")
        except Exception as e:
            raise TemplateError(f"Failed to load template: {e}")
        self.validate(self._template)
        return self._template

    def validate(self, template: str) -> None:
        """Validates that required placeholders are present.

        Args:
            template (str): The template string.

        Raises:
            TemplateError: If required placeholders are missing.
        """
        missing = [
            key for key in self.REQUIRED_PLACEHOLDERS
            if f"{{{key}}}" not in template
        ]
        if missing:
            raise TemplateError(
                f"Missing required placeholders: {', '.join(missing)}"
            )

    def render(self, variables: Dict[str, Any]) -> str:
        """Renders the template with provided variables.

        Args:
            variables (dict[str, Any]): Variables to substitute.

        Returns:
            str: Rendered prompt string.

        Raises:
            TemplateError: If rendering fails.
        """
        template = self._template or self.load_template()
        try:
            return template.format_map(self._escape_curly_braces(variables))
        except KeyError as e:
            raise TemplateError(f"Missing variable for rendering: {e}")
        except Exception as e:
            raise TemplateError(f"Failed to render template: {e}")

    @staticmethod
    def _escape_curly_braces(variables: Dict[str, Any]) -> Dict[str, Any]:
        """Escapes curly braces in variable values.

        Args:
            variables (dict[str, Any]): Variables to escape.

        Returns:
            dict[str, Any]: Escaped variables.
        """
        def escape(val: Any) -> Any:
            if isinstance(val, str):
                return val.replace("{", "{{").replace("}", "}}")
            return val
        return {k: escape(v) for k, v in variables.items()}