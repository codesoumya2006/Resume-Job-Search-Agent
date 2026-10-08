from google.adk.agents import LlmAgent
from services.model_router import get_model
from .prompt import JOB_DISCOVERY_SYSTEM_PROMPT
from .tools import (
    search_linkedin, search_naukri, search_internshala, 
    search_indeed, web_discovery, dedupe_merge
)

def get_job_discovery_agent() -> LlmAgent:
    return LlmAgent(
        name="job_discovery_agent",
        model=get_model(),
        instruction=JOB_DISCOVERY_SYSTEM_PROMPT,
        tools=[
            search_linkedin,
            search_naukri,
            search_internshala,
            search_indeed,
            web_discovery,
            dedupe_merge
        ],
        output_key="discovered_jobs"
    )

job_discovery_agent = get_job_discovery_agent()
