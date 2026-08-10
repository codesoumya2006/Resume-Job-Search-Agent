import pytest
from unittest.mock import patch, AsyncMock
from schemas.preferences import Preferences, JobType, WorkMode
from schemas.job_listing import JobListing
from sub_agents.job_discovery_agent.tools import dedupe_merge

@pytest.fixture
def dummy_preferences():
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
    mock_internshala, mock_naukri, mock_indeed, mock_linkedin, dummy_preferences
):
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
