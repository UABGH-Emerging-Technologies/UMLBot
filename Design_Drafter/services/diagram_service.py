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

from Design_Drafter.config.config import Design_DrafterConfig
from Design_Drafter.uml_draft_handler import UMLDraftHandler

LOGGER = logging.getLogger(__name__)


@dataclass
class DiagramGenerationResult:
    plantuml_code: str
    pil_image: Image.Image | None
    status_message: str
    image_url: str


def generate_diagram_from_description(
    description: str,
    diagram_type: str,
    theme: Optional[str] = None,
) -> DiagramGenerationResult:
    """
    Runs the UMLDraftHandler pipeline and returns the PlantUML code plus the rendered image.
    Errors are converted to a fallback PlantUML stub with contextual messaging.
    """
    try:
        api_key = Design_DrafterConfig.LLM_API_KEY
    except KeyError:
        return DiagramGenerationResult(
            plantuml_code="",
            pil_image=None,
            status_message=Design_DrafterConfig.API_KEY_MISSING_MSG,
            image_url="",
        )

    handler = UMLDraftHandler()
    handler._init_openai(
        openai_compatible_endpoint=Design_DrafterConfig.LLM_API_BASE,
        openai_compatible_key=api_key,
        openai_compatible_model=Design_DrafterConfig.LLM_MODEL,
        name="Design_Drafter",
    )

    try:
        plantuml_code = handler.process(
            diagram_type=diagram_type,
            description=description,
            theme=theme,
            llm_interface=handler.llm_interface,
        )
        status_msg = Design_DrafterConfig.DIAGRAM_SUCCESS_MSG
    except Exception as exc:
        LOGGER.exception("LLM-backed generation failed, returning fallback diagram.")
        plantuml_code = Design_DrafterConfig.FALLBACK_PLANTUML_TEMPLATE.format(
            diagram_type=diagram_type,
            description=description,
        )
        status_msg = f"LLM error: {exc}. Showing fallback stub."

    cleaned_code = _strip_code_block_markers(plantuml_code)
    normalized_code = _normalize_curly_braces(cleaned_code)
    image_url = build_plantuml_image_url(normalized_code)
    pil_image, status_msg = _fetch_plantuml_image(
        image_url=image_url,
        status_msg=status_msg,
    )
    if pil_image is None:
        image_url = ""
    return DiagramGenerationResult(
        plantuml_code=normalized_code,
        pil_image=pil_image,
        status_message=status_msg,
        image_url=image_url,
    )


def render_diagram_from_code(plantuml_code: str) -> Tuple[Image.Image, str, str]:
    """
    Re-renders an already generated PlantUML snippet.
    Returns a placeholder image if the render fails so the UI can continue gracefully.
    """
    image_url = build_plantuml_image_url(plantuml_code)
    pil_image, status_msg = _fetch_plantuml_image(
        image_url=image_url,
        status_msg="Re-rendered from PlantUML code.",
    )
    if pil_image is None:
        pil_image = _create_placeholder_image("Diagram preview unavailable")
    return pil_image, status_msg, image_url


def diagram_image_to_base64(image: Image.Image | None) -> Optional[str]:
    if image is None:
        return None
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def build_plantuml_image_url(plantuml_code: str) -> str:
    encoded = _plantuml_encode(plantuml_code)
    return Design_DrafterConfig.PLANTUML_SERVER_URL_TEMPLATE.format(encoded=encoded)


def _strip_code_block_markers(text: str) -> str:
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
    try:
        resp = requests.get(image_url, timeout=10)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if content_type != "image/png":
            status_msg += f" | PlantUML server error: Unexpected content-type '{content_type}'."
            return None, status_msg
        return Image.open(io.BytesIO(resp.content)), status_msg
    except Exception as exc:
        LOGGER.warning("PlantUML rendering failed: %s", exc)
        failure_msg = f"PlantUML rendering failed: {exc}"
        if status_msg == Design_DrafterConfig.DIAGRAM_SUCCESS_MSG:
            status_msg = f"Diagram generated, but rendering failed: {exc}"
        elif status_msg:
            status_msg = f"{status_msg} | {failure_msg}"
        else:
            status_msg = failure_msg
        return None, status_msg


def _create_placeholder_image(message: str) -> Image.Image:
    image = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 80), message, fill="red", font=font)
    return image


def _plantuml_encode(text: str) -> str:
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(text.encode("utf-8")) + compressor.flush()
    b64 = base64.b64encode(compressed).decode("utf-8")
    translation = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_",
    )
    return b64.translate(translation)
