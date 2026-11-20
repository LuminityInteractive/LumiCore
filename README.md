# LumiCore

[![Python](https://img.shields.io/badge/python-3.14%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.163%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Open-source backend infrastructure for modern applications.

## Status

Early development. The current implementation includes the HTTP API
foundation, PostgreSQL integration, project management, authentication,
protected Management API endpoints, Docker Compose runtime, and automated
tests.

## Implemented

- FastAPI application with versioned `/v1` endpoints.
- Standard `{ "data": ..., "error": ... }` response envelope.
- Centralized HTTP and validation error handling.
- PostgreSQL 16 with SQLAlchemy 2.x and `asyncpg`.
- Alembic database migrations.
- Project CRUD operations.
- Project membership checks and owner membership on project creation.
- Password hashing with Argon2.
- JWT access and refresh tokens.
- Refresh token rotation and revocation.
- Bearer-token authentication for the Management API.
- Docker Compose runtime for the API and PostgreSQL.

## Requirements

- Python 3.14 or newer.
- [`uv`](https://docs.astral.sh/uv/).
- Docker Engine.
- Docker Compose.

PostgreSQL does not need to be installed on the host system. It runs in a
Docker container.

## Quick start

Copy the environment template:

```bash
cp .env.example .env
```

Set a local PostgreSQL password and a random JWT secret in `.env`. The password
in `DATABASE_URL` must match `POSTGRES_PASSWORD`.

Start the complete local stack:

```bash
docker compose up -d --build
```

Check container status:

```bash
docker compose ps
```

The API is available at:

```text
http://localhost:8000
```

Basic health checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/database
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

Stop the stack:

```bash
docker compose down
```

`docker compose down -v` also deletes the PostgreSQL data volume.

## Local development

Run only PostgreSQL in Docker:

```bash
docker compose up -d database
```

Run the API locally with auto-reload:

```bash
uv run --env-file .env uvicorn lumicore.main:app --reload
```

When running the API locally, `DATABASE_URL` must use `localhost`:

```text
postgresql+asyncpg://<user>:<password>@localhost:5432/<database>
```

When running the API inside Docker Compose, the database hostname is the
Compose service name:

```text
postgresql+asyncpg://<user>:<password>@database:5432/<database>
```

## Tests

Tests use the separate `lumicore_test` PostgreSQL database. Create it once:

```bash
docker compose exec database psql \
  -U lumicore \
  -d postgres \
  -c "CREATE DATABASE lumicore_test OWNER lumicore;"
```

Apply migrations to the test database:

```bash
env \
  DATABASE_URL="postgresql+asyncpg://<user>:<password>@localhost:5432/lumicore_test" \
  JWT_SECRET="test-secret-0123456789-0123456789" \
  uv run alembic upgrade head
```

Run the test suite:

```bash
env \
  DATABASE_URL="postgresql+asyncpg://<user>:<password>@localhost:5432/lumicore_test" \
  JWT_SECRET="test-secret-0123456789-0123456789" \
  uv run pytest
```

The test fixtures clear the test tables between tests. The development
database is not used by the test suite.

## Database migrations

Check the current migration revision:

```bash
uv run --env-file .env alembic current
```

Check for model/schema drift:

```bash
uv run --env-file .env alembic check
```

Create a migration after changing SQLAlchemy models:

```bash
uv run --env-file .env alembic revision --autogenerate -m "describe the change"
```

Review the generated migration before applying it:

```bash
uv run --env-file .env alembic upgrade head
```

Do not edit migrations that have already been applied. Create a new migration
for subsequent schema changes.

## API

### Health

```http
GET /
GET /health
GET /health/database
GET /v1/health
```

### Authentication

```http
POST /v1/auth/signup
POST /v1/auth/login
POST /v1/auth/refresh
POST /v1/auth/logout
GET  /v1/auth/me
```

Signup request:

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

Login returns an access token and a refresh token:

```json
{
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer"
  },
  "error": null
}
```

Use the access token for protected endpoints:

```http
Authorization: Bearer <access_token>
```

### Management API

All Management API endpoints require a valid access token and project
membership where applicable.

```http
POST   /v1/management/projects
GET    /v1/management/projects
GET    /v1/management/projects/{project_id}
PATCH  /v1/management/projects/{project_id}
DELETE /v1/management/projects/{project_id}
```

Project creation request:

```json
{
  "name": "My Application",
  "slug": "my-application"
}
```

The authenticated creator receives an `owner` membership for the new project.

## Response format

Successful response:

```json
{
  "data": {
    "status": "healthy"
  },
  "error": null
}
```

Error response:

```json
{
  "data": null,
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "The requested project does not exist."
  }
}
```

Clients should use the stable `error.code` for programmatic handling.

## Project structure

```text
lumicore/
├── config.py       # environment configuration
├── database.py     # SQLAlchemy engine and sessions
├── main.py         # FastAPI application and routes
├── models.py       # SQLAlchemy models
├── responses.py    # response models and exception handlers
├── schemas.py      # Pydantic request/response schemas
└── security.py     # password hashing and JWT helpers

migrations/         # Alembic migrations
tests/              # pytest test suite
compose.yml         # API and PostgreSQL services
Dockerfile          # API image
```

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
