import os
os.environ["API_KEY"] = "test-secret-key"

import json
from typing import Any, AsyncGenerator
from unittest.mock import patch
import pytest
import numpy as np
from fastapi.testclient import TestClient
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from google.adk.models.llm_response import LlmResponse

from agent import root_agent
from sub_agents.resume_agent.agent import resume_agent
from sub_agents.job_discovery_agent.agent import job_discovery_agent
from sub_agents.interview_agent.tools import _generate_questions_impl
from sub_agents.application_agent.tools import _draft_email_impl, _send_email_impl
from google.adk.tools import ToolContext
from google.adk.events import EventActions
from schemas.job_listing import JobListing
from schemas.preferences import WorkMode, JobType
from api.main import app, session_service
from services.db import Base, engine

Base.metadata.create_all(engine)
client = TestClient(app)


@pytest.mark.asyncio
async def test_resume_agent_state_propagation() -> None:
    """
    Test 1 — Resume Profile:
    resume_agent -> state["resume_profile"]
    Verifies that the real ADK Runner executes resume_agent and produces session.state["resume_profile"].
    """
    sess_svc = InMemorySessionService()
    test_runner = Runner(agent=resume_agent, session_service=sess_svc, app_name="job_hunter_adk")

    initial_resume_text = "Software Engineer with Python, FastAPI, and PostgreSQL skills."
    await sess_svc.create_session(
        app_name="job_hunter_adk",
        user_id="test_user",
        session_id="test_resume_sess",
        state={"resume_raw": initial_resume_text}
    )

    parsed_profile_json = json.dumps({
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience": [{"title": "Software Engineer", "company": "Tech Corp", "duration": "2 yrs", "description": "Backend dev"}],
        "internships": [],
        "certifications": [],
        "education": [],
        "projects": []
    })

    async def mock_generate_content(*args: Any, **kwargs: Any) -> AsyncGenerator[LlmResponse, None]:
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=parsed_profile_json)]
            ),
            partial=False,
            turn_complete=True
        )

    original_gen = getattr(resume_agent.model, "generate_content_async", None)
    object.__setattr__(resume_agent.model, "generate_content_async", mock_generate_content)

    try:
        msg = types.Content(role="user", parts=[types.Part.from_text(text="Extract candidate profile from resume.")])
        async for _ in test_runner.run_async(user_id="test_user", session_id="test_resume_sess", new_message=msg):
            pass

        final_sess = await sess_svc.get_session(app_name="job_hunter_adk", user_id="test_user", session_id="test_resume_sess")
        assert final_sess is not None
        assert "resume_profile" in final_sess.state
        profile_state = final_sess.state["resume_profile"]
        assert "Python" in str(profile_state)
    finally:
        if original_gen:
            object.__setattr__(resume_agent.model, "generate_content_async", original_gen)


@pytest.mark.asyncio
async def test_job_discovery_agent_state_propagation() -> None:
    """
    Test 2 — Discovered Jobs:
    job_discovery_agent -> state["discovered_jobs"]
    Verifies that the real ADK Runner executes job_discovery_agent and produces session.state["discovered_jobs"].
    """
    sess_svc = InMemorySessionService()
    test_runner = Runner(agent=job_discovery_agent, session_service=sess_svc, app_name="job_hunter_adk")

    await sess_svc.create_session(
        app_name="job_hunter_adk",
        user_id="test_user",
        session_id="test_discovery_sess",
        state={"preferences": {"job_type": "permanent", "work_mode": "remote", "locations": ["Bangalore"]}}
    )

    discovered_json = json.dumps([
        {
            "title": "Backend Engineer",
            "company": "FastAPI Labs",
            "source": "web",
            "url": "https://example.com/jobs/1",
            "location": "Bangalore",
            "work_mode": "remote",
            "job_type": "permanent",
            "stipend_or_salary": "$120k",
            "description": "FastAPI services engineer",
            "posted_date": None,
            "raw_text_hash": "hash_back_1"
        }
    ])

    async def mock_generate_content(*args: Any, **kwargs: Any) -> AsyncGenerator[LlmResponse, None]:
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=discovered_json)]
            ),
            partial=False,
            turn_complete=True
        )

    original_gen = getattr(job_discovery_agent.model, "generate_content_async", None)
    object.__setattr__(job_discovery_agent.model, "generate_content_async", mock_generate_content)

    try:
        msg = types.Content(role="user", parts=[types.Part.from_text(text="Find jobs matching preferences.")])
        async for _ in test_runner.run_async(user_id="test_user", session_id="test_discovery_sess", new_message=msg):
            pass

        final_sess = await sess_svc.get_session(app_name="job_hunter_adk", user_id="test_user", session_id="test_discovery_sess")
        assert final_sess is not None
        assert "discovered_jobs" in final_sess.state
        assert "FastAPI Labs" in str(final_sess.state["discovered_jobs"])
    finally:
        if original_gen:
            object.__setattr__(job_discovery_agent.model, "generate_content_async", original_gen)


