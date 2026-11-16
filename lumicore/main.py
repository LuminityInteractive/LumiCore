from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from lumicore.responces import (
    APIResponce,
    http_exception_handler,
    validation_exception_handler,
)
from lumicore.config import settings
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

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
