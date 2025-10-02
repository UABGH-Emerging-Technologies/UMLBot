# Design_Drafter

Design_Drafter is an interactive tool for generating, revising, and validating UML diagrams using a chat-based workflow powered by LLMs. The system supports iterative UML refinement, automatic error correction, and transparent error reporting, all accessible through a conversational interface.

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

### 2. Running the App

Start the Gradio UI:

```bash
python app/gradio_app.py
```

Or the Streamlit UI:

```bash
python app/streamlit_app.py
```

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
   - If an error occurs (e.g., invalid UML, rendering failure), the error handler will display a clear message and attempt auto-correction.
   - All status updates and errors are shown in the UI for transparency.

### 4. Documentation

- [Architecture Overview](docs/architecture.md)
- [UML Rendering & Error Handling Workflow](docs/Design_Drafter_streamlit_app.md)
- [Configuration](docs/Design_Drafter/config/config.md)
- [Test Coverage](tests/README.md)

See the [docs/](docs/index.md) directory for more details.

---

## Citation

Godwin, R. C.* , Melvin, R. L.*, “Toward Efficient Data Science: A Comprehensive MLOps Template for Collaborative Code Development and Automation”, SoftwareX, 26, 101723, 2024