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

### 2. Configuration (LLM + PlantUML)

Copy the example environment files and set your own values:

```bash
cp .env.example .env
cp app/frontend/.env.local.example app/frontend/.env.local
```

Set your LLM endpoint and key in `.env`:

- `UMLBOT_LLM_API_BASE` (OpenAI-compatible base URL)
- `UMLBOT_LLM_API_KEY`
- `UMLBOT_LLM_MODEL` (optional; default is `gpt-4o-mini`)

Example base URL for OpenAI-compatible endpoints: `https://api.openai.com/v1`

Start a local PlantUML render server (recommended) from the repo root:

```bash
docker compose up -d plantuml
```

Or use the make targets:

```bash
make plantuml-up
make plantuml-logs
make plantuml-down
```

Defaults point at the local server:

- Backend: `UMLBOT_PLANTUML_SERVER_URL_TEMPLATE=http://localhost:8080/png/{encoded}`

If you prefer a hosted PlantUML server, update those values.

### 3. Docker Compose (Full Stack)

Run the full stack (PlantUML + backend + frontend) with a single command:

```bash
cp .env.example .env
docker compose up --build
```

Edit `.env` to set `UMLBOT_LLM_API_BASE` and `UMLBOT_LLM_API_KEY` before starting
if you want LLM-backed generation.

Then open:

- Frontend: http://localhost:3000

The compose file wires the backend to the internal PlantUML service name
(`http://plantuml:8080`) and keeps backend/PlantUML internal to the Docker network.
The frontend proxies API calls to the backend using `GRADIO_API_BASE` (defaults to
`http://backend:7860` inside Docker).

### 4. Docker Devcontainer Setup (Recommended)

The devcontainer uses `.venv` and runs the startup script in `Docker/startup.sh` to
install dependencies, build the frontend, and launch the backend/frontend. If a `.env`
file exists, it is loaded automatically by the startup script.

1. Ensure Docker Desktop is running (WSL users should have Docker Desktop with WSL integration enabled).
2. Open the repo in VS Code and run **Dev Containers: Reopen in Container**.
3. Set your LLM endpoint and key by copying the example file inside the container:

```bash
cp .env.example .env
```

Then edit `.env` with your values:

- `UMLBOT_LLM_API_BASE`
- `UMLBOT_LLM_API_KEY`
- `UMLBOT_LLM_MODEL` (optional)

4. PlantUML (devcontainer compose):

The devcontainer compose file starts a PlantUML server on the same Docker network.
Set the backend URL to the service name:

```
UMLBOT_PLANTUML_SERVER_URL_TEMPLATE=http://plantuml:8080/png/{encoded}
```

The frontend (browser) should still use:

```
NEXT_PUBLIC_PLANTUML_SERVER_BASE=http://localhost:8080/svg/
```

5. (Optional) Start a local PlantUML server (non-devcontainer workflows):

```bash
make plantuml-up
```

### 5. Running the Apps (Local)

Ensure environment variables are exported before launching the backend:

```bash
set -a
source .env
set +a
```

Start the Gradio/LLM backend:

```bash
uvicorn gradio_app:app --reload
```

Launch the TypeScript/Next.js frontend (now located at `app/frontend`):

```bash
cd app/frontend
npm install
NEXT_PUBLIC_GRADIO_API_BASE=http://localhost:7860 npm run dev
```

The VS Code devcontainer/Docker flow will automatically spin up both the Gradio API (port 7860) and the production Next.js server (port 3000).

### 6. Chat-Based UML Revision Workflow

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

### 5. Documentation

- [Architecture Overview](docs/architecture.md)
- [UML Rendering & Error Handling Workflow](docs/UMLBot_streamlit_app.md)
- [Configuration](docs/UMLBot/config/config.md)
- [Test Coverage](tests/README.md)

See the [docs/](docs/index.md) directory for more details.

---

## Citation

Godwin, R. C.* , Melvin, R. L.*, “Toward Efficient Data Science: A Comprehensive MLOps Template for Collaborative Code Development and Automation”, SoftwareX, 26, 101723, 2024
