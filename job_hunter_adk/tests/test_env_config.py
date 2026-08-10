import os
import sys
import pytest

def test_model_router_imports_without_vertex_env():
    """
    Proves that the application (specifically model_router.py) 
    does not depend on GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION
    and does not crash when they are missing.
    """
    # Temporarily hide env vars if they happen to exist in the runner's environment
    old_project = os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    old_location = os.environ.pop("GOOGLE_CLOUD_LOCATION", None)
    
    try:
        # Force a fresh import
        if "services.model_router" in sys.modules:
            del sys.modules["services.model_router"]
            
        try:
            import services.model_router
        except Exception as e:
            pytest.fail(f"Importing model_router failed without Vertex env vars: {e}")
            
    finally:
        # Restore environment
        if old_project is not None:
            os.environ["GOOGLE_CLOUD_PROJECT"] = old_project
        if old_location is not None:
            os.environ["GOOGLE_CLOUD_LOCATION"] = old_location
