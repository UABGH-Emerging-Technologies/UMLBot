"""Application configuration for UMLBot."""

import logging
import logging.config
import os
from pathlib import Path


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

    LLM credentials are supplied per-request (v1 paradigm).
    Only non-LLM settings are stored here.

    Directories prepopulated in the template:
        BASE_DIR, CONFIG_DIR, LOGS_DIR, DATA_DIR, RAW_DATA, INTERMEDIATE_DIR, RESULTS_DIR

    See Also:
        azurify.md for the v1 credential paradigm.
    """

    BASE_DIR = Path(__file__).parent.parent.absolute()
    CONFIG_DIR = Path(BASE_DIR, "config")
    LOGS_DIR = Path(BASE_DIR, "logs")

    # Data Directories
    DATA_DIR = Path(os.getenv("UMLBOT_DATA_DIR", "/data"))
    RAW_DATA = Path(DATA_DIR, "raw")
    INTERMEDIATE_DIR = Path(DATA_DIR, "intermediate")
    RESULTS_DIR = Path(DATA_DIR, "results")

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

    FALLBACK_PLANTUML_TEMPLATE = "@startuml\n' {diagram_type} diagram\n' {description}\n@enduml"
    FALLBACK_MINDMAP_TEMPLATE = (
        "@startmindmap\n* {diagram_type}\n** {description}\n@endmindmap"
    )
    FALLBACK_SALT_TEMPLATE = (
        "@startsalt\n{diagram_type}\n{description}\n@endsalt"
    )
    FALLBACK_GANTT_TEMPLATE = (
        "@startgantt\n[Task] lasts 1 day\n@endgantt"
    )
    FALLBACK_ERD_TEMPLATE = (
        "@startuml\nentity \"Entity\" as E {\n  *id : int\n}\n@enduml"
    )
    FALLBACK_JSON_TEMPLATE = (
        "@startjson\n{\n  \"sample\": true\n}\n@endjson"
    )
    FALLBACK_C4_TEMPLATE = (
        "@startuml\n"
        "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml\n"
        "title {diagram_type}\n"
        "Person(user, \"User\", \"\")\n"
        "System(system, \"System\", \"{description}\")\n"
        "Rel(user, system, \"Uses\")\n"
        "@enduml"
    )
    DIAGRAM_SUCCESS_MSG = "Diagram generated successfully using LLM."

    # PlantUML JAR rendering
    PLANTUML_JAR_PATH = os.getenv(
        "UMLBOT_PLANTUML_JAR_PATH",
        "/opt/plantuml/plantuml.jar",
    )


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
            "markup": True,
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
