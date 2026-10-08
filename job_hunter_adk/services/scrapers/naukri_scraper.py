"""
NOTE: Naukri restricts automated access per their Terms of Service.
This scraper is a best-effort fallback layer, not to be called aggressively.
"""
import logging
from playwright.async_api import async_playwright
from schemas.preferences import Preferences
from schemas.job_listing import JobListing, clean_text, compute_job_hash
from services.rate_limiter import NAUKRI_LIMITER, with_retry_and_fallback

logger = logging.getLogger(__name__)

@with_retry_and_fallback(NAUKRI_LIMITER)
async def search(query: str, preferences: Preferences) -> list[JobListing]:
    logger.info(f"Searching Naukri for: {query}")
    results: list[JobListing] = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            
            search_url = f"https://www.naukri.com/{query.replace(' ', '-')}-jobs"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            
            job_cards = await page.locator(".jobTuple, .srp-jobtuple-wrapper").all()
            for card in job_cards[:5]:
                try:
                    title_el = card.locator(".title")
                    company_el = card.locator(".companyInfo a, .comp-name")
                    url_el = card.locator(".title")
                    loc_el = card.locator(".loc-wrap, .location")
                    snippet_el = card.locator(".job-desc, .job-description, .ellipsis.job-description, .row6")
                    salary_el = card.locator(".salary, .sal-wrap")
                    
                    title = clean_text(await title_el.text_content() if await title_el.count() > 0 else "")
                    company = clean_text(await company_el.first.text_content() if await company_el.count() > 0 else "")
                    url = clean_text(await url_el.get_attribute("href") if await url_el.count() > 0 else "")
                    loc = clean_text(await loc_el.first.text_content() if await loc_el.count() > 0 else "") or (preferences.locations[0] if preferences.locations else "India")
                    description = clean_text(await snippet_el.first.text_content() if await snippet_el.count() > 0 else "")
                    salary = clean_text(await salary_el.first.text_content() if await salary_el.count() > 0 else "") or None
                    
                    if title and company and url:
                        raw_hash = compute_job_hash(
                            title=title,
                            company=company,
                            location=loc,
                            url=url,
                            description=description
                        )
                        results.append(JobListing(
                            title=title,
                            company=company,
                            source="naukri",
                            url=url,
                            location=loc,
                            work_mode=preferences.work_mode,
                            job_type=preferences.job_type,
                            stipend_or_salary=salary,
                            description=description,
                            posted_date=None,
                            raw_text_hash=raw_hash
                        ))
                except Exception as card_err:
                    logger.debug(f"Failed parsing individual Naukri card: {card_err}")
                    continue
        finally:
            await browser.close()
            
    return results
