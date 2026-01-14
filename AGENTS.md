# Repository Guidelines

## Project Structure & Module Organization
- `app/`: Gradio and Streamlit entrypoints (`gradio_app.py`, `streamlit_app.py`), FastAPI server config, and UI assets under `frontend/`.
- `llm_utils/`: Shared AI utilities (packaged via uv workspace); keep cross-cutting helpers here instead of duplicating logic in `app/`.
- `docs/`: MkDocs content and architecture notes; update when adding new flows.
- `tests/`: Pytest suites (`test_*`) covering handlers, chat flows, and error logic; mirror new modules with matching test files.
- `assets/`, `data/`, `PlantUML/`: Sample diagrams, prompt assets, and reference UML snippets used by the apps.

## Setup, Build, and Development Commands
- Create env (uses uv) and install deps:  
  ```bash
  make venv && source .venv/bin/activate
  ```
- Run UI locally: `python app/gradio_app.py` (Gradio) or `python app/streamlit_app.py` (Streamlit).
- Run API server (if used): `python app/server.py`.
- Docs: `mkdocs serve` for live preview, `mkdocs build` for publishable artifacts (or `make docs` to build & serve).
- Lint/format: `make style` runs `black`, `flake8`, `isort`, `autopep8`.

## Coding Style & Naming Conventions
- Python 3.11, 4-space indentation; max line length 100 (black/isort/autopep8 configured in `pyproject.toml`).
- Prefer snake_case for functions/vars, PascalCase for classes, kebab-case for filenames in `frontend/` assets.
- Keep UI strings and prompts near their handlers; avoid hard-coded secrets—read from environment or config.
- Group imports as per isort (standard, third-party, local); avoid unused imports to satisfy flake8.

## Testing Guidelines
- Framework: Pytest. Run full suite with `pytest` (default target `tests/`).
- Name tests `test_<feature>.py` and functions `test_<behavior>`; mirror module structure for new features.
- Include regression cases for error handling and UML generation flows; use small sample UML/PlantUML snippets kept under `assets/` or `PlantUML/`.

## Commit & Pull Request Guidelines
- Commit messages: short, imperative tense (e.g., “Add sequence diagram validator”, “Refine error handler retries”); keep scope focused.
- Before opening a PR: ensure `make style` and `pytest` pass; include a brief summary, how to reproduce/run, and screenshots or sample UML output for UI changes.
- Link related issues and call out config requirements (API keys, env vars) in the description to ease reviewer setup.

## Security & Configuration Tips
- Do not commit secrets; load API keys (OpenAI/Azure, etc.) via environment or a local, git-ignored `.env`.
- Review `docs/Design_Drafter/config/config.md` when adding providers or storage backends; document any new required variables.
- Validate user-provided UML safely—prefer existing sanitization/error-handling helpers in `llm_utils/` and the generic error handler to avoid silent failures.
