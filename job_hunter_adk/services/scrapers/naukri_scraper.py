"""
NOTE: Naukri restricts automated access per their Terms of Service.
This scraper is a best-effort fallback layer, not to be called aggressively.
"""
import logging
from playwright.async_api import async_playwright
from schemas.preferences import Preferences
from schemas.job_listing import JobListing
from services.rate_limiter import NAUKRI_LIMITER, with_retry_and_fallback

logger = logging.getLogger(__name__)

@with_retry_and_fallback(NAUKRI_LIMITER)
async def search(query: str, preferences: Preferences) -> list[JobListing]:
    logger.info(f"Searching Naukri for: {query}")
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        search_url = f"https://www.naukri.com/{query.replace(' ', '-')}-jobs"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        
        job_cards = await page.locator(".jobTuple").all()
        for card in job_cards[:5]:
            title = await card.locator(".title").text_content()
            company = await card.locator(".companyInfo a").first.text_content()
            url = await card.locator(".title").get_attribute("href")
            
            if title and company and url:
                results.append(JobListing(
                    title=title.strip(),
                    company=company.strip(),
                    source="naukri",
                    url=url.strip(),
                    location=preferences.locations[0] if preferences.locations else "India",
                    work_mode=preferences.work_mode,
                    job_type=preferences.job_type,
                    stipend_or_salary=None,
                    description="[Description pending]",
                    posted_date=None,
                    raw_text_hash="hash_placeholder"
                ))
        await browser.close()
        
    return results
