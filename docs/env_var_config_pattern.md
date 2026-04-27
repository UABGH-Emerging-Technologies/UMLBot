# Environment Variable Configuration Pattern

This document describes the pattern for using environment variables to override
application configuration values.  The goal is a **single name** that appears
identically in the Python config class, the Docker Compose `environment:`
block, the Azure Container App configuration screen, and any `.env` files.

## Core rule

> **The Python constant name and the environment variable name MUST be
> identical.**

When an operator sets `REASONING_EFFORT=medium` on an Azure container, they
should be able to grep the codebase for that exact string and land on the
config class attribute that consumes it.  No prefix translation, no casing
changes.

## How to add a new overridable config value

### 1. Add the class attribute with `os.getenv`

```python
# UMLBot/config/config.py
class UMLBotConfig:
    # <short comment explaining the setting and valid values>
    MY_NEW_SETTING: str = os.getenv("MY_NEW_SETTING", "default_value")
```

- The first argument to `os.getenv` is the **same string** as the attribute name.
- Always provide a sensible default so the app runs without any env vars set.
- Use a type annotation on the attribute.

### 2. Add it to `docker-compose.yml`

```yaml
services:
  umlbot:
    environment:
      MY_NEW_SETTING: ${MY_NEW_SETTING:-default_value}
```

The `${VAR:-default}` syntax lets the host's env override the compose default,
which in turn overrides the Python default.  Use the **same default** in both
places to avoid surprises.

### 3. Add it to `.env.example`

```bash
# Description of the setting (default: default_value)
# MY_NEW_SETTING=default_value
```

Keep entries commented out so a bare `cp .env.example .env` produces a
working configuration that matches the Python defaults.

### 4. Reference it in code

```python
from UMLBot.config.config import UMLBotConfig

value = UMLBotConfig.MY_NEW_SETTING
```

Never call `os.getenv` a second time elsewhere in the code.  All env var
reads are centralized in the config class.

## Naming conventions

| Scope | Convention | Example |
|-------|-----------|---------|
| UMLBot-specific infrastructure | `UMLBOT_` prefix | `UMLBOT_PLANTUML_JAR_PATH` |
| LLM / API behaviour settings | Descriptive, no prefix | `REASONING_EFFORT` |
| Cross-service URLs | `UMLBOT_` prefix | `UMLBOT_ENDPOINT` |

The prefix is useful when an env var might collide with another service's
variable in a shared container group.  For settings that are clearly
domain-specific (like `REASONING_EFFORT` for OpenAI's Responses API), a prefix
adds noise without reducing ambiguity.

Use your judgement, but when in doubt, match the name the external API or
documentation already uses.

## Current inventory

| Python constant | Env var | Default | Location |
|----------------|---------|---------|----------|
| `UMLBOT_PLANTUML_JAR_PATH` | `UMLBOT_PLANTUML_JAR_PATH` | `/opt/plantuml/plantuml.jar` | `UMLBotConfig` |
| `UMLBOT_DATA_DIR`* | `UMLBOT_DATA_DIR` | `/data` | `UMLBotConfig` |
| `REASONING_EFFORT` | `REASONING_EFFORT` | `low` | `UMLBotConfig` |
| `UMLBOT_ENDPOINT`** | `UMLBOT_ENDPOINT` | `http://localhost:8000` | `streamlit_app.py` |

\* `UMLBOT_DATA_DIR` is consumed as `DATA_DIR` in the config class today.
This is a legacy inconsistency that should be aligned in a future PR.

\** `UMLBOT_ENDPOINT` lives in `streamlit_app.py` as `API_BASE_URL` rather
than in `UMLBotConfig`.  This is another legacy inconsistency to align.

## Anti-patterns

- **Different names for the same thing.** Don't name the attribute
  `JAR_PATH` and the env var `UMLBOT_PLANTUML_JAR_PATH`.  An operator
  reading the Azure config screen should be able to find the code with a
  single search.

- **Scattered `os.getenv` calls.** Every env-var read should be in
  `UMLBotConfig` (or the equivalent config module for other projects).
  Duplicate reads in service code make it hard to audit what the app
  depends on.

- **Missing defaults.** If a setting doesn't have a default, the app crashes
  on startup when the env var is absent.  If a value is truly required (like
  an API key), use `manage_sensitive()` instead of `os.getenv`.
