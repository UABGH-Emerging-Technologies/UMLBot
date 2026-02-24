"""Diagram generation services and PlantUML rendering helpers."""

from __future__ import annotations

import base64
import io
import logging
import re
import zlib
from dataclasses import dataclass
from typing import Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont

from UMLBot.config.config import UMLBotConfig
from UMLBot.uml_draft_handler import UMLDraftHandler
from UMLBot.mindmap_draft_handler import MindmapDraftHandler
from UMLBot.ui_mockup_draft_handler import UIMockupDraftHandler
from UMLBot.gantt_draft_handler import GanttDraftHandler
from UMLBot.er_draft_handler import ERDraftHandler

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
    ) -> DiagramGenerationResult:
        """
        Runs the UMLDraftHandler pipeline and returns the PlantUML code plus the rendered image.
        Errors are converted to a fallback PlantUML stub with contextual messaging.
        """
        handler = UMLDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_PLANTUML_TEMPLATE,
            failure_log="LLM-backed generation failed, returning fallback diagram.",
        )

    def generate_mindmap_from_description(
        self,
        description: str,
        diagram_type: str = "Mindmap",
        theme: Optional[str] = None,
    ) -> DiagramGenerationResult:
        """
        Runs the MindmapDraftHandler pipeline and returns the PlantUML code plus the rendered image.
        Errors are converted to a fallback mindmap stub with contextual messaging.
        """
        handler = MindmapDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_MINDMAP_TEMPLATE,
            failure_log="LLM-backed mindmap generation failed, returning fallback diagram.",
        )

    def generate_ui_mockup_from_description(
        self,
        description: str,
        diagram_type: str = "salt",
        theme: Optional[str] = None,
    ) -> DiagramGenerationResult:
        """
        Runs the UIMockupDraftHandler pipeline and returns the PlantUML SALT code plus the rendered image.
        Errors are converted to a fallback SALT stub with contextual messaging.
        """
        handler = UIMockupDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_SALT_TEMPLATE,
            failure_log="LLM-backed UI mockup generation failed, returning fallback diagram.",
        )

    def generate_gantt_from_description(
        self,
        description: str,
        diagram_type: str = "gantt",
        theme: Optional[str] = None,
    ) -> DiagramGenerationResult:
        """
        Runs the GanttDraftHandler pipeline and returns the PlantUML Gantt code plus the rendered image.
        Errors are converted to a fallback Gantt stub with contextual messaging.
        """
        handler = GanttDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_GANTT_TEMPLATE,
            failure_log="LLM-backed Gantt generation failed, returning fallback diagram.",
        )

    def generate_erd_from_description(
        self,
        description: str,
        diagram_type: str = "ERD",
        theme: Optional[str] = None,
    ) -> DiagramGenerationResult:
        """
        Runs the ERDraftHandler pipeline and returns the PlantUML ER diagram code plus the rendered image.
        Errors are converted to a fallback ER diagram stub with contextual messaging.
        """
        handler = ERDraftHandler()
        return self._generate_from_description(
            handler=handler,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
            fallback_template=UMLBotConfig.FALLBACK_ERD_TEMPLATE,
            failure_log="LLM-backed ERD generation failed, returning fallback diagram.",
        )

    def render_diagram_from_code(self, plantuml_code: str) -> Tuple[Image.Image, str, str]:
        """
        Re-renders an already generated PlantUML snippet.
        Returns a placeholder image if the render fails so the UI can continue gracefully.
        """
        image_url = self.build_plantuml_image_url(plantuml_code)
        pil_image, status_msg = _fetch_plantuml_image(
            image_url=image_url,
            status_msg="Re-rendered from PlantUML code.",
        )
        if pil_image is None:
            pil_image = _create_placeholder_image("Diagram preview unavailable")
        return pil_image, status_msg, image_url

    def diagram_image_to_base64(self, image: Image.Image | None) -> Optional[str]:
        """Encode a PIL image to a base64 PNG string."""
        if image is None:
            return None
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def build_plantuml_image_url(self, plantuml_code: str) -> str:
        """Build a PlantUML render URL for the given diagram code."""
        encoded = _plantuml_encode(plantuml_code)
        return self._build_plantuml_url(UMLBotConfig.PLANTUML_SERVER_URL_TEMPLATE, encoded)

    def _build_plantuml_url(self, template: str, encoded: str) -> str:
        """
        Support both full templates (with {encoded}) and base URLs.
        """
        if "{encoded}" in template:
            return template.format(encoded=encoded)
        base = template.rstrip("/")
        return f"{base}/{encoded}"

    def _resolve_llm_api_key(self) -> str:
        try:
            return UMLBotConfig.LLM_API_KEY
        except KeyError:
            return ""

    def _validate_llm_config(self) -> DiagramGenerationResult | None:
        api_key = self._resolve_llm_api_key()
        if not api_key or not UMLBotConfig.LLM_API_BASE:
            return DiagramGenerationResult(
                plantuml_code="",
                pil_image=None,
                status_message=UMLBotConfig.API_KEY_MISSING_MSG,
                image_url="",
            )
        return None

    def _generate_from_description(
        self,
        handler: UMLDraftHandler,
        description: str,
        diagram_type: str,
        theme: Optional[str],
        fallback_template: str,
        failure_log: str,
    ) -> DiagramGenerationResult:
        """Shared diagram/mindmap generation pipeline with LLM initialization and rendering."""
        missing_config = self._validate_llm_config()
        if missing_config is not None:
            return missing_config

        handler._init_openai(
            openai_compatible_endpoint=UMLBotConfig.LLM_API_BASE,
            openai_compatible_key=self._resolve_llm_api_key(),
            openai_compatible_model=UMLBotConfig.LLM_MODEL,
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
        image_url = self.build_plantuml_image_url(normalized_code)
        pil_image, status_msg = _fetch_plantuml_image(
            image_url=image_url,
            status_msg=status_msg,
        )
        return DiagramGenerationResult(
            plantuml_code=normalized_code,
            pil_image=pil_image,
            status_message=status_msg,
            image_url=image_url,
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
    """
    PlantUML expects single curly braces for container nodes.
    Sometimes LLM output contains doubled braces like {{ ... }}, which breaks rendering.
    Collapse any repeated opening/closing braces into a single brace.
    """
    normalized = re.sub(r"\{+", "{", plantuml_code)
    normalized = re.sub(r"\}+", "}", normalized)
    return normalized


def _fetch_plantuml_image(
    image_url: str,
    status_msg: str,
) -> Tuple[Image.Image | None, str]:
    """Fetch and decode a PlantUML PNG image from the render server."""
    try:
        resp = requests.get(image_url, timeout=10)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("image/png"):
            status_msg += f" | PlantUML server error: Unexpected content-type '{content_type}'."
            return None, status_msg
        return Image.open(io.BytesIO(resp.content)), status_msg
    except Exception as exc:
        LOGGER.warning("PlantUML rendering failed: %s", exc)
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


def _plantuml_encode(text: str) -> str:
    """Encode PlantUML text for the server URL format."""
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(text.encode("utf-8")) + compressor.flush()
    b64 = base64.b64encode(compressed).decode("utf-8")
    translation = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_",
    )
    return b64.translate(translation)
