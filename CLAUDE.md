# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UMLBot is an interactive chat-based LLM-powered tool for generating, revising, and validating diagrams using PlantUML. It consists of:
- **Python backend** (Gradio/FastAPI/Uvicorn): LLM-backed diagram generation and PlantUML rendering
- **TypeScript/Next.js frontend** (port 3000): Chat UI for diagram interaction
- **PlantUML server** (Docker): Diagram rendering service

The system supports multiple diagram types: UML diagrams (class, sequence, use case, etc.), mindmaps, UI mockups (SALT), Gantt charts, ER diagrams, and JSON visualizations.

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
# Create virtual environment with uv (preferred)
make venv

# Or manually:
uv venv .venv --clear
source .venv/bin/activate
uv add setuptools wheel
uv add -r requirements.txt
uv pip install -e ".[dev]"
```

### Frontend Setup
```bash
# Install dependencies
make npm-install
# Or: cd app/frontend && npm install

# Development build
make npm-dev
# Or: cd app/frontend && npm run dev

# Production build
make npm-build
# Or: cd app/frontend && npm run build
```

### Running the Application

**Option 1: Docker Compose (Full Stack)**
```bash
docker compose up --build
# Access frontend at http://localhost:3000
```

**Option 2: Local Development**
```bash
# Start PlantUML server
make plantuml-up

# Start backend (from repo root, with .env loaded)
set -a && source .env && set +a
uvicorn gradio_app:app --reload
# Backend runs on http://localhost:7860

# Start frontend (separate terminal)
cd app/frontend
NEXT_PUBLIC_GRADIO_API_BASE=http://localhost:7860 npm run dev
# Frontend runs on http://localhost:3000
```

**Option 3: Devcontainer (VS Code)**
The devcontainer automatically:
- Creates `.venv` and installs dependencies
- Runs startup script (`Docker/startup.sh`)
- Starts PlantUML server via compose
- Backend uses `http://plantuml:8080` inside container
- Frontend proxies to backend via `http://backend:7860`

## Common Commands

```bash
# Code formatting (black, isort, autopep8, flake8)
make style

# Run tests
make test
# Or: PYTHONPATH=$(pwd) .venv/bin/python -m pytest -q

# Run specific test
PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/test_file.py::test_name -v

# PlantUML server management
make plantuml-up    # Start server
make plantuml-logs  # View logs
make plantuml-down  # Stop server

# Documentation
make docs  # Build and serve MkDocs on http://0.0.0.0:8000

# Clean temporary files
make clean
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
├── app/                     # Next.js app router
│   ├── page.tsx             # Main chat interface
│   └── api/                 # API routes (proxy to backend)
├── actions/                 # Server actions for backend calls
└── components/              # React components

assets/                      # Prompty templates (*.prompty)
llm_utils/aiweb_common/      # Shared workspace LLM utilities (WorkflowHandler, etc.)
tests/                       # pytest test suite
docs/                        # MkDocs documentation
```

### Core Workflow - Detailed Flow

**1. User Input → Frontend**
- User types description in chat interface (`app/frontend/app/page.tsx`)
- Selects diagram type from dropdown (UML Diagram, Mindmap, UI Mockup, Gantt, ER Diagram, JSON)
- For UML Diagrams, also selects specific type (Use Case, Class, Sequence, etc.)

**2. Frontend → Backend API**
- Frontend calls server action in `app/frontend/actions/*.action.ts`
- Action proxies to backend via `NEXT_PUBLIC_GRADIO_API_BASE` (default: `http://localhost:7860`)
- Request: `{description: string, diagram_type: string, theme?: string}`

**3. Backend Routing**
- **Option A (Gradio)**: `gradio_app.py` handles chat interface callbacks
- **Option B (FastAPI)**: `api_server.py` exposes REST endpoints
  - `/api/generate` - Generate new diagram
  - `/api/render` - Render existing PlantUML code
  - `/api/chat` - Chat-based revision workflow
  - `/api/mindmap`, `/api/ui-mockup`, `/api/gantt`, `/api/erd`, `/api/json` - Specialized endpoints

