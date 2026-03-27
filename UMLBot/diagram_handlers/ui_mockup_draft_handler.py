"""UIMockupDraftHandler: Handles SALT UI mockup generation via LLM using prompty template."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from UMLBot.config.config import UMLBotConfig
from UMLBot.diagram_handlers.uml_draft_handler import UMLDraftHandler


class UIMockupDraftHandler(UMLDraftHandler):
    """
    Handler for generating PlantUML SALT UI mockups using an LLM and a prompty template.

    Attributes:
        prompty_path (Path): Path to the prompty file.
    """

    def __init__(self, config: Optional[UMLBotConfig] = None):
        """Initialize the handler with optional configuration overrides."""
        super().__init__(config=config)
        self.prompty_path = Path(__file__).resolve().parents[2] / "assets" / "ui_mockup.prompty"
