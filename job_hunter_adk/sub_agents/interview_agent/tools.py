import json
import logging
import re
from google.adk.tools import FunctionTool, ToolContext

from services.model_router import get_model
from schemas.job_listing import JobListing
from schemas.resume_profile import ResumeProfile

logger = logging.getLogger(__name__)

def _generate_questions_impl(
    job_listing: dict | None = None,
    resume_profile: dict | None = None,
    tool_context: ToolContext | None = None
) -> list[str]:
    """Generate tailored interview questions based on job and resume."""
    if tool_context is not None and hasattr(tool_context, "state"):
        if job_listing is None:
            job_listing = tool_context.state.get("selected_job")
        if resume_profile is None:
            resume_profile = tool_context.state.get("resume_profile")

    if isinstance(job_listing, str):
        try:
            job_listing = json.loads(job_listing)
        except Exception:
            job_listing = {}

    if isinstance(resume_profile, str):
        try:
            resume_profile = json.loads(resume_profile)
        except Exception:
            resume_profile = {}

    job = JobListing.model_validate(job_listing or {})
    resume = ResumeProfile.model_validate(resume_profile or {})
    model = get_model()
    from services.security import SECURITY_PROMPT_HEADER, wrap_untrusted_data

    wrapped_job = wrap_untrusted_data(job.model_dump_json(), data_type="job_listing")
    wrapped_resume = wrap_untrusted_data(resume.model_dump_json(), data_type="resume_profile")
    prompt = f"""
    You are an expert technical interviewer. Create a list of 5 tailored interview questions 
    based on the following Job Listing and Resume Profile.
    Return a JSON list of strings. Do not include markdown formatting other than the JSON block.

    {SECURITY_PROMPT_HEADER}

    Job Listing:
    {wrapped_job}

    Resume Profile:
    {wrapped_resume}
    """
    
    questions = ["Could you walk me through your experience?"]
    try:
        response = model.generate(prompt)
        text = response.text if hasattr(response, 'text') else str(response)
        
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        data = json.loads(text)
        if isinstance(data, list):
            questions = data
    except Exception as e:
        logger.error(f"Failed to generate questions: {e}")

    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["interview_prep"] = questions

    return questions

generate_questions = FunctionTool(func=_generate_questions_impl)

def _coding_practice_impl(topic: str) -> dict:
    """Generate one practice problem + hints, no full solution unless asked."""
    model = get_model()
    prompt = f"""
    Provide a coding practice problem and some hints for the following topic: {topic}
    Do NOT provide the full solution. Return ONLY valid JSON with keys: "problem" (str) and "hints" (list[str]).
    """
    
    try:
        response = model.generate(prompt)
        text = response.text if hasattr(response, 'text') else str(response)
        
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to generate coding practice: {e}")
        return {"problem": f"Write a function related to {topic}.", "hints": ["Think step by step."]}

coding_practice = FunctionTool(func=_coding_practice_impl)

def _mock_interview_turn_impl(history: list[dict], user_answer: str) -> dict:
    """Provide feedback on user_answer and generate the next question."""
    model = get_model()
    from services.security import SECURITY_PROMPT_HEADER, wrap_untrusted_data

    wrapped_history = wrap_untrusted_data(json.dumps(history), data_type="interview_history")
    wrapped_answer = wrap_untrusted_data(user_answer, data_type="user_answer")
    prompt = f"""
    You are conducting a mock interview.
    
    {SECURITY_PROMPT_HEADER}
    
    History: {wrapped_history}
    User Answer: {wrapped_answer}

    Provide brief feedback on the user's answer and ask the next question.
    Return ONLY valid JSON with keys: "feedback" (str) and "next_question" (str).
    """
    
    try:
        response = model.generate(prompt)
        text = response.text if hasattr(response, 'text') else str(response)
        
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to generate mock turn: {e}")
        return {"feedback": "Good point.", "next_question": "Can you elaborate more on your background?"}

mock_interview_turn = FunctionTool(func=_mock_interview_turn_impl)

def _feedback_impl(transcript: list[dict]) -> str:
    """End-of-session summary based on the interview transcript."""
    model = get_model()
    from services.security import SECURITY_PROMPT_HEADER, wrap_untrusted_data

    wrapped_transcript = wrap_untrusted_data(json.dumps(transcript), data_type="interview_transcript")
    prompt = f"""
    You are an expert interview coach. Review the following interview transcript and provide a comprehensive summary of strengths and areas for improvement.

    {SECURITY_PROMPT_HEADER}

    Transcript:
    {wrapped_transcript}
    """
    
    try:
        response = model.generate(prompt)
        return response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        logger.error(f"Failed to generate feedback: {e}")
        return "Keep practicing and refining your answers!"

feedback = FunctionTool(func=_feedback_impl)
