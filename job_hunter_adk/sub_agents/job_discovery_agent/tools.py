import asyncio
from rapidfuzz import fuzz
from schemas.preferences import Preferences
from schemas.job_listing import JobListing
from services.search_router import search_web
from services.scrapers import linkedin_scraper, naukri_scraper, internshala_scraper, indeed_scraper
from google.adk.tools import FunctionTool


async def _search_linkedin_impl(query: str, preferences: dict) -> list[dict]:
    """Search LinkedIn for jobs based on query and preferences."""
    prefs = Preferences.model_validate(preferences)
    return [r.model_dump() for r in await linkedin_scraper.search(query, prefs)]

search_linkedin = FunctionTool(func=_search_linkedin_impl)


async def _search_naukri_impl(query: str, preferences: dict) -> list[dict]:
    """Search Naukri for jobs based on query and preferences."""
    prefs = Preferences.model_validate(preferences)
    return [r.model_dump() for r in await naukri_scraper.search(query, prefs)]

search_naukri = FunctionTool(func=_search_naukri_impl)


async def _search_internshala_impl(query: str, preferences: dict) -> list[dict]:
    """Search Internshala for jobs based on query and preferences."""
    prefs = Preferences.model_validate(preferences)
    return [r.model_dump() for r in await internshala_scraper.search(query, prefs)]

search_internshala = FunctionTool(func=_search_internshala_impl)


async def _search_indeed_impl(query: str, preferences: dict) -> list[dict]:
    """Search Indeed for jobs based on query and preferences."""
    prefs = Preferences.model_validate(preferences)
    return [r.model_dump() for r in await indeed_scraper.search(query, prefs)]

search_indeed = FunctionTool(func=_search_indeed_impl)


async def _web_discovery_impl(query: str, preferences: dict) -> list[dict]:
    """
    Finds job postings on the open web (e.g. company career pages, campus placements)
    by running multiple targeted search queries concurrently.
    """
    prefs = Preferences.model_validate(preferences)
    loc = prefs.locations[0] if prefs.locations else ""
    queries = [
        f"{query} careers {loc}".strip(),
        f"{query} {prefs.job_type.value} opportunities {loc}".strip(),
        f"site:lever.co OR site:greenhouse.io {query} {loc}".strip()
    ]
    
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, search_web, q, 5)
        for q in queries
    ]
    
    results = []
    for f in asyncio.as_completed(tasks):
        try:
            search_results = await f
            for r in search_results:
                results.append(JobListing(
                    title=r.get("title", "Unknown"),
                    company="Web Discovery (Various)",
                    source="web",
                    url=r.get("url", ""),
                    location=loc or "Unknown",
                    work_mode=prefs.work_mode,
                    job_type=prefs.job_type,
                    stipend_or_salary=None,
                    description=r.get("snippet", ""),
                    posted_date=None,
                    raw_text_hash="hash_placeholder"
                ).model_dump())
        except Exception:
            pass
            
    return results

web_discovery = FunctionTool(func=_web_discovery_impl)


def _dedupe_merge_impl(listings: list[dict]) -> list[dict]:
    """
    Deduplicates a list of JobListing objects using fuzzy matching on company, title, and location.
    Retains the listing with the longer description.
    """
    job_listings = [JobListing.model_validate(job) for job in listings]
    merged = []
    for current in job_listings:
        is_duplicate = False
        for idx, existing in enumerate(merged):
            str1 = f"{current.company} {current.title} {current.location}".lower()
            str2 = f"{existing.company} {existing.title} {existing.location}".lower()
            
            similarity = fuzz.ratio(str1, str2)
            if similarity > 85: 
                is_duplicate = True
                desc1 = current.description or ""
                desc2 = existing.description or ""
                if len(desc1) > len(desc2):
                    merged[idx] = current
                break
        
        if not is_duplicate:
            merged.append(current)
            
    return [m.model_dump() for m in merged]

dedupe_merge = FunctionTool(func=_dedupe_merge_impl)
