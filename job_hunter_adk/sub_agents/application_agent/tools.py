import logging
import json
from google.adk.tools import FunctionTool, ToolContext

from services.model_router import get_model
from services.db import record_application as db_record_application
from schemas.job_listing import JobListing
from schemas.resume_profile import ResumeProfile

logger = logging.getLogger(__name__)

from services.security import SECURITY_PROMPT_HEADER, wrap_untrusted_data

def _draft_cover_letter_impl(
    job_listing: dict | None = None,
    resume_profile: dict | None = None,
    tool_context: ToolContext | None = None
) -> str:
    """Draft a cover letter using LLM."""
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
    
    wrapped_job = wrap_untrusted_data(job.model_dump_json(), data_type="job_listing")
    wrapped_resume = wrap_untrusted_data(resume.model_dump_json(), data_type="resume_profile")
    
    prompt = f"""
    You are an expert career coach. Draft a compelling cover letter for the following job using the candidate's resume profile.
    Keep it concise, professional, and highlight the most relevant skills. Do not include markdown blocks, just the text.

    {SECURITY_PROMPT_HEADER}

    Job Listing:
    {wrapped_job}

    Resume Profile:
    {wrapped_resume}
    """
    try:
        response = model.generate(prompt)
        return response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        logger.error(f"Failed to draft cover letter: {e}")
        return "Dear Hiring Manager,\n\nI am writing to express my interest in this position.\n\nSincerely,\nCandidate"

draft_cover_letter = FunctionTool(func=_draft_cover_letter_impl)

def _draft_email_impl(
    job_listing: dict | None = None,
    cover_letter: str | None = None,
    recruiter_contact: str | None = None,
    tool_context: ToolContext | None = None
) -> dict:
    """Returns a DRAFT email dict. Must never actually send anything."""
    if tool_context is not None and hasattr(tool_context, "state"):
        if job_listing is None:
            job_listing = tool_context.state.get("selected_job")
        if cover_letter is None:
            cover_letter = "Dear Hiring Manager,\n\nI am interested in this position.\n\nSincerely,\nCandidate"

    if isinstance(job_listing, str):
        try:
            job_listing = json.loads(job_listing)
        except Exception:
            job_listing = {}

    job = JobListing.model_validate(job_listing or {})
    contact = recruiter_contact if recruiter_contact else "hr@company.com"
    draft = {
        "to": contact,
        "subject": f"Application for {job.title} at {job.company}",
        "body": cover_letter or "",
        "status": "pending_user_approval"
    }

    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["email_draft"] = draft

    return draft

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

def _send_email_impl(draft: dict, user_confirmed: bool = False) -> dict:
    """Only actually sends if user_confirmed is True."""
    if not user_confirmed:
        return {"status": "not_sent", "reason": "awaiting confirmation"}
    
    # Stub for sending email (e.g. via smtplib or SendGrid)
    logger.info(f"Mock sending email to {draft.get('to')} with subject {draft.get('subject')}")
    
    return {"status": "sent", "reason": "user confirmed"}

send_email = FunctionTool(func=_send_email_impl)
