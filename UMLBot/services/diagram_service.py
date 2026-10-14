"""Diagram generation services and PlantUML rendering helpers."""

from __future__ import annotations

import base64
import io
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Tuple
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

from UMLBot.config.config import UMLBotConfig, is_responses_api_model
from UMLBot.diagram_handlers import (
    C4DraftHandler,
    ERDraftHandler,
    GanttDraftHandler,
    JsonDraftHandler,
    MindmapDraftHandler,
    UIMockupDraftHandler,
    UMLDraftHandler,
)
from UMLBot.utils.gantt_planning import (
    Quarter,
    check_gantt_plan,
    plan_total_days,
    quarter_table,
    style_gantt,
    wants_auto_style,
)
from UMLBot.utils.plantuml_sanitizer import sanitize_plantuml

LOGGER = logging.getLogger(__name__)

# Maximum number of LLM-backed repair attempts after a failed render.
MAX_REPAIR_ATTEMPTS = 2

# Gantt syntax reminder sent with repair prompts (other modes send none).
GANTT_REPAIR_HINT = (
    "PlantUML Gantt rules: wrap in @startgantt/@endgantt; place every task with "
    "exactly two lines, `[Task label] starts <start>` and `[Task label] ends <end>`, "
    "with identical labels; never use `lasts`, aliases (`as [X]`), or invented dates; "
    "milestones are `[Label] happens at [Task]'s end`; no arrows unless requested; "
    "do not write printscale/zoom/hide/colour lines."
)


@dataclass
class DiagramGenerationResult:
    """Result container for a UML generation request."""

    plantuml_code: str
    pil_image: Image.Image | None
    status_message: str
    image_url: str
    svg_text: Optional[str] = None
    render_ok: bool = False
    plan_warnings: list[str] = field(default_factory=list)