**4. DiagramService Orchestration** (`UMLBot/services/diagram_service.py`)
Routes to appropriate generation method based on diagram type:
- `generate_diagram_from_description()` → UML diagrams
- `generate_mindmap_from_description()` → Mindmaps
- `generate_ui_mockup_from_description()` → SALT UI mockups
- `generate_gantt_from_description()` → Gantt charts
- `generate_erd_from_description()` → ER diagrams
- `generate_json_from_description()` → JSON visualization

**5. Handler Selection & Execution**
Each diagram type has a dedicated handler in `UMLBot/diagram_handlers/`:
- `UMLDraftHandler` - Standard UML diagrams
- `MindmapDraftHandler` - Mindmaps
- `UIMockupDraftHandler` - SALT UI mockups
- `GanttDraftHandler` - Gantt charts
- `ERDraftHandler` - ER diagrams
- `JsonDraftHandler` - JSON visualization

**All handlers inherit from `WorkflowHandler` and follow this pattern:**

```python
class UMLDraftHandler(WorkflowHandler):
    def __init__(self, config=None):
        super().__init__()
        # Path to prompty template in assets/
        self.prompty_path = Path(__file__).parents[2] / "assets" / "uml_diagram.prompty"
        self.config = config or UMLBotConfig()

    def generate(self, description: str, diagram_type: str, theme: Optional[str]) -> str:
        # 1. Load prompty template
        prompt_template = self.load_prompty()

        # 2. Initialize LLM interface
        self._init_openai(
            openai_compatible_endpoint=self.config.LLM_API_BASE,
            openai_compatible_key=self.config.LLM_API_KEY,
            openai_compatible_model=self.config.LLM_MODEL,
            name="UMLBot"
        )

        # 3. Format prompt with variables
        formatted_prompt = prompt_template.format_messages(
            diagram_type=diagram_type,
            description=description,
            theme=theme or ""
        )

        # 4. Invoke LLM
        response = self.llm_interface.invoke(formatted_prompt)

        # 5. Extract and validate content
        content = self.check_content_type(response)

        # 6. Return PlantUML code
        return content
```

**6. Prompty Template Loading** (`assets/*.prompty`)
Prompty files are YAML with Jinja2 templates:
```yaml
---
name: UML Diagram Generator
description: "Converts description into PlantUML diagram"
model:
  api: chat
  configuration:
    type: azure_openai
    azure_endpoint: ${UMLBOT_LLM_API_BASE}
  parameters:
    max_tokens: 3000
    temperature: 0.1
variables:
  diagram_type: {type: string, required: true}
  description: {type: string, required: true}
  theme: {type: string, required: false}
---
prompt:
  template: |
    You are an expert UML diagram generator...
    **Diagram Type:** {{ diagram_type }}
    **Description:** {{ description }}
    {% if theme %}**Theme:** {{ theme }}{% endif %}
```

**7. LLM Invocation**
- LangChain `ChatOpenAI` interface (configured in `WorkflowHandler._init_openai()`)
- Supports OpenAI-compatible endpoints (OpenAI, Azure, local models)
- Response: PlantUML code block wrapped in ```@startuml...@enduml```

**8. PlantUML Code Extraction**
- `extract_last_plantuml_block()` in `UMLBot/utils/plantuml_extractor.py`
- Finds code between `@startuml` and `@enduml` markers
- Strips markdown code fences if present

**9. PlantUML Rendering** (`DiagramService.render_plantuml()`)
```python
def render_plantuml(self, plantuml_code: str) -> Tuple[Image.Image | None, str]:
    # 1. Encode PlantUML code
    from plantuml import deflate_and_encode
    encoded = deflate_and_encode(plantuml_code)

    # 2. Construct URL
    url = UMLBotConfig.PLANTUML_SERVER_URL_TEMPLATE.format(encoded=encoded)
    # Example: http://localhost:8080/png/{encoded}

    # 3. Fetch rendered image
    response = requests.get(url, timeout=30)

    # 4. Load as PIL Image
    if response.status_code == 200:
        image = Image.open(io.BytesIO(response.content))
        return (image, url)
    else:
        return (None, url)
```

