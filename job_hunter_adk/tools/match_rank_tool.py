import logging
import re
from collections.abc import Sequence
from typing import Any
import numpy as np
from schemas.resume_profile import ResumeProfile
from schemas.job_listing import JobListing
from schemas.preferences import Preferences
from services.embeddings import get_embeddings

import json
from google.adk.tools import FunctionTool, ToolContext

logger = logging.getLogger(__name__)

def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))

def is_paid_job(stipend_or_salary: str | None) -> bool:
    """
    Determines if a job's compensation represents an explicitly paid position.
    Returns True for explicitly paid, False for unpaid or unknown/missing compensation.
    """
    if not stipend_or_salary:
        return False
    val = stipend_or_salary.strip().lower()
    if not val or val in ("none", "n/a", "unknown", "null", "-", "unspecified", "0", "$0", "₹0"):
        return False
    unpaid_terms = ["unpaid", "no stipend", "volunteer", "without stipend", "zero stipend", "not paid"]
    if any(term in val for term in unpaid_terms):
        return False
    # Check for zero amount like 0/month or $0/month, avoiding false positive on numbers ending in 0 (e.g. 25,000/month)
    if re.search(r'(?:^|[^\d])0\s*(?:/|\bper\b|\bmonth\b|\byear\b|\bhr\b|\bhour\b|\bmo\b)', val):
        return False
    return True

def rank_jobs(
    resume_profile: dict[str, Any] | None = None,
    listings: list[dict[str, Any]] | None = None,
    preferences: dict[str, Any] | None = None,
    tool_context: ToolContext | None = None
) -> list[dict[str, Any]]:
    """
    Hard-filters job listings based on preferences (job_type, work_mode, locations, paid_only)
    and then scores the survivors using semantic similarity (cosine similarity via embeddings).
    Persists ranked jobs to ADK session state if tool_context is provided.
    Returns a list of dicts containing the job and score, sorted descending, max 25.
    """
    # Fallback to ADK session state if arguments are omitted by LLM
    if tool_context is not None and hasattr(tool_context, "state"):
        if resume_profile is None and "resume_profile" in tool_context.state:
            resume_profile = tool_context.state.get("resume_profile")
        if listings is None:
            listings = tool_context.state.get("discovered_jobs") or tool_context.state.get("job_listings")
        if preferences is None and "preferences" in tool_context.state:
            preferences = tool_context.state.get("preferences")

    if isinstance(resume_profile, str):
        try:
            resume_profile = json.loads(resume_profile)
        except Exception:
            resume_profile = None

    if isinstance(listings, str):
        try:
            listings = json.loads(listings)
        except Exception:
            listings = []

    if isinstance(preferences, str):
        try:
            preferences = json.loads(preferences)
        except Exception:
            preferences = None

    if not resume_profile or not listings:
        if tool_context is not None and hasattr(tool_context, "state"):
            tool_context.state["ranked_jobs"] = []
        return []

    # Parse from dicts to Pydantic models to bypass Gemini's complex schema limitations
    resume_prof = resume_profile if isinstance(resume_profile, ResumeProfile) else ResumeProfile.model_validate(resume_profile)
    job_listings = [job if isinstance(job, JobListing) else JobListing.model_validate(job) for job in listings]
    prefs: Preferences | None = None
    if isinstance(preferences, Preferences):
        prefs = preferences
    elif preferences:
        try:
            prefs = Preferences.model_validate(preferences)
        except Exception as e:
            logger.warning("Failed to validate preferences: %s", e)
            prefs = None

    survivors = []
    preferred_locs = [loc.lower() for loc in prefs.locations] if (prefs and prefs.locations) else []
    
    for job in job_listings:
        if prefs:
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
                    
            # paid_only filter: reject unpaid and unknown/missing compensation
            if prefs.paid_only and not is_paid_job(job.stipend_or_salary):
                continue
                    
        survivors.append(job)
        
    if not survivors:
        if tool_context is not None and hasattr(tool_context, "state"):
            tool_context.state["ranked_jobs"] = []
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
        
    scored_jobs: list[dict[str, Any]] = []
    for job, job_emb in zip(survivors, job_embs):
        score = _cosine_similarity(resume_emb, job_emb)
        scored_jobs.append({"job": job, "score": score})
        
    scored_jobs.sort(key=lambda x: float(x["score"]), reverse=True)
    final_ranked = scored_jobs[:25]

    if tool_context is not None and hasattr(tool_context, "state"):
        serializable_ranked = []
        for item in final_ranked:
            j = item["job"]
            job_dict = j.model_dump() if hasattr(j, "model_dump") else (j if isinstance(j, dict) else dict(j))
            serializable_ranked.append({
                "job": job_dict,
                "score": float(item["score"])
            })
        tool_context.state["ranked_jobs"] = serializable_ranked

    return final_ranked

_rank_jobs_impl = rank_jobs
rank_jobs = FunctionTool(func=rank_jobs)