class DiagramService:
    """Interface layer for diagram generation and rendering workflows."""

    def generate_diagram_from_description(
        self,
        description: str,
        diagram_type: str,
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
        fmt: str = "png",
    ) -> DiagramGenerationResult:
        """Run the UMLDraftHandler pipeline and return PlantUML code plus rendered image."""
        handler = UMLDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_PLANTUML_TEMPLATE,
            failure_log="LLM-backed generation failed, returning fallback diagram.",
            mode="uml",
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            fmt=fmt,
        )

    def generate_mindmap_from_description(
        self,
        description: str,
        diagram_type: str = "Mindmap",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
        fmt: str = "png",
    ) -> DiagramGenerationResult:
        """Run the MindmapDraftHandler pipeline and return PlantUML code plus rendered image."""
        handler = MindmapDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_MINDMAP_TEMPLATE,
            failure_log="LLM-backed mindmap generation failed, returning fallback diagram.",
            mode="mindmap",
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            fmt=fmt,
        )

    def generate_ui_mockup_from_description(
        self,
        description: str,
        diagram_type: str = "salt",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
        fmt: str = "png",
    ) -> DiagramGenerationResult:
        """Run the UIMockupDraftHandler pipeline and return PlantUML SALT code plus rendered image."""
        handler = UIMockupDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_SALT_TEMPLATE,
            failure_log="LLM-backed UI mockup generation failed, returning fallback diagram.",
            mode="ui_mockup",
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            fmt=fmt,
        )

    def generate_gantt_from_description(
        self,
        description: str,
        diagram_type: str = "gantt",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
        fmt: str = "png",
    ) -> DiagramGenerationResult:
        """Run the GanttDraftHandler pipeline and return PlantUML Gantt code plus rendered image."""
        handler = GanttDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_GANTT_TEMPLATE,
            failure_log="LLM-backed Gantt generation failed, returning fallback diagram.",
            mode="gantt",
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            fmt=fmt,
        )

    def generate_erd_from_description(
        self,
        description: str,
        diagram_type: str = "ERD",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
        fmt: str = "png",
    ) -> DiagramGenerationResult:
        """Run the ERDraftHandler pipeline and return PlantUML ER diagram code plus rendered image."""
        handler = ERDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_ERD_TEMPLATE,
            failure_log="LLM-backed ERD generation failed, returning fallback diagram.",
            mode="erd",
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            fmt=fmt,
        )

    def generate_json_from_description(
        self,
        description: str,
        diagram_type: str = "json",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
        fmt: str = "png",
    ) -> DiagramGenerationResult:
        """Run the JsonDraftHandler pipeline and return PlantUML JSON code plus rendered image."""
        handler = JsonDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_JSON_TEMPLATE,
            failure_log="LLM-backed JSON generation failed, returning fallback diagram.",
            mode="json",
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            fmt=fmt,
        )

    def generate_c4_from_description(
        self,
        description: str,
        diagram_type: str = "C4",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
        fmt: str = "png",
    ) -> DiagramGenerationResult:
        """Run the C4DraftHandler pipeline and return PlantUML C4 diagram code plus rendered image."""
        handler = C4DraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_C4_TEMPLATE,
            failure_log="LLM-backed C4 generation failed, returning fallback diagram.",
            mode="c4",
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            fmt=fmt,
        )

    def render_diagram_from_code(
        self, plantuml_code: str, mode: str = "uml", fmt: str = "png"
    ) -> Tuple[Image.Image | str, str, str, bool, str, list[str]]:
        """Re-render an already generated PlantUML snippet via the local JAR.

        Returns a placeholder image if the render fails so the UI can continue
        gracefully.  The fourth value reports whether the JAR rendered
        successfully; the fifth is the sanitized code that was actually rendered;
        the sixth lists Gantt plan-check warnings (empty for other modes).
        """
        sanitized_code = sanitize_plantuml(plantuml_code, mode)
        # Hand-edited code is rendered as written unless it opts in to styling.
        if mode == "gantt" and wants_auto_style(sanitized_code):
            sanitized_code = style_gantt(
                sanitized_code,
                dated=_infer_gantt_plan_from_code(sanitized_code)[0] is not None,
                total_days=plan_total_days(sanitized_code),
                preserve_user_choices=True,
            )
        rendered, status_msg, render_ok = _render_plantuml_jar(
            plantuml_code=sanitized_code,
            status_msg="Re-rendered from PlantUML code.",
            fmt=fmt,
        )
        if rendered is None:
            if fmt == "svg":
                rendered = _create_placeholder_svg("Diagram preview unavailable")
            else:
                rendered = _create_placeholder_image("Diagram preview unavailable")
            render_ok = False
        problems: list[str] = []
        if mode == "gantt":
            start, quarters = _infer_gantt_plan_from_code(sanitized_code)
            problems = check_gantt_plan(sanitized_code, start, quarters, None, check_dates=False)
            if problems:
                warning = "Plan check: " + "; ".join(problems)
                status_msg = f"{status_msg} | {warning}" if status_msg else warning
        return rendered, status_msg, "", render_ok, sanitized_code, problems

    def diagram_image_to_base64(self, image: Image.Image | None) -> Optional[str]:
        """Encode a PIL image to a base64 PNG string."""
        if image is None:
            return None
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def svg_to_base64(self, svg_text: Optional[str]) -> Optional[str]:
        """Encode an SVG string to a base64 UTF-8 string."""
        if not svg_text:
            return None
        return base64.b64encode(svg_text.encode("utf-8")).decode("utf-8")

    def _generate_from_description(
        self,
        handler: UMLDraftHandler,
        description: str,
        diagram_type: str,
        theme: Optional[str],
        fallback_template: str,
        failure_log: str,
        openai_compatible_endpoint: str,
        openai_compatible_key: str,
        openai_compatible_model: str,
        mode: str = "uml",
        fmt: str = "png",
    ) -> DiagramGenerationResult:
        """Shared diagram generation pipeline with per-request LLM credentials."""
        _use_responses: bool = is_responses_api_model(openai_compatible_model)
        handler._init_openai(
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            name="UMLBot",
            use_responses_api=_use_responses,
            reasoning_effort=UMLBotConfig.REASONING_EFFORT if _use_responses else None,
        )

        llm_succeeded = True
        try:
            plantuml_code = handler.process(
                diagram_type=diagram_type,
                description=description,
                theme=theme,
                llm_interface=handler.llm_interface,
            )
            base_status = UMLBotConfig.DIAGRAM_SUCCESS_MSG
        except Exception as exc:
            LOGGER.exception(failure_log)
            plantuml_code = fallback_template.format(
                diagram_type=diagram_type,
                description=description,
            )
            base_status = f"LLM error: {exc}. Showing fallback stub."
            llm_succeeded = False

        plan_start = getattr(handler, "plan_start", None)
        plan_quarters = getattr(handler, "plan_quarters", None)
        plan_max_quarters = getattr(handler, "plan_max_quarters", None)
        plan_detailed = bool(getattr(handler, "plan_detailed", False))
        max_tasks = None if plan_detailed else 10

        current_code = sanitize_plantuml(
            _normalize_curly_braces(_strip_code_block_markers(plantuml_code)),
            mode,
        )
        if mode == "gantt":
            current_code = style_gantt(
                current_code,
                dated=plan_start is not None,
                total_days=plan_total_days(current_code),
            )
        rendered, status_msg, render_ok = _render_plantuml_jar(
            plantuml_code=current_code,
            status_msg=base_status,
            fmt=fmt,
        )

        plan_problems: list[str] = []
        if mode == "gantt" and render_ok:
            plan_problems = check_gantt_plan(
                current_code,
                plan_start,
                plan_quarters,
                plan_max_quarters,
                max_tasks=max_tasks,
            )

        if (not render_ok or plan_problems) and llm_succeeded:
            for _attempt in range(MAX_REPAIR_ATTEMPTS):
                if plan_problems:
                    stderr_text = "PLAN CHECK FAILED:\n" + "\n".join(
                        f"- {problem}" for problem in plan_problems
                    )
                    if any("Plan runs past" in problem for problem in plan_problems):
                        stderr_text += (
                            "\nOverlap independent work and shorten tasks; run "
                            "secondary analyses alongside the main analysis rather "
                            "than after it."
                        )
                else:
                    stderr_text = status_msg
                syntax_hint = (
                    _gantt_syntax_hint(plan_start, plan_quarters) if mode == "gantt" else ""
                )
                repair_prompt = _build_repair_prompt(current_code, stderr_text, syntax_hint)
                try:
                    response = handler.llm_interface.invoke(repair_prompt)
                    repaired_code = handler.check_content_type(response)
                except Exception as exc:
                    LOGGER.warning("LLM repair attempt failed: %s", exc)
                    break
                current_code = sanitize_plantuml(
                    _normalize_curly_braces(_strip_code_block_markers(repaired_code)),
                    mode,
                )
                if mode == "gantt":
                    current_code = style_gantt(
                        current_code,
                        dated=plan_start is not None,
                        total_days=plan_total_days(current_code),
                    )
                rendered, status_msg, render_ok = _render_plantuml_jar(
                    plantuml_code=current_code,
                    status_msg=base_status,
                    fmt=fmt,
                )
                plan_problems = []
                if mode == "gantt" and render_ok:
                    plan_problems = check_gantt_plan(
                        current_code,
                        plan_start,
                        plan_quarters,
                        plan_max_quarters,
                        max_tasks=max_tasks,
                    )
                if render_ok and not plan_problems:
                    break

        if plan_problems:
            warning = "Plan check: " + "; ".join(plan_problems)
            status_msg = f"{status_msg} | {warning}" if status_msg else warning

        if fmt == "svg":
            pil_image = None
            svg_text = rendered
        else:
            pil_image = rendered
            svg_text = None
        return DiagramGenerationResult(
            plantuml_code=current_code,
            pil_image=pil_image,
            status_message=status_msg,
            image_url="",
            svg_text=svg_text,
            render_ok=render_ok,
            plan_warnings=plan_problems,
        )