**10. Error Handling with Retry Logic**
`UMLRetryManager` tracks attempts and errors:
```python
retry_manager = UMLRetryManager(max_retries=3)

while retry_manager.should_retry():
    try:
        result = handler.generate(description, diagram_type, theme)
        # Success - break loop
        break
    except Exception as e:
        retry_manager.record_error(e)
        if not retry_manager.should_retry():
            # Exhausted retries - use fallback
            result = UMLBotConfig.FALLBACK_PLANTUML_TEMPLATE.format(
                diagram_type=diagram_type,
                description=description
            )
```

**11. Fallback Diagrams**
If LLM or rendering fails after retries, return stub diagram:
- `FALLBACK_PLANTUML_TEMPLATE` = `@startuml\n' {diagram_type} diagram\n' {description}\n@enduml`
- `FALLBACK_MINDMAP_TEMPLATE` = `@startmindmap\n* {diagram_type}\n** {description}\n@endmindmap`
- Similar fallbacks for SALT, Gantt, ERD, JSON

**12. Response Assembly**
`DiagramGenerationResult` dataclass:
```python
@dataclass
class DiagramGenerationResult:
    plantuml_code: str          # Generated PlantUML code
    pil_image: Image.Image | None  # Rendered PNG image
    status_message: str         # Success/error message for user
    image_url: str              # PlantUML server URL for rendering
```

**13. Frontend Display**
- PlantUML code displayed in code editor (editable)
- Image displayed in preview pane
- Chat history shows conversation
- User can:
  - Request changes via chat ("add a class called User")
  - Edit PlantUML code directly and re-render
  - Download image
  - Copy PlantUML code

### Key Design Patterns
- **Handler Pattern**: Each diagram type has a dedicated `*DraftHandler` inheriting from `WorkflowHandler`
- **Prompty Templates**: LLM prompts defined in `.prompty` files (assets/) with variable injection
- **Service Layer**: `DiagramService` abstracts generation + rendering for all diagram types
- **Retry Strategy**: `UMLRetryManager` tracks attempts and error context for auto-correction
- **Fallback Diagrams**: `FALLBACK_*_TEMPLATE` constants provide graceful degradation on LLM/rendering failures

## How to Add a New Diagram Type

Follow this checklist to add a new diagram type (e.g., "Network Diagram"):

**1. Create Prompty Template** (`assets/network_diagram.prompty`)
```yaml
---
name: Network Diagram Generator
description: "Converts description into PlantUML network diagram"
model:
  api: chat
  configuration:
    type: azure_openai
    azure_endpoint: ${UMLBOT_LLM_API_BASE}
  parameters:
    max_tokens: 3000
    temperature: 0.1
variables:
  diagram_type: {type: string, required: true}
  description: {type: string, required: true}
  theme: {type: string, required: false}
---
prompt:
  template: |
    You are an expert network diagram generator...
    [Your prompt here]
```

**2. Create Handler** (`UMLBot/diagram_handlers/network_draft_handler.py`)
```python
from pathlib import Path
from typing import Optional
from llm_utils.aiweb_common.WorkflowHandler import WorkflowHandler
from UMLBot.config.config import UMLBotConfig

class NetworkDraftHandler(WorkflowHandler):
    """Handler for generating network diagrams using PlantUML nwdiag syntax."""

    def __init__(self, config: Optional[UMLBotConfig] = None):
        super().__init__()
        self.prompty_path = Path(__file__).parents[2] / "assets" / "network_diagram.prompty"
        self.config = config or UMLBotConfig()

    def generate(self, description: str, diagram_type: str = "network", theme: Optional[str] = None) -> str:
        """Generate network diagram PlantUML code from description."""
        prompt_template = self.load_prompty()
        self._init_openai(
            openai_compatible_endpoint=self.config.LLM_API_BASE,
            openai_compatible_key=self.config.LLM_API_KEY,
            openai_compatible_model=self.config.LLM_MODEL,
            name="UMLBot"
        )
        formatted_prompt = prompt_template.format_messages(
            diagram_type=diagram_type,
            description=description,
            theme=theme or ""
        )
        response = self.llm_interface.invoke(formatted_prompt)
        return self.check_content_type(response)
```

