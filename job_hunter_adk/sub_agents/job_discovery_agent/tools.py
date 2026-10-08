import asyncio
import logging
import re
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse
from rapidfuzz import fuzz
from schemas.preferences import Preferences
from schemas.job_listing import JobListing, clean_text, compute_job_hash
from services.search_router import search_web
from services.scrapers import linkedin_scraper, naukri_scraper, internshala_scraper, indeed_scraper
from google.adk.tools import FunctionTool, ToolContext

logger = logging.getLogger(__name__)


def extract_company_from_web_result(title: str, url: str) -> str:
    """
    Attempts to extract a company name from an ATS URL or search result title.
    Returns 'Unknown' if company identity cannot be reliably determined.
    """
    # 1. Check known ATS URL patterns
    if url:
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            
            if "lever.co" in netloc and path_parts:
                return path_parts[0].replace("-", " ").title()
            if "greenhouse.io" in netloc and path_parts:
                return path_parts[0].replace("-", " ").title()
            if "ashbyhq.com" in netloc and path_parts:
                return path_parts[0].replace("-", " ").title()
            if "myworkdayjobs.com" in netloc:
                subdomain = netloc.split(".")[0]
                if subdomain and subdomain != "jobs":
                    return subdomain.replace("-", " ").title()
        except Exception:
            pass

    # 2. Check title patterns like "Role at Company", "Role @ Company", "Role | Company", "Company - Role"
    if title:
        # Match "Role at Company" or "Role @ Company"
        m = re.search(r'(?:\bat\b|@)\s+([A-Z0-9][A-Za-z0-9\s&.,\'\-]+)', title)
        if m:
            comp = clean_text(m.group(1))
            comp = re.sub(r'[\-|–|—|\|].*$', '', comp).strip()
            if comp and len(comp) < 40:
                return comp

        # Match "Company - Role" or "Role - Company" or "Role | Company"
        for sep in [" | ", " - ", " – ", " — "]:
            if sep in title:
                parts = title.split(sep)
                if len(parts) == 2:
                    p0 = clean_text(parts[0])
                    p1 = clean_text(parts[1])
                    role_keywords = ["engineer", "developer", "intern", "scientist", "manager", "analyst", "designer", "architect", "lead", "specialist"]
                    p0_is_role = any(kw in p0.lower() for kw in role_keywords)
                    p1_is_role = any(kw in p1.lower() for kw in role_keywords)
                    if p0_is_role and not p1_is_role and len(p1) < 40:
                        return p1
                    elif p1_is_role and not p0_is_role and len(p0) < 40:
                        return p0

    return "Unknown"


async def _search_linkedin_impl(query: str, preferences: dict[str, Any]) -> list[dict[str, Any]]:
    """Search LinkedIn for jobs based on query and preferences."""
    try:
        prefs = Preferences.model_validate(preferences)
        results = await linkedin_scraper.search(query, prefs)
        return [r.model_dump() for r in results]
    except Exception as e:
        logger.error(f"LinkedIn search failed: {e}", exc_info=True)
        return []

search_linkedin = FunctionTool(func=_search_linkedin_impl)


async def _search_naukri_impl(query: str, preferences: dict[str, Any]) -> list[dict[str, Any]]:
    """Search Naukri for jobs based on query and preferences."""
    try:
        prefs = Preferences.model_validate(preferences)
        results = await naukri_scraper.search(query, prefs)
        return [r.model_dump() for r in results]
    except Exception as e:
        logger.error(f"Naukri search failed: {e}", exc_info=True)
        return []

search_naukri = FunctionTool(func=_search_naukri_impl)


async def _search_internshala_impl(query: str, preferences: dict[str, Any]) -> list[dict[str, Any]]:
    """Search Internshala for jobs based on query and preferences."""
    try:
        prefs = Preferences.model_validate(preferences)
        results = await internshala_scraper.search(query, prefs)
        return [r.model_dump() for r in results]
    except Exception as e:
        logger.error(f"Internshala search failed: {e}", exc_info=True)
        return []

search_internshala = FunctionTool(func=_search_internshala_impl)


async def _search_indeed_impl(query: str, preferences: dict[str, Any]) -> list[dict[str, Any]]:
    """Search Indeed for jobs based on query and preferences."""
    try:
        prefs = Preferences.model_validate(preferences)
        results = await indeed_scraper.search(query, prefs)
        return [r.model_dump() for r in results]
    except Exception as e:
        logger.error(f"Indeed search failed: {e}", exc_info=True)
        return []

