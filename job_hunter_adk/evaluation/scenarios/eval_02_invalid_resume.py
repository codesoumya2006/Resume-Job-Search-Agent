"""
EVAL-02 — Invalid Resume
Corrupt or unparseable resume -> transparent failure, no fake fallback profile.
"""
from unittest.mock import MagicMock, patch
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from evaluation.fixtures.resumes import CORRUPT_RESUME_BYTES
from sub_agents.resume_agent.tools import _parse_resume_impl


class Eval02InvalidResume(BaseScenario):
    scenario_id = "EVAL-02"
    name = "Invalid Resume Handling"
    category = "Resume"
    description = "Validates that unparseable input fails transparently with zero fabricated fallback data."

    def run(self, metrics: EvaluationMetrics) -> bool:
        mock_model = MagicMock()
        # Model returns invalid / garbage text
        mock_response = MagicMock()
        mock_response.text = "NOT_A_VALID_JSON_STRING"
        mock_model.generate.return_value = mock_response

        with patch("sub_agents.resume_agent.tools.get_model", return_value=mock_model):
            try:
                # Should raise ValueError and NEVER return fake profile
                _parse_resume_impl("random corrupt text")
                # If it reached here without exception, it failed
                metrics.fabricated_data_count += 1
                metrics.record_scenario(self.scenario_id, self.name, self.category, False, "Failed to raise error on invalid resume")
                return False
            except ValueError:
                # Controlled expected failure
                metrics.controlled_error_count += 1
                metrics.record_scenario(self.scenario_id, self.name, self.category, True, "Raised controlled ValueError without fabrication")
                return True
            except Exception as e:
                metrics.record_scenario(self.scenario_id, self.name, self.category, False, f"Unexpected exception type: {type(e).__name__}")
                return False
