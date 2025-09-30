"""
Gradio-based UML Diagram Generator App

- Accepts free-text description and diagram type
- Uses LLM-based NLPParser (llm_utils/aiweb_common/generate)
- Orchestrates DiagramBuilder, Validator, PlantUML rendering, and preview/download
"""

import gradio as gr
from typing import Tuple, Optional

# Workaround for local llm_utils and Design_Drafter import
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "llm_utils"))
sys.path.append(str(Path(__file__).parent.parent))

# Import config and LangChain LLM
from Design_Drafter.config.config import Design_DrafterConfig

# Import UMLDraftHandler for diagram generation
from Design_Drafter.uml_draft_handler import UMLDraftHandler

# Use config for diagram types

import requests
import io
from PIL import Image, ImageDraw, ImageFont

import re
import zlib
import base64

def _plantuml_encode(text: str) -> str:
    """
    Encodes PlantUML text for PlantUML server URL (raw deflate + PlantUML base64).
    """
    # Raw deflate (no zlib header/footer)
    compressor = zlib.compressobj(level=9, wbits=-15)
    data = compressor.compress(text.encode("utf-8")) + compressor.flush()
    # Standard base64
    b64 = base64.b64encode(data).decode("utf-8")
    # PlantUML custom base64 alphabet for URLs
    # See: https://plantuml.com/text-encoding
    trans = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
    )
    return b64.translate(trans)

def generate_diagram(description: str, diagram_type: str, theme: Optional[str] = None) -> Tuple[Optional[str], Optional[bytes], Optional[str]]:
    """
    Main handler for diagram generation.
    Returns: (PlantUML code, image bytes, status message)
    """
    # Securely retrieve the API key using manage_sensitive

    try:
        api_key = Design_DrafterConfig.LLM_API_KEY
    except KeyError:
        return (
            "",
            None,
            Design_DrafterConfig.API_KEY_MISSING_MSG
        )

    # Instantiate UMLDraftHandler
    handler = UMLDraftHandler()
    handler._init_openai(
        openai_compatible_endpoint = Design_DrafterConfig.LLM_API_BASE, 
        openai_compatible_key = api_key,
        openai_compatible_model = Design_DrafterConfig.LLM_MODEL,
        name = "Design_Drafter"
    )
    
    # Generate diagram using handler
    try:
        plantuml_code = handler.process(
            diagram_type=diagram_type,
            description=description,
            theme=theme,
            llm_interface=handler.llm_interface
        )
        status_msg = Design_DrafterConfig.DIAGRAM_SUCCESS_MSG
    except Exception as e:
        plantuml_code = Design_DrafterConfig.FALLBACK_PLANTUML_TEMPLATE.format(
            diagram_type=diagram_type, description=description
        )
        status_msg = f"LLM error: {e}. Showing fallback stub."

    # --- Strip code block markers and whitespace ---
    plantuml_code = re.sub(r"^```(?:plantuml)?\s*|```$", "", plantuml_code.strip(), flags=re.MULTILINE).strip()

    # --- Proper PlantUML encoding (deflate+base64+URL-safe) ---
    encoded = _plantuml_encode(plantuml_code)
    image_url = Design_DrafterConfig.PLANTUML_SERVER_URL_TEMPLATE.format(encoded=encoded)

    # Fetch image from PlantUML server
    image_bytes = None
    pil_image = None
    try:
        resp = requests.get(image_url, timeout=10)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if content_type != "image/png":
            status_msg += f" | PlantUML server error: Unexpected content-type '{content_type}'."
            pil_image = None
        else:
            image_bytes = resp.content
            try:
                pil_image = Image.open(io.BytesIO(image_bytes))
            except Exception as img_err:
                status_msg += f" | Image conversion failed: {img_err}"
                pil_image = None
    except Exception as fetch_err:
        status_msg += f" | Diagram rendering failed: {fetch_err}"

    return plantuml_code, pil_image, status_msg


with gr.Blocks(title="UML Diagram Generator") as demo:
    gr.Markdown("# UML Diagram Generator")

    with gr.Row():
        description = gr.Textbox(label="Diagram Description", lines=6, placeholder="Describe your UML diagram...")
        diagram_type = gr.Dropdown(
            label="Diagram Type",
            choices=Design_DrafterConfig.DIAGRAM_TYPES,
            value=Design_DrafterConfig.DIAGRAM_TYPES[0]
        )
    with gr.Row():
        gr.Markdown("**Click to send your description to the LLM and generate a UML diagram.**")
        generate_btn = gr.Button("Send to LLM")
    with gr.Row():
        plantuml_code = gr.Code(label="Generated PlantUML Code", interactive=True)
        image = gr.Image(label="Diagram Preview")
    status = gr.Markdown("")
    with gr.Row():
        rerender_btn = gr.Button("Re-render from PlantUML code")

    def on_generate(desc, dtype):
        code, img_bytes, msg = generate_diagram(desc, dtype)
        # If image is None, show a placeholder error image in preview
        if img_bytes is None:
            # Create a simple error image (red X or text)
            from PIL import ImageDraw, ImageFont
            error_img = Image.new("RGB", (600, 300), color="white")
            draw = ImageDraw.Draw(error_img)
            # Try to use a default font, fallback if not available
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except Exception:
                font = ImageFont.load_default()
            draw.text((20, 80), "Diagram preview unavailable", fill="red", font=font)
            img_bytes = error_img
        return code, img_bytes, msg

    def on_rerender(plantuml_code_text):
        """
        Re-render diagram image from user-edited PlantUML code.
        Does not change the code box content.
        """
        # --- Proper PlantUML encoding (deflate+base64+URL-safe) ---
        encoded = _plantuml_encode(plantuml_code_text)
        image_url = Design_DrafterConfig.PLANTUML_SERVER_URL_TEMPLATE.format(encoded=encoded)
        status_msg = "Re-rendered from PlantUML code."
        image_bytes = None
        pil_image = None
        try:
            resp = requests.get(image_url, timeout=10)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if content_type != "image/png":
                status_msg += f" | PlantUML server error: Unexpected content-type '{content_type}'."
                pil_image = None
            else:
                image_bytes = resp.content
                try:
                    pil_image = Image.open(io.BytesIO(image_bytes))
                except Exception as img_err:
                    status_msg += f" | Image conversion failed: {img_err}"
                    pil_image = None
        except Exception as fetch_err:
            status_msg += f" | Diagram rendering failed: {fetch_err}"
        # If image is None, show a placeholder error image in preview
        if pil_image is None:
            error_img = Image.new("RGB", (400, 200), color="white")
            draw = ImageDraw.Draw(error_img)
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except Exception:
                font = ImageFont.load_default()
            draw.text((20, 80), "Diagram preview unavailable", fill="red", font=font)
            pil_image = error_img
        return pil_image, status_msg

    generate_btn.click(
        fn=on_generate,
        inputs=[description, diagram_type],
        outputs=[plantuml_code, image, status]
    )

    rerender_btn.click(
        fn=on_rerender,
        inputs=[plantuml_code],
        outputs=[image, status]
    )

if __name__ == "__main__":
    demo.launch()