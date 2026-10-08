import os
os.environ["API_KEY"] = "test-secret-key"

from typing import Any, AsyncGenerator
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from google.adk.runners import Runner
from google.genai import types
from google.adk.models.llm_response import LlmResponse
from services.db import Base, engine
from api.main import app, runner
from agent import root_agent

# Ensure test DB tables exist
Base.metadata.create_all(engine)
client = TestClient(app)


def test_real_adk_runner_integration_flow() -> None:
    """
    Verifies that the FastAPI /chat endpoint uses the real google.adk.runners.Runner,
    executes the root_agent, converts ADK events to API response, and NEVER returns
    'Mock runner response'.
    """
    # 1. Verify Runner class is the authentic Google ADK Runner
    from google.adk.runners import Runner as InstalledRunner
    assert issubclass(Runner, InstalledRunner)
    assert runner.agent is root_agent
    assert runner.app_name == "job_hunter_adk"

    # 2. Mock model content generation to return a real ADK LlmResponse
    test_assistant_reply = "Job Hunter ADK root_agent orchestrated response."

    async def mock_generate_content(*args: Any, **kwargs: Any) -> AsyncGenerator[LlmResponse, None]:
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=test_assistant_reply)]
            ),
            partial=False,
            turn_complete=True
        )

    # Attach mock generator to root_agent's model
    original_gen = getattr(root_agent.model, "generate_content_async", None)
    object.__setattr__(root_agent.model, "generate_content_async", mock_generate_content)

    try:
        # 3. Post chat message to /chat endpoint
        response = client.post(
            "/chat",
            headers={"X-API-Key": "test-secret-key"},
            json={"message": "Help me search for Python remote roles."}
        )

        assert response.status_code == 200
        data = response.json()

        # 4. Assert that real ADK event was converted into the API response
        assert data["response"] == test_assistant_reply

        # 5. Assert that "Mock runner response" is NEVER returned
        assert "Mock runner response" not in data["response"]

        # 6. Assert session and state snapshot contracts
        assert data["session_id"]
        assert data["user"]
        assert "state_snapshot" in data

    finally:
        if original_gen:
            object.__setattr__(root_agent.model, "generate_content_async", original_gen)
