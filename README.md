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

## Database (PostgreSQL)

This service is configured to use PostgreSQL by default.

```bash
docker run --name template-service-postgres \
	-e POSTGRES_USER=postgres \
	-e POSTGRES_PASSWORD=postgres \
	-e POSTGRES_DB=template_service \
	-p 5432:5432 \
	-d postgres:16-alpine
```

Set `DATABASE_URL` in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/template_service
```

## Vault Secrets (Deployment)

This service supports loading runtime settings from HashiCorp Vault KV v2.
When enabled, Vault values are injected into environment variables before app
settings and Alembic migrations are initialized.

### Environment Indicator

Use `ENVIRONMENT` outside Vault (in process env or `.env`) as the source of truth
for selecting config context.

- `ENVIRONMENT=dev` or `ENVIRONMENT=development` -> loads `.env` then `.env.dev`
- `ENVIRONMENT=prod` or `ENVIRONMENT=production` -> loads `.env` then `.env.prod`

Recommended layout:

- `.env`: shared values and Vault connection/auth settings
- `.env.dev`: development overrides (for example `VAULT_KV_PATH=templates/dev`)
- `.env.prod`: production overrides (for example `VAULT_KV_PATH=templates/prod`)

Precedence for determining the environment:

1. Process environment variable `ENVIRONMENT`
2. `ENVIRONMENT` value in `.env`
3. Default `development`

Vault should contain runtime secrets for the selected environment, but should not
be the primary selector of the environment itself.

### Expected Secret Shape (JSON)

Store the secret as a flat JSON object where keys are environment variable names:

```json
{
	"DATABASE_URL": "postgresql+asyncpg://user:password@db-host:5432/template_service",
	"FILES_SERVICE_AUTH_TOKEN": "your-production-token",
	"FILES_SERVICE_BASE_URL": "https://gateway.example.com"
}
```

### App Environment Variables

Set these in your deployment environment:

```env
ENVIRONMENT=prod
VAULT_ENABLED=true
VAULT_ADDR=https://vault.moeenlaw.com
VAULT_ROLE_ID=<approle-role-id>
VAULT_SECRET_ID=<approle-secret-id>
VAULT_AUTH_PATH=approle
VAULT_KV_MOUNT=env
VAULT_KV_PATH=templates/dev
VAULT_FAIL_FAST=true
```

Optional:

```env
VAULT_NAMESPACE=
VAULT_TIMEOUT_SECONDS=10
VAULT_SKIP_VERIFY=false
VAULT_CACERT=
```

### What You Need To Do In Vault (Website/UI)

1. Sign in to Vault UI.
2. Ensure a KV v2 secrets engine exists at mount path `env`.
3. Create secret path `templates/dev` under that mount.
4. Add required runtime keys (for example `DATABASE_URL` and `FILES_SERVICE_AUTH_TOKEN`) and save.
5. Enable AppRole auth method (path `approle`) if it is not already enabled.
6. Create an AppRole with read permission on `env/data/templates/dev`.
7. Retrieve the role ID and generate a secret ID for that AppRole.
8. Put them in deployment variables `VAULT_ROLE_ID` and `VAULT_SECRET_ID`.

### Notes

- With `VAULT_FAIL_FAST=true`, the service fails startup if Vault cannot be read.
- The same Vault loading flow is used by Alembic migrations, so migration
	commands can read `DATABASE_URL` from Vault too.

## Consul Service Registry

This service supports automatic registration and deregistration in Consul during
application startup and shutdown.

- Registration endpoint: `PUT /v1/agent/service/register`
- Deregistration endpoint: `PUT /v1/agent/service/deregister/:service_id`
- Health check target defaults to `http://127.0.0.1:${PORT}/health` when not
	explicitly configured.

### Vault Secret Format (Nested `consul` object)

This project now supports the nested format below directly from Vault:

```json
{
	"consul": {
		"check": {
			"deregisterCriticalServiceAfter": "1m",
			"http": "http://moeenlaw.com:9009/health",
			"interval": "15s",
			"timeout": "5s"
		},
		"host": "discovery.moeenlaw.com",
		"port": "443",
		"schema": "https",
		"secure": true,
		"serviceName": "template-service",
		"token": "<consul-acl-token>"
	}
}
```

The Vault loader injects the top-level `consul` key as an environment variable,
and the settings layer maps it to typed `CONSUL_*` runtime fields.

### Optional Flat Environment Variables

Flat variables are also supported and take precedence over nested `consul`
values when both are present.

```env
CONSUL_ENABLED=true
CONSUL_FAIL_FAST=true
CONSUL_HOST=discovery.moeenlaw.com
CONSUL_PORT=443
CONSUL_SCHEME=https
CONSUL_SECURE=true
CONSUL_TOKEN=<consul-acl-token>
CONSUL_SERVICE_NAME=template-service
CONSUL_SERVICE_ID=
CONSUL_SERVICE_ADDRESS=
CONSUL_CHECK_HTTP=
CONSUL_CHECK_INTERVAL=15s
CONSUL_CHECK_TIMEOUT=5s
CONSUL_CHECK_DEREGISTER_CRITICAL_SERVICE_AFTER=1m
```

### ACL Requirements

- Registration and deregistration require a token with `service:write`.
- If registration should not block startup in non-critical environments, set
	`CONSUL_FAIL_FAST=false`.

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
