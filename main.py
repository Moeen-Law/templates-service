from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.main import app


def run() -> None:
    import uvicorn

    settings = get_settings()
    configure_logging(settings)
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None,
        access_log=True,
    )


if __name__ == "__main__":
    run()
