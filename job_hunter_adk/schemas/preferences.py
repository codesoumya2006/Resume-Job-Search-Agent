from enum import Enum
from pydantic import BaseModel, ConfigDict, model_validator

class JobType(str, Enum):
    """Types of jobs the user is looking for."""
    internship = "internship"
    permanent = "permanent"
    parttime = "parttime"

class WorkMode(str, Enum):
    """Work mode preferences."""
    inoffice = "inoffice"
    remote = "remote"
    hybrid = "hybrid"

class Preferences(BaseModel):
    """
    User job search preferences.
    Typically written/extracted by a setup UI or an onboarding agent to guide the search.
    """
    model_config = ConfigDict(extra="ignore")
    
    @model_validator(mode='before')
    @classmethod
    def lowercase_enums(cls, data: dict) -> dict:
        if isinstance(data, dict):
            if isinstance(data.get("job_type"), str):
                data["job_type"] = data["job_type"].lower()
            if isinstance(data.get("work_mode"), str):
                data["work_mode"] = data["work_mode"].lower()
        return data

    job_type: JobType
    work_mode: WorkMode
    locations: list[str] = []
    paid_only: bool = False
