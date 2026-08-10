import json
import logging
import re
from google.adk.tools import FunctionTool
from services.model_router import get_model
from schemas.job_listing import JobListing
from schemas.resume_profile import ResumeProfile

logger = logging.getLogger(__name__)

def _generate_questions_impl(job_listing: dict, resume_profile: dict) -> list[str]:
    """Generate tailored interview questions based on job and resume."""
    job = JobListing.model_validate(job_listing)
    resume = ResumeProfile.model_validate(resume_profile)
    model = get_model()
    prompt = f"""
    You are an expert technical interviewer. Create a list of 5 tailored interview questions 
    based on the following Job Listing and Resume Profile.
    Return a JSON list of strings. Do not include markdown formatting other than the JSON block.

    Job Listing:
    {job.model_dump_json()}

    Resume Profile:
    {resume.model_dump_json()}
    """
    
    try:
        response = model.generate(prompt)
        text = response.text if hasattr(response, 'text') else str(response)
        
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        data = json.loads(text)
        if isinstance(data, list):
            return data
        return ["Could you walk me through your experience?"]
    except Exception as e:
        logger.error(f"Failed to generate questions: {e}")
        return ["Could you walk me through your experience?"]

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
    prompt = f"""
    You are conducting a mock interview.
    History: {json.dumps(history)}
    User Answer: {user_answer}

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
    prompt = f"""
    You are an expert interview coach. Review the following interview transcript and provide a comprehensive summary of strengths and areas for improvement.

    Transcript:
    {json.dumps(transcript)}
    """
    
    try:
        response = model.generate(prompt)
        return response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        logger.error(f"Failed to generate feedback: {e}")
        return "Keep practicing and refining your answers!"

feedback = FunctionTool(func=_feedback_impl)