**3. Export Handler** (`UMLBot/diagram_handlers/__init__.py`)
```python
from UMLBot.diagram_handlers.network_draft_handler import NetworkDraftHandler

__all__ = [
    "UMLDraftHandler",
    "MindmapDraftHandler",
    # ... other handlers ...
    "NetworkDraftHandler",  # Add this
]
```

**4. Add Fallback Template** (`UMLBot/config/config.py`)
```python
class UMLBotConfig:
    # ... existing config ...
    FALLBACK_NETWORK_TEMPLATE = (
        "@startuml\nnwdiag {\n  network dmz {\n    server [address = \"192.168.0.1\"];\n  }\n}\n@enduml"
    )
```

**5. Add Service Method** (`UMLBot/services/diagram_service.py`)
```python
def generate_network_from_description(
    self,
    description: str,
    diagram_type: str = "network",
    theme: Optional[str] = None,
) -> DiagramGenerationResult:
    """Generate network diagram from description."""
    handler = NetworkDraftHandler()
    return self._generate_from_description(
        handler=handler,
        description=description,
        diagram_type=diagram_type,
        theme=theme,
        fallback_template=UMLBotConfig.FALLBACK_NETWORK_TEMPLATE,
        failure_log="LLM-backed network diagram generation failed, returning fallback.",
    )
```

**6. Add API Endpoint** (`UMLBot/api_server.py`)
```python
def create_api_app(
    # ... existing parameters ...
    network_generate_fn: Callable[[str, str, str | None], "DiagramGenerationResult"] | None = None,
    service: DiagramService | None = None,
) -> FastAPI:
    """Builds the FastAPI application..."""
    diagram_service = service or DiagramService()
    if network_generate_fn is None:
        network_generate_fn = diagram_service.generate_network_from_description

    # ... existing setup ...

    @api_app.post("/api/network")
    async def network_endpoint(request: Request):
        """Generate network diagram."""
        try:
            data = await request.json()
            description = data.get("description")
            diagram_type = data.get("diagram_type", "network")
            theme = data.get("theme")

            if not description:
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "message": "Missing description"},
                )

            result = network_generate_fn(description, diagram_type, theme)
            # ... handle result same as other endpoints ...
```

**7. Add to Gradio UI** (`gradio_app.py`)
- Add "Network Diagram" to `output_mode_dropdown` choices
- Add handler in chat callback
- Update routing logic

**8. Add Frontend Support** (`app/frontend/`)
- Add to `constants.ts` diagram type options
- Add server action in `actions/network.action.ts`
- Add API route in `app/api/network/route.ts`
- Update UI to show new option

**9. Add Tests** (`tests/test_network_draft_handler.py`)
```python
import pytest
from UMLBot.diagram_handlers import NetworkDraftHandler

def test_network_handler_loads_prompty():
    handler = NetworkDraftHandler()
    assert handler.prompty_path.exists()

def test_network_handler_generate(monkeypatch):
    # Mock LLM response
    def mock_invoke(prompt):
        return "@startuml\nnwdiag {...}\n@enduml"
    # ... test implementation ...
```

**10. Update Documentation**
- Add entry to `docs/UMLBot/diagram_handlers/network_draft_handler.md`
- Update `docs/index.md` with new diagram type
- Add example to README.md

## Coding Standards

### Core Principles (from .kilocode/rules/coding_standard.md)

**CRITICAL: Reuse Before You Write**
1. **ALWAYS search `./llm_utils/aiweb_common` FIRST** before writing any new code
2. If you find existing functionality in `llm_utils`, import and use it
3. If functionality would be useful across multiple projects, propose adding it to `llm_utils` (never edit `llm_utils` directly)
4. Use `aiweb_common` classes/methods for ALL LLM-related operations

