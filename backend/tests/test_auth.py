from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.services.auth_service import AuthService


def auth_payload() -> dict:
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    return {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
        "expires_in": 900,
        "user": {
            "id": user_id,
            "email": "admin@example.com",
            "is_active": True,
            "role": "ADMIN",
            "tenant_id": tenant_id,
            "created_at": now,
            "updated_at": now,
        },
        "tenant": {
            "id": tenant_id,
            "name": "NeuralShieldDigital",
            "slug": "neuralshielddigital",
            "created_at": now,
            "updated_at": now,
        },
    }


def test_signup_login_and_me(client, monkeypatch):
    monkeypatch.setattr(AuthService, "signup", lambda self, payload: auth_payload())
    monkeypatch.setattr(AuthService, "login", lambda self, payload: auth_payload())

    signup = client.post(
        "/api/auth/signup",
        json={
            "email": "admin@example.com",
            "password": "StrongPassword!123",
            "tenant_name": "NeuralShieldDigital",
        },
    )
    assert signup.status_code == 201
    assert signup.json()["access_token"] == "access-token"

    login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "StrongPassword!123"})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "ADMIN"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "admin@example.com"
