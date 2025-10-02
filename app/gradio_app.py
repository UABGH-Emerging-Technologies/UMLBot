"""
Gradio-based UML Diagram Generator App

- Accepts free-text description and diagram type
- Uses LLM-based NLPParser (llm_utils/aiweb_common/generate)
- Orchestrates DiagramBuilder, Validator, PlantUML rendering, and preview/download
"""
import logging

import gradio as gr
from typing import Tuple, Optional, Any, Callable

# Workaround for local llm_utils and Design_Drafter import
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "llm_utils"))
sys.path.append(str(Path(__file__).parent.parent))

# Import config and LangChain LLM
from Design_Drafter.config.config import Design_DrafterConfig

# Import UMLDraftHandler for diagram generation
from Design_Drafter.uml_draft_handler import UMLDraftHandler
from llm_utils.aiweb_common.generate.GenericErrorHandler import GenericErrorHandler
from llm_utils.aiweb_common.generate.ChatResponse import ChatResponseHandler
from llm_utils.aiweb_common.generate.ChatSchemas import Message, Role, ChatRequest
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

def generate_diagram(description: str, diagram_type: str, theme: Optional[str] = None) -> Tuple[str, Image.Image | None, str]:
    """
    Main handler for diagram generation.
    Returns:
        Tuple[str, Image.Image | None, str]: PlantUML code, PIL image (or None), status message.
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

    # --- UML Change Recommendation Chat UI ---
    gr.Markdown("## UML Change Recommendation Chat")
    with gr.Row():
        chatbox = gr.Chatbot(label="UML Change Suggestions", height=300)
    with gr.Row():
        chat_input = gr.Textbox(label="Suggest a UML Change", placeholder="Describe your recommended change...", lines=2)
        submit_chat_btn = gr.Button("Submit Change Suggestion")

    # State for chat history and context
    chat_state = gr.State([])  # List of (user, message) tuples

    # State for revised UML code (for chat-based revision workflow)
    revised_uml_code = gr.State("")


    def on_chat_submit(user_input, chat_history, plantuml_code_text):
        """
        Handles submission of a UML change suggestion in the chat workflow.
        Calls the LLM backend and updates the chat and diagram preview.
        """

        logging.basicConfig(level=logging.DEBUG)
        if not chat_history:
            chat_history = []
        # Add user suggestion
        chat_history = chat_history + [("user", user_input)]
        # Compose single system message
        system_msg = (
            f"Here's the current PlantUML text:\n"
            "```plantuml\n"
            f"{plantuml_code_text.strip()}\n"
            "```\n"
            f"And here's the description of how I would like it changed:\n"
            f"{user_input}\n"
            "Please return only the updated PlantUML code."
        )
        chat_history = chat_history + [("system", system_msg)]

        # Convert chat_history to list of Message objects
        messages = []
        for role, content in chat_history:
            if role == "user":
                messages.append(Message(role=Role.human, content=content))
            else:
                messages.append(Message(role=Role.ai, content=content))

        # Call the LLM backend
        handler = UMLDraftHandler()
        handler._init_openai(
            openai_compatible_endpoint=Design_DrafterConfig.LLM_API_BASE,
            openai_compatible_key=Design_DrafterConfig.LLM_API_KEY,
            openai_compatible_model=Design_DrafterConfig.LLM_MODEL,
            name="Design_Drafter"
        )
        # LOG the prompt value before passing to ChatResponseHandler
        prompt_value = None
        logging.debug(f"on_chat_submit: passing prompt={prompt_value} to ChatResponseHandler")
        chat_response_handler = ChatResponseHandler(handler.llm_interface, prompt=prompt_value)
        chat_request = ChatRequest(history=messages)
        chat_response = chat_response_handler.generate_response(chat_request.history)

        # Extract updated PlantUML code from response
        updated_plantuml = chat_response.response.content
        chat_history = chat_history + [("system", updated_plantuml)]

        logging.debug(f"on_chat_submit returning: chat_history={chat_history}, chat_input=''")
        return chat_history, ""

    # --- Existing handlers ---
    def on_generate(desc, dtype):
        code, img_bytes, msg = generate_diagram(desc, dtype)
        # IMPORTANT: The code box value is always REPLACED with the new code from the LLM output.
        # It is never appended to previous values.
        # This ensures the code box always reflects only the latest generated diagram.
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
        Only the CURRENT code box value is used to generate the diagram image.
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

    # --- Chat-based UML revision workflow with error handling ---


    # --- UI Logic Wiring ---
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

    # Update UML context display whenever PlantUML code changes

    # Handle chat submission
    submit_chat_btn.click(
        fn=on_chat_submit,
        inputs=[chat_input, chat_state, plantuml_code],
        outputs=[chatbox, chat_input],
        queue=False
    )

    # Add a button for submitting revised UML code (for error correction workflow)


if __name__ == "__main__":
    demo.launch()