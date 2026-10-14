"""GanttDraftHandler: Handles Gantt chart generation via LLM using prompty template."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Optional

from UMLBot.config.config import UMLBotConfig
from UMLBot.diagram_handlers.uml_draft_handler import UMLDraftHandler, escape_curly_braces
from UMLBot.utils.gantt_planning import (
    Quarter,
    extract_max_quarters,
    extract_start_date,
    quarter_table,
    wants_detailed_plan,
)


class GanttDraftHandler(UMLDraftHandler):
    """
    Handler for generating PlantUML Gantt charts using an LLM and a prompty template.

    Attributes:
        prompty_path (Path): Path to the prompty file.
        plan_start (date | None): Project start date inferred from the request.
        plan_quarters (list[Quarter]): Quarter table inferred from the request.
        plan_max_quarters (int | None): Requested plan length in quarters.
        plan_detailed (bool): Whether the request explicitly asks for a detailed plan.
    """

    def __init__(self, config: Optional[UMLBotConfig] = None):
        """Initialize the handler with optional configuration overrides."""
        super().__init__(config=config)
        self.prompty_path = Path(__file__).resolve().parents[2] / "assets" / "gantt_chart.prompty"
        self.plan_start: date | None = None
        self.plan_quarters: list[Quarter] = []
        self.plan_max_quarters: int | None = None
        self.plan_detailed: bool = False

    def construct_prompt(
        self,
        diagram_type: str,
        description: str,
        theme: Optional[str] = None,
    ) -> Any:
        """Render the Gantt prompty template with date/quarter planning variables.

        The plan inferred from ``description`` is cached on the handler so the
        service can run :func:`check_gantt_plan` after rendering.
        """
        start = extract_start_date(description)
        self.plan_start = start
        self.plan_quarters = quarter_table(start, 20) if start is not None else []
        self.plan_max_quarters = extract_max_quarters(description)
        self.plan_detailed = wants_detailed_plan(description)

        quarters = [
            {
                "label": quarter.label,
                "start": quarter.start.isoformat(),
                "end": quarter.end.isoformat(),
            }
            for quarter in self.plan_quarters
        ]
        prompt_template = self.load_prompty()
        variables = {
            "diagram_type": escape_curly_braces(diagram_type),
            "description": escape_curly_braces(description),
            "theme": escape_curly_braces(theme),
            "dated": start is not None,
            "project_start": start.isoformat() if start is not None else "",
            "quarters": quarters,
        }
        return prompt_template.format_prompt(**variables)
