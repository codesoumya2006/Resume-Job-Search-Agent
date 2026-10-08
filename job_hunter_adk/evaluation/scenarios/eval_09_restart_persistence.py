"""
EVAL-09 — Process Restart Persistence
Validates that session state survives an in-memory wipe by rehydrating from persistent storage.
"""
from fastapi.testclient import TestClient
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from api.main import app, session_service, adk_session_service


class Eval09RestartPersistence(BaseScenario):
    scenario_id = "EVAL-09"
    name = "Process Restart Persistence"
    category = "Persistence"
    description = "Validates that state survives runtime restart by rehydrating from authoritative database storage."

    def run(self, metrics: EvaluationMetrics) -> bool:
        client = TestClient(app)

        # 1. Start session and save initial profile
        init_res = client.post("/session", headers={"X-API-Key": "test-secret-key"}, json={})
        session_id = init_res.json()["session_id"]
        user_id = init_res.json()["user_id"]

        test_skills = ["Rust", "Python", "Distributed Systems"]
        client.post(
            "/chat",
            headers={"X-API-Key": "test-secret-key"},
            json={
                "session_id": session_id,
                "user": user_id,
                "message": "Store profile pre-restart",
                "state_updates": {"resume_profile": {"skills": test_skills}}
            }
        )

        # 2. Check DB layer directly
        db_state = session_service.get_state(session_id)
        if db_state.get("resume_profile", {}).get("skills") != test_skills:
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, "State failed to write to DB")
            return False

        # 3. SIMULATE RESTART: Wipe ADK in-memory session cache completely
        adk_session_service.sessions.clear()
        if len(adk_session_service.sessions) != 0:
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, "Failed to clear in-memory cache")
            return False

        # 4. Make post-restart request without resending state
        post_res = client.post(
            "/chat",
            headers={"X-API-Key": "test-secret-key"},
            json={
                "session_id": session_id,
                "user": user_id,
                "message": "Continue conversation post-restart"
            }
        )

        snap = post_res.json().get("state_snapshot", {})
        rehydrated_skills = snap.get("resume_profile", {}).get("skills", [])
        passed = rehydrated_skills == test_skills

        if passed:
            metrics.persistence_success_count += 1

        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            f"Successfully rehydrated skills {rehydrated_skills} from DB after memory wipe." if passed else "State lost after restart simulation"
        )
        return passed
