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
- **Python backend** (Gradio/FastAPI/Uvicorn): LLM-backed diagram generation and PlantUML rendering
- **TypeScript/Next.js frontend** (port 3000): Chat UI for diagram interaction
- **PlantUML server** (Docker): Diagram rendering service

The system supports multiple diagram types: UML diagrams (class, sequence, use case, etc.), mindmaps, UI mockups (SALT), Gantt charts, ER diagrams, C4 diagrams, and JSON visualizations.

**Key Philosophy**: This project prioritizes reusability through the `llm_utils/aiweb_common` shared workspace. Always search for existing functionality before writing new code.

## Development Setup

### Environment Configuration
1. Copy `.env.example` to `.env` and configure:
   - `UMLBOT_LLM_API_BASE` - OpenAI-compatible API endpoint
   - `UMLBOT_LLM_API_KEY` - API key for LLM access
   - `UMLBOT_LLM_MODEL` (optional, defaults to `gpt-4o-mini`)
   - `UMLBOT_PLANTUML_SERVER_URL_TEMPLATE` (defaults to `http://localhost:8080/png/{encoded}`)

2. Copy `app/frontend/.env.local.example` to `app/frontend/.env.local` and configure:
   - `NEXT_PUBLIC_GRADIO_API_BASE` - Backend API URL (defaults to `http://localhost:7860`)
   - `NEXT_PUBLIC_PLANTUML_SERVER_BASE` - PlantUML server for browser rendering

### Python Backend Setup
```bash
make venv
# Or manually:
uv venv .venv --clear && source .venv/bin/activate
uv add setuptools wheel && uv add -r requirements.txt && uv pip install -e ".[dev]"
```

### Frontend Setup
```bash
make npm-install   # Or: cd app/frontend && npm install
make npm-dev       # Or: cd app/frontend && npm run dev
make npm-build     # Or: cd app/frontend && npm run build
```

### Running the Application

**Docker Compose (Full Stack):**
```bash
docker compose up --build  # Frontend at http://localhost:3000
```

**Local Development:**
```bash
make plantuml-up
set -a && source .env && set +a
uvicorn gradio_app:app --reload          # Backend at http://localhost:7860
cd app/frontend && npm run dev           # Frontend at http://localhost:3000
```

**Devcontainer (VS Code):** Automatically creates `.venv`, installs deps, starts PlantUML server. Backend uses `http://plantuml:8080`, frontend proxies via `http://backend:7860`.

## Common Commands

```bash
make style          # Code formatting (black, isort, autopep8, flake8)
make test           # Run tests (or: PYTHONPATH=$(pwd) .venv/bin/python -m pytest -q)
make plantuml-up    # Start PlantUML server
make plantuml-down  # Stop PlantUML server
make docs           # Build and serve MkDocs on http://0.0.0.0:8000
make clean          # Clean temporary files

# Run specific test
PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/test_file.py::test_name -v
```

## Architecture

### High-Level Structure
```
UMLBot/                      # Main Python package
├── config/                  # Configuration (config.py with UMLBotConfig)
├── diagram_handlers/        # LLM prompt handlers for each diagram type
│   ├── uml_draft_handler.py      # UML diagrams via uml_diagram.prompty
│   ├── mindmap_draft_handler.py  # Mindmaps via mindmap.prompty
│   ├── ui_mockup_draft_handler.py # SALT UI mockups via ui_mockup.prompty
│   ├── gantt_draft_handler.py    # Gantt charts via gantt_chart.prompty
│   ├── er_draft_handler.py       # ER diagrams via erd.prompty
│   └── json_draft_handler.py     # JSON via json.prompty
├── services/                # Business logic
│   └── diagram_service.py   # DiagramService orchestrates generation + rendering
├── utils/                   # Utilities (PlantUML extraction, encoding)
├── api_server.py            # FastAPI endpoints (/api/generate, /api/render, etc.)
└── llm_interface.py         # LLM interaction wrapper

app/frontend/                # Next.js frontend
├── app/                     # Next.js app router (page.tsx = main chat interface)
├── actions/                 # Server actions for backend calls
└── components/              # React components

assets/                      # Prompty templates (*.prompty)
llm_utils/aiweb_common/      # Shared workspace LLM utilities (WorkflowHandler, etc.)
tests/                       # pytest test suite
docs/                        # MkDocs documentation
```

### Core Workflow

1. **User Input**: Chat interface (`app/frontend/app/page.tsx`) sends description + diagram type to backend
2. **Backend Routing**: `api_server.py` receives request, routes to `DiagramService`
3. **DiagramService** (`UMLBot/services/diagram_service.py`): Routes to appropriate handler method based on diagram type
4. **Handler Execution**: Each `*DraftHandler` (in `UMLBot/diagram_handlers/`) inherits from `WorkflowHandler`, loads a prompty template from `assets/`, invokes the LLM, and returns PlantUML code
5. **PlantUML Rendering**: `DiagramService.render_plantuml()` encodes the code, sends to PlantUML server, returns PIL Image
6. **Error Handling**: `UMLRetryManager` retries on failure; fallback templates (`FALLBACK_*_TEMPLATE` in config) provide graceful degradation
7. **Response**: `DiagramGenerationResult` dataclass returned with plantuml_code, image, status_message, image_url

