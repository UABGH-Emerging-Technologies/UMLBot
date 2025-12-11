"""
Gradio-based UML Diagram Generator App

- Accepts free-text description and diagram type
- Uses LLM-based NLPParser (llm_utils/aiweb_common/generate)
- Orchestrates DiagramBuilder, Validator, PlantUML rendering, and preview/download
"""

import logging
import sys
from pathlib import Path

import gradio as gr
from PIL import Image, ImageDraw, ImageFont

# Workaround for local llm_utils and Design_Drafter import
sys.path.append(str(Path(__file__).parent.parent / "llm_utils"))
sys.path.append(str(Path(__file__).parent.parent))

from Design_Drafter.api_server import create_api_app
from Design_Drafter.config.config import Design_DrafterConfig
from Design_Drafter.services import (
    generate_diagram_from_description,
    render_diagram_from_code,
)
from Design_Drafter.uml_draft_handler import UMLDraftHandler
from llm_utils.aiweb_common.generate.ChatResponse import ChatResponseHandler


with gr.Blocks(title="UML Diagram Generator") as demo:
    gr.Markdown("# UML Diagram Generator")

    # --- UML Change Recommendation Chat UI (moved to top) ---
    gr.Markdown("## UML Chat Interface")
    with gr.Row():
        diagram_type_dropdown = gr.Dropdown(
            choices=Design_DrafterConfig.DIAGRAM_TYPES,
            value=Design_DrafterConfig.DEFAULT_DIAGRAM_TYPE,
            label="Diagram Type",
            interactive=True,
            show_label=True,
        )
        chat_input = gr.Textbox(
            label="UML Chat Input", placeholder="Type your UML question or change...", lines=2
        )
        submit_chat_btn = gr.Button("Send to UML Chat")
    with gr.Row():
        # Make chatbox scrollable and persistent for full history
        chatbox = gr.Chatbot(
            label="UML Chat History",
            height=400,
            type="messages",
            show_copy_button=True,
            show_label=True,
            layout="panel",  # vertical panel layout for clarity
            avatar_images=None,  # can be customized per role if desired
            container=True,  # enables scrollable container
            min_width=400,
            elem_id="uml-chatbox",
            elem_classes=["scrollable-chatbox"],
        )

    # Remove initial text input and diagram type controls
    # Only use the Chat interface for all diagram generation and revision

    with gr.Row():
        plantuml_code = gr.Code(label="Generated PlantUML Code", interactive=True)
        image = gr.Image(label="Diagram Preview")
    status = gr.Markdown("")
    with gr.Row():
        rerender_btn = gr.Button("Re-render from PlantUML code")

    # State for chat history and context
    # State for chat history as list of dicts with explicit role
    chat_state = gr.State(
        []
    )  # List of dicts: {"role": "user"/"assistant"/"system"/"error", "content": ...}

    # State for revised UML code (for chat-based revision workflow)
    revised_uml_code = gr.State("")

    from Design_Drafter.utils.plantuml_extractor import extract_last_plantuml_block

    def format_chat_history(chat_history):
        """
        Formats chat history for display, ensuring all roles are shown and error/system messages are styled.
        Args:
            chat_history (list[dict]): List of chat messages with 'role' and 'content'.
        Returns:
            list[dict]: Formatted chat history for Gradio display.
        """
        formatted = []
        for msg in chat_history:
            if msg["role"] == "error":
                formatted.append({"role": "error", "content": f"❌ {msg['content']}"})
            elif msg["role"] == "system":
                formatted.append({"role": "system", "content": f"ℹ️ {msg['content']}"})
            else:
                formatted.append({"role": msg["role"], "content": msg["content"]})
        return formatted

    # Custom CSS for scrollable chatbox
    gr.HTML(
        """
        <style>
        #uml-chatbox {
            overflow-y: auto !important;
            max-height: 400px !important;
            min-width: 400px;
        }
        </style>
        """
    )

    def on_chat_submit(user_input, chat_history, plantuml_code_text, diagram_type):
        """
        Handles submission of a UML change suggestion in the chat workflow.
        Calls the LLM backend and updates the chat and diagram preview.
        After each response, extracts PlantUML code and updates the code window and diagram preview.
        Robust error handling: if any error occurs, previous code/diagram remain visible and user receives feedback.

        The selected diagram_type is injected into the prompt for the LLM backend.
        """
        logging.basicConfig(level=logging.DEBUG)
        if not chat_history:
            chat_history = []

        # Escape curly braces in user input and PlantUML code to avoid template variable mismatch
        def escape_curly(text: str) -> str:
            return text.replace("{", "{{").replace("}", "}}")

        safe_user_input = escape_curly(user_input)
        safe_plantuml_code = escape_curly(plantuml_code_text.strip())
        # Add user suggestion
        chat_history = chat_history + [{"role": "user", "content": user_input}]
        # Compose single system message, injecting diagram_type
        system_msg = (
            f"Diagram type: {diagram_type}\n"
            f"User request: {safe_user_input}\n"
            f"Current PlantUML code:\n"
            "```plantuml\n"
            f"{safe_plantuml_code}\n"
            "```\n"
            "Please return only the updated PlantUML code."
        )
        chat_history = chat_history + [{"role": "system", "content": system_msg}]

        # Prepare messages for LLM backend (role mapping for ChatResponseHandler)
        messages = []
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append({"role": "human", "content": msg["content"]})
            elif msg["role"] == "assistant":
                messages.append({"role": "ai", "content": msg["content"]})
            elif msg["role"] == "system":
                messages.append({"role": "system", "content": msg["content"]})
            elif msg["role"] == "error":
                messages.append({"role": "error", "content": msg["content"]})

        # Call the LLM backend with retry logic
        handler = UMLDraftHandler()
        handler._init_openai(
            openai_compatible_endpoint=Design_DrafterConfig.LLM_API_BASE,
            openai_compatible_key=Design_DrafterConfig.LLM_API_KEY,
            openai_compatible_model=Design_DrafterConfig.LLM_MODEL,
            name="Design_Drafter",
        )
        from Design_Drafter.uml_draft_handler import UMLRetryManager

        retry_manager = UMLRetryManager(max_retries=3)
        raw_response = None
        error_feedback = ""
        pil_image = None  # Always defined before loop
        for attempt in range(1, retry_manager.max_retries + 1):
            try:
                chat_response_handler = ChatResponseHandler(
                    handler.llm_interface, prompt=system_msg
                )
                chat_response = chat_response_handler.generate_response(messages)
                raw_response = chat_response.response.content
                extracted_plantuml = extract_last_plantuml_block(raw_response)
                plantuml_code_text = extracted_plantuml
                pil_image, status_msg = on_rerender(plantuml_code_text)
                chat_history = chat_history + [{"role": "assistant", "content": raw_response}]
                break
            except Exception as e:
                retry_manager.record_error(e)
                error_msg = f"Attempt {attempt}: UML rendering failed: {e}"
                chat_history = chat_history + [{"role": "error", "content": error_msg}]
                pil_image = None
                status_msg = error_msg
                error_feedback = f"⚠️ {error_msg}"
                if not retry_manager.should_retry():
                    error_feedback += (
                        f"\nMax retries reached. Error context:\n{retry_manager.error_context()}"
                    )
                    break

        # For Gradio Chatbot, display all messages (user, assistant, system, error)
        gradio_chat_history = []
        for msg in chat_history:
            # Format error/system messages for UI clarity
            if msg["role"] == "error":
                gradio_chat_history.append({"role": "error", "content": f"❌ {msg['content']}"})
            elif msg["role"] == "system":
                gradio_chat_history.append({"role": "system", "content": f"ℹ️ {msg['content']}"})
            else:
                gradio_chat_history.append({"role": msg["role"], "content": msg["content"]})

        # Return chat history, clear chat input, update code window, image, and status
        # Ensure pil_image is always defined
        return gradio_chat_history, "", plantuml_code_text, pil_image, error_feedback

    # --- Existing handlers ---
    def _placeholder_image(width: int = 600, height: int = 300) -> Image.Image:
        image = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
        draw.text((20, 80), "Diagram preview unavailable", fill="red", font=font)
        return image

    def on_generate(desc, dtype):
        result = generate_diagram_from_description(desc, dtype)
        pil_image = result.pil_image or _placeholder_image()
        return result.plantuml_code, pil_image, result.status_message

    def on_rerender(plantuml_code_text):
        """
        Re-render diagram image from user-edited PlantUML code.
        Does not change the code box content.
        Only the CURRENT code box value is used to generate the diagram image.
        """
        pil_image, status_msg, _ = render_diagram_from_code(plantuml_code_text)
        return pil_image, status_msg

    # --- Chat-based UML revision workflow with error handling ---

    # --- UI Logic Wiring ---
    # Remove generate_btn.click wiring, as diagram generation is now handled via chat only

    rerender_btn.click(fn=on_rerender, inputs=[plantuml_code], outputs=[image, status])

    # Update UML context display whenever PlantUML code changes

    # Handle chat submission
    submit_chat_btn.click(
        fn=on_chat_submit,
        inputs=[chat_input, chat_state, plantuml_code, diagram_type_dropdown],
        outputs=[chatbox, chat_input, plantuml_code, image, status],
        queue=False,
    )

    # Add a button for submitting revised UML code (for error correction workflow)
app = gr.mount_gradio_app(create_api_app(), demo, path="/")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
