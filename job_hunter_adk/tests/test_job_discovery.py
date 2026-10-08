import pytest
from unittest.mock import patch, AsyncMock
from schemas.preferences import Preferences, JobType, WorkMode
from schemas.job_listing import JobListing
from sub_agents.job_discovery_agent.tools import dedupe_merge

@pytest.fixture
def dummy_preferences() -> Preferences:
    return Preferences(
        job_type=JobType.internship,
        work_mode=WorkMode.remote,
        locations=["Bangalore"],
        paid_only=True
    )

@pytest.mark.asyncio
@patch('services.scrapers.linkedin_scraper.search', new_callable=AsyncMock)
@patch('services.scrapers.indeed_scraper.search', new_callable=AsyncMock)
@patch('services.scrapers.naukri_scraper.search', new_callable=AsyncMock)
@patch('services.scrapers.internshala_scraper.search', new_callable=AsyncMock)
async def test_dedupe_merge_with_mocked_scrapers(
    mock_internshala: AsyncMock,
    mock_naukri: AsyncMock,
    mock_indeed: AsyncMock,
    mock_linkedin: AsyncMock,
    dummy_preferences: Preferences
) -> None:
    # Canned job listings containing an intentional duplicate pair
    job1 = JobListing(
        title="Software Engineer Intern",
        company="Tech Innovators",
        source="linkedin",
        url="http://linkedin.com/1",
        location="Bangalore",
        work_mode=dummy_preferences.work_mode,
        job_type=dummy_preferences.job_type,
        stipend_or_salary=None,
        description="Short desc",
        posted_date=None,
        raw_text_hash="1"
    )
    
    job2 = JobListing(
        title="Software Eng Intern",
        company="Tech Innovator", # intentional fuzzy duplicate
        source="indeed",
        url="http://indeed.com/1",
        location="Bangalore",
        work_mode=dummy_preferences.work_mode,
        job_type=dummy_preferences.job_type,
        stipend_or_salary=None,
        description="Longer description that is much more detailed.",
        posted_date=None,
        raw_text_hash="2"
    )
    
    job3 = JobListing(
        title="Data Scientist",
        company="Data Corp",
        source="naukri",
        url="http://naukri.com/1",
        location="Mumbai",
        work_mode=dummy_preferences.work_mode,
        job_type=dummy_preferences.job_type,
        stipend_or_salary=None,
        description="Data role.",
        posted_date=None,
        raw_text_hash="3"
    )

    # Mock the scrapers to return these canned results
    mock_linkedin.return_value = [job1]
    mock_indeed.return_value = [job2]
    mock_naukri.return_value = [job3]
    mock_internshala.return_value = []

    # Get the combined list as if we called all of them
    listings = []
    listings.extend(await mock_linkedin())
    listings.extend(await mock_indeed())
    listings.extend(await mock_naukri())
    listings.extend(await mock_internshala())

    # If dedupe_merge is an ADK FunctionTool, we might need to call its underlying function,
    # or if the mock FunctionTool allows calling, we can just call it.
    # In our tools.py, if FunctionTool is a dummy, it just returns the function.
    # Otherwise we'll test the actual _dedupe_merge_impl logic.
    from sub_agents.job_discovery_agent.tools import _dedupe_merge_impl
    merged = _dedupe_merge_impl(listings)
    
    assert len(merged) == 2
    # Ensure job2 (longer description) is kept over job1
    assert any(j.description == "Longer description that is much more detailed." for j in merged)
    assert not any(j.description == "Short desc" for j in merged)


def test_dedupe_edge_cases() -> None:
    from sub_agents.job_discovery_agent.tools import _dedupe_merge_impl

    # 1. Different companies with exact same title and location -> NOT merged
    job_google = JobListing(
        title="Software Engineer",
        company="Google",
        source="linkedin",
        url="http://google.com/job/1",
        location="Bangalore",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$150k",
        description="Google SWE role",
        posted_date=None,
        raw_text_hash="hash_google"
    )
    job_msft = JobListing(
        title="Software Engineer",
        company="Microsoft",
        source="indeed",
        url="http://microsoft.com/job/2",
        location="Bangalore",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$140k",
        description="Microsoft SWE role",
        posted_date=None,
        raw_text_hash="hash_msft"
    )
    merged_diff_companies = _dedupe_merge_impl([job_google, job_msft])
    assert len(merged_diff_companies) == 2

    # 2. Same company but distinctly different titles -> NOT merged
    job_stripe_swe = JobListing(
        title="Software Engineer",
        company="Stripe",
        source="web",
        url="http://stripe.com/job/swe",
        location="Remote",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$160k",
        description="Stripe SWE",
        posted_date=None,
        raw_text_hash="hash_stripe_1"
    )
    job_stripe_data = JobListing(
        title="Data Scientist",
        company="Stripe",
        source="web",
        url="http://stripe.com/job/ds",
        location="Remote",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$160k",
        description="Stripe DS",
        posted_date=None,
        raw_text_hash="hash_stripe_2"
    )
    merged_diff_titles = _dedupe_merge_impl([job_stripe_swe, job_stripe_data])
    assert len(merged_diff_titles) == 2

    # 3. Web-discovery jobs without known company ("Unknown") with different URLs -> NOT merged
    job_unknown_1 = JobListing(
        title="Frontend Developer",
        company="Unknown",
        source="web",
        url="http://startupa.com/careers/1",
        location="Remote",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$100k",
        description="Startup A frontend role",
        posted_date=None,
        raw_text_hash="hash_unknown_1"
    )
    job_unknown_2 = JobListing(
        title="Frontend Developer",
        company="Unknown",
        source="web",
        url="http://startupb.com/careers/2",
        location="Remote",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$100k",
        description="Startup B frontend role",
        posted_date=None,
        raw_text_hash="hash_unknown_2"
    )
    merged_unknowns = _dedupe_merge_impl([job_unknown_1, job_unknown_2])
    assert len(merged_unknowns) == 2, "Unrelated jobs with Unknown company must not be incorrectly merged"

    # 4. Web-discovery jobs with exact same URL -> Deduplicated, longer description kept
    job_dup_url_short = JobListing(
        title="Frontend Developer",
        company="Unknown",
        source="web",
        url="http://startupa.com/careers/1",
        location="Remote",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$100k",
        description="Short description",
        posted_date=None,
        raw_text_hash="hash_unknown_url_1"
    )
    job_dup_url_long = JobListing(
        title="Frontend Developer",
        company="Unknown",
        source="web",
        url="http://startupa.com/careers/1",
        location="Remote",
        work_mode=WorkMode.remote,
        job_type=JobType.permanent,
        stipend_or_salary="$100k",
        description="Detailed long description of the frontend developer position",
        posted_date=None,
        raw_text_hash="hash_unknown_url_2"
    )
    merged_same_url = _dedupe_merge_impl([job_dup_url_short, job_dup_url_long])
    assert len(merged_same_url) == 1
    assert merged_same_url[0].description == "Detailed long description of the frontend developer position"


