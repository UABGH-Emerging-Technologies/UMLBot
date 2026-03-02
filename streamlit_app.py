"""
Streamlit-based UMLBot frontend.

Communicates with the FastAPI backend API endpoints to generate and render
PlantUML diagrams across all supported diagram types.
"""

import base64
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# Workaround for local llm_utils and UMLBot import
repo_root = Path(__file__).resolve().parent
sys.path.append(str(repo_root / "llm_utils"))
sys.path.append(str(repo_root))

from aiweb_common.streamlit.page_renderer import StreamlitUIHelper
from UMLBot.config.config import UMLBotConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODE_LABELS: Dict[str, str] = {
    "uml": "UML Diagram",
    "mindmap": "Mindmap",
    "ui_mockup": "UI Mockup (SALT)",
    "gantt": "Gantt Chart",
    "erd": "ER Diagram",
    "json": "JSON",
    "c4": "C4 Diagram",
}

# (generate_path, render_path, default_diagram_type)
ENDPOINT_MAP: Dict[str, tuple] = {
    "uml": ("/api/generate", "/api/render", "Use Case"),
    "mindmap": ("/api/mindmap/generate", "/api/mindmap/render", "Mindmap"),
    "ui_mockup": ("/api/ui-mockup/generate", "/api/ui-mockup/render", "salt"),
    "gantt": ("/api/gantt/generate", "/api/gantt/render", "gantt"),
    "erd": ("/api/erd/generate", "/api/erd/render", "ERD"),
    "json": ("/api/json/generate", "/api/json/render", "json"),
    "c4": ("/api/c4/generate", "/api/c4/render", "C4"),
}

DEFAULT_TEMPLATES: Dict[str, str] = {
    "uml": UMLBotConfig.FALLBACK_PLANTUML_TEMPLATE.format(
        diagram_type="Use Case", description="placeholder"
    ),
    "mindmap": UMLBotConfig.FALLBACK_MINDMAP_TEMPLATE.format(
        diagram_type="Mindmap", description="placeholder"
    ),
    "ui_mockup": UMLBotConfig.FALLBACK_SALT_TEMPLATE.format(
        diagram_type="salt", description="placeholder"
    ),
    "gantt": UMLBotConfig.FALLBACK_GANTT_TEMPLATE,
    "erd": UMLBotConfig.FALLBACK_ERD_TEMPLATE,
    "json": UMLBotConfig.FALLBACK_JSON_TEMPLATE,
    "c4": UMLBotConfig.FALLBACK_C4_TEMPLATE.format(
        diagram_type="C4", description="placeholder"
    ),
}

MAX_HISTORY_MESSAGES: int = 10

# ---------------------------------------------------------------------------
# Fence markers per mode (for prompt instructions)
# ---------------------------------------------------------------------------

_FENCE_MARKERS: Dict[str, str] = {
    "uml": "@startuml and @enduml",
    "mindmap": "@startmindmap and @endmindmap",
    "ui_mockup": "@startsalt and @endsalt",
    "gantt": "@startgantt and @endgantt",
    "erd": "@startuml and @enduml",
    "json": "@startjson and @endjson",
    "c4": "@startuml and @enduml with C4-PlantUML includes",
}

_MODE_FRIENDLY: Dict[str, str] = {
    "uml": "UML",
    "mindmap": "mindmap",
    "ui_mockup": "UI mockup",
    "gantt": "Gantt",
    "erd": "ERD",
    "json": "JSON",
    "c4": "C4",
}

# ---------------------------------------------------------------------------
# API Client
# ---------------------------------------------------------------------------

ApiResponse = Dict[str, Any]


def api_generate(
    backend_url: str,
    mode: str,
    description: str,
    diagram_type: str,
    theme: Optional[str] = None,
) -> ApiResponse:
    """Call the backend generate endpoint for the given mode.

    Args:
        backend_url: Base URL of the FastAPI backend (e.g. ``http://localhost:7860``).
        mode: Diagram mode key (``uml``, ``mindmap``, etc.).
        description: User description / prompt to send.
        diagram_type: Specific diagram sub-type (e.g. ``Class``, ``Sequence``).
        theme: Optional PlantUML theme name.

    Returns:
        Dict with keys: status, plantuml_code, image_base64, image_url, message.
    """
    generate_path = ENDPOINT_MAP[mode][0]
    url = f"{backend_url.rstrip('/')}{generate_path}"
    payload: Dict[str, Any] = {
        "description": description,
        "diagram_type": diagram_type,
    }
    if theme:
        payload["theme"] = theme
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": data.get("status", "ok"),
            "plantuml_code": data.get("plantuml_code", ""),
            "image_base64": data.get("image_base64"),
            "image_url": data.get("image_url", ""),
            "message": data.get("message", ""),
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "plantuml_code": "",
            "image_base64": None,
            "image_url": "",
            "message": "Request timed out. The backend may be overloaded.",
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "plantuml_code": "",
            "image_base64": None,
            "image_url": "",
            "message": f"Cannot connect to backend at {backend_url}. Is it running?",
        }
    except requests.exceptions.HTTPError as exc:
        body = {}
        try:
            body = exc.response.json()
        except Exception:
            pass
        return {
            "status": "error",
            "plantuml_code": "",
            "image_base64": None,
            "image_url": "",
            "message": body.get("message", f"HTTP {exc.response.status_code}"),
        }
    except Exception as exc:
        return {
            "status": "error",
            "plantuml_code": "",
            "image_base64": None,
            "image_url": "",
            "message": str(exc),
        }


