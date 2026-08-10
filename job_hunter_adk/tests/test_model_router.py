import pytest
import logging
from unittest.mock import MagicMock, patch

class DummyAPIError(Exception):
    def __init__(self, code):
        super().__init__(f"Error code {code}")
        self.code = code

@patch("services.model_router.APIError", DummyAPIError)
def test_model_router_fallback(caplog):
    from services.model_router import get_model
    model = get_model()
    
    # Mock primary to raise APIError 429
    error = DummyAPIError(code=429)
    model.primary.generate_content = MagicMock(side_effect=error)
    
    # Mock fallback to return a success
    model.fallback.generate_content = MagicMock(return_value="fallback_response")
    
    with caplog.at_level(logging.WARNING):
        result = model.generate_content("Hello")
        
    assert result == "fallback_response"
    assert "Gemini quota exhausted, falling back to Ollama Cloud gpt-oss:120b-cloud" in caplog.text
