from fastapi import FastAPI, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from lumicore.responces import (
    APIResponce,
    http_exception_handler,
    validation_exception_handler,
)
from lumicore.config import settings
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from lumicore.database import get_db
from lumicore.models import Project
from lumicore.schemas import ProjectCreate, ProjectResponse

logging.basicConfig(
    level=getattr(
        logging,
        settings.log_level.upper(),
        logging.INFO,
    ),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("lumicore")

app = FastAPI(
    title="LumiCore",
    description="Open-source backend infrastructure for modern applications.",
    version="0.0.1",
    debug=settings.debug,
)

logger.info(
    "LumiCore started in %s environment",
    settings.app_env,
)

app.add_exception_handler(
    StarletteHTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

@app.get("/", response_model=APIResponce)
async def root():
    return APIResponce(
        data={
            "name": "LumiCore",
            "version": "0.0.1",
            "status": "running",
        }
    )

@app.get("/health", response_model=APIResponce)
async def health():
    return APIResponce(
        data={
            "status": "healthy",
        }
    )

@app.get("/v1/health", response_model=APIResponce)
async def versioned_health():
    return APIResponce(
        data={
            "status": "healthy",
        }
    )

@app.post(
    "/v1/management/projects",
    response_model=APIResponce,
    status_code=201,
)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    project = Project(
        name=project_data.name,
        slug=project_data.slug,
    )
    db.add(project)
    try:
        await db.commit()
        await db.refresh(project)
    except IntegrityError:
        await db.rollback()

        raise HTTPException(
            status_code=409,
            detail={
                "code": "PROJECT_ALREADY_EXISTS",
                "message": "A project with this slug already exists.",
            },
        )
    project_response = ProjectResponse.model_validate(project)

    return APIResponce(
        data=project_response.model_dump(mode="json"),
    )

if __name__ == "__main__":
    import uvicorn

    if settings.debug:
        uvicorn.run(
            "lumicore.main:app",
            host=settings.host,
            port=settings.port,
            reload=True,
        )
    else:
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            reload=False,
        )
