import json
import logging
import asyncio
from schemas.company_intel import ReviewSummary
from services.search_router import search_web
from services.scrapers import glassdoor_scraper
from services.model_router import get_model

try:
    from google.adk.tools import FunctionTool
except ImportError:
    class FunctionTool:
        def __init__(self, func):
            self.func = func

logger = logging.getLogger(__name__)

async def _company_website_lookup_impl(company_name: str) -> dict:
    """Fetch and summarize the official site."""
    results = await asyncio.to_thread(search_web, f"{company_name} official website", 2)
    if results:
        return {"website": results[0].get("url", ""), "snippet": results[0].get("snippet", "")}
    return {}

company_website_lookup = FunctionTool(func=_company_website_lookup_impl)

async def _news_search_impl(company_name: str) -> list[str]:
    """Recent news headlines via search_web()."""
    results = await asyncio.to_thread(search_web, f"{company_name} news recent", 5)
    return [r.get("title", "") for r in results]

news_search = FunctionTool(func=_news_search_impl)

async def _financial_snapshot_impl(company_name: str) -> str | None:
    """Brief funding/financials if public, None if not findable."""
    results = await asyncio.to_thread(search_web, f"{company_name} revenue funding financials", 3)
    if results:
        return " ".join([r.get("snippet", "") for r in results])
    return None

financial_snapshot = FunctionTool(func=_financial_snapshot_impl)

async def _glassdoor_reviews_impl(company_name: str) -> list[ReviewSummary]:
    """Wrapper around rate-limited glassdoor scraper."""
    return await glassdoor_scraper.search(company_name)

glassdoor_reviews = FunctionTool(func=_glassdoor_reviews_impl)

async def _community_reviews_impl(company_name: str) -> list[ReviewSummary]:
    """Search Reddit/Quora/Blind for candid intern/employee mentions."""
    results = await asyncio.to_thread(search_web, f"{company_name} working culture site:reddit.com OR site:quora.com OR site:teamblind.com", 5)
    reviews = []
    for r in results:
        url = r.get("url", "")
        source = "reddit"
        if "quora.com" in url: source = "quora"
        elif "teamblind.com" in url: source = "blind"
        reviews.append(ReviewSummary(source=source, sentiment="neutral", summary=r.get("snippet", "")))
    return reviews

community_reviews = FunctionTool(func=_community_reviews_impl)

def _summarize_sentiment_impl(reviews: list[ReviewSummary]) -> list[ReviewSummary]:
    """Collapse many raw review snippets into a handful of sentiment-labeled summaries."""
    if not reviews:
        return []
    
    model = get_model()
    prompt = f"""
    You are an expert sentiment analyst. Condense the following raw reviews into a handful of distinct, sentiment-labeled summaries.
    Return ONLY valid JSON as a list of ReviewSummary objects. Do not invent information.
    
    Schema:
    {ReviewSummary.model_json_schema()}
    
    Raw Reviews:
    {[r.model_dump() for r in reviews]}
    """
    
    try:
        response = model.generate(prompt)
        text = response.text if hasattr(response, 'text') else str(response)
        
        import re
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        data = json.loads(text)
        return [ReviewSummary(**item) for item in data]
    except Exception as e:
        logger.error(f"Failed to summarize sentiment: {e}")
        return [ReviewSummary(source="reddit", sentiment="neutral", summary="Mixed reviews regarding work environment.")]

summarize_sentiment = FunctionTool(func=_summarize_sentiment_impl)
