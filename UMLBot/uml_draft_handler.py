"""UMLDraftHandler: Handles UML diagram generation via LLM using prompty template.

Refactored to inherit WorkflowHandler and provide methods for:
- Loading prompty file
- Constructing prompt with required variables
- Generating diagram (LLM call, error handling)

No UI/Gradio code.
"""


class UMLRetryManager:
    """
    Tracks retry count and error context for UML rendering attempts.

    Attributes:
        max_retries (int): Maximum number of retries allowed.
        attempt (int): Current attempt number.
        errors (list[str]): List of error messages from each failed attempt.
    """

    def __init__(self, max_retries: int = 3) -> None:
        """Initialize the retry manager with a maximum retry count."""
        self.max_retries = max_retries
        self.attempt = 0
        self.errors: list[str] = []

    def record_error(self, error: Exception) -> None:
        """Record an error and increment the attempt counter."""
        self.attempt += 1
        self.errors.append(str(error))

    def should_retry(self) -> bool:
        """Return True when another retry attempt is allowed."""
        return self.attempt < self.max_retries

    def last_error(self) -> str:
        """Return the most recent error message, or empty string if none."""
        return self.errors[-1] if self.errors else ""

    def error_context(self) -> str:
        """Return a multi-line summary of attempts and errors."""
        return "\n".join(f"Attempt {i+1}: {msg}" for i, msg in enumerate(self.errors))


import logging
from pathlib import Path
from typing import Optional, Any


def escape_curly_braces(val: Optional[str]) -> Optional[str]:
    """
    Escapes all curly braces in a string for safe prompt injection.
    Args:
        val (Optional[str]): Input string.
    Returns:
        Optional[str]: String with '{' replaced by '{{' and '}' replaced by '}}'.
    """
    if val is None:
        return val
    return val.replace("{", "{{").replace("}", "}}")


from llm_utils.aiweb_common.WorkflowHandler import WorkflowHandler
from UMLBot.config.config import UMLBotConfig


