from google.adk.agents import LlmAgent
from services.model_router import get_model
from sub_agents.interview_agent.prompt import INTERVIEW_AGENT_INSTRUCTION
from sub_agents.interview_agent.tools import (
    generate_questions,
    coding_practice,
    mock_interview_turn,
    feedback
)

def create_interview_agent() -> LlmAgent:
    return LlmAgent(
        name="interview_agent",
        model=get_model(),
        instruction=INTERVIEW_AGENT_INSTRUCTION,
        tools=[
            generate_questions,
            coding_practice,
            mock_interview_turn,
            feedback
        ],
        output_key="interview_prep"
    )

interview_agent = create_interview_agent()
