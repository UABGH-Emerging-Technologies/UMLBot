"""UMLDraftHandler: Handles UML diagram generation via LLM using prompty template.

Refactored to inherit WorkflowHandler and provide methods for:
- Loading prompty file
- Constructing prompt with required variables
- Generating diagram (LLM call, error handling)

No UI/Gradio code.
"""

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
from Design_Drafter.config.config import Design_DrafterConfig

class UMLDraftHandler(WorkflowHandler):
    """
    Handler for generating UML diagrams using an LLM and a prompty template.

    Attributes:
        prompty_path (Path): Path to the prompty file.
    """

    def __init__(self, config: Optional[Design_DrafterConfig] = None):
        super().__init__()
        self.prompty_path = Path("assets/uml_diagram.prompty")
        self.config = config or Design_DrafterConfig()

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
            raise ValueError(
                f"Malformed placeholder(s) found: {malformed_jinja2 + malformed_py}"
            )

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
        llm_interface=None,
    ) -> str:
        """
        Generates a UML diagram using the LLM and prompty template.

        Args:
            diagram_type (str): Type of UML diagram to generate.
            description (str): Description of the system/process to diagram.
            theme (Optional[str]): PlantUML theme/style.
            llm_interface: Optional LLM interface for invocation (must have .invoke()).

        Returns:
            str: PlantUML diagram code.

        Raises:
            Exception: On LLM invocation or prompt errors.
        """
        try:
            prompt = self.construct_prompt(diagram_type, description, theme)
            # If no llm_interface provided, raise error (could be injected for testability)
            if llm_interface is None:
                raise ValueError("LLM interface must be provided for diagram generation.")
            # Extract messages if present (Langchain ChatPromptValue)
            if hasattr(prompt, "to_messages"):
                messages = prompt.to_messages()
                # Try passing just the content string of the first message
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
            # Example: If you construct an image URL here, log it as well
            # image_url = f"http://plantuml-server/plantuml/png/{urllib.parse.quote(diagram_code)}"
            # print("DEBUG: PlantUML image URL:", image_url)
            return diagram_code
        except Exception as exc:
            # Optionally log error, re-raise for caller to handle
            print("ERROR: UML diagram generation failed:", exc)
            raise RuntimeError(f"UML diagram generation failed: {exc}") from exc