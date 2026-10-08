import pytest
from schemas.resume_profile import ResumeProfile
from schemas.preferences import Preferences, JobType, WorkMode
from schemas.job_listing import JobListing
from tools.match_rank_tool import _rank_jobs_impl

def test_rank_jobs_filtering_and_scoring() -> None:
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
        stipend_or_salary="$120k",
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
        stipend_or_salary="$90k",
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
        stipend_or_salary="$90k",
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


def test_paid_only_filtering() -> None:
    from tools.match_rank_tool import is_paid_job

    # Unit tests for is_paid_job
    assert is_paid_job("$100k") is True
    assert is_paid_job("₹25,000/month") is True
    assert is_paid_job("Competitive") is True
    assert is_paid_job("Paid") is True
    assert is_paid_job("80000 - 100000 USD") is True

    # Unpaid positions
    assert is_paid_job("unpaid") is False
    assert is_paid_job("Unpaid Internship") is False
    assert is_paid_job("Volunteer role") is False
    assert is_paid_job("no stipend") is False
    assert is_paid_job("0") is False
    assert is_paid_job("$0") is False

    # Missing / unknown compensation
    assert is_paid_job(None) is False
    assert is_paid_job("") is False
    assert is_paid_job("   ") is False
    assert is_paid_job("Unknown") is False
    assert is_paid_job("None") is False
    assert is_paid_job("N/A") is False


def test_rank_jobs_paid_only_rejection_and_acceptance() -> None:
    resume = ResumeProfile(
        skills=["Python"],
        experience=[],
        internships=[],
        certifications=[],
        education=[],
        projects=[]
    )

    paid_job = JobListing(
        title="Python Dev",
        company="Paid Corp",
        source="web",
        url="http://paid.com",
        location="Bangalore",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$100k",
        description="Python developer.",
        posted_date=None,
        raw_text_hash="paid_1"
    )

    unpaid_job = JobListing(
        title="Python Dev",
        company="Unpaid Corp",
        source="web",
        url="http://unpaid.com",
        location="Bangalore",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="Unpaid internship",
        description="Python developer.",
        posted_date=None,
        raw_text_hash="unpaid_1"
    )

    missing_pay_job = JobListing(
        title="Python Dev",
        company="Missing Pay Corp",
        source="web",
        url="http://missing.com",
        location="Bangalore",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary=None,
        description="Python developer.",
        posted_date=None,
        raw_text_hash="missing_1"
    )

    unknown_pay_job = JobListing(
        title="Python Dev",
        company="Unknown Pay Corp",
        source="web",
        url="http://unknown.com",
        location="Bangalore",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="Unknown",
        description="Python developer.",
        posted_date=None,
        raw_text_hash="unknown_1"
    )

    listings = [paid_job, unpaid_job, missing_pay_job, unknown_pay_job]

    # When paid_only=True: only explicitly paid jobs survive
    prefs_paid_only = Preferences(
        job_type=JobType.permanent,
        work_mode=WorkMode.remote,
        locations=["Bangalore"],
        paid_only=True
    )
    survivors_paid = _rank_jobs_impl(resume, listings, prefs_paid_only)
    survivor_hashes = [r["job"].raw_text_hash for r in survivors_paid]
    assert survivor_hashes == ["paid_1"]

    # When paid_only=False: all jobs survive (paid, unpaid, missing, unknown)
    prefs_all = Preferences(
        job_type=JobType.permanent,
        work_mode=WorkMode.remote,
        locations=["Bangalore"],
        paid_only=False
    )
    survivors_all = _rank_jobs_impl(resume, listings, prefs_all)
    assert len(survivors_all) == 4