**Python Requirements**
- Target Python ≥ 3.11
- **Type annotations are MANDATORY** - always annotate types for all functions, methods, and variables
- Keep functions small, pure, and independent when possible
- Follow single responsibility principle

**Code Organization**
- `UMLBot/` - Main package & sub-packages
- `UMLBot/config/` - **ALL** hard-coded variables and configuration (never hardcode values in implementation files)
- `tests/` - pytest test suite
- `docs/` - MkDocs documentation
- `docs/PlantUML/` - PlantUML diagram sources

**Security & Privacy**
- Protect PHI/PII: **NEVER** include secrets, patient data, or PII in code or logs
- Use environment variables or `manage_sensitive()` for all credentials
- Validate & sanitize **ALL** external input (including LLM output) before use
- Use parameterized queries for all database access
- Prefer HTTPS/TLS for all external calls
- Limit subprocess calls with `shell=True`; avoid `eval()`, `exec()` on dynamic text
- Follow least-privilege principle: minimal IAM roles, scoped tokens
- All encryption keys must rotate at least every 90 days

### Formatting Standards (.kilocode/rules/formatting.md)

**Single Source of Truth - These settings are STRICT:**
- `black` - Line length 100 (matches `pyproject.toml`)
- `isort` - `profile=black`, `line_length=100`, trailing comma on multiline imports
- `autopep8` - `aggressive=2`, respect same line length

**Before ANY commit, run:**
```bash
make style
```

### Naming Conventions (.kilocode/rules/naming_conventions.md)

| Item | Convention | Example |
|------|------------|---------|
| Package/module | snake_case | `data_loader.py` |
| Variable/function | snake_case | `load_data()` |
| Async function | snake_case + `_async` suffix | `fetch_data_async()` |
| Class | PascalCase | `PatientRecord`, `DiagramService` |
| Constant/enum | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Test modules | `test_*.py` | `test_utils.py`, `test_diagram_service.py` |
| Private attr/method | `_single_leading_underscore` | `_connect()`, `_validate()` |

### Documentation Style (.kilocode/rules/documentation_style.md)

**Docstrings are REQUIRED for:**
- Every public module
- Every public class
- Every public method
- Every public function

**Format:** Use **Google** or **NumPy** style with:
- Clear description
- Args section with types
- Returns section with type
- Raises section (if applicable)
- Examples (when helpful)

**Example:**
```python
def generate_diagram(description: str, diagram_type: str) -> DiagramGenerationResult:
    """Generate a diagram from a text description.

    Args:
        description: Detailed description of the system to diagram.
        diagram_type: Type of diagram (e.g., "class", "sequence").

    Returns:
        DiagramGenerationResult containing PlantUML code and rendered image.

    Raises:
        ValueError: If diagram_type is not supported.
        RuntimeError: If LLM generation fails after all retries.

    Example:
        >>> result = generate_diagram("A user logs in", "sequence")
        >>> print(result.plantuml_code)
    """
```

**MkDocs Requirements:**
- `mkdocs serve` must build with **ZERO warnings**
- `mkdocstrings[python]` autogenerates API reference from docstrings
- Keep these files current:
  - `README.md` - High-level usage
  - `CHANGELOG.md` - Keep-a-Changelog format
  - `CONTRIBUTING.md` - How to run tests & docs
- Diagrams (`.wsd` or `.puml`) live in `docs/uml/` and are rendered in docs

### Restricted Files (.kilocode/rules/restricted_files.md)

**MUST NOT READ, WRITE, OR COMMIT:**
- `.env`, `.env.*` (any environment files)
- `.venv`, `.venv.*` (virtual environments)
- `secrets/` directory
- `supersecrets.txt`
- `credentials.json`
- `*.pem`, `*.key` (certificate/key files)
- `id_rsa`, `id_rsa.pub` (SSH keys)
- Any file in `data/` containing PHI/PII

### Package Management
- **Python**: Use `uv` (preferred) for package management
  - Virtual environment: `.venv/`
  - Pre-installed in Docker devcontainer
- **Frontend**: Use `npm`
  - Dependencies: `app/frontend/package.json`
  - Lock file: `package-lock.json`

