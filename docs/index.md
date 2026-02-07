## Documentation

### Key Features

- **Chat-Based UML Revision Workflow:**
  Generate, revise, and correct UML diagrams interactively via a conversational interface. See [UML Rendering & Error Handling Workflow](UMLBot_streamlit_app.md) and [Architecture Overview](architecture.md).
- **Generic Error Handler:**
  All errors are captured, reported, and auto-corrected when possible. See [Error Handling](UMLBot_streamlit_app.md).

### Environment Setup

Copy the example file and set your LLM endpoint and key:

```bash
cp .env.example .env
```

Required env vars:

- `UMLBOT_LLM_API_BASE`
- `UMLBOT_LLM_API_KEY`

Optional:

- `UMLBOT_LLM_MODEL` (defaults to `gpt-4o-mini`)
- `UMLBOT_PLANTUML_SERVER_URL_TEMPLATE` (defaults to `http://localhost:8080/png/{encoded}`)
- `UMLBOT_CORS_ALLOW_ORIGINS`
- `NEXT_PUBLIC_PLANTUML_SERVER_URL_TEMPLATE` (frontend fallback; set to match the PlantUML server, e.g. `http://localhost:8080/svg/{encoded}`)

### Main Documentation

- [Workflows](UMLBot/uml_draft_handler.md): main workflows.
- [Configuration](UMLBot/config/config.md): Configuration Details
- [User Interface](UMLBot_streamlit_app.md)
- [Architecture Overview](architecture.md)
- [Test Coverage](tests/README.md)

If you found this helpful in your work, please cite:

Godwin, R. C.* , Melvin, R. L.*, “Toward Efficient Data Science: A Comprehensive MLOps Template for Collaborative Code Development and Automation”, SoftwareX, 26, 101723, 2024
