import logging
import numpy as np
from schemas.resume_profile import ResumeProfile
from schemas.job_listing import JobListing
from schemas.preferences import Preferences
from services.embeddings import get_embeddings

try:
    from google.adk.tools import FunctionTool
except ImportError:
    class FunctionTool:
        def __init__(self, func):
            self.func = func

logger = logging.getLogger(__name__)

def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))

def _rank_jobs_impl(resume_profile: dict, listings: list[dict], preferences: dict) -> list[dict]:
    """
    Hard-filters job listings based on preferences (job_type, work_mode, locations, paid_only)
    and then scores the survivors using semantic similarity (cosine similarity via embeddings).
    Returns a list of dicts containing the job and score, sorted descending, max 25.
    """
    # Parse from dicts to Pydantic models to bypass Gemini's complex schema limitations
    resume_prof = ResumeProfile.model_validate(resume_profile)
    job_listings = [JobListing.model_validate(job) for job in listings]
    prefs = Preferences.model_validate(preferences)

    survivors = []
    preferred_locs = [loc.lower() for loc in prefs.locations] if prefs.locations else []
    
    for job in job_listings:
        # job_type filter
        if job.job_type != prefs.job_type:
            continue
            
        # work_mode filter
        if job.work_mode != prefs.work_mode:
            continue
            
        # locations filter (case-insensitive substring)
        if preferred_locs:
            job_loc = (job.location or "").lower()
            if not any(pref_loc in job_loc for pref_loc in preferred_locs):
                continue
                
        # paid_only filter (reject only explicit "unpaid")
        if prefs.paid_only:
            stipend = (job.stipend_or_salary or "").lower()
            if "unpaid" in stipend:
                continue
                
        survivors.append(job)
        
    if not survivors:
        return []
        
    resume_text = " ".join(resume_prof.skills) + " " + " ".join([e.description for e in resume_prof.experience])
    
    texts_to_embed = [resume_text] + [(job.description or job.title) for job in survivors]
    
    try:
        embeddings = get_embeddings(texts_to_embed)
        resume_emb = embeddings[0]
        job_embs = embeddings[1:]
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        resume_emb = np.zeros(384)
        job_embs = [np.zeros(384) for _ in survivors]
        
    scored_jobs = []
    for job, job_emb in zip(survivors, job_embs):
        score = _cosine_similarity(resume_emb, job_emb)
        scored_jobs.append({"job": job, "score": score})
        
    scored_jobs.sort(key=lambda x: x["score"], reverse=True)
    return scored_jobs[:25]

rank_jobs = FunctionTool(func=_rank_jobs_impl)