### CI Expectations
**Every PR MUST pass:**
- `black` (formatting check)
- `isort` (import ordering check)
- `autopep8` (additional style checks)
- `mypy` (type checking)
- `pytest -q` (all tests pass)

**Testing Requirements:**
- Add/adjust tests with EVERY behavioral change
- Test files: `tests/test_*.py`
- Tests should be fast, isolated, and deterministic

## Testing

- Test files: `tests/test_*.py`
- Run all tests: `make test` or `PYTHONPATH=$(pwd) .venv/bin/python -m pytest -q`
- Run specific test: `PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/test_file.py::test_name -v`
- Tests may require `.env` configuration for LLM integration tests

## Key Configuration

### Backend (UMLBotConfig)
- `BASE_DIR`: UMLBot package root
- `DIAGRAM_TYPES`: Supported UML diagram types (Use Case, Class, Activity, etc.)
- `PLANTUML_SERVER_URL_TEMPLATE`: PlantUML render endpoint (auto-detects Docker vs local)
- `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`: LLM configuration loaded from env or `manage_sensitive()`
- `CORS_ALLOW_ORIGINS`: Frontend origins (defaults to localhost:3000)
- Fallback templates: `FALLBACK_PLANTUML_TEMPLATE`, `FALLBACK_MINDMAP_TEMPLATE`, etc.

### Frontend
- `NEXT_PUBLIC_GRADIO_API_BASE`: Backend API URL
- `NEXT_PUBLIC_PLANTUML_SERVER_BASE`: PlantUML server for client-side rendering

## llm_utils & aiweb_common - The Shared Workspace (.kilocode/.kilocode/rules/llm_utils_guide.md)

**PURPOSE**: Centralize reusable code for building LLM-based applications. Minimize duplication by sharing helpers, utilities, and abstractions across multiple projects.

