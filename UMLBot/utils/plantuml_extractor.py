"""
PlantUML Extraction Utility

Extracts the last valid PlantUML code block from a chat response string.
- Finds blocks delimited by triple backticks (```plantuml ... ```) or containing @startuml.
- Strips code block markers and whitespace.
- Validates presence of @startuml and @enduml.

Raises:
    ValueError: If no valid PlantUML block is found.

Example:
    >>> extract_last_plantuml_block("... ```plantuml\\n@startuml ... @enduml\\n``` ...")
    '@startuml ... @enduml'
"""

import re


def extract_last_plantuml_block(text: str) -> str:
    """
    Extracts the last valid PlantUML code block from the input text.

    Args:
        text (str): The chat response string.

    Returns:
        str: The extracted PlantUML code.

    Raises:
        ValueError: If no valid PlantUML block is found.
    """
    # Find all code blocks: ```plantuml ... ``` or ``` ... ```
    code_block_pattern = re.compile(r"```(?:plantuml)?\s*([\s\S]*?)```", re.MULTILINE)
    blocks = code_block_pattern.findall(text)

    # Also find any @startuml ... @enduml blocks outside code blocks
    uml_pattern = re.compile(r"@startuml[\s\S]*?@enduml", re.MULTILINE)
    blocks += uml_pattern.findall(text)

    # Filter for valid PlantUML blocks
    valid_blocks = []
    for block in blocks:
        block_stripped = block.strip()
        # Remove code block markers if present
        block_stripped = re.sub(
            r"^```(?:plantuml)?\s*|```$", "", block_stripped, flags=re.MULTILINE
        ).strip()
        if "@startuml" in block_stripped and "@enduml" in block_stripped:
            valid_blocks.append(block_stripped)

    if not valid_blocks:
        raise ValueError("No valid PlantUML block found in response.")

    # Return the last valid block
    return valid_blocks[-1]
