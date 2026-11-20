# LumiCore

[![Python](https://img.shields.io/badge/python-3.14%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.163%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Open-source backend infrastructure for modern applications.

## Status

Early development. The current implementation includes:

- FastAPI HTTP API;
- PostgreSQL with SQLAlchemy and Alembic;
- project CRUD and membership checks;
- password hashing and JWT authentication;
- protected Management API;
- Docker Compose runtime;
- automated HTTP and authentication tests.

## Requirements

- Python 3.14+;
- `uv`;
- Docker Engine;
- Docker Compose.

PostgreSQL does not need to be installed on the host. Docker Compose pulls the
`postgres:16-alpine` image and runs PostgreSQL in a container.

## Quick start

Clone the repository and enter its directory:

```bash
git clone https://github.com/LuminityInteractive/LumiCore.git
cd LumiCore
```

### 1. Configure the environment

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```env
POSTGRES_PASSWORD=<local-password>
JWT_SECRET=<random-secret>
```

The password in `DATABASE_URL` must match `POSTGRES_PASSWORD` for local API
execution. When the API runs in Docker Compose, Compose provides an internal
database URL using the `database` service hostname.

### 2. Start the stack

```bash
docker compose up -d --build
```

This starts:

```text
lumicore-api        FastAPI + Uvicorn
lumicore-database   PostgreSQL 16
```

### 3. Apply database migrations

On a new database, apply the schema before using database-backed endpoints:

```bash
docker compose exec api uv run --no-sync alembic upgrade head
```

### 4. Verify the runtime

```bash
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/health/database
```

Both Compose services should be running and healthy. API documentation is
available at:

```text
http://localhost:8000/docs
```

Stop the stack:

```bash
docker compose down
```

`docker compose down -v` also deletes the PostgreSQL data volume.

## Local development

Run PostgreSQL in Docker and the API locally with auto-reload:

```bash
docker compose up -d database
uv run --env-file .env uvicorn lumicore.main:app --reload
```

For local API execution, `DATABASE_URL` must use `localhost`. For the Docker
API service, the database hostname is `database` and is configured by
`compose.yml`.

## Tests

Tests use a separate PostgreSQL database named `lumicore_test`.

Create it once:

```bash
docker compose exec database psql \
  -U lumicore \
  -d postgres \
  -c "CREATE DATABASE lumicore_test OWNER lumicore;"
```

Apply migrations:

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

Test fixtures clear the test tables between tests. The development database is
not used by the test suite.

## Database migrations

Check the current revision:

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

Review generated migrations before applying them:

```bash
uv run --env-file .env alembic upgrade head
```

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

### Management API

All Management API endpoints require a Bearer access token and project
membership where applicable.

```http
POST   /v1/management/projects
GET    /v1/management/projects
GET    /v1/management/projects/{project_id}
PATCH  /v1/management/projects/{project_id}
DELETE /v1/management/projects/{project_id}
```

## Response format

Success:

```json
{
  "data": {},
  "error": null
}
```

Error:

```json
{
  "data": null,
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "The requested project does not exist."
  }
}
```

Clients should use the stable `error.code` for programmatic error handling.

## Project structure

```text
lumicore/
├── config.py       # environment configuration
├── database.py     # SQLAlchemy engine and sessions
├── main.py         # FastAPI application and routes
├── models.py       # SQLAlchemy models
├── responses.py    # response models and exception handlers
├── schemas.py      # Pydantic schemas
└── security.py     # password hashing and JWT helpers

migrations/         # Alembic migrations
tests/              # pytest test suite
compose.yml         # API and PostgreSQL services
Dockerfile          # API image
```

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