def api_render(
    backend_url: str,
    mode: str,
    plantuml_code: str,
) -> ApiResponse:
    """Call the backend render endpoint for the given mode.

    Args:
        backend_url: Base URL of the FastAPI backend.
        mode: Diagram mode key.
        plantuml_code: Raw PlantUML code to render.

    Returns:
        Dict with keys: status, image_base64, image_url, message.
    """
    render_path = ENDPOINT_MAP[mode][1]
    url = f"{backend_url.rstrip('/')}{render_path}"
    payload = {"plantuml_code": plantuml_code}
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": data.get("status", "ok"),
            "plantuml_code": plantuml_code,
            "image_base64": data.get("image_base64"),
            "image_url": data.get("image_url", ""),
            "message": data.get("message", ""),
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "plantuml_code": plantuml_code,
            "image_base64": None,
            "image_url": "",
            "message": "Render request timed out.",
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "plantuml_code": plantuml_code,
            "image_base64": None,
            "image_url": "",
            "message": f"Cannot connect to backend at {backend_url}. Is it running?",
        }
    except requests.exceptions.HTTPError as exc:
        body = {}
        try:
            body = exc.response.json()
        except Exception:
            pass
        return {
            "status": "error",
            "plantuml_code": plantuml_code,
            "image_base64": None,
            "image_url": "",
            "message": body.get("message", f"HTTP {exc.response.status_code}"),
        }
    except Exception as exc:
        return {
            "status": "error",
            "plantuml_code": plantuml_code,
            "image_base64": None,
            "image_url": "",
            "message": str(exc),
        }


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------


def _summarize_chat_history(history: List[Dict[str, str]]) -> str:
    """Return a newline-joined summary of the most recent chat messages.

    Args:
        history: Full chat history list of ``{"role": ..., "content": ...}`` dicts.

    Returns:
        String summary of the last ``MAX_HISTORY_MESSAGES`` messages.
    """
    recent = history[-MAX_HISTORY_MESSAGES:]
    lines: List[str] = []
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _build_prompt_description(
    user_request: str,
    current_code: str,
    chat_history: List[Dict[str, str]],
    mode: str,
    diagram_type: str,
) -> str:
    """Compose a full description to send as the ``description`` field to the backend.

    Mirrors the Next.js ``buildPromptDescription`` function.

    Args:
        user_request: Latest user message.
        current_code: Current PlantUML code in the editor (may be empty).
        chat_history: Full chat history.
        mode: Diagram mode key.
        diagram_type: Specific diagram sub-type.

    Returns:
        Composed description string for the backend.
    """
    fence = _FENCE_MARKERS.get(mode, "@startuml and @enduml")
    friendly = _MODE_FRIENDLY.get(mode, "UML")

    code_label = (
        f"Existing PlantUML {friendly} diagram (reuse and refine rather than restart):"
        if current_code.strip()
        else f"No {friendly} diagram has been created yet. Create a fresh PlantUML {friendly} diagram."
    )

    chat_summary = _summarize_chat_history(chat_history)

    sections: List[str] = [
        f"You are an expert {friendly} assistant following the prompty template rules.",
        f"Diagram Type: {diagram_type}",
        f"Generate valid PlantUML enclosed between {fence} with concise, professional notation. "
        "No extra prose or markdown fences.",
        f"Latest user request:\n{user_request}",
    ]

    if current_code.strip():
        sections.append(f"{code_label}\n{current_code}")
    else:
        sections.append(code_label)

    if chat_summary:
        sections.append(f"Recent conversation:\n{chat_summary}")

    sections.append(f"Respond with PlantUML only between {fence}.")

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Session State Helpers
# ---------------------------------------------------------------------------


def _state_key(mode: str, field: str) -> str:
    """Build a session-state key scoped to a diagram mode.

    Args:
        mode: Diagram mode key (e.g. ``uml``, ``mindmap``).
        field: Field name (e.g. ``chat_history``, ``plantuml_code``).

    Returns:
        Key string like ``"chat_history_mindmap"``.
    """
    return f"{field}_{mode}"


