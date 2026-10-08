"""
NOTE: Internshala restricts automated access per their Terms of Service.
This scraper is a best-effort fallback layer, not to be called aggressively.
"""
import logging
from playwright.async_api import async_playwright
from schemas.preferences import Preferences
from schemas.job_listing import JobListing, clean_text, compute_job_hash
from services.rate_limiter import INTERNSHALA_LIMITER, with_retry_and_fallback

logger = logging.getLogger(__name__)

@with_retry_and_fallback(INTERNSHALA_LIMITER)
async def search(query: str, preferences: Preferences) -> list[JobListing]:
    logger.info(f"Searching Internshala for: {query}")
    results: list[JobListing] = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            
            search_url = f"https://internshala.com/internships/keywords-{query.replace(' ', '%20')}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            
            job_cards = await page.locator(".internship_meta, .individual_internship").all()
            for card in job_cards[:5]:
                try:
                    title_el = card.locator(".profile a, .job-title-href")
                    company_el = card.locator(".company_name a, .company-name")
                    url_el = card.locator(".profile a, .job-title-href")
                    loc_el = card.locator("#location_names a, .location_link, .locations")
                    snippet_el = card.locator(".internship_details, .other_detail_item, .job_description")
                    stipend_el = card.locator(".stipend")
                    
                    title = clean_text(await title_el.first.text_content() if await title_el.count() > 0 else "")
                    company = clean_text(await company_el.first.text_content() if await company_el.count() > 0 else "")
                    url = clean_text(await url_el.first.get_attribute("href") if await url_el.count() > 0 else "")
                    loc = clean_text(await loc_el.first.text_content() if await loc_el.count() > 0 else "") or (preferences.locations[0] if preferences.locations else "India")
                    description = clean_text(await snippet_el.first.text_content() if await snippet_el.count() > 0 else "")
                    stipend = clean_text(await stipend_el.first.text_content() if await stipend_el.count() > 0 else "") or None
                    
                    if title and company and url:
                        full_url = f"https://internshala.com{url}" if url.startswith("/") else url
                        raw_hash = compute_job_hash(
                            title=title,
                            company=company,
                            location=loc,
                            url=full_url,
                            description=description
                        )
                        results.append(JobListing(
                            title=title,
                            company=company,
                            source="internshala",
                            url=full_url,
                            location=loc,
                            work_mode=preferences.work_mode,
                            job_type=preferences.job_type,
                            stipend_or_salary=stipend,
                            description=description,
                            posted_date=None,
                            raw_text_hash=raw_hash
                        ))
                except Exception as card_err:
                    logger.debug(f"Failed parsing individual Internshala card: {card_err}")
                    continue
        finally:
            await browser.close()
            
    return results
