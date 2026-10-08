from collections.abc import Generator
import os
import pytest
from fastapi.testclient import TestClient

# Must set the environment variable before importing main so deps.py picks it up
os.environ["API_KEY"] = "test-secret-key"

from api.main import app
from services.db import Base, engine

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database() -> Generator[None, None, None]:
    # Setup test DB tables (they should already exist from session_store.py or db.py)
    Base.metadata.create_all(engine)
    yield


def test_health_with_valid_key_returns_ok() -> None:
    response = client.get("/health", headers={"X-API-Key": "test-secret-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "job_hunter_adk"
    assert data["session_backend"] == "database"


def test_health_without_key_returns_401() -> None:
    response = client.get("/health")
    assert response.status_code == 401
    assert "Invalid or missing API Key" in response.json()["detail"] or "Not authenticated" in response.json()["detail"]


def test_chat_without_session_auto_creates_one() -> None:
    # First call: missing session_id and user
    response = client.post("/chat", headers={"X-API-Key": "test-secret-key"}, json={"message": "hi"})
    assert response.status_code == 200
    data1 = response.json()
    assert data1["session_id"]
    assert data1["user"]
    
    # Store the generated session_id
    session_id = data1["session_id"]
    user = data1["user"]
    
    # Second call: use the generated session_id
    response2 = client.post("/chat", headers={"X-API-Key": "test-secret-key"}, json={"session_id": session_id, "user": user, "message": "hello again"})
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["session_id"] == session_id
    assert data2["user"] == user


def test_chat_rejects_missing_api_key() -> None:
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 401


def test_chat_with_user_confirmed_true_sends_application() -> None:
    draft = {
        "to": "hiring@techcorp.com",
        "subject": "Application for Software Engineer",
        "body": "Dear Hiring Manager, please find my application attached.",
        "status": "pending_user_approval"
    }
    response = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "message": "Send the email now.",
            "state_updates": {"email_draft": draft},
            "user_confirmed": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "sent successfully" in data["response"].lower()
    snapshot = data["state_snapshot"]
    assert snapshot["user_confirmed"] is True
    assert snapshot["email_draft"]["status"] == "sent"
    assert snapshot["application_status"] == "sent"


def test_chat_with_user_confirmed_false_refuses_application() -> None:
    draft = {
        "to": "hiring@techcorp.com",
        "subject": "Application for Software Engineer",
        "body": "Dear Hiring Manager, please find my application attached.",
        "status": "pending_user_approval"
    }
    response = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "message": "Send the email now.",
            "state_updates": {"email_draft": draft},
            "user_confirmed": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "refused" in data["response"].lower()
    snapshot = data["state_snapshot"]
    assert snapshot["user_confirmed"] is False
    assert snapshot["email_draft"]["status"] != "sent"
    assert snapshot["application_status"] == "refused_unconfirmed"


def test_chat_with_missing_user_confirmed_safely_defaults_to_unconfirmed() -> None:
    draft = {
        "to": "hiring@techcorp.com",
        "subject": "Application for Software Engineer",
        "body": "Dear Hiring Manager, please find my application attached.",
        "status": "pending_user_approval"
    }
    # Notice: user_confirmed field is completely omitted from JSON request
    response = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "message": "Send the email now.",
            "state_updates": {"email_draft": draft}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "refused" in data["response"].lower()
    snapshot = data["state_snapshot"]
    assert snapshot["user_confirmed"] is False
    assert snapshot["email_draft"]["status"] != "sent"
    assert snapshot["application_status"] == "refused_unconfirmed"


def test_unconfirmed_application_refusal_never_sends_email() -> None:
    draft = {
        "to": "recruiter@bigco.com",
        "subject": "Application for Lead Developer",
        "body": "Cover letter text",
        "status": "pending_user_approval"
    }
    response = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "message": "Send application immediately without waiting",
            "state_updates": {"email_draft": draft},
            "user_confirmed": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "refused" in data["response"].lower()
    assert data["state_snapshot"]["email_draft"]["status"] == "pending_user_approval"
