from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes import contracts, templates
from app.core.config import get_settings
from app.core.db import init_db
from app.core.exceptions import (
    FileServiceError,
    TemplateNotFoundError,
    ValidationError,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.auto_create_tables:
        await init_db()
    yield


settings = get_settings()


app = FastAPI(
    title=settings.service_name,
    version=settings.version,
    lifespan=lifespan,
)

app.include_router(templates.router, prefix="/templates", tags=["templates"])
app.include_router(contracts.router, prefix="/contracts", tags=["contracts"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(TemplateNotFoundError)
async def template_not_found_handler(_, exc: TemplateNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(_, exc: ValidationError):
    return JSONResponse(status_code=422, content={"errors": exc.errors})


@app.exception_handler(FileServiceError)
async def file_service_error_handler(_, exc: FileServiceError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})
