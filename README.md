# UMLBot
<img width="256" height="256" alt="umlbot" align="right" src="https://github.com/user-attachments/assets/f49dc59a-6862-4765-988b-61c6d752b2cf" />

UMLBot is an interactive tool for generating, revising, and validating UML diagrams using a chat-based workflow powered by LLMs. The system supports iterative UML refinement, automatic error correction, and transparent error reporting, all accessible through a conversational interface. This code is release in conjuction with publication submission to SoftwareX. 

## Features

- **Chat-Based UML Revision Workflow:**  
  Interactively describe, generate, and refine UML diagrams via a chat interface. The system supports iterative feedback, allowing users to request changes, corrections, or enhancements in natural language.

- **Generic Error Handler:**  
  All errors (LLM, prompt, PlantUML rendering, network, etc.) are captured and surfaced to the user with actionable messages. The error handler provides fallback behaviors and clear status updates, ensuring a robust user experience.

- **Automated Error Correction:**  
  When UML code or rendering fails, the system attempts to auto-correct issues using LLM-based repair strategies, with user feedback and transparency.

- **Flexible UI:**  
  Accessible via Gradio (and Streamlit) interfaces, supporting free-text input, diagram type selection, and theme customization.

## Usage

### 1. Installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pip setuptools wheel
python3 -m pip install -e .
```

For development:

```bash
python3 -m pip install -e ".[dev]"
```

### 2. Credentials (LLM proxy)

LLM credentials resolve through `aiweb_common.manage_sensitive()`, which checks
in order: `/run/secrets` (compose secrets), `/workspaces/*/secrets`
(devcontainer), `/mnt/p/Secrets` (shared team mount), then environment
variables. Two supported workflows:

- **Shared secrets mount (default):** if `/mnt/p/Secrets/azure_proxy_key.txt`
  and `/mnt/p/Secrets/azure_proxy_endpoint.txt` exist, no configuration is
  needed — `docker compose up` mounts them as compose secrets and `make run`
  reads the mount directly.
- **.env (off-network / no mount):** `cp .env.example .env` and fill in
  `azure_proxy_key` / `azure_proxy_endpoint`. For Docker, switch each secret in
  `docker-compose.yml` from its `file:` source to its `environment:` source
  (instructions are in both files).

### 3. Docker Compose (Full Stack)

```bash
docker compose up --build
```

- Backend API: http://localhost:8000 (override host port with `UMLBOT_API_PORT`)
- Streamlit frontend: http://localhost:8501 (override with `UMLBOT_STREAMLIT_PORT`)

The single image bundles Python, a JRE, and the PlantUML JAR — there is no
separate PlantUML server. The streamlit service reaches the backend over
compose DNS (`http://umlbot:8000`).

### 4. Local Development (`make run`)

```bash
make venv      # create .venv with uv
make run       # backend on :8000 + minimal testing UI on :8501
```

`make run` starts the FastAPI backend and the minimal testing UI
(`streamlit/diagram_builder.py`). Credentials come from `/mnt/p/Secrets` or
your `.env` (loaded automatically by the Makefile). Java 17+ is required for
the PlantUML JAR; set `UMLBOT_PLANTUML_JAR_PATH` if yours is not at the
default location.

### 5. Chat-Based UML Revision Workflow

1. **Describe your system:**  
   Enter a free-text description of the system or process you want to model.
2. **Select diagram type and theme:**  
   Choose the UML diagram type (e.g., class, sequence) and an optional theme.
3. **Iterate via chat:**  
   - Review the generated diagram and PlantUML code.
   - Use the chat interface to request changes, corrections, or ask questions (e.g., "Add a new class", "Fix the association", "Why did this error occur?").
   - The system will update the diagram and code, handling errors and providing feedback as needed.
4. **Error Handling:**  
   - If an error occurs (e.g., invalid UML, rendering failure), the error handler will display a clear message. Refreshing and trying again is usually a sufficient fix. 
   - All status updates and errors are shown in the UI for transparency.

### 6. Documentation

- [Architecture Overview](docs/architecture.md)
- [UML Rendering & Error Handling Workflow](docs/UMLBot_streamlit_app.md)
- [Configuration](docs/UMLBot/config/config.md)
- [Test Coverage](tests/README.md)

See the [docs/](docs/index.md) directory for more details.

---

## Citation

Godwin, R. C.* , Melvin, R. L.*, “Toward Efficient Data Science: A Comprehensive MLOps Template for Collaborative Code Development and Automation”, SoftwareX, 26, 101723, 2024
