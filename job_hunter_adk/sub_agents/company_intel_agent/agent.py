from google.adk.agents import LlmAgent
from services.model_router import get_model
from .prompt import COMPANY_INTEL_SYSTEM_PROMPT
from .tools import (
    company_website_lookup,
    news_search,
    financial_snapshot,
    glassdoor_reviews,
    community_reviews,
    summarize_sentiment
)

def get_company_intel_agent() -> LlmAgent:
    return LlmAgent(
        name="company_intel_agent",
        model=get_model(),
        instruction=COMPANY_INTEL_SYSTEM_PROMPT,
        tools=[
            company_website_lookup,
            news_search,
            financial_snapshot,
            glassdoor_reviews,
            community_reviews,
            summarize_sentiment
        ],
        output_key="company_intel"
    )

company_intel_agent = get_company_intel_agent()
