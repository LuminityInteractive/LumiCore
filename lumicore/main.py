from weakref import ref

from fastapi import FastAPI, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
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
    RefreshToken,
)
from lumicore.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    SignupRequest,
    UserResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from lumicore.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from uuid import UUID
from datetime import datetime, timedelta, timezone

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

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_ACCESS_TOKEN",
                "message": "The access token is required.",
            },
        )

    token = credentials.credentials

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

async def require_project_membership(
    project_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> ProjectMembership:
    result = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code":"FORBIDDEN",
                "message":"You do not have access to this project.",
            },
        )
    return membership

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        name=project_data.name,
        slug=project_data.slug,
    )
    db.add(project)
    try:
        await db.flush()

        membership = ProjectMembership(
            user_id=current_user.id,
            project_id=project.id,
            role="owner",
        )
        db.add(membership)
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
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
        .join(
            ProjectMembership,
            ProjectMembership.project_id == Project.id,
        ).where(
            ProjectMembership.user_id == current_user.id,
        ).order_by(Project.created_at.desc())
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
    current_user: User = Depends(get_current_user),
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

    membership_result = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == current_user.id,
        )
    )
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": "You do not have access to this project.",
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
    current_user: User = Depends(get_current_user),
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

    await require_project_membership(
        project_id,
        current_user,
        db,
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
    project = None

    if signup_data.project_id is not None:
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

        if project is not None:
            membership = ProjectMembership(
                user_id=user.id,
                project_id=project.id,
                role="member",
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
    access_token=create_access_token(user.id)
    refresh_token=create_refresh_token(user.id)

    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_token_record)
    await db.commit()

    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )

    return APIResponse(
        data=token_response.model_dump(),
    )

@app.post(
    "/v1/auth/refresh",
    response_model=APIResponse,
)
async def refresh_access_token(
    refresh_data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    try:
        payload = decode_refresh_token(
            refresh_data.refresh_token
        )
        user_id = UUID(str(payload["sub"]))
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_REFRESH_TOKEN",
                "message": "The refresh token is invalid or expired.",
            },
        )

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_token(refresh_data.refresh_token)
        )
    )

    stored_token = result.scalar_one_or_none()

    if (
        stored_token is None
        or stored_token.revoked_at is not None
        or stored_token.expires_at <= now
        or stored_token.user_id != user_id
    ):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_REFRESH_TOKEN",
                "message": "The refresh token is invalid or expired.",
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
                "code": "INVALID_REFRESH_TOKEN",
                "message": "The refresh token is invalid or expired.",
            },
        )

    stored_token.revoked_at = now

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=now
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )

    await db.commit()

    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )

    return APIResponse(
        data=token_response.model_dump(),
    )

@app.post(
    "/v1/auth/logout",
    response_model=APIResponse,
)
async def logout(
    refresh_data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    try:
        payload = decode_refresh_token(
            refresh_data.refresh_token
        )
        user_id = UUID(str(payload["sub"]))
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=401,
            detail={
                "code":"INVALID_REFRESH_TOKEN",
                "message":"The refresh token is invalid or expired.",
            },
        )
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(refresh_data.refresh_token)
        )
    )

    stored_token = result.scalar_one_or_none()

    if(stored_token is None or stored_token.user_id != user_id):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_REFRESH_TOKEN",
                "message": "The refresh token is invalid or expired.",
            },
        )
    if stored_token.revoked_at is None:
        stored_token.revoked_at = now
        await db.commit()
    return APIResponse(
        data={"logged_out":True,}
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
