import pytest
import logging
from unittest.mock import patch, MagicMock

class DummyAPIError(Exception):
    def __init__(self, code):
        super().__init__(f"Error code {code}")
        self.code = code

@patch("services.search_router.APIError", DummyAPIError)
@patch("services.search_router.google_search")
@patch("services.search_router.DDGS")
def test_search_router_fallback(mock_ddgs_class, mock_google_search, caplog):
    from services.search_router import search_web
    
    # Setup mock primary error
    error = DummyAPIError(code=429)
    mock_google_search.side_effect = error
    
    # Setup mock DDGS
    mock_ddgs_instance = MagicMock()
    mock_ddgs_class.return_value = mock_ddgs_instance
    mock_ddgs_instance.text.return_value = [
        {"title": "DDG Title", "href": "http://ddg.com", "body": "DDG Snippet"}
    ]
    
    with caplog.at_level(logging.WARNING):
        results = search_web("test query", max_results=1)
        
    assert len(results) == 1
    assert results[0] == {
        "title": "DDG Title",
        "url": "http://ddg.com",
        "snippet": "DDG Snippet"
    }
    assert "Gemini quota exhausted, falling back to DuckDuckGo search" in caplog.text
    mock_ddgs_instance.text.assert_called_once_with("test query", max_results=1)
