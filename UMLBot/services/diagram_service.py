"""Diagram generation services and PlantUML rendering helpers."""

from __future__ import annotations

import base64
import io
import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from UMLBot.config.config import UMLBotConfig
from UMLBot.diagram_handlers import (
    C4DraftHandler,
    ERDraftHandler,
    GanttDraftHandler,
    JsonDraftHandler,
    MindmapDraftHandler,
    UIMockupDraftHandler,
    UMLDraftHandler,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class DiagramGenerationResult:
    """Result container for a UML generation request."""
    plantuml_code: str
    pil_image: Image.Image | None
    status_message: str
    image_url: str


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
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )

    def generate_mindmap_from_description(
        self,
        description: str,
        diagram_type: str = "Mindmap",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
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
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )

    def generate_ui_mockup_from_description(
        self,
        description: str,
        diagram_type: str = "salt",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
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
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )

    def generate_gantt_from_description(
        self,
        description: str,
        diagram_type: str = "gantt",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
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
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )

    def generate_erd_from_description(
        self,
        description: str,
        diagram_type: str = "ERD",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
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
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )

    def generate_json_from_description(
        self,
        description: str,
        diagram_type: str = "json",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
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
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )

    def generate_c4_from_description(
        self,
        description: str,
        diagram_type: str = "C4",
        theme: Optional[str] = None,
        openai_compatible_endpoint: str = "",
        openai_compatible_key: str = "",
        openai_compatible_model: str = "",
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
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
        )

    def render_diagram_from_code(self, plantuml_code: str) -> Tuple[Image.Image, str, str]:
        """Re-render an already generated PlantUML snippet via the local JAR.

        Returns a placeholder image if the render fails so the UI can continue gracefully.
        """
        pil_image, status_msg = _render_plantuml_jar(
            plantuml_code=plantuml_code,
            status_msg="Re-rendered from PlantUML code.",
        )
        if pil_image is None:
            pil_image = _create_placeholder_image("Diagram preview unavailable")
        return pil_image, status_msg, ""

    def diagram_image_to_base64(self, image: Image.Image | None) -> Optional[str]:
        """Encode a PIL image to a base64 PNG string."""
        if image is None:
            return None
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

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
    ) -> DiagramGenerationResult:
        """Shared diagram generation pipeline with per-request LLM credentials."""
        handler._init_openai(
            openai_compatible_endpoint=openai_compatible_endpoint,
            openai_compatible_key=openai_compatible_key,
            openai_compatible_model=openai_compatible_model,
            name="UMLBot",
        )

        try:
            plantuml_code = handler.process(
                diagram_type=diagram_type,
                description=description,
                theme=theme,
                llm_interface=handler.llm_interface,
            )
            status_msg = UMLBotConfig.DIAGRAM_SUCCESS_MSG
        except Exception as exc:
            LOGGER.exception(failure_log)
            plantuml_code = fallback_template.format(
                diagram_type=diagram_type,
                description=description,
            )
            status_msg = f"LLM error: {exc}. Showing fallback stub."

        cleaned_code = _strip_code_block_markers(plantuml_code)
        normalized_code = _normalize_curly_braces(cleaned_code)
        pil_image, status_msg = _render_plantuml_jar(
            plantuml_code=normalized_code,
            status_msg=status_msg,
        )
        return DiagramGenerationResult(
            plantuml_code=normalized_code,
            pil_image=pil_image,
            status_message=status_msg,
            image_url="",
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
) -> Tuple[Image.Image | None, str]:
    """Render PlantUML code to a PNG image using the local PlantUML JAR.

    Invokes ``java -jar plantuml.jar -tpng -pipe`` with the code on stdin.
    """
    jar_path = UMLBotConfig.PLANTUML_JAR_PATH
    try:
        proc = subprocess.run(
            ["java", "-jar", jar_path, "-tpng", "-pipe"],
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
            return None, status_msg

        return Image.open(io.BytesIO(proc.stdout)), status_msg
    except Exception as exc:
        LOGGER.warning("PlantUML JAR rendering failed: %s", exc)
        failure_msg = f"PlantUML rendering failed: {exc}"
        if status_msg == UMLBotConfig.DIAGRAM_SUCCESS_MSG:
            status_msg = f"Diagram generated, but rendering failed: {exc}"
        elif status_msg:
            status_msg = f"{status_msg} | {failure_msg}"
        else:
            status_msg = failure_msg
        return None, status_msg


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
