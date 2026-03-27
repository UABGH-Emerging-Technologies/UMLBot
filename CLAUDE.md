# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Standards & Rules

**All coding standards are defined in `.kilocode/.kilocode/rules/`** — reference these files when writing or reviewing code:

| Rule File | Covers |
|-----------|--------|
| `coding_standard.md` | Reuse-first philosophy, Python requirements, code organization, CI expectations |
| `llm_utils_guide.md` | Shared `llm_utils/aiweb_common` workspace: WorkflowHandler, manage_sensitive, GenericErrorHandler, etc. |
| `formatting.md` | black/isort/autopep8 settings; run `make style` before any commit |
| `naming_conventions.md` | snake_case, PascalCase, UPPER_SNAKE_CASE conventions |
| `documentation_style.md` | Docstring format (Google/NumPy), MkDocs requirements |
| `security_guidelines.md` | Secret management, input validation, PHI/PII protection |
| `restricted_files.md` | Files that must never be read, written, or committed (.env, .venv, secrets, keys, etc.) |

**Key points that apply to every task:**
- **ALWAYS search `llm_utils/aiweb_common/` FIRST** before writing new code
- **DO NOT edit `llm_utils/` directly** — propose changes to the maintainer
- **Type annotations are MANDATORY** on all functions, methods, and variables
- **Run `make style`** before any commit
- **Run `make test`** to verify all tests pass

## Project Overview

UMLBot is an interactive chat-based LLM-powered tool for generating, revising, and validating diagrams using PlantUML. It consists of:
- **Python backend** (FastAPI/Uvicorn on port 8000): LLM-backed diagram generation and PlantUML rendering
- **Streamlit frontend** (port 8501): Chat UI for diagram interaction
- **PlantUML JAR** (local subprocess): Diagram rendering via `java -jar plantuml.jar`

The system supports multiple diagram types: UML diagrams (class, sequence, use case, etc.), mindmaps, UI mockups (SALT), Gantt charts, ER diagrams, C4 diagrams, and JSON visualizations.

**Key Philosophy**: This project prioritizes reusability through the `llm_utils/aiweb_common` shared workspace. Always search for existing functionality before writing new code.

**v1 Paradigm**: LLM credentials are supplied per-request (see `azurify.md`). The server does NOT store API keys. Every generate request must include `openai_compatible_endpoint`, `openai_compatible_model` in the body and `Authorization: Bearer <key>` in the header.

## Development Setup

### Environment Configuration
1. Copy `.env.example` to `.env` and configure:
   - `UMLBOT_PLANTUML_JAR_PATH` (optional, defaults to `/opt/plantuml/plantuml.jar`)

2. Ensure Java (JRE 17+) is installed for PlantUML JAR rendering.

### Python Backend Setup
```bash
make venv
# Or manually:
uv venv .venv --clear && source .venv/bin/activate && uv sync
```

### Running the Application

**Docker Compose:**
```bash
docker compose up --build  # API at http://localhost:8000
```

**Local Development:**
```bash
set -a && source .env && set +a
make run                                # Backend at http://localhost:8000
make streamlit                          # Streamlit UI at http://localhost:8501
```

**Devcontainer (VS Code):** Automatically creates `.venv`, installs deps, downloads PlantUML JAR.

## Common Commands

```bash
make style          # Code formatting (black, isort, autopep8, flake8)
make test           # Run tests (or: PYTHONPATH=$(pwd) .venv/bin/python -m pytest -q)
make run            # Start FastAPI server locally
make streamlit      # Start Streamlit frontend
make docs           # Build and serve MkDocs on http://0.0.0.0:8000
make clean          # Clean temporary files

# Run specific test
PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/test_file.py::test_name -v
```

## Architecture

