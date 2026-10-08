"""
EVAL-05 — Job Deduplication
Validates that duplicate job listings merge into one while distinct jobs are preserved.
"""
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from evaluation.fixtures.jobs import JOB_PAID_1, JOB_PAID_2, JOB_DUPLICATE_OF_1, JOB_UNPAID
from sub_agents.job_discovery_agent.tools import _dedupe_merge_impl


class Eval05Deduplication(BaseScenario):
    scenario_id = "EVAL-05"
    name = "Job Deduplication"
    category = "Job Discovery"
    description = "Validates that duplicate and near-duplicate job postings merge correctly without dropping unique jobs."

    def run(self, metrics: EvaluationMetrics) -> bool:
        # Input has 4 jobs: JOB_PAID_1 and JOB_DUPLICATE_OF_1 are duplicates
        scraped_batches = [
            [JOB_PAID_1.model_dump(), JOB_PAID_2.model_dump()],
            [JOB_DUPLICATE_OF_1.model_dump(), JOB_UNPAID.model_dump()]
        ]
        listings_pool = [j for batch in scraped_batches for j in batch]
        
        merged = _dedupe_merge_impl(listings_pool)
        
        metrics.dedup_checks += 1
        # Expect exactly 3 jobs (duplicate merged)
        is_length_correct = len(merged) == 3
        
        # Verify the duplicate was merged and distinct jobs retained
        titles = {j.title for j in merged}
        has_all_titles = titles == {JOB_PAID_1.title, JOB_PAID_2.title, JOB_UNPAID.title}
        
        passed = is_length_correct and has_all_titles
        if passed:
            metrics.dedup_correct += 1
            
        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            f"Merged 4 inputs (including 1 duplicate) to {len(merged)} unique listings."
        )
        return passed
