"""
NOTE: Indeed heavily restricts automated access per their Terms of Service.
This scraper is a best-effort fallback layer, not to be called aggressively.
"""
import logging
from playwright.async_api import async_playwright
from schemas.preferences import Preferences
from schemas.job_listing import JobListing, clean_text, compute_job_hash
from services.rate_limiter import INDEED_LIMITER, with_retry_and_fallback

logger = logging.getLogger(__name__)

@with_retry_and_fallback(INDEED_LIMITER)
async def search(query: str, preferences: Preferences) -> list[JobListing]:
    logger.info(f"Searching Indeed for: {query}")
    results: list[JobListing] = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            
            loc = preferences.locations[0] if preferences.locations else ""
            search_url = f"https://www.indeed.com/jobs?q={query}&l={loc}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            
            job_cards = await page.locator(".job_seen_beacon").all()
            for card in job_cards[:5]:
                try:
                    title_el = card.locator(".jobTitle")
                    company_el = card.locator(".companyName, [data-testid='company-name']")
                    url_el = card.locator(".jcs-JobTitle")
                    loc_el = card.locator(".companyLocation, [data-testid='text-location']")
                    snippet_el = card.locator(".job-snippet, .jobCardShelfContainer")
                    salary_el = card.locator(".salary-snippet-container, .metadata.salary-snippet-container, .estimated-salary")
                    date_el = card.locator(".date, span.date")

                    title = clean_text(await title_el.text_content() if await title_el.count() > 0 else "")
                    company = clean_text(await company_el.text_content() if await company_el.count() > 0 else "")
                    url = clean_text(await url_el.get_attribute("href") if await url_el.count() > 0 else "")
                    card_loc = clean_text(await loc_el.text_content() if await loc_el.count() > 0 else "") or (loc or "Unknown")
                    description = clean_text(await snippet_el.first.text_content() if await snippet_el.count() > 0 else "")
                    salary = clean_text(await salary_el.first.text_content() if await salary_el.count() > 0 else "") or None
                    posted_date = clean_text(await date_el.first.text_content() if await date_el.count() > 0 else "") or None

                    if title and company and url:
                        full_url = f"https://www.indeed.com{url}" if url.startswith("/") else url
                        raw_hash = compute_job_hash(
                            title=title,
                            company=company,
                            location=card_loc,
                            url=full_url,
                            description=description
                        )
                        results.append(JobListing(
                            title=title,
                            company=company,
                            source="indeed",
                            url=full_url,
                            location=card_loc,
                            work_mode=preferences.work_mode,
                            job_type=preferences.job_type,
                            stipend_or_salary=salary,
                            description=description,
                            posted_date=posted_date,
                            raw_text_hash=raw_hash
                        ))
                except Exception as card_err:
                    logger.debug(f"Failed parsing individual Indeed card: {card_err}")
                    continue
        finally:
            await browser.close()
            
    return results