### High-Level Structure
```
app/                             # FastAPI application layer
├── server.py                    # FastAPI entry point (port 8000)
├── fastapi_config.py            # API metadata (title, version, contact)
└── v01/                         # v01 API version
    ├── __init__.py              # Aggregates sub-routers into v01_router
    ├── schemas.py               # Pydantic request/response models
    ├── dependencies.py          # Bearer token extraction, service singleton
    ├── generate.py              # All /generate endpoints (auth required)
    ├── render.py                # All /render endpoints (no auth)
    └── config_router.py         # GET /config endpoint

UMLBot/                          # Core Python package
├── config/                      # Configuration (config.py with UMLBotConfig)
├── diagram_handlers/            # LLM prompt handlers for each diagram type
│   ├── uml_draft_handler.py     # UML diagrams via uml_diagram.prompty
│   ├── mindmap_draft_handler.py # Mindmaps via mindmap.prompty
│   ├── ui_mockup_draft_handler.py # SALT UI mockups
│   ├── gantt_draft_handler.py   # Gantt charts
│   ├── er_draft_handler.py      # ER diagrams
│   ├── json_draft_handler.py    # JSON visualizations
│   └── c4_draft_handler.py      # C4 diagrams
├── services/                    # Business logic
│   └── diagram_service.py       # DiagramService: generation + JAR rendering
├── utils/                       # Utilities (PlantUML extraction)
└── llm_interface.py             # LLM interaction wrapper

explorations/                    # Archived exploration code
├── frontend-nextjs/             # Former Next.js frontend
└── gradio-ui/                   # Former Gradio app

assets/                          # Prompty templates (*.prompty)
llm_utils/aiweb_common/          # Shared workspace LLM utilities (WorkflowHandler, etc.)
tests/                           # pytest test suite
docs/                            # MkDocs documentation
streamlit_app.py                 # Streamlit frontend (decoupled, uses /v01/ API)
```

### Core Workflow

1. **User Input**: Streamlit UI (`streamlit_app.py`) sends description + diagram type + LLM credentials to backend
2. **Backend Routing**: `app/server.py` → `app/v01/generate.py` extracts bearer token, validates request
3. **DiagramService** (`UMLBot/services/diagram_service.py`): Routes to appropriate handler, passes per-request credentials
4. **Handler Execution**: Each `*DraftHandler` inherits from `WorkflowHandler`, loads prompty template, invokes LLM
5. **PlantUML Rendering**: `_render_plantuml_jar()` invokes `java -jar plantuml.jar -tpng -pipe` via subprocess
6. **Error Handling**: `UMLRetryManager` retries on failure; fallback templates provide graceful degradation
7. **Response**: `DiagramGenerationResult` dataclass returned with plantuml_code, image, status_message

### API Endpoints (all under `/v01/`)

**Generate endpoints** (POST, auth required — `Authorization: Bearer <key>`):
- `/v01/generate` — UML diagrams
- `/v01/mindmap/generate`, `/v01/ui-mockup/generate`, `/v01/gantt/generate`
- `/v01/erd/generate`, `/v01/json/generate`, `/v01/c4/generate`

**Render endpoints** (POST, no auth):
- `/v01/render`, `/v01/mindmap/render`, `/v01/ui-mockup/render`, `/v01/gantt/render`
- `/v01/erd/render`, `/v01/json/render`, `/v01/c4/render`

**Config**: `GET /v01/config` — returns diagram types and fallback templates

**Health**: `GET /health` — returns `{"status": "ok"}`

### Key Design Patterns
- **v1 Paradigm**: LLM credentials per-request, no server-side API key storage
- **Handler Pattern**: Each diagram type has a dedicated `*DraftHandler` inheriting from `WorkflowHandler`
- **Prompty Templates**: LLM prompts defined in `.prompty` files (assets/) with variable injection
- **Service Layer**: `DiagramService` abstracts generation + rendering for all diagram types
- **Local JAR Rendering**: PlantUML renders via subprocess (`java -jar plantuml.jar -tpng -pipe`)
- **Retry Strategy**: `UMLRetryManager` tracks attempts and error context for auto-correction
- **Fallback Diagrams**: `FALLBACK_*_TEMPLATE` constants provide graceful degradation

## How to Add a New Diagram Type

Follow this checklist (using "Network Diagram" as example):

1. **Create Prompty Template** — `assets/network_diagram.prompty` (copy structure from existing prompty)
2. **Create Handler** — `UMLBot/diagram_handlers/network_draft_handler.py` inheriting from `WorkflowHandler`
3. **Export Handler** — Add to `UMLBot/diagram_handlers/__init__.py`
4. **Add Fallback Template** — `FALLBACK_NETWORK_TEMPLATE` in `UMLBot/config/config.py`
5. **Add Service Method** — `generate_network_from_description()` in `UMLBot/services/diagram_service.py` (with per-request credential params)
6. **Add API Endpoint** — Add to `app/v01/generate.py` and `app/v01/render.py`
7. **Add Frontend Support** — Update `ENDPOINT_MAP` in `streamlit_app.py`
8. **Add Tests** — `tests/test_network_draft_handler.py`
9. **Update Documentation** — docs/ entries and README