search_indeed = FunctionTool(func=_search_indeed_impl)


async def _web_discovery_impl(query: str, preferences: dict[str, Any]) -> list[dict[str, Any]]:
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
    
    results: list[dict[str, Any]] = []
    for f in asyncio.as_completed(tasks):
        try:
            search_results = await f
            for r in search_results:
                title = clean_text(r.get("title", "")) or "Unknown"
                url = clean_text(r.get("url", ""))
                snippet = clean_text(r.get("snippet", ""))
                company = extract_company_from_web_result(title, url)
                job_loc = loc or "Unknown"
                job_hash = compute_job_hash(
                    title=title,
                    company=company,
                    location=job_loc,
                    url=url,
                    description=snippet
                )
                results.append(JobListing(
                    title=title,
                    company=company,
                    source="web",
                    url=url,
                    location=job_loc,
                    work_mode=prefs.work_mode,
                    job_type=prefs.job_type,
                    stipend_or_salary=None,
                    description=snippet,
                    posted_date=None,
                    raw_text_hash=job_hash
                ).model_dump())
        except Exception as e:
            logger.error(f"Web discovery search task failed: {e}", exc_info=True)
            
    return results

web_discovery = FunctionTool(func=_web_discovery_impl)


def _is_duplicate_listing(current: JobListing, existing: JobListing) -> bool:
    """
    Determines if two JobListing records represent the same job.
    Uses URL, raw text hash, and fuzzy matching on company, title, and location.
    Does NOT incorrectly merge unrelated jobs that share a placeholder/unknown company.
    """
    # 1. Exact non-empty URL match
    if current.url and existing.url and current.url.strip() == existing.url.strip():
        return True

    # 2. Exact non-empty raw content hash match
    if current.raw_text_hash and existing.raw_text_hash and current.raw_text_hash == existing.raw_text_hash:
        return True

    c1 = clean_text(current.company).lower()
    c2 = clean_text(existing.company).lower()
    unknown_companies = {"", "unknown", "n/a", "none", "web discovery (various)", "various"}
    c1_unknown = c1 in unknown_companies
    c2_unknown = c2 in unknown_companies

    # If either company is unknown or placeholder, do not merge without exact URL/hash
    if c1_unknown or c2_unknown:
        return False

    # Both companies are known: check company similarity
    company_sim = fuzz.ratio(c1, c2)
    if company_sim < 80:
        return False

    # Check title similarity
    t1 = clean_text(current.title).lower()
    t2 = clean_text(existing.title).lower()
    title_sim = fuzz.ratio(t1, t2)
    if title_sim < 80:
        return False

    # Check location similarity if both are known and non-empty
    l1 = clean_text(current.location).lower()
    l2 = clean_text(existing.location).lower()
    if l1 and l2 and l1 != "unknown" and l2 != "unknown":
        loc_sim = fuzz.token_set_ratio(l1, l2)
        if loc_sim < 60:
            return False

    # Overall string similarity check
    str1 = f"{c1} {t1} {l1}"
    str2 = f"{c2} {t2} {l2}"
    return fuzz.ratio(str1, str2) > 75


def _dedupe_merge_impl(
    listings: list[dict[str, Any]],
    tool_context: ToolContext | None = None
) -> list[JobListing]:
    """
    Deduplicates a list of JobListing objects using reliable identifying information
    (URL, hash, and fuzzy matching on company, title, and location).
    Retains the listing with the longer description.
    """
    flat_listings: list[Any] = []
    for item in listings:
        if isinstance(item, list):
            flat_listings.extend(item)
        else:
            flat_listings.append(item)

    job_listings = [
        job if isinstance(job, JobListing) else JobListing.model_validate(job)
        for job in flat_listings
    ]
    merged: list[JobListing] = []
    for current in job_listings:
        is_duplicate = False
        for idx, existing in enumerate(merged):
            if _is_duplicate_listing(current, existing):
                is_duplicate = True
                desc1 = current.description or ""
                desc2 = existing.description or ""
                if len(desc1) > len(desc2):
                    merged[idx] = current
                break
        
        if not is_duplicate:
            merged.append(current)
            
    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["discovered_jobs"] = [m.model_dump() for m in merged]

    return merged

dedupe_merge = FunctionTool(func=_dedupe_merge_impl)