def _init_session_state() -> None:
    """Initialise all per-mode and global session state keys if absent."""
    for mode in MODE_LABELS:
        for field, default in [
            ("chat_history", []),
            ("plantuml_code", ""),
            ("image_base64", None),
            ("status_message", ""),
            ("error_message", ""),
        ]:
            key = _state_key(mode, field)
            if key not in st.session_state:
                st.session_state[key] = default

    # Global state
    if "backend_url" not in st.session_state:
        st.session_state["backend_url"] = "http://localhost:7860"
    if "theme" not in st.session_state:
        st.session_state["theme"] = ""
    if "uml_subtype" not in st.session_state:
        st.session_state["uml_subtype"] = UMLBotConfig.DEFAULT_DIAGRAM_TYPE


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar(ui: StreamlitUIHelper, current_mode: str) -> None:
    """Render the sidebar controls.

    Args:
        ui: StreamlitUIHelper instance.
        current_mode: Active diagram mode key.
    """
    with st.sidebar:
        ui.header("Settings")

        st.session_state["backend_url"] = ui.text_input(
            "Backend URL",
            value=st.session_state["backend_url"],
            key="sidebar_backend_url",
        )

        st.session_state["theme"] = ui.text_input(
            "PlantUML Theme (optional)",
            value=st.session_state["theme"],
            key="sidebar_theme",
        )

        ui.markdown("---")

        if ui.button("Clear Chat History", key="clear_history"):
            st.session_state[_state_key(current_mode, "chat_history")] = []
            st.session_state[_state_key(current_mode, "status_message")] = ""
            st.session_state[_state_key(current_mode, "error_message")] = ""
            st.rerun()

        # Download PlantUML code
        code = st.session_state.get(_state_key(current_mode, "plantuml_code"), "")
        if code:
            ui.download_button(
                label="Download PlantUML Code",
                data=code,
                file_name=f"{current_mode}_diagram.puml",
                mime="text/plain",
                key="dl_code",
            )

        # Download image
        img_b64 = st.session_state.get(_state_key(current_mode, "image_base64"))
        if img_b64:
            img_bytes = base64.b64decode(img_b64)
            ui.download_button(
                label="Download Image (PNG)",
                data=img_bytes,
                file_name=f"{current_mode}_diagram.png",
                mime="image/png",
                key="dl_image",
            )


# ---------------------------------------------------------------------------
# Tab Rendering
# ---------------------------------------------------------------------------


def _handle_chat_input(
    ui: StreamlitUIHelper,
    mode: str,
    user_message: str,
) -> None:
    """Process a new chat message: call backend generate, update state.

    Args:
        ui: StreamlitUIHelper instance.
        mode: Diagram mode key.
        user_message: The user's chat input.
    """
    history_key = _state_key(mode, "chat_history")
    code_key = _state_key(mode, "plantuml_code")
    img_key = _state_key(mode, "image_base64")
    status_key = _state_key(mode, "status_message")
    error_key = _state_key(mode, "error_message")

    # Append user message
    history: List[Dict[str, str]] = st.session_state[history_key]
    history.append({"role": "user", "content": user_message})

    current_code = st.session_state.get(code_key, "")

    # Determine diagram_type
    if mode == "uml":
        diagram_type = st.session_state.get("uml_subtype", UMLBotConfig.DEFAULT_DIAGRAM_TYPE)
    else:
        diagram_type = ENDPOINT_MAP[mode][2]

    description = _build_prompt_description(
        user_request=user_message,
        current_code=current_code,
        chat_history=history,
        mode=mode,
        diagram_type=diagram_type,
    )

    theme = st.session_state.get("theme") or None

    with ui.spinner("Generating diagram..."):
        result = api_generate(
            backend_url=st.session_state["backend_url"],
            mode=mode,
            description=description,
            diagram_type=diagram_type,
            theme=theme,
        )

    if result["status"] == "ok":
        if result["plantuml_code"]:
            st.session_state[code_key] = result["plantuml_code"]
        if result["image_base64"]:
            st.session_state[img_key] = result["image_base64"]
        st.session_state[status_key] = result.get("message", "Diagram generated.")
        st.session_state[error_key] = ""
        history.append(
            {"role": "assistant", "content": result.get("message", "Diagram generated.")}
        )
    else:
        st.session_state[error_key] = result.get("message", "Generation failed.")
        st.session_state[status_key] = ""
        history.append({"role": "assistant", "content": f"Error: {result.get('message', '')}"})

    st.session_state[history_key] = history


