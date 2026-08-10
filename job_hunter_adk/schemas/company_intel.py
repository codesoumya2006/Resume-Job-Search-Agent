from typing import Literal
from pydantic import BaseModel, ConfigDict

class ReviewSummary(BaseModel):
    """
    A brief summary of employee/community sentiment for a company.
    Written by the company_intel_agent after searching sources like Glassdoor/Reddit.
    """
    model_config = ConfigDict(extra="forbid")
    
    source: Literal["glassdoor", "reddit", "quora", "blind"]
    sentiment: Literal["positive", "neutral", "negative"]
    summary: str

class CompanyIntel(BaseModel):
    """
    Comprehensive intelligence about a shortlisted company.
    Written by the company_intel_agent to provide context before application/interview.
    """
    model_config = ConfigDict(extra="forbid")
    
    company_name: str
    website: str | None
    recent_news: list[str]
    financial_snapshot: str | None
    reviews: list[ReviewSummary]
