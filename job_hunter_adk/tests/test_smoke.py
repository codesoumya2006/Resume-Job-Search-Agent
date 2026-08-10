import pytest
from schemas.preferences import Preferences, JobType, WorkMode
from schemas.resume_profile import ResumeProfile, Experience, Education
from schemas.job_listing import JobListing
from schemas.company_intel import CompanyIntel, ReviewSummary

def test_preferences_roundtrip():
    prefs = Preferences(
        job_type=JobType.internship,
        work_mode=WorkMode.remote,
        locations=["San Francisco", "New York"],
        paid_only=True
    )
    json_data = prefs.model_dump_json()
    parsed = Preferences.model_validate_json(json_data)
    assert prefs == parsed

def test_resume_profile_roundtrip():
    profile = ResumeProfile(
        skills=["Python", "Machine Learning"],
        experience=[
            Experience(title="Software Engineer", company="Tech Corp", duration="2022-2023", description="Developed APIs")
        ],
        internships=[],
        certifications=["AWS Certified"],
        education=[
            Education(degree="B.S. Computer Science", institution="State University", year="2024")
        ],
        projects=[{"name": "Job Hunter", "description": "Agentic system"}]
    )
    json_data = profile.model_dump_json()
    parsed = ResumeProfile.model_validate_json(json_data)
    assert profile == parsed

def test_job_listing_roundtrip():
    job = JobListing(
        title="AI Engineer",
        company="Startup Inc",
        source="linkedin",
        url="https://linkedin.com/jobs/123",
        location="Remote",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$120k",
        description="Looking for AI engineer.",
        posted_date="2024-01-01",
        raw_text_hash="abcdef123456"
    )
    json_data = job.model_dump_json()
    parsed = JobListing.model_validate_json(json_data)
    assert job == parsed

def test_company_intel_roundtrip():
    intel = CompanyIntel(
        company_name="Startup Inc",
        website="https://startup.inc",
        recent_news=["Raised Series A"],
        financial_snapshot=None,
        reviews=[
            ReviewSummary(source="glassdoor", sentiment="positive", summary="Great culture.")
        ]
    )
    json_data = intel.model_dump_json()
    parsed = CompanyIntel.model_validate_json(json_data)
    assert intel == parsed
