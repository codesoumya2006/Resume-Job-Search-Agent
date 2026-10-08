"""
EVAL-03 — Job Discovery
Resume + preferences -> scrapes/merges job listings.
"""
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from evaluation.fixtures.jobs import JOB_PAID_1, JOB_PAID_2
from sub_agents.job_discovery_agent.tools import _dedupe_merge_impl
from schemas.job_listing import JobListing


class Eval03JobDiscovery(BaseScenario):
    scenario_id = "EVAL-03"
    name = "Job Discovery & Ingestion"
    category = "Job Discovery"
    description = "Validates that discovered jobs are correctly merged, structured, and saved without phantom listings."

    def run(self, metrics: EvaluationMetrics) -> bool:
        scraped_sources = [
            [JOB_PAID_1.model_dump()],
            [JOB_PAID_2.model_dump()]
        ]
        combined = [j for batch in scraped_sources for j in batch]
        merged = _dedupe_merge_impl(combined)

        is_list = isinstance(merged, list)
        has_two = len(merged) == 2
        all_job_listings = all(isinstance(j, JobListing) for j in merged)
        titles = {j.title for j in merged}
        expected_titles = {JOB_PAID_1.title, JOB_PAID_2.title}

        passed = is_list and has_two and all_job_listings and (titles == expected_titles)
        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            f"Merged {len(merged)} jobs successfully" if passed else "Merged count or type mismatch"
        )
        return passed
