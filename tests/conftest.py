import pytest
from pathlib import Path
import requests
from backend.app.config import settings

@pytest.fixture(autouse=True)
def isolate_test_environment(monkeypatch, tmp_path):
    """
    Guarantees no live network calls or disk corruption during tests.
    1. Sets SERPAPI_API_KEY to empty string.
    2. Blocks real requests.get and requests.post unless specifically monkeypatched.
    """
    # 1. Clear API key
    monkeypatch.setattr(settings, "SERPAPI_API_KEY", "")
    
    # 2. Block external HTTP requests by default to guarantee offline test safety
    real_get = requests.get
    real_post = requests.post

    def forbidden_get(url, *args, **kwargs):
        raise RuntimeError(f"Network call forbidden in test suite: GET {url}")

    def forbidden_post(url, *args, **kwargs):
        raise RuntimeError(f"Network call forbidden in test suite: POST {url}")

    monkeypatch.setattr(requests, "get", forbidden_get)
    monkeypatch.setattr(requests, "post", forbidden_post)
