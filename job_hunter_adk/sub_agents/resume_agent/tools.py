import json
import logging
import re
from schemas.resume_profile import ResumeProfile
from schemas.preferences import Preferences
from services.model_router import get_model

logger = logging.getLogger(__name__)

from google.adk.tools import FunctionTool

def _parse_resume_impl(resume_text: str) -> ResumeProfile:
    """
    Calls the model with a strict instruction to extract skills, experience, internships,
    certifications, education, projects from raw resume text.
    """
    # For a deterministic and robust scaffold execution in tests, we provide a robust extraction mechanism.
    # In production, this would call the get_model() API.
    # We will try to call the model via a simple agent structure if possible, but fallback to a robust parser.
    model = get_model()
    from services.security import SECURITY_PROMPT_HEADER, wrap_untrusted_data
    wrapped_resume = wrap_untrusted_data(resume_text, data_type="resume_text")
    prompt = f"""
    You are a strict data extraction assistant.
    Extract the candidate's skills, experience, internships, certifications, education, and projects from the provided resume text.
    Return ONLY valid JSON matching this schema:
    {ResumeProfile.model_json_schema()}
    
    {SECURITY_PROMPT_HEADER}
    
    Resume Text:
    {wrapped_resume}
    """
    
    try:
        # Attempt to call ADK model's generate method if it exists
        response = model.generate(prompt)
        text = response.text if hasattr(response, 'text') else str(response)
        
        # Clean markdown code blocks if any
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        return ResumeProfile.model_validate_json(text)
    except Exception as e:
        logger.error(f"Failed to parse resume into structured profile: {e}")
        raise ValueError(f"Resume parsing failed: unable to extract candidate profile ({e})") from e

parse_resume = FunctionTool(func=_parse_resume_impl)

def _ats_score_impl(resume_profile: dict, job_description: str) -> dict:
    """
    Deterministic keyword + section-presence scoring.
    Returns {"score": 0-100, "missing_keywords": [...]}.
    """
    resume_prof = ResumeProfile.model_validate(resume_profile)
    desc_words = {w.strip('.,!?;:()[]{}') for w in job_description.lower().split() if len(w) > 3}
    
    resume_words = set()
    for s in resume_prof.skills:
        resume_words.update(w.strip('.,!?;:()[]{}') for w in s.lower().split() if len(w) > 3)
    for exp in resume_prof.experience:
        resume_words.update(w.strip('.,!?;:()[]{}') for w in exp.title.lower().split() if len(w) > 3)
        resume_words.update(w.strip('.,!?;:()[]{}') for w in exp.description.lower().split() if len(w) > 3)
        
    overlap = resume_words.intersection(desc_words)
    missing = list(desc_words - resume_words)[:10]
    
    # Calculate score based on overlap percentage + bonus for having multiple sections filled
    base_score = int((len(overlap) / len(desc_words)) * 80) if desc_words else 80
    section_bonus = 0
    if resume_prof.experience: section_bonus += 10
    if resume_prof.education: section_bonus += 10
    
    return {
        "score": min(100, base_score + section_bonus),
        "missing_keywords": missing
    }

ats_score = FunctionTool(func=_ats_score_impl)

def _skill_gap_impl(resume_profile: dict, preferences: dict) -> dict:
    """
    Compares resume_profile.skills against a keyword set implied by preferences.job_type,
    flags likely mismatches.
    """
    resume_prof = ResumeProfile.model_validate(resume_profile)
    prefs = Preferences.model_validate(preferences)
    
    expected_skills = set()
    job_type = prefs.job_type.value
    
    if job_type == "internship":
        expected_skills = {"fundamentals", "teamwork", "learning"}
    elif job_type == "permanent":
        expected_skills = {"production", "architecture", "deployment"}
    else:
        expected_skills = {"communication", "flexibility"}
        
    resume_skills_flat = " ".join(resume_prof.skills).lower()
    missing = [skill for skill in expected_skills if skill not in resume_skills_flat]
    
    return {
        "missing_core_skills": missing,
        "match_level": "High" if not missing else ("Medium" if len(missing) == 1 else "Low")
    }

skill_gap = FunctionTool(func=_skill_gap_impl)
