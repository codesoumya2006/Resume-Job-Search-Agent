"""
NOTE: LinkedIn strictly restricts automated access and scraping per their Terms of Service.
This scraper is a best-effort, minimal fallback layer demonstrating playwright capabilities
and should NOT be used aggressively or in production without appropriate enterprise APIs.
"""
import logging
from playwright.async_api import async_playwright
from schemas.preferences import Preferences
from schemas.job_listing import JobListing, clean_text, compute_job_hash
from services.rate_limiter import LINKEDIN_LIMITER, with_retry_and_fallback

logger = logging.getLogger(__name__)

@with_retry_and_fallback(LINKEDIN_LIMITER)
async def search(query: str, preferences: Preferences) -> list[JobListing]:
    logger.info(f"Searching LinkedIn for: {query}")
    results: list[JobListing] = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            loc = preferences.locations[0] if preferences.locations else ""
            search_url = f"https://www.linkedin.com/jobs/search?keywords={query}&location={loc}"
            
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            
            job_cards = await page.locator(".job-search-card, .base-search-card").all()
            for card in job_cards[:5]:
                try:
                    title_el = card.locator(".base-search-card__title")
                    company_el = card.locator(".base-search-card__subtitle")
                    url_el = card.locator("a.base-card__full-link")
                    location_el = card.locator(".job-search-card__location")
                    snippet_el = card.locator(".job-search-card__snippet, .base-search-card__metadata, .job-result-card__snippet")
                    salary_el = card.locator(".job-search-card__salary-info")
                    time_el = card.locator("time")

                    title = clean_text(await title_el.text_content() if await title_el.count() > 0 else "")
                    company = clean_text(await company_el.text_content() if await company_el.count() > 0 else "")
                    url = clean_text(await url_el.get_attribute("href") if await url_el.count() > 0 else "")
                    location = clean_text(await location_el.text_content() if await location_el.count() > 0 else "") or (loc or "Unknown")
                    
                    description = clean_text(await snippet_el.first.text_content() if await snippet_el.count() > 0 else "")
                    salary = clean_text(await salary_el.first.text_content() if await salary_el.count() > 0 else "") or None
                    posted_date = None
                    if await time_el.count() > 0:
                        posted_date = clean_text(await time_el.first.get_attribute("datetime") or await time_el.first.text_content()) or None

                    if title and company and url:
                        raw_hash = compute_job_hash(
                            title=title,
                            company=company,
                            location=location,
                            url=url,
                            description=description
                        )
                        results.append(JobListing(
                            title=title,
                            company=company,
                            source="linkedin",
                            url=url,
                            location=location,
                            work_mode=preferences.work_mode,
                            job_type=preferences.job_type,
                            stipend_or_salary=salary,
                            description=description,
                            posted_date=posted_date,
                            raw_text_hash=raw_hash
                        ))
                except Exception as card_err:
                    logger.debug(f"Failed parsing individual LinkedIn card: {card_err}")
                    continue
        finally:
            await browser.close()
            
    return results
