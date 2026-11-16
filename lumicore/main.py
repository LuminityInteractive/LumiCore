from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from lumicore.responces import (
    APIResponce,
    http_exception_handler,
    validation_exception_handler,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(
    title="LumiCore",
    description="Open-source backend infrastructure for modern applications.",
    version="0.0.1",
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

@app.get("/health")
async def health():
    return APIResponce(
        data={
            "status": "healthy",
        }
    )
