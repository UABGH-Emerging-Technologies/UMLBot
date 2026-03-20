"""
Streamlit-based UMLBot frontend.

Communicates with the FastAPI backend API endpoints to generate and render
PlantUML diagrams across all supported diagram types.
LLM credentials are supplied per-request via the sidebar (v1 paradigm).
"""

import base64
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# Workaround for local llm_utils import
repo_root = Path(__file__).resolve().parent
sys.path.append(str(repo_root / "llm_utils"))
sys.path.append(str(repo_root))

from aiweb_common.streamlit.page_renderer import StreamlitUIHelper

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
    "uml": ("/v01/generate", "/v01/render", "Use Case"),
    "mindmap": ("/v01/mindmap/generate", "/v01/mindmap/render", "Mindmap"),
    "ui_mockup": ("/v01/ui-mockup/generate", "/v01/ui-mockup/render", "salt"),
    "gantt": ("/v01/gantt/generate", "/v01/gantt/render", "gantt"),
    "erd": ("/v01/erd/generate", "/v01/erd/render", "ERD"),
    "json": ("/v01/json/generate", "/v01/json/render", "json"),
    "c4": ("/v01/c4/generate", "/v01/c4/render", "C4"),
}

MAX_HISTORY_MESSAGES: int = 10

# ---------------------------------------------------------------------------
# Remote config fetcher (replaces direct UMLBotConfig import)
# ---------------------------------------------------------------------------

_remote_config: Optional[Dict[str, Any]] = None


def _fetch_remote_config(backend_url: str) -> Dict[str, Any]:
    """Fetch diagram types and fallback templates from the backend /v01/config endpoint."""
    global _remote_config  # noqa: PLW0603
    if _remote_config is not None:
        return _remote_config
    try:
        resp = requests.get(f"{backend_url.rstrip('/')}/v01/config", timeout=10)
        resp.raise_for_status()
        _remote_config = resp.json()
        return _remote_config
    except Exception as exc:
        logger.warning("Failed to fetch remote config: %s", exc)
        return {
            "diagram_types": [
                "Use Case", "Class", "Activity", "Component",
                "Deployment", "State Machine", "Timing", "Sequence",
            ],
            "default_diagram_type": "Use Case",
            "fallback_templates": {},
        }


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
    openai_compatible_endpoint: str = "",
    openai_compatible_model: str = "",
    api_key: str = "",
) -> ApiResponse:
    """Call the backend generate endpoint for the given mode.

    Includes per-request LLM credentials per v1 paradigm.
    """
    generate_path = ENDPOINT_MAP[mode][0]
    url = f"{backend_url.rstrip('/')}{generate_path}"
    payload: Dict[str, Any] = {
        "description": description,
        "diagram_type": diagram_type,
        "openai_compatible_endpoint": openai_compatible_endpoint,
        "openai_compatible_model": openai_compatible_model,
    }
    if theme:
        payload["theme"] = theme
    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
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
            "message": body.get("message", body.get("detail", f"HTTP {exc.response.status_code}")),
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
    """Call the backend render endpoint for the given mode (no auth required)."""
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
    """Return a newline-joined summary of the most recent chat messages."""
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
    """Compose a full description to send as the ``description`` field to the backend."""
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
    """Build a session-state key scoped to a diagram mode."""
    return f"{field}_{mode}"


def _init_session_state(config: Dict[str, Any]) -> None:
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
        st.session_state["backend_url"] = "http://localhost:8000"
    if "theme" not in st.session_state:
        st.session_state["theme"] = ""
    if "uml_subtype" not in st.session_state:
        st.session_state["uml_subtype"] = config.get("default_diagram_type", "Use Case")
    if "openai_compatible_endpoint" not in st.session_state:
        st.session_state["openai_compatible_endpoint"] = ""
    if "openai_compatible_model" not in st.session_state:
        st.session_state["openai_compatible_model"] = ""
    if "api_key" not in st.session_state:
        st.session_state["api_key"] = ""


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar(ui: StreamlitUIHelper, current_mode: str, config: Dict[str, Any]) -> None:
    """Render the sidebar controls."""
    with st.sidebar:
        ui.header("Settings")

        st.session_state["backend_url"] = ui.text_input(
            "Backend URL",
            value=st.session_state["backend_url"],
            key="sidebar_backend_url",
        )

        ui.markdown("---")
        ui.subheader("LLM Credentials")

        st.session_state["openai_compatible_endpoint"] = ui.text_input(
            "OpenAI-Compatible Endpoint",
            value=st.session_state["openai_compatible_endpoint"],
            key="sidebar_endpoint",
        )

        st.session_state["openai_compatible_model"] = ui.text_input(
            "Model Name",
            value=st.session_state["openai_compatible_model"],
            key="sidebar_model",
        )

        st.session_state["api_key"] = st.text_input(
            "API Key",
            value=st.session_state["api_key"],
            type="password",
            key="sidebar_api_key",
        )

        ui.markdown("---")

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
    config: Dict[str, Any],
) -> None:
    """Process a new chat message: call backend generate, update state."""
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
        diagram_type = st.session_state.get("uml_subtype", config.get("default_diagram_type", "Use Case"))
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
            openai_compatible_endpoint=st.session_state.get("openai_compatible_endpoint", ""),
            openai_compatible_model=st.session_state.get("openai_compatible_model", ""),
            api_key=st.session_state.get("api_key", ""),
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
    """Re-render diagram from the current code in the editor."""
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


def _render_mode_tab(ui: StreamlitUIHelper, mode: str, config: Dict[str, Any]) -> None:
    """Render the contents of a single diagram mode tab."""
    history_key = _state_key(mode, "chat_history")
    code_key = _state_key(mode, "plantuml_code")
    img_key = _state_key(mode, "image_base64")
    status_key = _state_key(mode, "status_message")
    error_key = _state_key(mode, "error_message")

    # UML sub-type dropdown (only for uml mode)
    diagram_types = config.get("diagram_types", ["Use Case", "Class", "Sequence"])
    if mode == "uml":
        current_subtype = st.session_state.get("uml_subtype", config.get("default_diagram_type", "Use Case"))
        idx = diagram_types.index(current_subtype) if current_subtype in diagram_types else 0
        st.session_state["uml_subtype"] = ui.selectbox(
            "UML Diagram Type",
            options=diagram_types,
            index=idx,
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
        _handle_chat_input(ui, mode, user_input, config)
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

    # Fetch config from backend (with fallback defaults)
    backend_url = st.session_state.get("backend_url", "http://localhost:8000")
    config = _fetch_remote_config(backend_url)

    _init_session_state(config)

    ui.title("UMLBot")
    ui.markdown("Interactive diagram generation powered by LLM + PlantUML")

    # Build tabs for each mode
    tab_labels = list(MODE_LABELS.values())
    tabs = ui.tabs(tab_labels)

    mode_keys = list(MODE_LABELS.keys())

    if "active_mode" not in st.session_state:
        st.session_state["active_mode"] = mode_keys[0]

    for tab, mode_key in zip(tabs, mode_keys):
        with tab:
            _render_mode_tab(ui, mode_key, config)

    _render_sidebar(ui, st.session_state.get("active_mode", "uml"), config)


if __name__ == "__main__":
    main()
