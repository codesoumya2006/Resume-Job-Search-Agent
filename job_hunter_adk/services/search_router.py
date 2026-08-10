import logging
from google.genai.errors import APIError
from ddgs import DDGS

logger = logging.getLogger(__name__)

# Fallback import for google_search just in case it's missing in some adk versions
try:
    from google.adk.tools import google_search
except ImportError:
    # Dummy mock if not found, to allow tests to run without the exact ADK import path
    def google_search(*args, **kwargs):
        raise NotImplementedError("google_search not found in google.adk.tools")

def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using Gemini-grounded search as the primary,
    and DuckDuckGo (via ddgs) as the fallback on quota errors.
    """
    try:
        results = google_search(query, max_results=max_results)
        
        normalized = []
        for r in results:
            if isinstance(r, dict):
                normalized.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", r.get("link", "")),
                    "snippet": r.get("snippet", "")
                })
            else:
                normalized.append({
                    "title": getattr(r, "title", ""),
                    "url": getattr(r, "url", getattr(r, "link", "")),
                    "snippet": getattr(r, "snippet", "")
                })
        return normalized

    except APIError as e:
        if getattr(e, "code", None) == 429:
            logger.warning("Gemini quota exhausted, falling back to DuckDuckGo search")
            return _ddgs_search(query, max_results)
        raise

def _ddgs_search(query: str, max_results: int) -> list[dict]:
    normalized = []
    # DuckDuckGo search via ddgs
    ddgs = DDGS()
    results = ddgs.text(query, max_results=max_results)
    if results:
        for r in results:
            normalized.append({
                "title": r.get("title", ""),
                "url": r.get("href", r.get("url", "")),
                "snippet": r.get("body", "")
            })
    return normalized
