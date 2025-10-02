# config.py
import logging
import logging.config
import sys
from pathlib import Path
from aiweb_common.WorkflowHandler import manage_sensitive
from rich.logging import RichHandler

class Design_DrafterConfig:
    """
    Configuration class for Design Drafter.

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
    DATA_DIR = Path("/data/DATASCI")
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
        "Sequence"
    ]
    DEFAULT_DIAGRAM_TYPE = "Use Case"
    DEFAULT_INPUT = "Test"
    SYSTEM_PROMPT_TEMPLATE = "Convert the following description into a PlantUML {diagram_type} diagram.\n{input}"
    FALLBACK_PLANTUML_TEMPLATE = "@startuml\n' {diagram_type} diagram\n' {description}\n@enduml"
    API_KEY_MISSING_MSG = (
        "OpenAI API key not found. Please ensure it is available via /run/secrets, /workspaces/*/secrets, or as an environment variable."
    )
    DIAGRAM_SUCCESS_MSG = "Diagram generated successfully using LLM."
    PLANTUML_SERVER_URL_TEMPLATE = "http://138.26.48.104:8080/png/{encoded}"

    # LLM Configuration
    # For security, prefer to set LLM_API_KEY as an environment variable.
    import os
    LLM_API_KEY = manage_sensitive("azure_proxy_key")  # Replace with your default or leave blank
    LLM_MODEL = "gpt-4o-mini"
    LLM_API_BASE = "https://proxy-ai-anes-uabmc-awefchfueccrddhf.eastus2-01.azurewebsites.net/v1"
    # If using Azure, set LLM_API_BASE to your Azure endpoint and adjust model name as needed.

    # MLFlow model registry



# Make sure log directory exists
Design_DrafterConfig.LOGS_DIR.mkdir(parents=True, exist_ok=True)

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
            "filename": str(Design_DrafterConfig.LOGS_DIR / "info.log"),
            "maxBytes": 10485760,
            "backupCount": 10,
            "formatter": "detailed",
            "level": logging.INFO,
            "mode": "a", 
        },
        "error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(Design_DrafterConfig.LOGS_DIR / "error.log"),
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