"""
Metrics recording and aggregation engine for agent evaluation.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationMetrics:
    # Scenarios summary
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    
    # Reliability
    controlled_error_count: int = 0
    tool_failure_handled_count: int = 0
    
    # State correctness
    state_propagation_success_count: int = 0
    persistence_success_count: int = 0
    
    # Safety metrics (must remain 0)
    hitl_bypass_count: int = 0
    prompt_injection_escape_count: int = 0
    fabricated_data_count: int = 0
    unsafe_action_count: int = 0
    
    # Data quality
    paid_filter_checks: int = 0
    paid_filter_correct: int = 0
    dedup_checks: int = 0
    dedup_correct: int = 0
    ranking_deterministic_runs: int = 0
    ranking_deterministic_passes: int = 0

    scenario_results: list[dict[str, Any]] = field(default_factory=list)

    @property
    def scenario_pass_rate(self) -> float:
        return (self.passed_scenarios / self.total_scenarios) if self.total_scenarios > 0 else 0.0

    @property
    def paid_filter_accuracy(self) -> float:
        return (self.paid_filter_correct / self.paid_filter_checks) if self.paid_filter_checks > 0 else 1.0

    @property
    def deduplication_accuracy(self) -> float:
        return (self.dedup_correct / self.dedup_checks) if self.dedup_checks > 0 else 1.0

    @property
    def ranking_determinism_rate(self) -> float:
        return (self.ranking_deterministic_passes / self.ranking_deterministic_runs) if self.ranking_deterministic_runs > 0 else 1.0

    def record_scenario(self, scenario_id: str, name: str, category: str, passed: bool, details: str = "") -> None:
        self.total_scenarios += 1
        if passed:
            self.passed_scenarios += 1
        else:
            self.failed_scenarios += 1
            
        self.scenario_results.append({
            "id": scenario_id,
            "name": name,
            "category": category,
            "passed": passed,
            "details": details
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_scenarios": self.total_scenarios,
            "passed_scenarios": self.passed_scenarios,
            "failed_scenarios": self.failed_scenarios,
            "scenario_pass_rate": self.scenario_pass_rate,
            "hitl_bypass_count": self.hitl_bypass_count,
            "prompt_injection_escape_count": self.prompt_injection_escape_count,
            "fabricated_data_count": self.fabricated_data_count,
            "unsafe_action_count": self.unsafe_action_count,
            "paid_filter_accuracy": self.paid_filter_accuracy,
            "deduplication_accuracy": self.deduplication_accuracy,
            "ranking_determinism_rate": self.ranking_determinism_rate,
            "scenarios": self.scenario_results
        }
