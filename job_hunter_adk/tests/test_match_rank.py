import pytest
from schemas.resume_profile import ResumeProfile
from schemas.preferences import Preferences, JobType, WorkMode
from schemas.job_listing import JobListing
from tools.match_rank_tool import _rank_jobs_impl

def test_rank_jobs_filtering_and_scoring():
    resume = ResumeProfile(
        skills=["Python", "Machine Learning", "FastAPI"],
        experience=[],
        internships=[],
        certifications=[],
        education=[],
        projects=[]
    )
    
    preferences = Preferences(
        job_type=JobType.permanent,
        work_mode=WorkMode.remote,
        locations=["Bangalore"],
        paid_only=True
    )
    
    job_valid_high = JobListing(
        title="Python ML Engineer",
        company="AI Corp",
        source="web",
        url="",
        location="Bengaluru / Bangalore",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary=None,
        description="Looking for Python and Machine Learning expert to build FastAPI backends.",
        posted_date=None,
        raw_text_hash="1"
    )
    
    job_valid_low = JobListing(
        title="Java Developer",
        company="Enterprise Inc",
        source="web",
        url="",
        location="Bangalore, KA",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="100k",
        description="We need a Java Spring Boot developer with Oracle DB experience.",
        posted_date=None,
        raw_text_hash="2"
    )
    
    job_invalid_work_mode = JobListing(
        title="Python Dev",
        company="InOffice Corp",
        source="web",
        url="",
        location="Bangalore",
        work_mode=WorkMode.inoffice, # Mismatch
        job_type=JobType.permanent,
        stipend_or_salary=None,
        description="Python dev.",
        posted_date=None,
        raw_text_hash="3"
    )
    
    job_invalid_location = JobListing(
        title="Python Dev",
        company="Mumbai Corp",
        source="web",
        url="",
        location="Mumbai", # Mismatch
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary=None,
        description="Python dev.",
        posted_date=None,
        raw_text_hash="4"
    )
    
    job_invalid_unpaid = JobListing(
        title="Python Dev",
        company="Startup",
        source="web",
        url="",
        location="Bangalore",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="Unpaid internship followed by PPO", # Mismatch
        description="Python dev.",
        posted_date=None,
        raw_text_hash="5"
    )
    
    listings = [
        job_valid_high,
        job_valid_low,
        job_invalid_work_mode,
        job_invalid_location,
        job_invalid_unpaid
    ]
    
    results = _rank_jobs_impl(resume, listings, preferences)
    
    # 3 should be filtered out, 2 should survive
    assert len(results) == 2
    
    # Verify survivors
    survivor_hashes = [r["job"].raw_text_hash for r in results]
    assert "1" in survivor_hashes
    assert "2" in survivor_hashes
    
    # Verify sorting (Python ML Engineer should score higher than Java Developer)
    # The models are loaded lazily, sentence-transformers should score them
    # Ensure job 1 is ranked above job 2
    assert results[0]["job"].raw_text_hash == "1"
    assert results[1]["job"].raw_text_hash == "2"
    assert results[0]["score"] >= results[1]["score"]
