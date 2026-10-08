from google.adk.agents import LlmAgent
from services.model_router import get_model
from sub_agents.application_agent.prompt import APPLICATION_AGENT_INSTRUCTION
from sub_agents.application_agent.tools import (
    draft_cover_letter,
    draft_email,
    record_application,
    send_email
)

def create_application_agent() -> LlmAgent:
    return LlmAgent(
        name="application_agent",
        model=get_model(),
        instruction=APPLICATION_AGENT_INSTRUCTION,
        tools=[
            draft_cover_letter,
            draft_email,
            record_application,
            send_email
        ],
        output_key="email_draft"
    )

application_agent = create_application_agent()
