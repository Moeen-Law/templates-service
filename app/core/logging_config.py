import logging
from logging.config import dictConfig
from pathlib import Path

from app.core.config import Settings, get_settings

_configured = False


def configure_logging(settings: Settings | None = None) -> None:
    global _configured

    if _configured:
        return

    resolved_settings = settings or get_settings()
    log_file = Path(resolved_settings.log_file_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "text": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                },
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_file),
                    "mode": "w" if resolved_settings.log_overwrite_on_start else "a",
                    "encoding": "utf-8",
                    "formatter": "text",
                },
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "text",
                },
            },
            "root": {
                "level": resolved_settings.log_level.upper(),
                "handlers": ["file", "console"],
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["file", "console"],
                    "level": resolved_settings.log_level.upper(),
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["file", "console"],
                    "level": resolved_settings.log_level.upper(),
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["file", "console"],
                    "level": resolved_settings.log_level.upper(),
                    "propagate": False,
                },
            },
        }
    )

    _configured = True
    logging.getLogger(__name__).info(
        "Logging configured level=%s file=%s overwrite=%s",
        resolved_settings.log_level.upper(),
        str(log_file),
        resolved_settings.log_overwrite_on_start,
    )