### Critical Rules for llm_utils
1. **DO NOT EDIT `llm_utils` DIRECTLY** - It is a shared workspace used by multiple projects
2. **ALWAYS search `llm_utils` for existing functionality BEFORE writing new code**
3. If you identify reusable functionality that benefits multiple projects, propose adding it to `llm_utils` (don't implement it yourself)
4. Import and reuse classes/functions from `aiweb_common` to maintain consistency

### Key Components You MUST Use

#### WorkflowHandler (aiweb_common/WorkflowHandler.py)
**What**: Abstract base class for managing LLM workflows
**When to use**: ALL diagram handlers inherit from this
**Key methods:**
- `load_prompty()` - Loads and validates prompty template files
- `_init_openai()` - Initializes LLM interface with OpenAI-compatible endpoint
- `check_content_type()` - Handles AIMessage vs str responses from LLM
- `log_to_database()` - Background task logging to DB (optional)
- `_get_db_connection()` - Database connection helper (optional)

**Example:**
```python
from llm_utils.aiweb_common.WorkflowHandler import WorkflowHandler

class MyDraftHandler(WorkflowHandler):
    def __init__(self, config=None):
        super().__init__()
        self.prompty_path = Path(__file__).parents[2] / "assets" / "my_diagram.prompty"
        self.config = config or UMLBotConfig()
```

#### manage_sensitive (aiweb_common/WorkflowHandler.py)
**What**: Secure credential retrieval across environments
**When to use**: For ANY secret/credential access
**Search order:**
1. `/run/secrets/{name}` (Docker secrets)
2. `/workspaces/*/secrets/{name}.txt` (Devcontainer)
3. `os.getenv(name)` (Environment variables)

**Example:**
```python
from llm_utils.aiweb_common.WorkflowHandler import manage_sensitive

try:
    api_key = manage_sensitive("azure_proxy_key")
except KeyError:
    api_key = os.getenv("UMLBOT_LLM_API_KEY", "")
```

#### ChatResponseHandler (aiweb_common/generate/ChatResponse.py)
**What**: Handler for conversational LLM interactions
**When to use**: For chat-based workflows (like UMLBot's revision workflow)
**Key methods:**
- `generate_response(messages)` - Generate chat response from message history
- `update_history(message, conversation_history)` - Update conversation history

#### GenericErrorHandler (aiweb_common/generate/GenericErrorHandler.py)
**What**: Reusable error handling with retry and correction logic
**When to use**: For operations requiring retries and error correction
**Pattern:**
```python
from llm_utils.aiweb_common.generate.GenericErrorHandler import GenericErrorHandler

def main_operation():
    # ... perform operation ...
    return result

def error_predicate(result) -> bool:
    return isinstance(result, Exception)

def correction_callback(attempt: int, last_result):
    print(f"Attempt {attempt}: Error detected")
    # ... correction logic ...

handler = GenericErrorHandler(
    operation=main_operation,
    error_predicate=error_predicate,
    correction_callback=correction_callback,
    max_retries=5
)
final_result = handler.run()
```

#### ObjectFactory (aiweb_common/ObjectFactory.py)
**What**: Generic factory pattern for creating objects by key
**When to use**: For decoupling/extending object creation logic

#### PromptAssembler (aiweb_common/generate/PromptAssembler.py)
**What**: Construct prompts from templates
**When to use**: When not using prompty templates

### aiweb_common Directory Structure
```
aiweb_common/
├── WorkflowHandler.py         # Base class for all workflow handlers
├── ObjectFactory.py            # Factory pattern implementation
├── configurables/              # Configuration helpers
├── fastapi/                    # FastAPI schemas and validators
├── file_operations/            # File handling utilities
├── generate/                   # LLM generation components
│   ├── ChatResponse.py         # Chat response handler
│   ├── ChatServicer.py         # Chat LLM servicer
│   ├── ChatSchemas.py          # Chat message schemas
│   ├── GenericErrorHandler.py  # Error handling with retries
│   ├── PromptAssembler.py      # Prompt construction
│   ├── PromptyHandler.py       # Prompty file handler
│   ├── QueryInterface.py       # Query abstraction
│   └── ...
├── report_builder/             # Report generation tools
├── resource/                   # External resource interfaces (NIH, PubMed)
└── streamlit/                  # Streamlit UI helpers

```

### When Working with LLM Code

**DO:**
- ✅ Use `WorkflowHandler` as base class for all handlers
- ✅ Use `manage_sensitive()` for credential access
- ✅ Use `ChatResponseHandler` for chat-based LLM interactions
- ✅ Use `GenericErrorHandler` for retry logic
- ✅ Search `aiweb_common/generate/` before writing LLM code
- ✅ Search `aiweb_common/file_operations/` before writing file code
- ✅ Search `aiweb_common/fastapi/` before writing FastAPI schemas

**DON'T:**
- ❌ Write custom LLM clients (use ChatServicer)
- ❌ Write custom retry logic (use GenericErrorHandler)
- ❌ Write custom prompt loaders (use WorkflowHandler.load_prompty)
- ❌ Hardcode credentials (use manage_sensitive)
- ❌ Edit files in `llm_utils/` directly

## Important Notes

- **llm_utils workspace**: `llm_utils/aiweb_common` is a shared workspace package used across multiple projects; **DO NOT EDIT DIRECTLY**—propose changes to the maintainer instead
- **PlantUML server**: Must be running for diagram rendering; use `make plantuml-up` locally or Docker Compose
- **Docker networking**: Inside Docker, services communicate via service names (`http://plantuml:8080`, `http://backend:7860`)
- **Error transparency**: All errors surface to the user with actionable messages; the system attempts LLM-based auto-correction
- **Chat-based workflow**: The frontend chat interface enables iterative diagram refinement through natural language

## Documentation

- Architecture overview: `docs/architecture.md`
- UML workflow: `docs/UMLBot_streamlit_app.md`
- API server: `docs/UMLBot/api_server.md`
- Diagram handlers: `docs/UMLBot/diagram_handlers/`
- Build docs: `make docs` (serves on port 8000)

## Git Workflow

- Main branch: `main`
- Development branch: `develop`
- PRs typically target `develop`
- Format code with `make style` before committing
