import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from lumicore.database import engine
from lumicore.main import app
from lumicore.models import Project, ProjectMembership, RefreshToken, User


async def clear_database() -> None:
    await engine.dispose()

    async with engine.begin() as connection:
        await connection.execute(delete(RefreshToken))
        await connection.execute(delete(ProjectMembership))
        await connection.execute(delete(User))
        await connection.execute(delete(Project))

    await engine.dispose()


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    asyncio.run(clear_database())
    yield
    asyncio.run(clear_database())


@pytest.fixture
def client(clean_database: None) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