class UMLDraftHandler(WorkflowHandler):
    """
    Handler for generating UML diagrams using an LLM and a prompty template.

    Attributes:
        prompty_path (Path): Path to the prompty file.
    """

    def __init__(self, config: Optional[UMLBotConfig] = None):
        """Initialize the handler with optional configuration overrides."""
        super().__init__()
        self.prompty_path = (
            Path(__file__).resolve().parent.parent / "assets" / "uml_diagram.prompty"
        )
        self.config = config or UMLBotConfig()

    def _validate_prompt_template(self, template: str) -> None:
        """
        Validates a UML prompt template for required placeholders and syntax.

        This validator fully separates Python `.format()` style (`{name}`) and Jinja2 style (`{{ name }}` or `{% block %}`) placeholders.
        It does not flag valid Jinja2 constructs as malformed Python placeholders.

        Args:
            template (str): The prompt template string to validate.

        Raises:
            ValueError: If required placeholders are missing, curly braces/tags are unbalanced,
                or placeholders/tags are malformed.

        Examples:
            Python `.format()` style:
                "Generate a {diagram_type} diagram for: {description} {theme}"

            Jinja2 style:
                "Generate a {{ diagram_type }} diagram for: {{ description }} {% if theme %}Theme: {{ theme }}{% endif %}"
        """
        import re

        # Remove all Jinja2 tags for Python-style validation
        jinja2_tag_pattern = r"(\{\{.*?\}\}|\{%.*?%\})"
        template_no_jinja2 = re.sub(jinja2_tag_pattern, "", template)

        # 1. Python-style placeholder validation (only on non-Jinja2 content)
        py_placeholder_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        py_placeholders = set(re.findall(py_placeholder_pattern, template_no_jinja2))

        # Malformed Python-style: empty {}, non-identifier, or unclosed
        malformed_py = []
        if re.search(r"\{\s*\}", template_no_jinja2):
            malformed_py.append("Empty Python-style placeholder")
        if re.search(r"\{[^a-zA-Z_][^}]*\}", template_no_jinja2):
            malformed_py.append("Malformed Python-style placeholder")
        if template_no_jinja2.count("{") != template_no_jinja2.count("}"):
            malformed_py.append("Unbalanced curly braces in Python-style section")

        # 2. Jinja2-style placeholder validation (only on Jinja2 tags)
        jinja2_var_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
        jinja2_placeholders = set(re.findall(jinja2_var_pattern, template))
        jinja2_block_pattern = r"\{%\s*([a-zA-Z_][a-zA-Z0-9_ ]*)\s*%\}"
        jinja2_blocks = re.findall(jinja2_block_pattern, template)

        # Malformed Jinja2: unclosed or incomplete tags
        malformed_jinja2 = []
        if re.search(r"\{\{[^\}]*$", template) or re.search(r"\{%[^\}]*$", template):
            malformed_jinja2.append("Unclosed Jinja2 tag")
        if template.count("{{") != template.count("}}"):
            malformed_jinja2.append("Unbalanced Jinja2 variable tags")
        if template.count("{%") != template.count("%}"):
            malformed_jinja2.append("Unbalanced Jinja2 block tags")

        if malformed_py or malformed_jinja2:
            raise ValueError(f"Malformed placeholder(s) found: {malformed_jinja2 + malformed_py}")

        # 3. Required placeholders (must be present in either style)
        all_placeholders = py_placeholders | jinja2_placeholders
        required = {"diagram_type", "description"}
        missing = required - all_placeholders
        if missing:
            raise ValueError(
                f"Missing required placeholder(s): {', '.join(sorted(missing))}. "
                "Required placeholders must be present in either Python `.format()` ({name}) or Jinja2 ({{ name }}) style."
            )

        # 4. If 'theme' is referenced, ensure it's a valid placeholder in either style
        theme_referenced = (
            "theme" in template
            or re.search(r"\{\{\s*theme\s*\}\}", template)
            or re.search(r"\{theme\}", template)
        )
        theme_present = "theme" in all_placeholders
        if theme_referenced and not theme_present:
            raise ValueError(
                "Template references 'theme' but does not use a valid '{theme}' or '{{ theme }}' placeholder."
            )
        # All checks passed

    def construct_prompt(
        self,
        diagram_type: str,
        description: str,
        theme: Optional[str] = None,
    ) -> Any:
        """
        Loads the prompty template and constructs the prompt with provided variables.

        Args:
            diagram_type (str): Type of UML diagram to generate.
            description (str): Description of the system/process to diagram.
            theme (Optional[str]): PlantUML theme/style.

        Returns:
            ChatPromptTemplate: Assembled prompt template ready for LLM invocation.

        Raises:
            FileNotFoundError: If prompty file is missing.
            ValueError: If prompty file is invalid.
        """
        prompt_template = self.load_prompty()
        # Ensure prompt_template is a ChatPromptTemplate and validate its template
        # Skipping prompt template validation for now:
        # if hasattr(self, "_validate_prompt_template"):
        #     self._validate_prompt_template(prompt_template.template)
        variables = {
            "diagram_type": escape_curly_braces(diagram_type),
            "description": escape_curly_braces(description),
            "theme": escape_curly_braces(theme),
        }
        return prompt_template.format_prompt(**variables)

    def process(
        self,
        diagram_type: str,
        description: str,
        theme: Optional[str] = None,
        llm_interface: Optional[Any] = None,
        retry_manager: Optional["UMLRetryManager"] = None,
    ) -> str:
        """
        Generates a UML diagram using the LLM and prompty template, with error handling and retry logic.

        Args:
            diagram_type (str): Type of UML diagram to generate.
            description (str): Description of the system/process to diagram.
            theme (Optional[str]): PlantUML theme/style.
            llm_interface: Optional LLM interface for invocation (must have .invoke()).
            retry_manager (Optional[UMLRetryManager]): Helper for tracking retries and error context.

        Returns:
            str: PlantUML diagram code.

        Raises:
            RuntimeError: If all retries fail, with error context.
        """
        if retry_manager is None:
            retry_manager = UMLRetryManager(max_retries=3)
        while retry_manager.should_retry():
            try:
                prompt = self.construct_prompt(diagram_type, description, theme)
                if llm_interface is None:
                    raise ValueError("LLM interface must be provided for diagram generation.")
                # Extract messages if present (Langchain ChatPromptValue)
                if hasattr(prompt, "to_messages"):
                    messages = prompt.to_messages()
                    if messages and hasattr(messages[0], "content"):
                        prompt_input = messages[0].content
                    else:
                        prompt_input = messages
                elif hasattr(prompt, "messages"):
                    messages = prompt.messages
                    if messages and hasattr(messages[0], "content"):
                        prompt_input = messages[0].content
                    else:
                        prompt_input = messages
                elif isinstance(prompt, str):
                    prompt_input = prompt
                else:
                    raise TypeError("Prompt is not a recognized type for LLM input.")
                response = llm_interface.invoke(prompt_input)
                diagram_code = self.check_content_type(response)
                return diagram_code
            except Exception as exc:
                retry_manager.record_error(exc)
                logging.exception(
                    "UML diagram generation failed (attempt %s)", retry_manager.attempt
                )
        # After max retries, raise with error context
        error_msg = (
            f"UML diagram generation failed after {retry_manager.max_retries} attempts.\n"
            f"Error context:\n{retry_manager.error_context()}"
        )
        raise RuntimeError(error_msg)
