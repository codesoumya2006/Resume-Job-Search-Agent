import os
import pytest
from fastapi.testclient import TestClient

os.environ["API_KEY"] = "test-secret-key"

from api.main import app, session_service, adk_session_service
from services.db import Base, engine

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db() -> None:
    Base.metadata.create_all(engine)


def test_multi_turn_state_persists_without_client_resending() -> None:
    """
    Verifies that state persists across multiple distinct /chat requests
    without requiring the client to resend earlier state items.
    """
    # Initialize session
    init_res = client.post("/session", headers={"X-API-Key": "test-secret-key"}, json={})
    assert init_res.status_code == 200
    session_id = init_res.json()["session_id"]
    user_id = init_res.json()["user_id"]

    # Turn 1: Save resume_profile
    resume_data = {
        "skills": ["Python", "FastAPI", "SQLAlchemy"],
        "experience": [{"title": "Backend Dev", "company": "Acme Corp", "duration": "2y", "description": "APIs"}],
        "internships": [],
        "certifications": ["AWS Solutions Architect"],
        "education": [],
        "projects": []
    }
    t1_res = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": session_id,
            "user": user_id,
            "message": "Here is my parsed resume.",
            "state_updates": {"resume_profile": resume_data}
        }
    )
    assert t1_res.status_code == 200
    snap1 = t1_res.json()["state_snapshot"]
    assert snap1["resume_profile"] == resume_data

    # Turn 2: Save preferences (client does NOT resend resume_profile)
    prefs_data = {
        "job_type": "permanent",
        "work_mode": "remote",
        "locations": ["Bangalore", "Remote"],
        "paid_only": True
    }
    t2_res = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": session_id,
            "user": user_id,
            "message": "Set my job preferences.",
            "state_updates": {"preferences": prefs_data}
        }
    )
    assert t2_res.status_code == 200
    snap2 = t2_res.json()["state_snapshot"]
    # resume_profile must still exist from Turn 1
    assert snap2["resume_profile"] == resume_data

    # Turn 3: Add ranked_jobs and selected_job (client sends NO state_updates for resume or preferences)
    sample_jobs = [
        {"id": "job-101", "title": "Senior Python Engineer", "company": "TechNova", "url": "https://technova.io/jobs/1"}
    ]
    t3_res = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": session_id,
            "user": user_id,
            "message": "I want to apply for the Senior Python Engineer role.",
            "state_updates": {
                "ranked_jobs": sample_jobs,
                "selected_job": sample_jobs[0]
            }
        }
    )
    assert t3_res.status_code == 200
    snap3 = t3_res.json()["state_snapshot"]
    assert snap3["resume_profile"] == resume_data
    assert snap3["ranked_jobs"] == sample_jobs
    assert snap3["selected_job"]["title"] == "Senior Python Engineer"

    # Turn 4: Ordinary conversational message with NO state_updates at all
    t4_res = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": session_id,
            "user": user_id,
            "message": "What is the status of my selected job?"
        }
    )
    assert t4_res.status_code == 200
    snap4 = t4_res.json()["state_snapshot"]
    # All prior state items must survive
    assert snap4["resume_profile"] == resume_data
    assert snap4["ranked_jobs"] == sample_jobs
    assert snap4["selected_job"]["id"] == "job-101"


def test_hitl_security_boundary_in_multi_turn_flow() -> None:
    """Verifies that unconfirmed applications are blocked and explicit confirmation allows sending."""
    init_res = client.post("/session", headers={"X-API-Key": "test-secret-key"}, json={})
    session_id = init_res.json()["session_id"]
    user_id = init_res.json()["user_id"]

    draft = {
        "to": "jobs@acmecorp.com",
        "subject": "Application for Senior Engineer",
        "body": "I am applying for the role.",
        "status": "pending_user_approval"
    }

    # Step 1: Attempt to send with user_confirmed=False
    refused_res = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": session_id,
            "user": user_id,
            "message": "Please send the application now.",
            "state_updates": {"email_draft": draft},
            "user_confirmed": False
        }
    )
    assert refused_res.status_code == 200
    snap_refused = refused_res.json()["state_snapshot"]
    assert snap_refused["application_status"] == "refused_unconfirmed"
    assert snap_refused["email_draft"]["status"] == "pending_user_approval"

    # Step 2: Attempt to send with user_confirmed omitted (None)
    omitted_res = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": session_id,
            "user": user_id,
            "message": "Send it anyway!"
        }
    )
    assert omitted_res.status_code == 200
    snap_omitted = omitted_res.json()["state_snapshot"]
    assert snap_omitted["application_status"] == "refused_unconfirmed"
    assert snap_omitted["email_draft"]["status"] != "sent"

    # Step 3: Explicitly confirmed with user_confirmed=True
    confirmed_res = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": session_id,
            "user": user_id,
            "message": "Yes, I approve and confirm sending this email.",
            "user_confirmed": True
        }
    )
    assert confirmed_res.status_code == 200
    snap_confirmed = confirmed_res.json()["state_snapshot"]
    assert snap_confirmed["application_status"] == "sent"
    assert snap_confirmed["email_draft"]["status"] == "sent"


def test_restart_boundary_rehydrates_adk_from_authoritative_db() -> None:
    """
    Verifies that when in-memory ADK session is lost (simulating process restart),
    the session bridge rehydrates state from the authoritative database session store.
    """
    init_res = client.post("/session", headers={"X-API-Key": "test-secret-key"}, json={})
    session_id = init_res.json()["session_id"]
    user_id = init_res.json()["user_id"]

    # Pre-restart request
    client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": session_id,
            "user": user_id,
            "message": "Storing initial profile",
            "state_updates": {
                "resume_profile": {"skills": ["Rust", "Python"]},
                "company_intel": {"TechCorp": [{"source": "Glassdoor", "summary": "Great culture", "sentiment": "positive"}]}
            }
        }
    )

    # Verify state is written to SQLite / DB
    db_state = session_service.get_state(session_id)
    assert db_state["resume_profile"]["skills"] == ["Rust", "Python"]
    assert "TechCorp" in db_state["company_intel"]

    # SIMULATE RESTART: Wipe ADK in-memory session cache completely
    adk_session_service.sessions.clear()
    assert len(adk_session_service.sessions) == 0

    # Post-restart request: Client sends only a message
    post_restart_res = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": session_id,
            "user": user_id,
            "message": "Continuing conversation after restart"
        }
    )
    assert post_restart_res.status_code == 200
    post_snap = post_restart_res.json()["state_snapshot"]

    # State must have been restored from DB without divergence
    assert post_snap["resume_profile"]["skills"] == ["Rust", "Python"]
    assert "TechCorp" in post_snap["company_intel"]

    # ADK session service must now have the rehydrated session
    import asyncio
    rehydrated_sess = asyncio.run(adk_session_service.get_session(app_name="job_hunter_adk", user_id=user_id, session_id=session_id))
    assert rehydrated_sess is not None
    assert rehydrated_sess.state["resume_profile"]["skills"] == ["Rust", "Python"]
