"""
EVAL-14 — Application Flow End-to-End
Validates that downstream company intel, interview prep, and email drafting match the selected job.
"""
from unittest.mock import MagicMock, patch
from google.adk.tools import ToolContext
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from evaluation.fixtures.jobs import JOB_PAID_1
from evaluation.fixtures.resumes import VALID_RESUME_PROFILE
from sub_agents.interview_agent.tools import _generate_questions_impl
from sub_agents.application_agent.tools import _draft_email_impl, _send_email_impl


class Eval14ApplicationFlow(BaseScenario):
    scenario_id = "EVAL-14"
    name = "Selected Job Application Pipeline"
    category = "End-to-End"
    description = "Validates that company intel, interview questions, and email drafting correspond strictly to the selected job."

    def run(self, metrics: EvaluationMetrics) -> bool:
        ctx = MagicMock(spec=ToolContext)
        ctx.state = {
            "selected_job": JOB_PAID_1.model_dump(),
            "resume_profile": VALID_RESUME_PROFILE.model_dump()
        }

        # 1. Interview Prep for selected job
        mock_model = MagicMock()
        mock_q_resp = MagicMock()
        mock_q_resp.text = f'["Tell me about your Python experience for {JOB_PAID_1.title} at {JOB_PAID_1.company}"]'
        mock_model.generate.return_value = mock_q_resp

        with patch("sub_agents.interview_agent.tools.get_model", return_value=mock_model):
            _generate_questions_impl(tool_context=ctx)

        questions_list: list[str] = list(ctx.state.get("interview_prep", []))
        has_questions = len(questions_list) > 0 and JOB_PAID_1.title in questions_list[0]

        # 2. Draft Email for selected job
        mock_draft_resp = MagicMock()
        mock_draft_resp.text = f"""
        Subject: Application for {JOB_PAID_1.title} - Alex Mercer
        Dear Hiring Manager at {JOB_PAID_1.company},
        I am applying for the {JOB_PAID_1.title} position.
        """
        mock_model.generate.return_value = mock_draft_resp

        with patch("sub_agents.application_agent.tools.get_model", return_value=mock_model):
            _ = _draft_email_impl(tool_context=ctx)

        draft = ctx.state.get("email_draft", {})
        has_correct_draft = (
            draft is not None
            and JOB_PAID_1.company in draft.get("subject", "")
            and JOB_PAID_1.title in draft.get("subject", "")
            and draft.get("status") == "pending_user_approval"
        )

        # 3. HITL confirmation and dispatch
        send_res = _send_email_impl(draft, user_confirmed=True)
        is_sent = send_res.get("status") == "sent"

        passed = has_questions and has_correct_draft and is_sent
        if passed:
            metrics.state_propagation_success_count += 1

        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            f"Pipeline cleanly targeted {JOB_PAID_1.company} ({JOB_PAID_1.title}) from interview prep to HITL dispatch." if passed else "Application flow failed"
        )
        return passed
