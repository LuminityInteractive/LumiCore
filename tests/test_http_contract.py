import asyncio
import json

from fastapi.testclient import TestClient

from lumicore.main import app
from lumicore.responses import unexpected_exception_handler


client = TestClient(app)


def test_root_response():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["error"] is None
    assert response.json()["data"]["name"] == "LumiCore"


def test_health_response():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "status": "healthy",
        },
        "error": None,
    }


def test_versioned_health_response():
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "status": "healthy",
        },
        "error": None,
    }


def test_unknown_route_returns_not_found():
    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "data": None,
        "error": {
            "code": "NOT_FOUND",
            "message": "Not Found",
        },
    }


def test_protected_endpoint_requires_access_token():
    response = client.get("/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "data": None,
        "error": {
            "code": "INVALID_ACCESS_TOKEN",
            "message": "The access token is required.",
        },
    }


def test_invalid_signup_data_returns_validation_error():
    response = client.post(
        "/v1/auth/signup",
        json={
            "email": "not-an-email",
            "password": "short",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "data": None,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "The request contains invalid data.",
        },
    }


def test_openapi_contains_core_routes_and_http_bearer():
    schema = app.openapi()

    assert "/" in schema["paths"]
    assert "/health" in schema["paths"]
    assert "/v1/health" in schema["paths"]
    assert "/v1/auth/signup" in schema["paths"]
    assert "/v1/auth/login" in schema["paths"]
    assert "/v1/management/projects" in schema["paths"]
    assert "HTTPBearer" in schema["components"]["securitySchemes"]


def test_unexpected_exception_returns_safe_error_response():
    response = asyncio.run(
        unexpected_exception_handler(
            None,
            RuntimeError("secret implementation detail"),
        )
    )

    assert response.status_code == 500
    assert json.loads(response.body) == {
        "data": None,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
        },
    }
