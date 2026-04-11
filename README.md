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
## API Endpoints

- `POST /templates`
- `GET /templates`
- `GET /templates/{id}`
- `PUT /templates/{id}`
- `DELETE /templates/{id}`
- `POST /contracts/generate`
- `GET /health`
