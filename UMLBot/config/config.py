"""Application configuration for UMLBot."""

import logging
import logging.config
import os
from pathlib import Path

from aiweb_common.WorkflowHandler import manage_sensitive


def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file without overriding existing envs."""
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        os.environ[key] = value


# Load repo-root .env for local/dev runs (do not override explicit env vars).
_load_env_file(Path(__file__).resolve().parents[2] / ".env")


class UMLBotConfig:
    """
    Configuration class for UMLBot.

    Sensitive values (e.g., LLM_API_KEY) are retrieved using manage_sensitive for secure handling.
    If the secret is not found, a default value is used.

    Example:
        try:
            api_key = manage_sensitive("OPENAI_API_KEY")
        except KeyError:
            api_key = "sk-..."

    Raises:
        KeyError: If manage_sensitive is called and the secret is not found, unless fallback is provided.

    Directories prepopulated in the template:
        BASE_DIR, CONFIG_DIR, LOGS_DIR, DATA_DIR, RAW_DATA, INTERMEDIATE_DIR, RESULTS_DIR

    See Also:
        llm_utils.aiweb_common.WorkflowHandler.manage_sensitive
    """

    BASE_DIR = Path(__file__).parent.parent.absolute()
    CONFIG_DIR = Path(BASE_DIR, "config")
    LOGS_DIR = Path(BASE_DIR, "logs")

    # Data Directories
    DATA_DIR = Path(os.getenv("UMLBOT_DATA_DIR", "/data"))
    RAW_DATA = Path(DATA_DIR, "raw")
    INTERMEDIATE_DIR = Path(DATA_DIR, "intermediate")
    RESULTS_DIR = Path(DATA_DIR, "results")

    # Assets
    # Add assets here as needed.
    HEADER_MARKDOWN = """# EXAMPLE Header Markdown \r todo - update this """
    EXAMPLE_OUTPUT = Path(INTERMEDIATE_DIR, "Example_Output.csv")

    # UML Diagram Generator App Configs
    DIAGRAM_TYPES = [
        "Use Case",
        "Class",
        "Activity",
        "Component",
        "Deployment",
        "State Machine",
        "Timing",
        "Sequence",
    ]
    DEFAULT_DIAGRAM_TYPE = "Use Case"
    DEFAULT_INPUT = "Test"
    SYSTEM_PROMPT_TEMPLATE = (
        "Convert the following description into a PlantUML {diagram_type} diagram.\n{input}"
    )
    FALLBACK_PLANTUML_TEMPLATE = "@startuml\n' {diagram_type} diagram\n' {description}\n@enduml"
    API_KEY_MISSING_MSG = (
        "LLM API key or base URL not found. Please ensure UMLBOT_LLM_API_KEY and "
        "UMLBOT_LLM_API_BASE are set (via /run/secrets, /workspaces/*/secrets, or "
        "environment variables)."
    )
    DIAGRAM_SUCCESS_MSG = "Diagram generated successfully using LLM."
    _DEFAULT_PLANTUML_TEMPLATE = "http://localhost:8080/png/{encoded}"
    _RUNNING_IN_DOCKER = Path("/.dockerenv").exists()
    if _RUNNING_IN_DOCKER:
        _DEFAULT_PLANTUML_TEMPLATE = "http://plantuml:8080/png/{encoded}"
    PLANTUML_SERVER_URL_TEMPLATE = os.getenv(
        "UMLBOT_PLANTUML_SERVER_URL_TEMPLATE",
        _DEFAULT_PLANTUML_TEMPLATE,
    )
    if _RUNNING_IN_DOCKER and PLANTUML_SERVER_URL_TEMPLATE.startswith(
        ("http://localhost:8080", "http://127.0.0.1:8080")
    ):
        PLANTUML_SERVER_URL_TEMPLATE = PLANTUML_SERVER_URL_TEMPLATE.replace(
            "http://localhost:8080", "http://plantuml:8080"
        ).replace("http://127.0.0.1:8080", "http://plantuml:8080")

    # LLM Configuration
    # For security, prefer to set LLM_API_KEY as an environment variable.
    try:
        LLM_API_KEY = manage_sensitive("azure_proxy_key")
    except KeyError:
        LLM_API_KEY = os.getenv("UMLBOT_LLM_API_KEY", "")
    LLM_MODEL = os.getenv("UMLBOT_LLM_MODEL", "gpt-4o-mini")
    LLM_API_BASE = os.getenv("UMLBOT_LLM_API_BASE", "")
    CORS_ALLOW_ORIGINS = os.getenv("UMLBOT_CORS_ALLOW_ORIGINS", "")
    if CORS_ALLOW_ORIGINS:
        CORS_ALLOW_ORIGINS = [origin.strip() for origin in CORS_ALLOW_ORIGINS.split(",")]
    else:
        CORS_ALLOW_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # If using Azure, set LLM_API_BASE to your Azure endpoint and adjust model name as needed.

    # MLFlow model registry


# Make sure log directory exists
UMLBotConfig.LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "minimal": {"format": "%(message)s"},
        "detailed": {
            "format": "%(levelname)s %(asctime)s [%(name)s:%(filename)s:%(funcName)s:%(lineno)d]\n%(message)s\n"
        },
    },
    "handlers": {
        "console": {
            "class": "rich.logging.RichHandler",
            "level": logging.DEBUG,
            "formatter": "minimal",
            "markup": True,  # Pass argument to RichHandler
        },
        "info": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(UMLBotConfig.LOGS_DIR / "info.log"),
            "maxBytes": 10485760,
            "backupCount": 10,
            "formatter": "detailed",
            "level": logging.INFO,
            "mode": "a",
        },
        "error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(UMLBotConfig.LOGS_DIR / "error.log"),
            "maxBytes": 10485760,
            "backupCount": 10,
            "formatter": "detailed",
            "level": logging.ERROR,
            "mode": "a",
        },
    },
    "root": {
        "handlers": ["console", "info", "error"],
        "level": logging.INFO,
        "propagate": False,
    },
}

logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)
