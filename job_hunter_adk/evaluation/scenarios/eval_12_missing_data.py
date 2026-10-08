"""
EVAL-12 — Missing External Data Handling
Validates that scraper or API outages degrade gracefully with zero data fabrication.
"""
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from sub_agents.job_discovery_agent.tools import _dedupe_merge_impl
from sub_agents.company_intel_agent.tools import _summarize_sentiment_impl


class Eval12MissingData(BaseScenario):
    scenario_id = "EVAL-12"
    name = "Missing External Data Handling"
    category = "Failure Handling"
    description = "Validates graceful degradation when external search/scraper sources return empty or fail."

    def run(self, metrics: EvaluationMetrics) -> bool:
        from typing import Any
        # Case 1: All scrapers return empty lists
        empty_scrapers: list[list[dict[str, Any]]] = [[], [], []]
        combined_listings: list[dict[str, Any]] = [j for s in empty_scrapers for j in s]
        merged = _dedupe_merge_impl(combined_listings)

        if not isinstance(merged, list) or len(merged) != 0:
            metrics.fabricated_data_count += 1
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, "Invented jobs on empty scraper results")
            return False

        # Case 2: Summarizing sentiment with no reviews
        sentiment_res = _summarize_sentiment_impl([])
        if not isinstance(sentiment_res, list) or len(sentiment_res) != 0:
            metrics.fabricated_data_count += 1
            metrics.record_scenario(self.scenario_id, self.name, self.category, False, "Fabricated reviews on empty reviews input")
            return False

        passed = (len(merged) == 0 and len(sentiment_res) == 0)
        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            "Gracefully returned empty job listings and neutral sentiment without fabricating data."
        )
        return passed
