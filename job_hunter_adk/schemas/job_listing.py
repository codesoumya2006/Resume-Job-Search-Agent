import hashlib
import re
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .preferences import JobType, WorkMode

def clean_text(text: str | None) -> str:
    """Normalizes whitespace and strips text. Returns empty string if empty or None."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

def compute_raw_text_hash(content: str) -> str:
    """Computes a deterministic SHA-256 hash of normalized text."""
    normalized = clean_text(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def compute_job_hash(
    title: str,
    company: str,
    location: str = "",
    url: str = "",
    description: str = "",
) -> str:
    """
    Computes a deterministic SHA-256 hash from normalized job attributes.
    Ensures identical content produces identical hash, and different content
    produces different hashes without Python built-in hash().
    """
    normalized_parts = [
        clean_text(title).lower(),
        clean_text(company).lower(),
        clean_text(location).lower(),
        clean_text(url),
        clean_text(description).lower(),
    ]
    raw_content = "|".join(normalized_parts)
    return hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

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
