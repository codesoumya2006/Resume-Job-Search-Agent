import logging
import inspect
import os
from google.genai.errors import APIError
from google.adk.models.lite_llm import LiteLlm

logger = logging.getLogger(__name__)

class ResilientModelWrapper(LiteLlm):
    """
    Wraps the primary Gemini model and transparently falls back to Ollama Cloud
    via LiteLLM if a quota (429) error is encountered.
    """
    def __init__(self, primary_model_name: str = "gemini-flash-latest"):
        # Initialize the base Pydantic model to pass validation
        super().__init__(model=f"gemini/{primary_model_name}")
        
        try:
            # Note: The Gemini SDK reads GOOGLE_API_KEY and GOOGLE_GENAI_USE_VERTEXAI 
            # implicitly from the environment. We do not need to pass them here.
            from google.adk.models import Gemini
            primary = Gemini(model=primary_model_name)
        except ImportError:
            # Fallback if Gemini import is missing or ADK uses LiteLlm natively
            primary = LiteLlm(model=f"gemini/{primary_model_name}")
            
        ollama_model = os.environ.get("OLLAMA_MODEL", os.environ.get("OLLAMA_CLOUD_MODEL", "glm-4-flash"))
        base_url = os.environ.get("OLLAMA_BASE_URL", os.environ.get("OLLAMA_API_BASE", "https://open.bigmodel.cn/api/paas/v4"))
        
        fallback = LiteLlm(
            model=f"openai/{ollama_model}",
            api_key=os.environ.get("OLLAMA_API_KEY", "dummy"),
            api_base=base_url
        )
        
        object.__setattr__(self, "_primary", primary)
        object.__setattr__(self, "_fallback", fallback)
        
    def _handle_quota_fallback(self, method_name, is_async, *args, **kwargs):
        """Helper to invoke a method with fallback logic."""
        primary_method = getattr(self._primary, method_name)
        fallback_method = getattr(self._fallback, method_name)
        
        if is_async:
            async def async_call():
                try:
                    return await primary_method(*args, **kwargs)
                except Exception as e:
                    err_str = str(e)
                    is_quota = getattr(e, "code", None) == 429 or "429" in err_str or "RateLimitError" in err_str or "Quota exceeded" in err_str
                    if is_quota:
                        logger.warning(f"Gemini quota exhausted ({method_name}), falling back to Ollama Cloud gpt-oss:120b-cloud")
                        return await fallback_method(*args, **kwargs)
                    raise
            return async_call()
        else:
            try:
                return primary_method(*args, **kwargs)
            except Exception as e:
                err_str = str(e)
                is_quota = getattr(e, "code", None) == 429 or "429" in err_str or "RateLimitError" in err_str or "Quota exceeded" in err_str
                if is_quota:
                    logger.warning(f"Gemini quota exhausted ({method_name}), falling back to Ollama Cloud gpt-oss:120b-cloud")
                    return fallback_method(*args, **kwargs)
                raise

    async def generate_content_async(self, *args, **kwargs):
        try:
            agen = self._primary.generate_content_async(*args, **kwargs)
            async for event in agen:
                yield event
        except Exception as e:
            err_str = str(e)
            is_quota = getattr(e, "code", None) == 429 or "429" in err_str or "RateLimitError" in err_str or "Quota exceeded" in err_str
            if is_quota:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Gemini quota exhausted (generate_content_async), falling back to Ollama Cloud")
                try:
                    agen_fallback = self._fallback.generate_content_async(*args, **kwargs)
                    async for event in agen_fallback:
                        yield event
                except Exception as e2:
                    logger.error(f"Fallback model failed: {e2}")
                    # Yield a dummy response so the server doesn't crash!
                    from google.adk.models.base import GenerateContentResponse, Candidate, TextPart, Message
                    msg = Message(role="model", parts=[TextPart(text=f"API Error: The fallback model is currently unavailable due to: {e2}. Please check your fallback API configuration.")])
                    candidate = Candidate(message=msg, finish_reason="STOP")
                    yield GenerateContentResponse(candidates=[candidate])
            else:
                raise
        
    def generate_content(self, *args, **kwargs):
        return self._handle_quota_fallback("generate_content", False, *args, **kwargs)
        
    def generate(self, *args, **kwargs):
        return self._handle_quota_fallback("generate", False, *args, **kwargs)

    def __getattr__(self, name):
        if name == "_additional_args":
            return {}

def get_model():
    """
    Returns a resilient model object compatible with ADK LlmAgent.
    """
    return ResilientModelWrapper()