def _handle_rerender(
    ui: StreamlitUIHelper,
    mode: str,
) -> None:
    """Re-render diagram from the current code in the editor.

    Args:
        ui: StreamlitUIHelper instance.
        mode: Diagram mode key.
    """
    code_key = _state_key(mode, "plantuml_code")
    img_key = _state_key(mode, "image_base64")
    status_key = _state_key(mode, "status_message")
    error_key = _state_key(mode, "error_message")

    code = st.session_state.get(code_key, "")
    if not code.strip():
        st.session_state[error_key] = "No PlantUML code to render."
        return

    with ui.spinner("Rendering diagram..."):
        result = api_render(
            backend_url=st.session_state["backend_url"],
            mode=mode,
            plantuml_code=code,
        )

    if result["status"] == "ok" and result["image_base64"]:
        st.session_state[img_key] = result["image_base64"]
        st.session_state[status_key] = result.get("message", "Rendered successfully.")
        st.session_state[error_key] = ""
    else:
        st.session_state[error_key] = result.get("message", "Rendering failed.")
        st.session_state[status_key] = ""


def _render_mode_tab(ui: StreamlitUIHelper, mode: str) -> None:
    """Render the contents of a single diagram mode tab.

    Args:
        ui: StreamlitUIHelper instance.
        mode: Diagram mode key.
    """
    history_key = _state_key(mode, "chat_history")
    code_key = _state_key(mode, "plantuml_code")
    img_key = _state_key(mode, "image_base64")
    status_key = _state_key(mode, "status_message")
    error_key = _state_key(mode, "error_message")

    # UML sub-type dropdown (only for uml mode)
    if mode == "uml":
        st.session_state["uml_subtype"] = ui.selectbox(
            "UML Diagram Type",
            options=UMLBotConfig.DIAGRAM_TYPES,
            index=UMLBotConfig.DIAGRAM_TYPES.index(
                st.session_state.get("uml_subtype", UMLBotConfig.DEFAULT_DIAGRAM_TYPE)
            ),
            key=f"uml_subtype_select_{mode}",
        )

    # Chat history display
    history: List[Dict[str, str]] = st.session_state.get(history_key, [])
    for msg in history:
        role = msg.get("role", "user")
        display_role = "user" if role == "user" else "assistant"
        with st.chat_message(display_role):
            st.markdown(msg.get("content", ""))

    # Chat input
    user_input = st.chat_input(
        f"Describe your {MODE_LABELS[mode].lower()}...",
        key=f"chat_input_{mode}",
    )

    if user_input:
        _handle_chat_input(ui, mode, user_input)
        st.rerun()

    # Two-column layout: code editor | image preview
    col1, col2 = ui.columns(2)

    with col1:
        ui.subheader("PlantUML Code")
        new_code = st.text_area(
            "Edit PlantUML code",
            value=st.session_state.get(code_key, ""),
            height=400,
            key=f"code_editor_{mode}",
            label_visibility="collapsed",
        )
        # Sync editor back to state
        if new_code != st.session_state.get(code_key, ""):
            st.session_state[code_key] = new_code

        if ui.button("Re-render", key=f"rerender_{mode}"):
            _handle_rerender(ui, mode)
            st.rerun()

    with col2:
        ui.subheader("Diagram Preview")
        img_b64 = st.session_state.get(img_key)
        if img_b64:
            st.image(
                f"data:image/png;base64,{img_b64}",
                use_container_width=True,
            )
        else:
            ui.info("No diagram rendered yet. Send a message or click Re-render.")

    # Status bar
    status_msg = st.session_state.get(status_key, "")
    error_msg = st.session_state.get(error_key, "")
    if error_msg:
        ui.error(error_msg)
    elif status_msg:
        ui.success(status_msg)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the Streamlit UMLBot frontend."""
    ui = StreamlitUIHelper()
    StreamlitUIHelper.setup_page("UMLBot", page_icon="📐", hide_branding=True)

    _init_session_state()

    ui.title("UMLBot")
    ui.markdown("Interactive diagram generation powered by LLM + PlantUML")

    # Build tabs for each mode
    tab_labels = list(MODE_LABELS.values())
    tabs = ui.tabs(tab_labels)

    mode_keys = list(MODE_LABELS.keys())

    # Determine current mode for sidebar (first tab by default, but we track via tabs)
    # Streamlit tabs don't expose which is active, so sidebar uses first mode or stored value.
    if "active_mode" not in st.session_state:
        st.session_state["active_mode"] = mode_keys[0]

    for tab, mode_key in zip(tabs, mode_keys):
        with tab:
            _render_mode_tab(ui, mode_key)

    _render_sidebar(ui, st.session_state.get("active_mode", "uml"))


if __name__ == "__main__":
    main()
