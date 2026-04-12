import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import contracts, templates
from app.core.config import get_settings
from app.core.db import init_db
from app.core.exceptions import (
    FileServiceError,
    TemplateNotFoundError,
    ValidationError,
)
from app.core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logger.info("Application startup started")
    if settings.auto_create_tables:
        logger.info("Auto-create tables is enabled, initializing database")
        await init_db()
    logger.info("Application startup completed")
    yield
    logger.info("Application shutdown completed")


settings = get_settings()


app = FastAPI(
    title=settings.service_name,
    version=settings.version,
    lifespan=lifespan,
)


@app.middleware("http")
async def log_request_lifecycle(request: Request, call_next):
    started_at = time.perf_counter()
    logger.info(
        "Incoming request method=%s path=%s query=%s",
        request.method,
        request.url.path,
        request.url.query,
    )
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.exception(
            "Request failed method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise
    duration_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "Request completed method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(templates.router, prefix="/templates", tags=["templates"])
app.include_router(contracts.router, prefix="/contracts", tags=["contracts"])


@app.get("/health")
async def health() -> dict[str, str]:
    logger.debug("Health endpoint called")
    return {"status": "ok"}


@app.exception_handler(TemplateNotFoundError)
async def template_not_found_handler(request: Request, exc: TemplateNotFoundError):
    logger.warning(
        "Template not found path=%s detail=%s",
        request.url.path,
        str(exc),
    )
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    logger.warning(
        "Validation error path=%s errors=%s",
        request.url.path,
        exc.errors,
    )
    return JSONResponse(status_code=422, content={"errors": exc.errors})


@app.exception_handler(FileServiceError)
async def file_service_error_handler(request: Request, exc: FileServiceError):
    logger.exception(
        "File service failure path=%s detail=%s",
        request.url.path,
        str(exc),
    )
    return JSONResponse(status_code=502, content={"detail": str(exc)})
