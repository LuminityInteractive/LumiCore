from uuid import uuid4


def signup(client, email: str):
    return client.post(
        "/v1/auth/signup",
        json={
            "email": email,
            "password": "strong-password",
        },
    )


def login(client, email: str):
    response = client.post(
        "/v1/auth/login",
        json={
            "email": email,
            "password": "strong-password",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_signup_and_login(client):
    email = f"user-{uuid4()}@example.com"

    response = signup(client, email)

    assert response.status_code == 201
    assert response.json()["data"]["email"] == email
    assert "password_hash" not in response.json()["data"]

    tokens = login(client, email)

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


def test_duplicate_email_returns_conflict(client):
    email = f"duplicate-{uuid4()}@example.com"

    assert signup(client, email).status_code == 201
    response = signup(client, email)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USER_ALREADY_EXISTS"


def test_invalid_credentials_return_unauthorized(client):
    email = f"invalid-login-{uuid4()}@example.com"
    assert signup(client, email).status_code == 201

    response = client.post(
        "/v1/auth/login",
        json={
            "email": email,
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_returns_current_user(client):
    email = f"me-{uuid4()}@example.com"
    assert signup(client, email).status_code == 201
    tokens = login(client, email)

    response = client.get(
        "/v1/auth/me",
        headers=auth_headers(tokens["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["data"]["email"] == email


def test_refresh_rotation_and_logout(client):
    email = f"refresh-{uuid4()}@example.com"
    assert signup(client, email).status_code == 201
    tokens = login(client, email)

    refreshed = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert refreshed.status_code == 200
    new_tokens = refreshed.json()["data"]
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    old_refresh_reuse = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert old_refresh_reuse.status_code == 401

    logout = client.post(
        "/v1/auth/logout",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert logout.status_code == 200

    revoked_refresh = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert revoked_refresh.status_code == 401


def test_management_api_requires_authentication(client):
    response = client.get("/v1/management/projects")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_ACCESS_TOKEN"


def test_owner_can_create_and_manage_project(client):
    email = f"owner-{uuid4()}@example.com"
    assert signup(client, email).status_code == 201
    tokens = login(client, email)
    headers = auth_headers(tokens["access_token"])

    created = client.post(
        "/v1/management/projects",
        headers=headers,
        json={
            "name": "Test Project",
            "slug": f"test-project-{uuid4().hex[:8]}",
        },
    )

    assert created.status_code == 201
    project_id = created.json()["data"]["id"]

    listed = client.get(
        "/v1/management/projects",
        headers=headers,
    )
    assert listed.status_code == 200
    assert any(item["id"] == project_id for item in listed.json()["data"])

    updated = client.patch(
        f"/v1/management/projects/{project_id}",
        headers=headers,
        json={"name": "Updated Test Project"},
    )
    assert updated.status_code == 200

    deleted = client.delete(
        f"/v1/management/projects/{project_id}",
        headers=headers,
    )
    assert deleted.status_code == 200


def test_non_member_cannot_access_project(client):
    owner_email = f"owner-{uuid4()}@example.com"
    member_email = f"member-{uuid4()}@example.com"

    assert signup(client, owner_email).status_code == 201
    owner_tokens = login(client, owner_email)
    owner_headers = auth_headers(owner_tokens["access_token"])

    created = client.post(
        "/v1/management/projects",
        headers=owner_headers,
        json={
            "name": "Private Project",
            "slug": f"private-project-{uuid4().hex[:8]}",
        },
    )
    assert created.status_code == 201
    project_id = created.json()["data"]["id"]

    assert signup(client, member_email).status_code == 201
    member_tokens = login(client, member_email)

    response = client.get(
        f"/v1/management/projects/{project_id}",
        headers=auth_headers(member_tokens["access_token"]),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
