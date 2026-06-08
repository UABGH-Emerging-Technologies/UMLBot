import os
from typing import Any

import requests

BASE_URL = os.environ.get("UMLBOT_ENDPOINT", "http://localhost:8000")
API_AUTH_TOKEN = os.environ.get("OPENAI_COMPATIBLE_KEY", "")
OPENAI_COMPATIBLE_ENDPOINT = os.environ.get("OPENAI_COMPATIBLE_ENDPOINT", "")
OPENAI_COMPATIBLE_MODEL = os.environ.get("OPENAI_COMPATIBLE_MODEL", "o3")
DEFAULT_TIMEOUT = 1800
MAX_HISTORY_MESSAGES = 10

MODE_LABELS: dict[str, str] = {
    "uml": "UML Diagram",
    "mindmap": "Mindmap",
    "ui_mockup": "UI Mockup (SALT)",
    "gantt": "Gantt Chart",
    "erd": "ER Diagram",
    "json": "JSON",
    "c4": "C4 Diagram",
}

ENDPOINT_MAP: dict[str, tuple[str, str, str]] = {
    "uml": ("/v01/generate", "/v01/render", "Use Case"),
    "mindmap": ("/v01/mindmap/generate", "/v01/mindmap/render", "Mindmap"),
    "ui_mockup": ("/v01/ui-mockup/generate", "/v01/ui-mockup/render", "salt"),
    "gantt": ("/v01/gantt/generate", "/v01/gantt/render", "gantt"),
    "erd": ("/v01/erd/generate", "/v01/erd/render", "ERD"),
    "json": ("/v01/json/generate", "/v01/json/render", "json"),
    "c4": ("/v01/c4/generate", "/v01/c4/render", "C4"),
}

UML_DIAGRAM_TYPES = [
    "Use Case",
    "Class",
    "Activity",
    "Component",
    "Deployment",
    "State Machine",
    "Timing",
    "Sequence",
]

_FENCE_MARKERS: dict[str, str] = {
    "uml": "@startuml and @enduml",
    "mindmap": "@startmindmap and @endmindmap",
    "ui_mockup": "@startsalt and @endsalt",
    "gantt": "@startgantt and @endgantt",
    "erd": "@startuml and @enduml",
    "json": "@startjson and @endjson",
    "c4": "@startuml and @enduml",
}

_C4_INSTRUCTIONS = (
    "Include the appropriate C4-PlantUML library directive after @startuml "
    "(e.g., !include <C4/C4_Context>, !include <C4/C4_Container>, "
    "!include <C4/C4_Component>, or !include <C4/C4_Deployment> depending on "
    "the diagram level). Use C4-PlantUML macros (Person, System, System_Ext, "
    "Container, Component, Rel, System_Boundary, Container_Boundary, etc.) "
    "rather than raw PlantUML shapes."
)

_ERD_INSTRUCTIONS = (
    "Use PlantUML Information Engineering (IE) notation for ER diagrams "
    "inside @startuml / @enduml. Define entities with "
    "'entity \"Name\" { ... }' blocks containing typed fields marked as "
    "primary (*) or mandatory (+). Express relationships using IE connectors: "
    "||--|| (one-to-one), ||--o{ (one-to-many), }o--o{ (many-to-many). "
    "Do NOT use Chen EER notation or @startchen / @endchen."
)

_MODE_FRIENDLY: dict[str, str] = {
    "uml": "UML",
    "mindmap": "mindmap",
    "ui_mockup": "UI mockup",
    "gantt": "Gantt",
    "erd": "ERD",
    "json": "JSON",
    "c4": "C4",
}


def _build_url(path: str) -> str:
    return f"{BASE_URL.rstrip('/')}{path}"


def _headers() -> dict[str, str]:
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
    }
    if API_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {API_AUTH_TOKEN}"
    return headers


def _inject_llm_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "openai_compatible_endpoint": OPENAI_COMPATIBLE_ENDPOINT,
        "openai_compatible_model": OPENAI_COMPATIBLE_MODEL,
    }


def _summarize_chat_history(history: list[dict[str, str]]) -> str:
    recent = history[-MAX_HISTORY_MESSAGES:]
    return "\n".join(
        f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent
    )


def build_prompt_description(
    user_request: str,
    current_code: str,
    chat_history: list[dict[str, str]],
    mode: str,
    diagram_type: str,
) -> str:
    fence = _FENCE_MARKERS.get(mode, "@startuml and @enduml")
    friendly = _MODE_FRIENDLY.get(mode, "UML")
    chat_summary = _summarize_chat_history(chat_history)

    sections = [
        f"You are an expert {friendly} assistant following the prompty template rules.",
        f"Diagram Type: {diagram_type}",
        f"Generate valid PlantUML enclosed between {fence} with concise, professional notation. No extra prose or markdown fences.",
    ]

    if mode == "c4":
        sections.append(_C4_INSTRUCTIONS)
    elif mode == "erd":
        sections.append(_ERD_INSTRUCTIONS)

    sections.append(f"Latest user request:\n{user_request}")

    if current_code.strip():
        sections.append(
            f"Existing PlantUML {friendly} diagram (reuse and refine rather than restart):\n{current_code}"
        )
    else:
        sections.append(
            f"No {friendly} diagram has been created yet. Create a fresh PlantUML {friendly} diagram."
        )

    if chat_summary:
        sections.append(f"Recent conversation:\n{chat_summary}")

    sections.append(f"Respond with PlantUML only between {fence}.")
    return "\n\n".join(sections)


def generate_diagram(
    mode: str,
    description: str,
    diagram_type: str,
    *,
    theme: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any] | None, str | None]:
    generate_path = ENDPOINT_MAP[mode][0]
    payload: dict[str, Any] = {"description": description}
    if mode == "uml":
        payload["diagram_type"] = diagram_type
    if theme:
        payload["theme"] = theme
    try:
        resp = requests.post(
            _build_url(generate_path),
            json=_inject_llm_fields(payload),
            headers=_headers(),
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json(), None
    except Exception as exc:
        return None, f"API error: {exc}"


def render_diagram(
    mode: str,
    plantuml_code: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any] | None, str | None]:
    render_path = ENDPOINT_MAP[mode][1]
    try:
        resp = requests.post(
            _build_url(render_path),
            json={"plantuml_code": plantuml_code},
            headers=_headers(),
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return {**data, "plantuml_code": plantuml_code}, None
    except Exception as exc:
        return None, f"API error: {exc}"
