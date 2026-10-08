"""
EVAL-01 — Resume Happy Path
Valid resume text -> parsing -> structured ResumeProfile.
"""
from unittest.mock import MagicMock, patch
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from evaluation.fixtures.resumes import VALID_RESUME_TEXT, VALID_RESUME_PROFILE
from sub_agents.resume_agent.tools import _parse_resume_impl
from schemas.resume_profile import ResumeProfile


class Eval01ResumeHappyPath(BaseScenario):
    scenario_id = "EVAL-01"
    name = "Resume Happy Path"
    category = "Resume"
    description = "Validates that a legitimate resume is parsed into a structured ResumeProfile without fabrication."

    def run(self, metrics: EvaluationMetrics) -> bool:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = VALID_RESUME_PROFILE.model_dump_json()
        mock_model.generate.return_value = mock_response

        with patch("sub_agents.resume_agent.tools.get_model", return_value=mock_model):
            try:
                profile = _parse_resume_impl(VALID_RESUME_TEXT)
                is_valid = isinstance(profile, ResumeProfile)
                has_skills = len(profile.skills) > 0 and "Python" in profile.skills
                has_exp = len(profile.experience) > 0

                passed = is_valid and has_skills and has_exp
                if passed:
                    metrics.state_propagation_success_count += 1
                metrics.record_scenario(self.scenario_id, self.name, self.category, passed, f"Skills: {len(profile.skills)}, Exp: {len(profile.experience)}")
                return passed
            except Exception as e:
                metrics.record_scenario(self.scenario_id, self.name, self.category, False, f"Exception: {e}")
                return False
