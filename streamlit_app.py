"""
Streamlit-based UMLBot frontend.

Communicates with the FastAPI backend API endpoints to generate and render
PlantUML diagrams across all supported diagram types.

LLM credentials are centralized via aiweb_common (manage_sensitive) and config
constants — the user never enters them.  The backend URL is read from the
UMLBOT_ENDPOINT environment variable.

NOTE FOR IMPLEMENTATION TEAM:
  This file is a *proposal*.  The implementation team will integrate it as a
  page inside ai_web_interface.  The sidebar is intentionally left empty so
  that the multi-page sidebar navigation is not disrupted.
"""

import base64
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Path setup (so aiweb_common / llm_utils resolve in standalone mode)
# ---------------------------------------------------------------------------
repo_root = Path(__file__).resolve().parent
sys.path.append(str(repo_root / "llm_utils"))
sys.path.append(str(repo_root))

from aiweb_common.streamlit.streamlit_common import apply_uab_font, hide_streamlit_branding
from aiweb_common.WorkflowHandler import manage_sensitive

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Centralized LLM credentials (matches ai_web_interface config pattern)
# ---------------------------------------------------------------------------

UABMC_PROXY_ENDPOINT: str = manage_sensitive("azure_proxy_endpoint")
UABMC_AZURE_KEY: str = manage_sensitive("azure_proxy_key")

# PRO_CHAT in the ai_web_interface config — required for consistently
# well-formed PlantUML output; lower-tier models produce syntax errors.
MODEL_TO_USE: str = "gpt-5.2"

# Backend URL from environment with localhost fallback for local dev
API_BASE_URL: str = os.environ.get("UMLBOT_ENDPOINT", "http://localhost:8000")

DEFAULT_TIMEOUT: int = 120

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
# Remote config fetcher
# ---------------------------------------------------------------------------

_remote_config: Optional[Dict[str, Any]] = None


