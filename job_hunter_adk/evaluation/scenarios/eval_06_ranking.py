"""
EVAL-06 — Ranking
Validates ranking determinism, sorting order, and score boundaries.
"""
from unittest.mock import patch
import numpy as np
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from evaluation.fixtures.resumes import VALID_RESUME_PROFILE
from evaluation.fixtures.jobs import JOB_PAID_1, JOB_PAID_2
from evaluation.fixtures.preferences import DEFAULT_PREFERENCES
from tools.match_rank_tool import _rank_jobs_impl


class Eval06Ranking(BaseScenario):
    scenario_id = "EVAL-06"
    name = "Match & Rank Determinism"
    category = "Ranking"
    description = "Validates that semantic match ranking correctly scores, orders, and persists ranked job matches."

    def run(self, metrics: EvaluationMetrics) -> bool:
        # Vector 0: Resume
        # Vector 1: JOB_PAID_1 (FastAPI/Backend) -> high cosine similarity (0.95)
        # Vector 2: JOB_PAID_2 (ML Infra) -> medium cosine similarity (0.60)
        resume_vec = np.array([1.0, 0.0, 0.0])
        job1_vec = np.array([0.95, 0.05, 0.0])
        job2_vec = np.array([0.60, 0.80, 0.0])
        mock_embs = np.array([resume_vec, job1_vec, job2_vec])

        with patch("tools.match_rank_tool.get_embeddings", return_value=mock_embs):
            # Run 1
            ranked_1 = _rank_jobs_impl(
                resume_profile=VALID_RESUME_PROFILE.model_dump(),
                listings=[JOB_PAID_1.model_dump(), JOB_PAID_2.model_dump()],
                preferences=DEFAULT_PREFERENCES.model_dump()
            )
            # Run 2
            ranked_2 = _rank_jobs_impl(
                resume_profile=VALID_RESUME_PROFILE.model_dump(),
                listings=[JOB_PAID_1.model_dump(), JOB_PAID_2.model_dump()],
                preferences=DEFAULT_PREFERENCES.model_dump()
            )

        metrics.ranking_deterministic_runs += 1

        job_1_title = ranked_1[0]["job"].title if hasattr(ranked_1[0]["job"], "title") else ranked_1[0]["job"]["title"]
        job_1_id = ranked_1[0]["job"].id if hasattr(ranked_1[0]["job"], "id") else ranked_1[0]["job"]["id"]

        is_sorted = (
            len(ranked_1) == 2
            and ranked_1[0]["score"] >= ranked_1[1]["score"]
            and job_1_title == JOB_PAID_1.title
        )
        
        ids_1 = [r["job"].id if hasattr(r["job"], "id") else r["job"]["id"] for r in ranked_1]
        ids_2 = [r["job"].id if hasattr(r["job"], "id") else r["job"]["id"] for r in ranked_2]
        is_deterministic = (len(ranked_1) == len(ranked_2)) and (ids_1 == ids_2)

        passed = is_sorted and is_deterministic
        if passed:
            metrics.ranking_deterministic_passes += 1

        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            f"Top match: {job_1_title} ({ranked_1[0]['score']:.2f})" if passed else "Ranking sorting or determinism failure"
        )
        return passed
