"""
EVAL-07 — State Propagation
Validates end-to-end data flow through ToolContext.state across sub-agent tools.
"""
from typing import Any
from unittest.mock import MagicMock, patch
import numpy as np
from google.adk.tools import ToolContext
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from evaluation.fixtures.resumes import VALID_RESUME_PROFILE
from evaluation.fixtures.jobs import JOB_PAID_1
from evaluation.fixtures.preferences import DEFAULT_PREFERENCES
from tools.match_rank_tool import _rank_jobs_impl
from sub_agents.interview_agent.tools import _generate_questions_impl
from sub_agents.application_agent.tools import _draft_email_impl


class Eval07StatePropagation(BaseScenario):
    scenario_id = "EVAL-07"
    name = "Agent State Propagation"
    category = "State"
    description = "Validates that session state flows unbroken through the entire sub-agent pipeline via ToolContext."

    def run(self, metrics: EvaluationMetrics) -> bool:
        # Create ToolContext with initial upstream state
        ctx = MagicMock(spec=ToolContext)
        ctx.state = {
            "resume_profile": VALID_RESUME_PROFILE.model_dump(),
            "preferences": DEFAULT_PREFERENCES.model_dump(),
            "discovered_jobs": [JOB_PAID_1.model_dump()]
        }

        # 1. Match & Rank reads discovered_jobs + resume_profile, writes ranked_jobs
        mock_embs = np.ones((2, 384))
        with patch("tools.match_rank_tool.get_embeddings", return_value=mock_embs):
            _rank_jobs_impl(tool_context=ctx)
        
        has_ranked = "ranked_jobs" in ctx.state and len(ctx.state["ranked_jobs"]) > 0
        
        # 2. Select top ranked job
        ranked_jobs = ctx.state.get("ranked_jobs", [])
        if isinstance(ranked_jobs, list) and ranked_jobs and isinstance(ranked_jobs[0], dict):
            top_job = ranked_jobs[0].get("job")
            if isinstance(top_job, dict):
                ctx.state["selected_job"] = top_job

        # 3. Interview Agent generates questions reading selected_job + resume_profile
        mock_model = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = '{"questions": ["Tell me about FastAPI", "How do you optimize PostgreSQL?"]}'
        mock_model.generate.return_value = mock_resp
        
        with patch("sub_agents.interview_agent.tools.get_model", return_value=mock_model):
            _generate_questions_impl(tool_context=ctx)
        
        has_interview = "interview_prep" in ctx.state and len(ctx.state["interview_prep"]) > 0

        # 4. Application Agent drafts email reading selected_job + resume_profile
        mock_draft_resp = MagicMock()
        mock_draft_resp.text = """
        Subject: Application for Senior Python Backend Engineer
        Dear Hiring Team,
        I am applying for the Senior Python Backend Engineer position at TechNova.
        """
        mock_model.generate.return_value = mock_draft_resp

        with patch("sub_agents.application_agent.tools.get_model", return_value=mock_model):
            _draft_email_impl(tool_context=ctx)

        has_draft = "email_draft" in ctx.state and ctx.state["email_draft"] is not None

        passed = has_ranked and has_interview and has_draft
        if passed:
            metrics.state_propagation_success_count += 1

        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            f"ranked_jobs: {has_ranked}, interview_prep: {has_interview}, email_draft: {has_draft}"
        )
        return passed
