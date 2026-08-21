from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.api.deps import get_current_user
from app.main import app
from app.models.enums import UserRole
from app.services.email_service import EmailService
from app.services.lead_service import LeadService
from app.services.public_lead_service import PublicLeadService
from app.services.workflow_service import WorkflowService
from conftest import make_user


def lead_payload(user_id: str | None = None) -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "user_id": user_id or str(uuid4()),
        "name": "Rahul",
        "email": "rahul@example.com",
        "phone": "9999999999",
        "source": "website",
        "stage": "NEW",
        "notes": None,
        "last_contacted_at": None,
        "tags": ["public-form"],
        "metadata_": {"message": "I need automation"},
        "created_at": now,
        "updated_at": now,
    }


def test_leads_crud(client, monkeypatch, fake_user):
    lead = lead_payload(str(fake_user.id))
    monkeypatch.setattr(LeadService, "create_lead", lambda self, user, payload: lead)
    monkeypatch.setattr(LeadService, "list_leads", lambda self, user, page, page_size, search=None: {"items": [lead], "pagination": {"page": 1, "page_size": 25, "total": 1, "total_pages": 1}})
    monkeypatch.setattr(LeadService, "get_lead", lambda self, user, lead_id: lead)
    monkeypatch.setattr(LeadService, "update_lead", lambda self, user, lead_id, payload: {**lead, "name": "Updated"})
    monkeypatch.setattr(LeadService, "delete_lead", lambda self, user, lead_id: None)

    assert client.post("/api/leads", json={"email": "rahul@example.com", "name": "Rahul", "tags": []}).status_code == 201
    assert client.get("/api/leads").json()["items"][0]["email"] == "rahul@example.com"
    assert client.get(f"/api/leads/{lead['id']}").status_code == 200
    assert client.put(f"/api/leads/{lead['id']}", json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.delete(f"/api/leads/{lead['id']}").status_code == 204


def test_public_lead_form(client, monkeypatch):
    monkeypatch.setattr(
        PublicLeadService,
        "create_public_lead",
        lambda self, payload: {"success": True, "message": "Thanks. We received your request."},
    )

    response = client.post(
        "/api/public/leads",
        json={
            "tenant_slug": "neuralshielddigital",
            "name": "Rahul",
            "email": "rahul@example.com",
            "phone": "9999999999",
            "source": "website",
            "message": "I need automation",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_workflow_webhook_trigger(client, monkeypatch):
    run_id = uuid4()
    monkeypatch.setattr(
        WorkflowService,
        "execute_public_webhook",
        lambda self, key, payload: {
            "message": "Workflow executed successfully",
            "workflow_run_id": run_id,
        },
    )

    response = client.post("/api/webhooks/workflow/public-key", json={"email": "lead@example.com"})

    assert response.status_code == 200
    assert response.json() == {
        "message": "Workflow executed successfully",
        "workflow_run_id": str(run_id),
    }


def test_send_email_workflow_action_with_mocked_smtp():
    service = EmailService()
    sent = {}

    service._validate_config = lambda: None

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["host"] = host

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            sent["tls"] = True

        def login(self, username, password):
            sent["username"] = username

        def send_message(self, message):
            sent["to"] = message["To"]

    service.settings.SMTP_HOST = "smtp.example.com"
    service.settings.SMTP_PORT = 587
    service.settings.SMTP_FROM_EMAIL = "noreply@example.com"
    service.settings.SMTP_FROM_NAME = "NeuralShieldDigital"
    service.settings.SMTP_USE_TLS = True
    service.settings.SMTP_USERNAME = ""

    import smtplib

    original_smtp = smtplib.SMTP
    smtplib.SMTP = FakeSMTP
    try:
        result = service.send_email("lead@example.com", "Hello", "Body")
    finally:
        smtplib.SMTP = original_smtp

    assert result["status"] == "sent"
    assert sent["to"] == "lead@example.com"


def test_admin_api_role_protection(client):
    app.dependency_overrides[get_current_user] = lambda: make_user(UserRole.USER)
    forbidden = client.get("/api/admin/stats")
    assert forbidden.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: make_user(UserRole.ADMIN)
