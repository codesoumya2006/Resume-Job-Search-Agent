"""
Deterministic preference fixtures for evaluation scenarios.
"""
from schemas.preferences import Preferences, JobType, WorkMode

DEFAULT_PREFERENCES = Preferences(
    job_type=JobType.permanent,
    work_mode=WorkMode.remote,
    locations=["Remote"],
    paid_only=True
)

INTERNSHIP_PREFERENCES = Preferences(
    job_type=JobType.internship,
    work_mode=WorkMode.remote,
    locations=["Remote", "Bangalore"],
    paid_only=True
)

ALL_JOBS_PREFERENCES = Preferences(
    job_type=JobType.permanent,
    work_mode=WorkMode.remote,
    locations=["Remote"],
    paid_only=False
)
