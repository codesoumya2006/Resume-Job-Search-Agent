import logging
import json
from google.adk.tools import FunctionTool
from services.model_router import get_model
from services.db import record_application as db_record_application
from schemas.job_listing import JobListing
from schemas.resume_profile import ResumeProfile

logger = logging.getLogger(__name__)

def _draft_cover_letter_impl(job_listing: dict, resume_profile: dict) -> str:
    """Draft a cover letter using LLM."""
    job = JobListing.model_validate(job_listing)
    resume = ResumeProfile.model_validate(resume_profile)
    model = get_model()
    prompt = f"""
    You are an expert career coach. Draft a compelling cover letter for the following job using the candidate's resume profile.
    Keep it concise, professional, and highlight the most relevant skills. Do not include markdown blocks, just the text.

    Job Listing:
    {job.model_dump_json()}

    Resume Profile:
    {resume.model_dump_json()}
    """
    try:
        response = model.generate(prompt)
        return response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        logger.error(f"Failed to draft cover letter: {e}")
        return "Dear Hiring Manager,\n\nI am writing to express my interest in this position.\n\nSincerely,\nCandidate"

draft_cover_letter = FunctionTool(func=_draft_cover_letter_impl)

def _draft_email_impl(job_listing: dict, cover_letter: str, recruiter_contact: str | None = None) -> dict:
    """Returns a DRAFT email dict. Must never actually send anything."""
    job = JobListing.model_validate(job_listing)
    contact = recruiter_contact if recruiter_contact else "hr@company.com"
    return {
        "to": contact,
        "subject": f"Application for {job.title} at {job.company}",
        "body": cover_letter,
        "status": "pending_user_approval"
    }

draft_email = FunctionTool(func=_draft_email_impl)

def _record_application_impl(job_listing: dict, status: str) -> None:
    """Writes a row via services/db.py to an `applications` table."""
    try:
        job = JobListing.model_validate(job_listing)
        db_record_application(job, status)
        logger.info(f"Recorded application for {job.title} at {job.company} with status: {status}")
    except Exception as e:
        logger.error(f"Failed to record application: {e}")

record_application = FunctionTool(func=_record_application_impl)

def _send_email_impl(draft: dict, user_confirmed: bool) -> dict:
    """Only actually sends if user_confirmed is True."""
    if not user_confirmed:
        return {"status": "not_sent", "reason": "awaiting confirmation"}
    
    # Stub for sending email (e.g. via smtplib or SendGrid)
    logger.info(f"Mock sending email to {draft.get('to')} with subject {draft.get('subject')}")
    
    return {"status": "sent", "reason": "user confirmed"}

send_email = FunctionTool(func=_send_email_impl)