@pytest.mark.asyncio
async def test_ranked_jobs_state_propagation() -> None:
    """
    Test 3 — Ranked Jobs:
    rank_jobs -> state["ranked_jobs"]
    Verifies that the real ADK Runner executes the rank_jobs tool call and persists state["ranked_jobs"].
    """
    sess_svc = InMemorySessionService()
    test_runner = Runner(agent=root_agent, session_service=sess_svc, app_name="job_hunter_adk")

    sample_resume = {
        "skills": ["Python", "FastAPI"],
        "experience": [{"title": "Software Engineer", "company": "Tech Corp", "duration": "2 yrs", "description": "Python web APIs"}],
        "internships": [],
        "certifications": [],
        "education": [],
        "projects": []
    }
    sample_jobs = [
        {
            "title": "Python Backend Engineer",
            "company": "Cloud Corp",
            "source": "web",
            "url": "https://example.com/job/101",
            "location": "Bangalore",
            "work_mode": "remote",
            "job_type": "permanent",
            "stipend_or_salary": "$110k",
            "description": "Python web APIs building",
            "posted_date": None,
            "raw_text_hash": "hash_101"
        }
    ]
    sample_prefs = {
        "job_type": "permanent",
        "work_mode": "remote",
        "locations": ["Bangalore"],
        "paid_only": True
    }

    await sess_svc.create_session(
        app_name="job_hunter_adk",
        user_id="test_user",
        session_id="test_rank_sess",
        state={
            "resume_profile": sample_resume,
            "discovered_jobs": sample_jobs,
            "preferences": sample_prefs
        }
    )

    turn = 0
    async def mock_generate_content(*args: Any, **kwargs: Any) -> AsyncGenerator[LlmResponse, None]:
        nonlocal turn
        turn += 1
        if turn == 1:
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part.from_function_call(
                            name="rank_jobs",
                            args={}
                        )
                    ]
                )
            )
        else:
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="I ranked the jobs successfully.")]
                ),
                turn_complete=True
            )

    original_gen = getattr(root_agent.model, "generate_content_async", None)
    object.__setattr__(root_agent.model, "generate_content_async", mock_generate_content)

    try:
        with patch("tools.match_rank_tool.get_embeddings", return_value=np.ones((2, 384))):
            msg = types.Content(role="user", parts=[types.Part.from_text(text="Rank these jobs for me.")])
            async for _ in test_runner.run_async(user_id="test_user", session_id="test_rank_sess", new_message=msg):
                pass

        final_sess = await sess_svc.get_session(app_name="job_hunter_adk", user_id="test_user", session_id="test_rank_sess")
        assert final_sess is not None
        assert "ranked_jobs" in final_sess.state
        ranked_jobs = final_sess.state["ranked_jobs"]
        assert isinstance(ranked_jobs, list)
        assert len(ranked_jobs) == 1
        assert "job" in ranked_jobs[0]
        assert "score" in ranked_jobs[0]
        assert ranked_jobs[0]["job"]["title"] == "Python Backend Engineer"
        assert isinstance(ranked_jobs[0]["score"], float)
    finally:
        if original_gen:
            object.__setattr__(root_agent.model, "generate_content_async", original_gen)


