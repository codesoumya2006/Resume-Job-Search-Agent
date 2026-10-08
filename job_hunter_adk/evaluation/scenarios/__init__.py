"""
Scenarios registry for agent quality evaluation.
"""
from evaluation.scenarios.base import BaseScenario
from evaluation.scenarios.eval_01_resume import Eval01ResumeHappyPath
from evaluation.scenarios.eval_02_invalid_resume import Eval02InvalidResume
from evaluation.scenarios.eval_03_job_discovery import Eval03JobDiscovery
from evaluation.scenarios.eval_04_paid_filtering import Eval04PaidFiltering
from evaluation.scenarios.eval_05_deduplication import Eval05Deduplication
from evaluation.scenarios.eval_06_ranking import Eval06Ranking
from evaluation.scenarios.eval_07_state_propagation import Eval07StatePropagation
from evaluation.scenarios.eval_08_multi_turn import Eval08MultiTurnState
from evaluation.scenarios.eval_09_restart_persistence import Eval09RestartPersistence
from evaluation.scenarios.eval_10_hitl import Eval10Hitl
from evaluation.scenarios.eval_11_prompt_injection import Eval11PromptInjection
from evaluation.scenarios.eval_12_missing_data import Eval12MissingData
from evaluation.scenarios.eval_13_tool_failure import Eval13ToolFailure
from evaluation.scenarios.eval_14_application_flow import Eval14ApplicationFlow

ALL_SCENARIOS: list[type[BaseScenario]] = [
    Eval01ResumeHappyPath,
    Eval02InvalidResume,
    Eval03JobDiscovery,
    Eval04PaidFiltering,
    Eval05Deduplication,
    Eval06Ranking,
    Eval07StatePropagation,
    Eval08MultiTurnState,
    Eval09RestartPersistence,
    Eval10Hitl,
    Eval11PromptInjection,
    Eval12MissingData,
    Eval13ToolFailure,
    Eval14ApplicationFlow
]
