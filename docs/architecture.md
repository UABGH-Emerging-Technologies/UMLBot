**System Component to Code Module and LLM Utility Mapping**

**UI Layer**
- Gradio UI: Handles user input, diagram type selection, preview, and download.
  - Code: `GradioInterface` (to be implemented in the main app, e.g., [`UMLBot_streamlit_app.md`](UMLBot_streamlit_app.md) or a new UI module)
  - Interacts with: `ChatBotService` (service layer)

**Service Layer**
- ChatBotService: Orchestrates the flow from user request to diagram generation.
  - Code: New module/class, e.g., `UMLBot/service/chatbot_service.py`
  - Uses: `NLPParser`, `DiagramBuilder`
- NLPParser: Converts free text to UML constructs using LLM.
  - Code: New module/class, e.g., `UMLBot/service/nlp_parser.py`
  - Leverages: `llm_utils/aiweb_common/generate/ChatServicer.py`, `PromptAssembler.py` for LLM calls and prompt construction.
- DiagramBuilder: Builds PlantUML code from parsed model, manages validation and repair.
  - Code: New module/class, e.g., `UMLBot/service/diagram_builder.py`
  - Uses: `PlantUMLValidator`, `ThemeManager`, `PlantUmlClient`
- PlantUMLValidator & AutoRepairStrategy: Validate and repair PlantUML code.
  - Code: New module/class, e.g., `UMLBot/service/plantuml_validator.py`
  - Can leverage: LLM utilities for advanced repair (e.g., `ChatServicer` for LLM-based repair suggestions)
- ThemeManager: Supplies PlantUML themes.
  - Code: New module/class, e.g., `UMLBot/service/theme_manager.py`

**Infrastructure Layer**
- PlantUmlClient: Renders PlantUML code (remote or local).
  - Code: New module/class, e.g., `UMLBot/infrastructure/plantuml_client.py`
  - Implements: HTTP and local JAR rendering, with failover logic.
- Database, Auth, Monitoring: Standard integrations for user/session/history, authentication, and logging.
  - Code: To be implemented as needed, e.g., `UMLBot/infrastructure/db.py`, `auth.py`, `monitoring.py`

**Supporting Services**
- DownloadController: Serves images to the UI.
  - Code: Part of UI or a small API endpoint.

---

**Chat-Based UML Revision Workflow**

- The chat workflow enables users to iteratively describe, revise, and correct UML diagrams through conversational interaction.
- The UI (Gradio/Streamlit) relays user messages to the service layer, which orchestrates prompt construction, LLM invocation, and diagram updates.
- Each chat turn can request new features, corrections, or explanations; the system updates the PlantUML code and diagram accordingly.
- The workflow supports error correction by leveraging LLM-based auto-repair and surfacing actionable feedback to the user.

**Generic Error Handler Integration**

- The generic error handler is integrated across all layers:
  - UI: Displays status and error messages, provides fallback diagrams.
  - Service: Captures errors from LLM, prompt, and rendering steps; attempts auto-correction.
  - Infrastructure: Handles network and rendering failures, reporting issues to the service layer.
- All errors are routed through the error handler, ensuring transparency and robust recovery.

---

**LLM Utility Integration**
- All LLM calls (NLP parsing, auto-repair, chat-based revision, error handling) should use the `llm_utils/aiweb_common/generate/` classes:
  - `ChatServicer` for conversational LLM calls.
  - `PromptAssembler` for prompt construction.
  - `QueryInterface` for abstraction.
  - `ObjectFactory` for extensibility (e.g., plugin new diagram types).
  - `WorkflowHandler` for orchestrating multi-step flows and logging.
  - `GenericErrorHandler` for capturing, reporting, and auto-correcting errors.

This mapping ensures that all LLM-related logic and error handling are centralized and reusable, following the project's coding standards and leveraging the common codebase.

Next steps: Specify in detail how and where to leverage these LLM interface classes and error handler in the design.
