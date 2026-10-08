"""
EVAL-08 — Multi-Turn State
Validates that session state persists across multiple requests without client resending.
"""
from fastapi.testclient import TestClient
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from evaluation.fixtures.resumes import VALID_RESUME_PROFILE
from evaluation.fixtures.preferences import DEFAULT_PREFERENCES
from api.main import app


class Eval08MultiTurnState(BaseScenario):
    scenario_id = "EVAL-08"
    name = "Multi-Turn Session State Accumulation"
    category = "Persistence"
    description = "Validates that state survives across conversational turns without client resending earlier state."

    def run(self, metrics: EvaluationMetrics) -> bool:
        client = TestClient(app)
        
        # Init session
        init_res = client.post("/session", headers={"X-API-Key": "test-secret-key"}, json={})
        if init_res.status_code != 200:
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, "Session initialization failed")
            return False
            
        session_id = init_res.json()["session_id"]
        user_id = init_res.json()["user_id"]

        # Turn 1: Store resume_profile
        t1_res = client.post(
            "/chat",
            headers={"X-API-Key": "test-secret-key"},
            json={
                "session_id": session_id,
                "user": user_id,
                "message": "Turn 1: Save profile",
                "state_updates": {"resume_profile": VALID_RESUME_PROFILE.model_dump()}
            }
        )
        if t1_res.status_code != 200:
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, "Turn 1 failed")
            return False

        # Turn 2: Store preferences (without resending resume_profile)
        t2_res = client.post(
            "/chat",
            headers={"X-API-Key": "test-secret-key"},
            json={
                "session_id": session_id,
                "user": user_id,
                "message": "Turn 2: Save preferences",
                "state_updates": {"preferences": DEFAULT_PREFERENCES.model_dump()}
            }
        )
        if t2_res.status_code != 200:
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, "Turn 2 failed")
            return False

        # Turn 3: Chat with NO state updates
        t3_res = client.post(
            "/chat",
            headers={"X-API-Key": "test-secret-key"},
            json={
                "session_id": session_id,
                "user": user_id,
                "message": "Turn 3: Continue"
            }
        )
        if t3_res.status_code != 200:
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, "Turn 3 failed")
            return False

        snap = t3_res.json().get("state_snapshot", {})
        has_resume = snap.get("resume_profile") is not None and "Python" in snap["resume_profile"].get("skills", [])
        
        passed = has_resume
        if passed:
            metrics.persistence_success_count += 1

        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            "State correctly accumulated and preserved across 3 turns without client resending." if passed else "Resume profile lost in turn 3"
        )
        return passed
