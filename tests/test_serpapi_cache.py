import tempfile
from pathlib import Path
from backend.app.services.serpapi_client import SerpApiClient

def test_serpapi_cache_read_write(tmp_path):
    client = SerpApiClient(api_key=None, cache_enabled=True)
    client.cache_dir = tmp_path

    # Initial query should generate mock response and write to disk
    res1 = client.search_jobs("Python Engineer", "India")
    assert "jobs_results" in res1
    assert len(res1["jobs_results"]) > 0

    # Verify cache file exists
    cache_files = list(tmp_path.glob("google_jobs_*.json"))
    assert len(cache_files) == 1

    # Second call should load directly from cache
    res2 = client.search_jobs("Python Engineer", "India")
    assert res2.get("_from_cache") is True
    assert res2["jobs_results"][0]["company_name"] == res1["jobs_results"][0]["company_name"]
