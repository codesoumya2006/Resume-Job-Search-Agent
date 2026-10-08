"""
EVAL-13 — Tool Failure Handling
Validates that exceptions in sub-agent tools are handled gracefully without corrupting state.
"""
from unittest.mock import MagicMock
from google.adk.tools import ToolContext
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from tools.match_rank_tool import _rank_jobs_impl
from sub_agents.application_agent.tools import _send_email_impl


class Eval13ToolFailure(BaseScenario):
    scenario_id = "EVAL-13"
    name = "Tool Failure & Robustness"
    category = "Failure Handling"
    description = "Validates that tool failures and edge cases produce controlled responses without process crashes."

    def run(self, metrics: EvaluationMetrics) -> bool:
        # Case 1: _rank_jobs_impl called with None / empty state
        ctx = MagicMock(spec=ToolContext)
        ctx.state = {}

        try:
            res = _rank_jobs_impl(tool_context=ctx)
            if res != [] or ctx.state.get("ranked_jobs") != []:
                metrics.record_scenario(self.scenario_id, self.name, self.category, False, "rank_jobs did not handle empty state gracefully")
                return False
            metrics.tool_failure_handled_count += 1
        except Exception as e:
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, f"rank_jobs raised unhandled error: {e}")
            return False

        # Case 2: _send_email_impl called with invalid / empty draft
        try:
            email_res = _send_email_impl({}, user_confirmed=False)
            if email_res.get("status") != "not_sent":
                metrics.record_scenario(self.scenario_id, self.name, self.category, False, "Failed to refuse unconfirmed email draft")
                return False
            metrics.tool_failure_handled_count += 1
        except Exception as e:
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, f"_send_email_impl raised unhandled error: {e}")
            return False

        passed = True
        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            "Handled empty rank inputs and unconfirmed email operations gracefully without crashing."
        )
        return passed