def test_downstream_state_consumption() -> None:
    """
    Test 4 — Downstream State:
    Verify that downstream agents/tools consume upstream state (selected_job, resume_profile)
    and produce state["interview_prep"] and state["email_draft"].
    """
    from unittest.mock import MagicMock

    selected_job = {
        "title": "Senior Python Developer",
        "company": "Acme Innovations",
        "location": "Bangalore",
        "work_mode": "remote",
        "job_type": "permanent",
        "source": "web",
        "url": "https://acme.com/jobs/1",
        "description": "Senior Python and distributed systems developer",
        "stipend_or_salary": "$150k",
        "posted_date": None,
        "raw_text_hash": "hash_acme_1"
    }
    resume_profile = {
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience": [{"title": "Python Dev", "company": "Prev Co", "duration": "3 yrs", "description": "Backend API engineer"}],
        "internships": [],
        "certifications": [],
        "education": [],
        "projects": []
    }

    inv_ctx = MagicMock()
    session = MagicMock()
    session.state = {
        "selected_job": selected_job,
        "resume_profile": resume_profile
    }
    inv_ctx.session = session
    actions = EventActions()
    tool_ctx = ToolContext(invocation_context=inv_ctx, event_actions=actions)

    # 1. Interview tool consumes state
    questions = _generate_questions_impl(tool_context=tool_ctx)
    assert isinstance(questions, list)
    assert len(questions) > 0
    assert "interview_prep" in tool_ctx.state

    # 2. Application tool consumes state
    draft = _draft_email_impl(
        cover_letter="Cover letter text for Acme Innovations",
        tool_context=tool_ctx
    )
    assert isinstance(draft, dict)
    assert draft["to"] == "hr@company.com"
    assert "Acme Innovations" in draft["subject"]
    assert "email_draft" in tool_ctx.state
    assert tool_ctx.state["email_draft"]["status"] == "pending_user_approval"


def test_multi_turn_state_continuity_and_hitl() -> None:
    """
    Test 5 — Multi-turn State & HITL:
    Turn 1: User sends resume_raw and preferences.
    Turn 2: User sends selected_job.
    Turn 3: Preparation state snapshot.
    Turn 4: HITL security verification:
            - Missing/False confirmation REFUSES send.
            - Explicit user_confirmed=True PERMITS send.
    """
    # Turn 1: Initialization
    resp1 = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "message": "Start job hunt",
            "state_updates": {
                "resume_raw": "Python, FastAPI developer with 3 yrs experience.",
                "preferences": {"job_type": "permanent", "work_mode": "remote", "locations": ["Bangalore"]}
            }
        }
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    sess_id = data1["session_id"]
    assert sess_id

    # Turn 2: Select Job
    selected_job = {
        "title": "Python Backend Engineer",
        "company": "NexTech Inc",
        "location": "Bangalore",
        "work_mode": "remote",
        "job_type": "permanent",
        "source": "web",
        "url": "https://nextech.com/career",
        "description": "Backend API engineer",
        "stipend_or_salary": "$130k",
        "posted_date": None,
        "raw_text_hash": "hash_nextech_1"
    }
    resp2 = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": sess_id,
            "message": "I picked NexTech role",
            "state_updates": {"selected_job": selected_job}
        }
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["state_snapshot"]["selected_job"]["company"] == "NexTech Inc"

    # Turn 3: Prepare Draft
    email_draft = {
        "to": "recruiter@nextech.com",
        "subject": "Application for Python Backend Engineer at NexTech Inc",
        "body": "Dear Hiring Manager,\nI am interested in this role.",
        "status": "pending_user_approval"
    }
    resp3 = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": sess_id,
            "message": "Draft my application email",
            "state_updates": {"email_draft": email_draft}
        }
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["state_snapshot"]["email_draft"]["status"] == "pending_user_approval"

    # Turn 4a: Refusal without user confirmation
    resp4a = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": sess_id,
            "message": "Send the application now",
            "user_confirmed": False
        }
    )
    assert resp4a.status_code == 200
    data4a = resp4a.json()
    assert data4a["state_snapshot"]["application_status"] == "refused_unconfirmed"
    assert data4a["state_snapshot"]["email_draft"]["status"] == "pending_user_approval"

    # Turn 4b: Sending with explicit confirmation
    resp4b = client.post(
        "/chat",
        headers={"X-API-Key": "test-secret-key"},
        json={
            "session_id": sess_id,
            "message": "I approve, please send the application",
            "user_confirmed": True
        }
    )
    assert resp4b.status_code == 200
    data4b = resp4b.json()
    assert data4b["state_snapshot"]["application_status"] == "sent"
    assert data4b["state_snapshot"]["email_draft"]["status"] == "sent"
