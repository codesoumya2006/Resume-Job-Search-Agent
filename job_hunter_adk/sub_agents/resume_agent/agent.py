from google.adk.agents import LlmAgent
from services.model_router import get_model
from .prompt import RESUME_AGENT_INSTRUCTION
from .tools import parse_resume, ats_score, skill_gap

def get_resume_agent():
    return LlmAgent(
        name="resume_agent",
        model=get_model(),
        instruction=RESUME_AGENT_INSTRUCTION,
        tools=[parse_resume, ats_score, skill_gap],
        output_key="resume_profile"
    )

resume_agent = get_resume_agent()
