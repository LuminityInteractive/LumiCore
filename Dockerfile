FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project

COPY lumicore ./lumicore
COPY migrations ./migrations
COPY alembic.ini .

CMD ["uv", "run", "--no-sync", "uvicorn", "lumicore.main:app", "--host", "0.0.0.0", "--port", "8000"]
