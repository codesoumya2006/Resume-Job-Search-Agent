"""
Base class definition for evaluation scenarios.
"""
from abc import ABC, abstractmethod
from evaluation.metrics import EvaluationMetrics


class BaseScenario(ABC):
    scenario_id: str = ""
    name: str = ""
    category: str = ""
    description: str = ""

    @abstractmethod
    def run(self, metrics: EvaluationMetrics) -> bool:
        """
        Executes the scenario, updates the metrics object,
        and returns True if evaluation succeeded, False otherwise.
        """
        pass