def _strip_code_block_markers(text: str) -> str:
    """Remove triple-backtick code fences from a PlantUML snippet."""
    stripped = re.sub(
        r"^```(?:plantuml)?\s*|```$",
        "",
        text.strip(),
        flags=re.MULTILINE,
    )
    return stripped.strip()


def _normalize_curly_braces(plantuml_code: str) -> str:
    """Collapse doubled curly braces from LLM output into single braces."""
    normalized = re.sub(r"\{+", "{", plantuml_code)
    normalized = re.sub(r"\}+", "}", normalized)
    return normalized


def _render_plantuml_jar(
    plantuml_code: str,
    status_msg: str,
    fmt: str = "png",
) -> Tuple[Image.Image | str | None, str, bool]:
    """Render PlantUML code using the local PlantUML JAR.

    Invokes ``java -jar plantuml.jar -t<fmt> -pipe`` with the code on stdin.
    Returns SVG text for fmt="svg", or a PIL Image for fmt="png", plus the
    status message and whether the JAR exited successfully without raising.
    """
    if fmt not in ("png", "svg"):
        fmt = "png"
    jar_path = UMLBotConfig.PLANTUML_JAR_PATH
    try:
        proc = subprocess.run(
            ["java", "-Xmx256m", "-jar", jar_path, f"-t{fmt}", "-pipe"],
            input=plantuml_code.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0:
            stderr_text = proc.stderr.decode("utf-8", errors="replace").strip()
            LOGGER.warning("PlantUML JAR returned non-zero: %s", stderr_text)
            failure_msg = f"PlantUML rendering failed: {stderr_text}"
            if status_msg == UMLBotConfig.DIAGRAM_SUCCESS_MSG:
                status_msg = f"Diagram generated, but rendering failed: {stderr_text}"
            elif status_msg:
                status_msg = f"{status_msg} | {failure_msg}"
            else:
                status_msg = failure_msg
            return None, status_msg, False

        if fmt == "svg":
            return proc.stdout.decode("utf-8"), status_msg, True
        return Image.open(io.BytesIO(proc.stdout)), status_msg, True
    except Exception as exc:
        LOGGER.warning("PlantUML JAR rendering failed: %s", exc)
        failure_msg = f"PlantUML rendering failed: {exc}"
        if status_msg == UMLBotConfig.DIAGRAM_SUCCESS_MSG:
            status_msg = f"Diagram generated, but rendering failed: {exc}"
        elif status_msg:
            status_msg = f"{status_msg} | {failure_msg}"
        else:
            status_msg = failure_msg
        return None, status_msg, False


def _gantt_syntax_hint(start: date | None, quarters: list[Quarter] | None) -> str:
    """Return a mode-aware Gantt repair hint listing allowed dates or D+N offsets."""
    base = GANTT_REPAIR_HINT
    if start is not None and quarters:
        allowed = sorted({value for quarter in quarters for value in (quarter.start, quarter.end)})
        dates = ", ".join(value.isoformat() for value in allowed)
        return f"{base} Dated mode: use only these dates, copied exactly: {dates}."
    return f"{base} No calendar dates; use D+N offsets (D+0 is the first day)."


def _infer_gantt_plan_from_code(code: str) -> tuple[date | None, list[Quarter] | None]:
    """Infer the start date and quarter table from a rendered Gantt snippet."""
    match = re.search(r"Project starts\s+(\d{4}-\d{2}-\d{2})", code)
    if match is None:
        return None, None
    try:
        start = date.fromisoformat(match.group(1))
    except ValueError:
        return None, None
    return start, quarter_table(start)


def _build_repair_prompt(code: str, stderr: str, syntax_hint: str = "") -> str:
    """Build the LLM repair prompt for PlantUML code that failed to render.

    PlantUML reports ``ERROR\\n<line>\\n<message>`` where ``<line>`` is the
    0-based line number in the code sent to the JAR (``@start...`` is line 0).
    The first integer-only line found in ``stderr`` is treated as that line
    number so the offending line text can be included in the prompt.
    """
    line_number: int | None = None
    match = re.search(r"^\s*(\d+)\s*$", stderr or "", re.MULTILINE)
    if match:
        line_number = int(match.group(1))

    offending_line = ""
    if line_number is not None:
        code_lines = code.splitlines()
        if 0 <= line_number < len(code_lines):
            offending_line = code_lines[line_number]

    prompt_parts = [
        "The following PlantUML code failed to render.",
        "",
        "Code:",
        code,
        "",
        "PlantUML error output:",
        stderr or "",
    ]
    if offending_line:
        prompt_parts.extend(["", f"Offending line: {offending_line}"])
    if syntax_hint:
        prompt_parts.extend(["", syntax_hint])
    prompt_parts.extend(
        [
            "",
            "Fix the syntax error and return only the corrected PlantUML code,",
            "with no explanation and no markdown code fences.",
        ]
    )
    return "\n".join(prompt_parts)


def _create_placeholder_image(message: str) -> Image.Image:
    """Create a placeholder image with a short error message."""
    image = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 80), message, fill="red", font=font)
    return image


def _create_placeholder_svg(message: str) -> str:
    """Create a placeholder SVG image with a short error message."""
    truncated = message[:60]
    escaped = escape(truncated)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">'
        '<rect width="400" height="200" fill="white"/>'
        f'<text x="20" y="100" fill="red" font-family="sans-serif" font-size="16">'
        f"{escaped}"
        "</text>"
        "</svg>"
    )