def test_extract_company_from_web_result() -> None:
    from sub_agents.job_discovery_agent.tools import extract_company_from_web_result

    # ATS URLs
    assert extract_company_from_web_result("Software Engineer", "https://jobs.lever.co/stripe/abc-123") == "Stripe"
    assert extract_company_from_web_result("Data Analyst", "https://boards.greenhouse.io/airbnb/jobs/456") == "Airbnb"
    assert extract_company_from_web_result("AI Researcher", "https://jobs.ashbyhq.com/openai/789") == "Openai"
    assert extract_company_from_web_result("Cloud Engineer", "https://salesforce.myworkdayjobs.com/en-US/Careers") == "Salesforce"

    # Title patterns
    assert extract_company_from_web_result("Software Engineer at Netflix", "https://example.com/job1") == "Netflix"
    assert extract_company_from_web_result("Senior ML Scientist @ Anthropic", "https://example.com/job2") == "Anthropic"
    assert extract_company_from_web_result("Frontend Architect | Vercel", "https://example.com/job3") == "Vercel"
    assert extract_company_from_web_result("Databricks - Systems Engineer", "https://example.com/job4") == "Databricks"

    # Unidentifiable -> "Unknown" (no fake placeholder like "Web Discovery (Various)")
    assert extract_company_from_web_result("Hiring Python Developers Immediately", "https://jobboard.com/post/999") == "Unknown"
    assert extract_company_from_web_result("", "") == "Unknown"


def test_sha256_job_hashing() -> None:
    from schemas.job_listing import compute_job_hash, compute_raw_text_hash
    import re

    # 1. Deterministic: same content -> same 64-char hex hash
    hash1 = compute_job_hash(
        title="Software Engineer",
        company="Google",
        location="Bangalore",
        url="http://google.com/job/1",
        description="Build scalable distributed systems."
    )
    hash2 = compute_job_hash(
        title="Software Engineer",
        company="Google",
        location="Bangalore",
        url="http://google.com/job/1",
        description="Build scalable distributed systems."
    )
    assert hash1 == hash2
    assert len(hash1) == 64
    assert re.match(r"^[0-9a-f]{64}$", hash1)

    # 2. Whitespace normalization: extra spacing does not alter hash
    hash3 = compute_job_hash(
        title="  Software   Engineer  ",
        company=" Google ",
        location="Bangalore\n",
        url="http://google.com/job/1",
        description="Build   scalable   distributed   systems."
    )
    assert hash1 == hash3

    # 3. Different content -> different hash
    hash_diff_title = compute_job_hash(
        title="Senior Software Engineer",
        company="Google",
        location="Bangalore",
        url="http://google.com/job/1",
        description="Build scalable distributed systems."
    )
    assert hash1 != hash_diff_title

    hash_diff_company = compute_job_hash(
        title="Software Engineer",
        company="Microsoft",
        location="Bangalore",
        url="http://google.com/job/1",
        description="Build scalable distributed systems."
    )
    assert hash1 != hash_diff_company

    # 4. compute_raw_text_hash validity
    raw_hash = compute_raw_text_hash("Sample job posting text")
    assert len(raw_hash) == 64
    assert re.match(r"^[0-9a-f]{64}$", raw_hash)


@pytest.mark.asyncio
async def test_scraper_failure_behavior_and_graceful_handling(dummy_preferences: Preferences) -> None:
    from sub_agents.job_discovery_agent.tools import _search_linkedin_impl
    
    with patch("services.scrapers.linkedin_scraper.search", side_effect=RuntimeError("Browser launch failed")):
        # Must fail gracefully, return empty list, not crash or fabricate jobs
        results = await _search_linkedin_impl("python", dummy_preferences.model_dump())
        assert results == []

