"""
EVAL-04 — Paid Job Filtering
Validates paid_only filter contract: explicitly paid positions pass; unpaid and missing/unknown fail.
"""
from evaluation.scenarios.base import BaseScenario
from evaluation.metrics import EvaluationMetrics
from evaluation.fixtures.jobs import JOB_PAID_1, JOB_PAID_2, JOB_UNPAID, JOB_MISSING_COMP
from tools.match_rank_tool import is_paid_job


class Eval04PaidFiltering(BaseScenario):
    scenario_id = "EVAL-04"
    name = "Paid Job Filtering"
    category = "Ranking"
    description = "Validates that paid_only filter strictly accepts paid compensation and rejects unpaid/unknown/missing values."

    def run(self, metrics: EvaluationMetrics) -> bool:
        test_cases = [
            # Paid jobs
            (JOB_PAID_1.stipend_or_salary, True),
            (JOB_PAID_2.stipend_or_salary, True),
            ("$50,000", True),
            ("150k", True),
            ("₹25,000 / month", True),
            ("Competitive", True),
            ("Paid", True),
            ("80000 - 100000 USD", True),
            # Unpaid jobs
            (JOB_UNPAID.stipend_or_salary, False),
            ("Unpaid", False),
            ("Volunteer role", False),
            ("no stipend", False),
            ("without stipend", False),
            # Unknown compensation
            ("Unknown", False),
            ("None", False),
            ("N/A", False),
            ("unspecified", False),
            ("-", False),
            # Missing compensation
            (JOB_MISSING_COMP.stipend_or_salary, False),
            (None, False),
            ("", False),
            ("   ", False),
            # Zero compensation
            ("0", False),
            ("$0", False),
            ("₹0", False),
            ("0/month", False),
            ("$0/month", False),
        ]

        passed = True
        for salary_str, expected in test_cases:
            metrics.paid_filter_checks += 1
            actual = is_paid_job(salary_str)
            if actual == expected:
                metrics.paid_filter_correct += 1
            else:
                passed = False

        metrics.record_scenario(
            self.scenario_id, self.name, self.category, passed,
            f"Accuracy: {metrics.paid_filter_accuracy:.2%}"
        )
        return passed