def _fetch_remote_config() -> Dict[str, Any]:
    """Fetch diagram types and fallback templates from the backend /v01/config endpoint."""
    global _remote_config  # noqa: PLW0603
    if _remote_config is not None:
        return _remote_config
    try:
        resp = requests.get(f"{API_BASE_URL.rstrip('/')}/v01/config", timeout=10)
        resp.raise_for_status()
        _remote_config = resp.json()
        return _remote_config
    except Exception as exc:
        logger.warning("Failed to fetch remote config: %s", exc)
        return {
            "diagram_types": [
                "Use Case",
                "Class",
                "Activity",
                "Component",
                "Deployment",
                "State Machine",
                "Timing",
                "Sequence",
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
# API helpers (matches ai_web_interface API module pattern)
# ---------------------------------------------------------------------------

ApiResponse = Dict[str, Any]


def _build_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}{path}"


def _headers() -> Dict[str, str]:
    """Build request headers with Bearer token from centralized credentials."""
    h: Dict[str, str] = {
        "accept": "application/json",
        "Content-Type": "application/json",
    }
    if UABMC_AZURE_KEY:
        h["Authorization"] = f"Bearer {UABMC_AZURE_KEY}"
    return h


def _inject_llm_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Inject centralized LLM endpoint/model into the request payload."""
    return {
        **payload,
        "openai_compatible_endpoint": UABMC_PROXY_ENDPOINT,
        "openai_compatible_model": MODEL_TO_USE,
    }


def api_generate(
    mode: str,
    description: str,
    diagram_type: str,
    theme: Optional[str] = None,
) -> ApiResponse:
    """Call the backend generate endpoint for the given mode.

    LLM credentials are injected from centralized config — callers do not
    supply them.
    """
    generate_path: str = ENDPOINT_MAP[mode][0]
    payload: Dict[str, Any] = {"description": description}
    # UML endpoint requires diagram_type; others ignore it
    if mode == "uml":
        payload["diagram_type"] = diagram_type
    if theme:
        payload["theme"] = theme

    body = _inject_llm_fields(payload)

    try:
        resp = requests.post(
            _build_url(generate_path),
            json=body,
            headers=_headers(),
            timeout=DEFAULT_TIMEOUT,
        )
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
            "message": f"Cannot connect to backend at {API_BASE_URL}. Is it running?",
        }
    except requests.exceptions.HTTPError as exc:
        body_json: Dict[str, Any] = {}
        try:
            body_json = exc.response.json()
        except Exception:
            pass
        return {
            "status": "error",
            "plantuml_code": "",
            "image_base64": None,
            "image_url": "",
            "message": body_json.get(
                "message", body_json.get("detail", f"HTTP {exc.response.status_code}")
            ),
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
    mode: str,
    plantuml_code: str,
) -> ApiResponse:
    """Call the backend render endpoint for the given mode (no auth required)."""
    render_path: str = ENDPOINT_MAP[mode][1]
    payload: Dict[str, Any] = {"plantuml_code": plantuml_code}
    try:
        resp = requests.post(_build_url(render_path), json=payload, timeout=60)
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
            "message": f"Cannot connect to backend at {API_BASE_URL}. Is it running?",
        }
    except requests.exceptions.HTTPError as exc:
        body_json: Dict[str, Any] = {}
        try:
            body_json = exc.response.json()
        except Exception:
            pass
        return {
            "status": "error",
            "plantuml_code": plantuml_code,
            "image_base64": None,
            "image_url": "",
            "message": body_json.get("message", f"HTTP {exc.response.status_code}"),
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
    fence: str = _FENCE_MARKERS.get(mode, "@startuml and @enduml")
    friendly: str = _MODE_FRIENDLY.get(mode, "UML")

    code_label: str = (
        f"Existing PlantUML {friendly} diagram (reuse and refine rather than restart):"
        if current_code.strip()
        else f"No {friendly} diagram has been created yet. Create a fresh PlantUML {friendly} diagram."
    )

    chat_summary: str = _summarize_chat_history(chat_history)

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

    if "theme" not in st.session_state:
        st.session_state["theme"] = ""
    if "uml_subtype" not in st.session_state:
        st.session_state["uml_subtype"] = config.get("default_diagram_type", "Use Case")


# ---------------------------------------------------------------------------
# Tab Rendering
# ---------------------------------------------------------------------------


def _handle_chat_input(
    mode: str,
    user_message: str,
    config: Dict[str, Any],
) -> None:
    """Process a new chat message: call backend generate, update state."""
    history_key: str = _state_key(mode, "chat_history")
    code_key: str = _state_key(mode, "plantuml_code")
    img_key: str = _state_key(mode, "image_base64")
    status_key: str = _state_key(mode, "status_message")
    error_key: str = _state_key(mode, "error_message")

    history: List[Dict[str, str]] = st.session_state[history_key]
    history.append({"role": "user", "content": user_message})

    current_code: str = st.session_state.get(code_key, "")

    if mode == "uml":
        diagram_type: str = st.session_state.get(
            "uml_subtype", config.get("default_diagram_type", "Use Case")
        )
    else:
        diagram_type = ENDPOINT_MAP[mode][2]

    description: str = _build_prompt_description(
        user_request=user_message,
        current_code=current_code,
        chat_history=history,
        mode=mode,
        diagram_type=diagram_type,
    )

    theme: Optional[str] = st.session_state.get("theme") or None

    with st.spinner("Generating diagram..."):
        result = api_generate(
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


def _handle_rerender(mode: str) -> None:
    """Re-render diagram from the current code in the editor."""
    code_key: str = _state_key(mode, "plantuml_code")
    img_key: str = _state_key(mode, "image_base64")
    status_key: str = _state_key(mode, "status_message")
    error_key: str = _state_key(mode, "error_message")

    code: str = st.session_state.get(code_key, "")
    if not code.strip():
        st.session_state[error_key] = "No PlantUML code to render."
        return

    with st.spinner("Rendering diagram..."):
        result = api_render(mode=mode, plantuml_code=code)

    if result["status"] == "ok" and result["image_base64"]:
        st.session_state[img_key] = result["image_base64"]
        st.session_state[status_key] = result.get("message", "Rendered successfully.")
        st.session_state[error_key] = ""
    else:
        st.session_state[error_key] = result.get("message", "Rendering failed.")
        st.session_state[status_key] = ""


def _render_mode_tab(mode: str, config: Dict[str, Any]) -> None:
    """Render the contents of a single diagram mode tab."""
    history_key: str = _state_key(mode, "chat_history")
    code_key: str = _state_key(mode, "plantuml_code")
    img_key: str = _state_key(mode, "image_base64")
    status_key: str = _state_key(mode, "status_message")
    error_key: str = _state_key(mode, "error_message")

    # UML sub-type dropdown (only for uml mode)
    diagram_types: List[str] = config.get("diagram_types", ["Use Case", "Class", "Sequence"])
    if mode == "uml":
        current_subtype: str = st.session_state.get(
            "uml_subtype", config.get("default_diagram_type", "Use Case")
        )
        idx: int = diagram_types.index(current_subtype) if current_subtype in diagram_types else 0
        st.session_state["uml_subtype"] = st.selectbox(
            "UML Diagram Type",
            options=diagram_types,
            index=idx,
            key=f"uml_subtype_select_{mode}",
        )

    # Optional PlantUML theme
    st.session_state["theme"] = st.text_input(
        "PlantUML Theme (optional)",
        value=st.session_state.get("theme", ""),
        key=f"theme_input_{mode}",
    )

    # Chat history display
    history: List[Dict[str, str]] = st.session_state.get(history_key, [])
    for msg in history:
        role: str = msg.get("role", "user")
        display_role: str = "user" if role == "user" else "assistant"
        with st.chat_message(display_role):
            st.markdown(msg.get("content", ""))

    # Chat input
    user_input: Optional[str] = st.chat_input(
        f"Describe your {MODE_LABELS[mode].lower()}...",
        key=f"chat_input_{mode}",
    )

    if user_input:
        _handle_chat_input(mode, user_input, config)
        st.rerun()

    # Two-column layout: code editor | image preview
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("PlantUML Code")
        new_code: str = st.text_area(
            "Edit PlantUML code",
            value=st.session_state.get(code_key, ""),
            height=400,
            key=f"code_editor_{mode}",
            label_visibility="collapsed",
        )
        if new_code != st.session_state.get(code_key, ""):
            st.session_state[code_key] = new_code

        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("Re-render", key=f"rerender_{mode}"):
                _handle_rerender(mode)
                st.rerun()
        with btn_col2:
            code: str = st.session_state.get(code_key, "")
            if code:
                st.download_button(
                    label="Download Code",
                    data=code,
                    file_name=f"{mode}_diagram.puml",
                    mime="text/plain",
                    key=f"dl_code_{mode}",
                )
        with btn_col3:
            if st.button("Clear History", key=f"clear_history_{mode}"):
                st.session_state[history_key] = []
                st.session_state[status_key] = ""
                st.session_state[error_key] = ""
                st.rerun()

    with col2:
        st.subheader("Diagram Preview")
        img_b64: Optional[str] = st.session_state.get(img_key)
        if img_b64:
            st.image(
                f"data:image/png;base64,{img_b64}",
                use_container_width=True,
            )
            img_bytes: bytes = base64.b64decode(img_b64)
            st.download_button(
                label="Download Image (PNG)",
                data=img_bytes,
                file_name=f"{mode}_diagram.png",
                mime="image/png",
                key=f"dl_image_{mode}",
            )
        else:
            st.info("No diagram rendered yet. Send a message or click Re-render.")

    # Status bar
    status_msg: str = st.session_state.get(status_key, "")
    error_msg: str = st.session_state.get(error_key, "")
    if error_msg:
        st.error(error_msg)
    elif status_msg:
        st.success(status_msg)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def show_umlbot_page() -> None:
    """Entry point for the UMLBot page.

    Named ``show_*_page`` to match ai_web_interface page conventions.
    When the implementation team integrates this as a numbered page, they
    should call this function from the page script.
    """
    page_title: str = "UMLBot"
    page_icon: str = "📐"

    st.set_page_config(page_title=page_title, page_icon=page_icon)
    hide_streamlit_branding()
    apply_uab_font()

    st.title(f"{page_icon} {page_title}")
    st.markdown("""
        **Interactive diagram generation powered by LLM + PlantUML**

        Describe what you want in plain language and the AI will generate
        PlantUML code and render it.  You can iterate on the diagram through
        the chat, or edit the code directly and re-render.

        ---
        """)

    config: Dict[str, Any] = _fetch_remote_config()
    _init_session_state(config)

    # Build tabs for each diagram mode
    tab_labels: List[str] = list(MODE_LABELS.values())
    tabs = st.tabs(tab_labels)
    mode_keys: List[str] = list(MODE_LABELS.keys())

    for tab, mode_key in zip(tabs, mode_keys):
        with tab:
            _render_mode_tab(mode_key, config)


if __name__ == "__main__":
    show_umlbot_page()
