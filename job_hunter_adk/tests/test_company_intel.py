import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from schemas.company_intel import CompanyIntel, ReviewSummary
from sub_agents.company_intel_agent.tools import (
    _company_website_lookup_impl,
    _news_search_impl,
    _financial_snapshot_impl,
    _glassdoor_reviews_impl,
    _community_reviews_impl,
    _summarize_sentiment_impl
)

@pytest.mark.asyncio
@patch('sub_agents.company_intel_agent.tools.search_web', new_callable=MagicMock)
@patch('services.scrapers.glassdoor_scraper.search', new_callable=AsyncMock)
async def test_company_intel_tools(mock_glassdoor, mock_search):
    # Setup mocks
    mock_search.return_value = [
        {"url": "http://apple.com", "snippet": "Tech company", "title": "Apple News"}
    ]
    mock_glassdoor.return_value = [
        ReviewSummary(source="glassdoor", sentiment="neutral", summary="Good pay.")
    ]
    
    # Run each tool
    web = await _company_website_lookup_impl("Apple")
    news = await _news_search_impl("Apple")
    fin = await _financial_snapshot_impl("Apple")
    gd = await _glassdoor_reviews_impl("Apple")
    cr = await _community_reviews_impl("Apple")
    
    # Assert tool results
    assert "apple.com" in web["website"]
    assert len(news) == 1
    assert news[0] == "Apple News"
    assert fin == "Tech company"
    assert len(gd) == 1
    assert len(cr) == 1
    assert cr[0].source in ["reddit", "quora", "blind"]
    
    # Test summarize_sentiment using mock model
    with patch('sub_agents.company_intel_agent.tools.get_model') as mock_get_model:
        class DummyResponse:
            text = '''
            [
              {"source": "glassdoor", "sentiment": "positive", "summary": "Great pay."}
            ]
            '''
        
        mock_get_model.return_value.generate.return_value = DummyResponse()
        
        summarized = _summarize_sentiment_impl(gd + cr)
        assert len(summarized) == 1
        assert summarized[0].sentiment == "positive"
        assert summarized[0].summary == "Great pay."
        
    # Test CompanyIntel Pydantic model validation
    intel = CompanyIntel(
        company_name="Apple",
        website=web["website"],
        recent_news=news,
        financial_snapshot=fin,
        reviews=summarized
    )
    
    assert intel.company_name == "Apple"
    assert len(intel.recent_news) == 1
    assert len(intel.reviews) == 1
