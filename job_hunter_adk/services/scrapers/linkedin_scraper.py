"""
NOTE: LinkedIn strictly restricts automated access and scraping per their Terms of Service.
This scraper is a best-effort, minimal fallback layer demonstrating playwright capabilities
and should NOT be used aggressively or in production without appropriate enterprise APIs.
"""
import logging
from playwright.async_api import async_playwright
from schemas.preferences import Preferences
from schemas.job_listing import JobListing
from services.rate_limiter import LINKEDIN_LIMITER, with_retry_and_fallback

logger = logging.getLogger(__name__)

@with_retry_and_fallback(LINKEDIN_LIMITER)
async def search(query: str, preferences: Preferences) -> list[JobListing]:
    logger.info(f"Searching LinkedIn for: {query}")
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        loc = preferences.locations[0] if preferences.locations else ""
        search_url = f"https://www.linkedin.com/jobs/search?keywords={query}&location={loc}"
        
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        
        job_cards = await page.locator(".job-search-card").all()
        for card in job_cards[:5]:
            title = await card.locator(".base-search-card__title").text_content()
            company = await card.locator(".base-search-card__subtitle").text_content()
            url = await card.locator("a.base-card__full-link").get_attribute("href")
            location = await card.locator(".job-search-card__location").text_content()
            
            if title and company and url:
                results.append(JobListing(
                    title=title.strip(),
                    company=company.strip(),
                    source="linkedin",
                    url=url.strip(),
                    location=location.strip() if location else "Unknown",
                    work_mode=preferences.work_mode,
                    job_type=preferences.job_type,
                    stipend_or_salary=None,
                    description="[Description omitted for rate limits]",
                    posted_date=None,
                    raw_text_hash="hash_placeholder"
                ))
                
        await browser.close()
        
    return results
