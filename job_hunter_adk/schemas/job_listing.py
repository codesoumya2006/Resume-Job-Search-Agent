import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .preferences import JobType, WorkMode

class JobListing(BaseModel):
    """
    A unified job listing scraped or discovered from job portals/web.
    Written by the job_discovery_agent (or underlying scrapers).
    """
    model_config = ConfigDict(extra="forbid")
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    company: str
    source: Literal["linkedin", "naukri", "internshala", "indeed", "web"]
    url: str
    location: str
    work_mode: WorkMode
    job_type: JobType
    stipend_or_salary: str | None
    description: str
    posted_date: str | None
    raw_text_hash: str
