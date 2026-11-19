from fastapi import FastAPI, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordBearer
from lumicore.responses import (
    APIResponse,
    http_exception_handler,
    validation_exception_handler,
)
from lumicore.config import settings
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from lumicore.database import get_db
from lumicore.models import (
    Project,
    ProjectMembership,
    User,
)
from lumicore.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    SignupRequest,
    UserResponse,
    LoginRequest,
    TokenResponse,
)
from lumicore.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from uuid import UUID

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

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/auth/login",
)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload["sub"]))
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=401,
            detail={
                "code":"INVALID_ACCESS_TOKEN",
                "message": "The access token is invalid or expired.",
            },
        )
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail={
                "code":"INVALID_ACCESS_TOKEN",
                "message": "The access token is invalid or expired.",
            },
        )
    return user

@app.get("/", response_model=APIResponse)
async def root():
    return APIResponse(
        data={
            "name": "LumiCore",
            "version": "0.0.1",
            "status": "running",
        }
    )

@app.get("/health", response_model=APIResponse)
async def health():
    return APIResponse(
        data={
            "status": "healthy",
        }
    )

@app.get("/v1/health", response_model=APIResponse)
async def versioned_health():
    return APIResponse(
        data={
            "status": "healthy",
        }
    )

@app.post(
    "/v1/management/projects",
    response_model=APIResponse,
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

    return APIResponse(
        data=project_response.model_dump(mode="json"),
    )

@app.get(
    "/v1/management/projects",
    response_model=APIResponse,
)
async def list_projects(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    project_responses = [
        ProjectResponse.model_validate(project).model_dump(mode="json")
        for project in projects
    ]
    return APIResponse(data=project_responses)

@app.get(
    "/v1/management/projects/{project_id}",
    response_model=APIResponse,
)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )

    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "The requested project does not exist.",
            },
        )
    project_response = ProjectResponse.model_validate(project)
    return APIResponse(
        data=project_response.model_dump(mode="json"),
    )

@app.patch(
    "/v1/management/projects/{project_id}",
    response_model=APIResponse,
)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code":"PROJECT_NOT_FOUND",
                "message": "The requested project does not exist.",
            },
        )

    updates = {
        field: value
        for field, value in project_data.model_dump(exclude_unset=True).items()
        if value is not None
    }

    for field, value in updates.items():
        setattr(project, field, value)
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
    return APIResponse(
        data=project_response.model_dump(mode="json"),
    )

@app.delete(
    "/v1/management/projects/{project_id}",
    response_model=APIResponse,
)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "The requested project does not exist.",
            },
        )
    await db.delete(project)
    await db.commit()

    return APIResponse(
        data={
            "id": str(project_id),
            "deleted": True,
        }
    )

@app.post(
    "/v1/auth/signup",
    response_model=APIResponse,
    status_code=201,
)
async def signup(
    signup_data: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(
            Project.id == signup_data.project_id
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "The requested project does not exist.",
            },
        )
    user = User(
        email=str(signup_data.email).lower(),
        password_hash=hash_password(signup_data.password),
    )

    db.add(user)

    try:
        await db.flush()
        membership = ProjectMembership(
            user_id=user.id,
            project_id=project.id,
        )

        db.add(membership)
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "code":"USER_ALREADY_EXISTS",
                "message":"A user with this email already exists",
            },
        )
    user_response = UserResponse.model_validate(user)

    return APIResponse(
        data=user_response.model_dump(mode="json"),
    )

@app.post(
    "/v1/auth/login",
    response_model=APIResponse,
)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.email == str(login_data.email).lower()
        )
    )

    user = result.scalar_one_or_none()

    if user is None or not verify_password(
        login_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail={
                "code":"INVALID_CREDENTIALS",
                "message":"Invalid email or password.",
            },
        )
    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail={
                "code":"INVALID_CREDENTIALS",
                "message":"Invalid email or password.",
            },
        )
    token_response = TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
    return APIResponse(
        data=token_response.model_dump(),
    )

@app.get(
    "/v1/auth/me",
    response_model=APIResponse,
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    user_response = UserResponse.model_validate(current_user)
    return APIResponse(
        data=user_response.model_dump(mode="json"),
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