### API Endpoints
- `/api/generate` - Generate new diagram
- `/api/render` - Render existing PlantUML code
- `/api/chat` - Chat-based revision workflow
- `/api/mindmap`, `/api/ui-mockup`, `/api/gantt`, `/api/erd`, `/api/json` - Specialized endpoints

### Key Design Patterns
- **Handler Pattern**: Each diagram type has a dedicated `*DraftHandler` inheriting from `WorkflowHandler`
- **Prompty Templates**: LLM prompts defined in `.prompty` files (assets/) with variable injection
- **Service Layer**: `DiagramService` abstracts generation + rendering for all diagram types
- **Retry Strategy**: `UMLRetryManager` tracks attempts and error context for auto-correction
- **Fallback Diagrams**: `FALLBACK_*_TEMPLATE` constants provide graceful degradation

## How to Add a New Diagram Type

Follow this checklist (using "Network Diagram" as example):

1. **Create Prompty Template** — `assets/network_diagram.prompty` (copy structure from existing prompty)
2. **Create Handler** — `UMLBot/diagram_handlers/network_draft_handler.py` inheriting from `WorkflowHandler`
3. **Export Handler** — Add to `UMLBot/diagram_handlers/__init__.py`
4. **Add Fallback Template** — `FALLBACK_NETWORK_TEMPLATE` in `UMLBot/config/config.py`
5. **Add Service Method** — `generate_network_from_description()` in `UMLBot/services/diagram_service.py`
6. **Add API Endpoint** — `/api/network` in `UMLBot/api_server.py`
7. **Add to Gradio UI** — Update `gradio_app.py` dropdown and routing
8. **Add Frontend Support** — `constants.ts`, server action, API route, UI updates
9. **Add Tests** — `tests/test_network_draft_handler.py`
10. **Update Documentation** — docs/ entries and README

**Handler pattern to follow:**
```python
from llm_utils.aiweb_common.WorkflowHandler import WorkflowHandler

class NetworkDraftHandler(WorkflowHandler):
    def __init__(self, config=None):
        super().__init__()
        self.prompty_path = Path(__file__).parents[2] / "assets" / "network_diagram.prompty"
        self.config = config or UMLBotConfig()

    def generate(self, description: str, diagram_type: str = "network", theme: Optional[str] = None) -> str:
        prompt_template = self.load_prompty()
        self._init_openai(
            openai_compatible_endpoint=self.config.LLM_API_BASE,
            openai_compatible_key=self.config.LLM_API_KEY,
            openai_compatible_model=self.config.LLM_MODEL,
            name="UMLBot"
        )
        formatted_prompt = prompt_template.format_messages(
            diagram_type=diagram_type, description=description, theme=theme or ""
        )
        response = self.llm_interface.invoke(formatted_prompt)
        return self.check_content_type(response)
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
| LLM API key not found | Check `.env` has `UMLBOT_LLM_API_KEY`; verify loaded: `set -a && source .env && set +a` |
| PlantUML connection refused | `make plantuml-up`; in Docker use `http://plantuml:8080` |
| Prompty file not found | Path should be `Path(__file__).parents[2] / "assets" / "diagram.prompty"` |
| Invalid PlantUML code | Check `@startuml`/`@enduml` markers; test directly against PlantUML server |
| Import errors | `export PYTHONPATH=$(pwd)`; verify `__init__.py` files exist |

## Key Configuration

### Backend (UMLBotConfig)
- `DIAGRAM_TYPES`: Supported UML diagram types
- `PLANTUML_SERVER_URL_TEMPLATE`: PlantUML render endpoint (auto-detects Docker vs local)
- `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`: LLM config from env or `manage_sensitive()`
- `CORS_ALLOW_ORIGINS`: Frontend origins (defaults to localhost:3000)
- `FALLBACK_*_TEMPLATE`: Fallback templates for each diagram type

### Frontend
- `NEXT_PUBLIC_GRADIO_API_BASE`: Backend API URL
- `NEXT_PUBLIC_PLANTUML_SERVER_BASE`: PlantUML server for client-side rendering

## Important Notes

- **PlantUML server**: Must be running for rendering; use `make plantuml-up` locally or Docker Compose
- **Docker networking**: Inside Docker, use service names (`http://plantuml:8080`, `http://backend:7860`)
- **Package management**: Python uses `uv` (preferred); frontend uses `npm`

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
- API server: `docs/UMLBot/api_server.md`
- Diagram handlers: `docs/UMLBot/diagram_handlers/`
- Build docs: `make docs` (serves on port 8000)
