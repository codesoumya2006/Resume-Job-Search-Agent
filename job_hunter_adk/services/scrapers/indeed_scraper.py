"""
NOTE: Indeed heavily restricts automated access per their Terms of Service.
This scraper is a best-effort fallback layer, not to be called aggressively.
"""
import logging
from playwright.async_api import async_playwright
from schemas.preferences import Preferences
from schemas.job_listing import JobListing
from services.rate_limiter import INDEED_LIMITER, with_retry_and_fallback

logger = logging.getLogger(__name__)

@with_retry_and_fallback(INDEED_LIMITER)
async def search(query: str, preferences: Preferences) -> list[JobListing]:
    logger.info(f"Searching Indeed for: {query}")
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        loc = preferences.locations[0] if preferences.locations else ""
        search_url = f"https://www.indeed.com/jobs?q={query}&l={loc}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        
        job_cards = await page.locator(".job_seen_beacon").all()
        for card in job_cards[:5]:
            title = await card.locator(".jobTitle").text_content()
            company = await card.locator(".companyName").text_content()
            url = await card.locator(".jcs-JobTitle").get_attribute("href")
            
            if title and company and url:
                full_url = f"https://www.indeed.com{url.strip()}" if url.startswith("/") else url.strip()
                results.append(JobListing(
                    title=title.strip(),
                    company=company.strip(),
                    source="indeed",
                    url=full_url,
                    location=loc,
                    work_mode=preferences.work_mode,
                    job_type=preferences.job_type,
                    stipend_or_salary=None,
                    description="[Description pending]",
                    posted_date=None,
                    raw_text_hash="hash_placeholder"
                ))
        await browser.close()
        
    return results
