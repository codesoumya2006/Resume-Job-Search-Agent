import os
import pytest
from fastapi.testclient import TestClient

# Must set the environment variable before importing main so deps.py picks it up
os.environ["API_KEY"] = "test-secret-key"

from api.main import app
from services.db import Base, engine

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    # Setup test DB tables (they should already exist from session_store.py or db.py)
    Base.metadata.create_all(engine)
    yield
    # We could drop tables here if we were using an in-memory db specifically for testing
    
def test_health_with_valid_key_returns_ok():
    response = client.get("/health", headers={"X-API-Key": "test-secret-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "job_hunter_adk"
    assert data["session_backend"] == "database"

def test_health_without_key_returns_401():
    response = client.get("/health")
    assert response.status_code == 401
    assert "Invalid or missing API Key" in response.json()["detail"] or "Not authenticated" in response.json()["detail"]

def test_chat_without_session_auto_creates_one():
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

def test_chat_rejects_missing_api_key():
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 401