**Handler pattern to follow:**
```python
from llm_utils.aiweb_common.WorkflowHandler import WorkflowHandler

class NetworkDraftHandler(WorkflowHandler):
    def __init__(self, config=None):
        super().__init__()
        self.prompty_path = Path(__file__).parents[2] / "assets" / "network_diagram.prompty"
        self.config = config or UMLBotConfig()
```

**Service method pattern** (credentials passed from API layer):
```python
def generate_network_from_description(
    self, description, diagram_type, theme=None,
    openai_compatible_endpoint="", openai_compatible_key="", openai_compatible_model="",
) -> DiagramGenerationResult:
    handler = NetworkDraftHandler()
    return self._generate_from_description(
        handler=handler, description=description, diagram_type=diagram_type,
        theme=theme, fallback_template=UMLBotConfig.FALLBACK_NETWORK_TEMPLATE,
        failure_log="...", openai_compatible_endpoint=openai_compatible_endpoint,
        openai_compatible_key=openai_compatible_key, openai_compatible_model=openai_compatible_model,
    )
```

## Testing

### Running Tests
```bash
make test                                                                    # All tests
PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/test_file.py -v           # Specific file
PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/test_file.py::test_fn -v  # Specific test
PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/test_file.py -v -s        # With output
PYTHONPATH=$(pwd) .venv/bin/python -m pytest --cov=UMLBot tests/             # With coverage
```

### Test Requirements
- Tests must be fast, isolated, and deterministic
- Mock external dependencies (LLM calls, HTTP requests, file I/O)
- Use pytest fixtures for common setup; `monkeypatch` for env vars and mocking
- Integration tests in `tests/test_integration_*.py` (mark with `@pytest.mark.integration`)
- Add/adjust tests with EVERY behavioral change

## Debugging

### Logging
Log files in `UMLBot/logs/`: `info.log` (INFO+), `error.log` (ERROR only).
```python
import logging
LOGGER = logging.getLogger(__name__)
```

### Common Issues
| Issue | Solution |
|-------|----------|
| PlantUML JAR not found | Set `UMLBOT_PLANTUML_JAR_PATH` env var or ensure JAR is at `/opt/plantuml/plantuml.jar` |
| Java not installed | Install JRE 17+: `apt install temurin-17-jre` or `default-jre-headless` |
| 401 on generate | Include `Authorization: Bearer <key>` header in request |
| Prompty file not found | Path should be `Path(__file__).parents[2] / "assets" / "diagram.prompty"` |
| Invalid PlantUML code | Check `@startuml`/`@enduml` markers |
| Import errors | `export PYTHONPATH=$(pwd)`; verify `__init__.py` files exist |

## Key Configuration

### Backend (UMLBotConfig)
- `DIAGRAM_TYPES`: Supported UML diagram types
- `PLANTUML_JAR_PATH`: Path to PlantUML JAR (env: `UMLBOT_PLANTUML_JAR_PATH`)
- `FALLBACK_*_TEMPLATE`: Fallback templates for each diagram type
- No LLM credentials stored server-side (v1 paradigm — per-request)

### Streamlit Frontend
- Backend URL configurable in sidebar (defaults to `http://localhost:8000`)
- LLM credentials entered via sidebar (endpoint, model, API key)

## Important Notes

- **PlantUML rendering**: Uses local JAR via subprocess — requires Java runtime
- **Single container**: Docker image includes Python + JRE, no separate PlantUML server
- **Package management**: Python uses `uv` (preferred)
- **Exploration artifacts**: Old Next.js frontend and Gradio app archived in `explorations/`

## Git Workflow

### Branch Structure
- **main** — Production-ready code
- **develop** — Integration branch
- **feature/**, **bugfix/** — Branch from develop
- **hotfix/** — Branch from main

### Commit Message Format
```
<type>: <subject>

<body>
```

Types: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`

### Before Creating PR
- [ ] `make style` passes
- [ ] `make test` passes
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No sensitive data or restricted files

## Documentation

- Architecture: `docs/architecture.md`
- API endpoints: `app/v01/` (generate.py, render.py, config_router.py)
- Diagram handlers: `docs/UMLBot/diagram_handlers/`
- Build docs: `make docs` (serves on port 8000)
