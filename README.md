# Template Service

Async FastAPI microservice for contract template CRUD, strict data validation, DOCX rendering, and file-service upload integration.

## Features

- Template CRUD with field schema management
- Strict contract input validation (missing, extra, empty, type mismatch)
- Placeholder/schema drift checks before rendering
- DOCX rendering with Jinja syntax via `docxtpl`
- Async integration with File Service
- In-memory metadata cache for generation path

## Structure

- `app/main.py`: FastAPI app entrypoint
- `app/api/routes/`: route handlers
- `app/services/`: business logic
- `app/models/`: SQLAlchemy models
- `app/schemas/`: Pydantic request/response models
- `app/integrations/`: external service clients

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 9000
```

## Migrations (Alembic)

```bash
alembic upgrade head
alembic downgrade -1
```

## Environment Variables

- `DATABASE_URL` (default: `sqlite+aiosqlite:///./template_service.db`)
- `FILES_SERVICE_BASE_URL` (default: `http://localhost:8001`)
- `FILES_SERVICE_DOWNLOAD_PATH_TEMPLATE` (default: `/files/{file_id}`)
- `FILES_SERVICE_UPLOAD_URL_PATH` (default: `/upload`)
- `FILES_SERVICE_AUTH_TOKEN` (default: empty)
- `FILES_SERVICE_TIMEOUT_SECONDS` (default: `20`)
- `FILES_SERVICE_VERIFY_TLS` (default: `true`)
- `FILES_SERVICE_UPLOAD_BUCKET` (default: `AI_DOCUMENTS`)
- `FILES_SERVICE_UPLOADER_ID` (default: empty)
- `TEMPLATE_CACHE_TTL_SECONDS` (default: `300`)
- `AUTO_CREATE_TABLES` (default: `true`)

## API Endpoints

- `POST /templates`
- `GET /templates`
- `GET /templates/{id}`
- `PUT /templates/{id}`
- `DELETE /templates/{id}`
- `POST /contracts/generate`
- `GET /health`
