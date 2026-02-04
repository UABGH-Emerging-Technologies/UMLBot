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
python3 -m venv venv
source venv/bin/activate
python3 -m pip install pip setuptools wheel
python3 -m pip install -e .
```

For development:

```bash
python3 -m pip install -e ".[dev]"
```

### 2. Running the Apps

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

### 3. Chat-Based UML Revision Workflow

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

### 4. Documentation

- [Architecture Overview](docs/architecture.md)
- [UML Rendering & Error Handling Workflow](docs/UMLBot_streamlit_app.md)
- [Configuration](docs/UMLBot/config/config.md)
- [Test Coverage](tests/README.md)

See the [docs/](docs/index.md) directory for more details.

---

## Citation

Godwin, R. C.* , Melvin, R. L.*, “Toward Efficient Data Science: A Comprehensive MLOps Template for Collaborative Code Development and Automation”, SoftwareX, 26, 101723, 2024
