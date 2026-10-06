import tempfile
from pathlib import Path
from backend.app.services.serpapi_client import SerpApiClient

def test_serpapi_cache_read_write(tmp_path):
    client = SerpApiClient(api_key=None, cache_enabled=True)
    client.cache_dir = tmp_path

    # 1. Genuine response with search_metadata is written to disk
    sample_data = {
        "search_metadata": {"id": "genuine_123"},
        "jobs_results": [{"title": "Software Engineer", "company_name": "Razorpay"}]
    }
    params = {"q": "Python Engineer", "location": "India", "start": 0, "hl": "en", "gl": "in", "engine": "google_jobs"}
    cache_key = client._get_cache_key("google_jobs", params)
    client._write_to_cache("google_jobs", cache_key, sample_data)

    # Verify cache file exists
    cache_files = list(tmp_path.glob("google_jobs_*.json"))
    assert len(cache_files) == 1

    # Second call should load directly from cache and be recognized as non-mock
    res = client.search_jobs("Python Engineer", "India")
    assert res.get("_from_cache") is True
    assert res.get("_is_mock") is False
    assert res["jobs_results"][0]["company_name"] == "Razorpay"

    # 2. Confirm that mock fallback queries NEVER write to disk cache
    initial_count = len(list(tmp_path.glob("*.json")))
    mock_res = client.search_jobs("Totally Uncached Query 999", "Unknown")
    assert mock_res.get("_is_mock") is True
    # Count of cached files must NOT have increased!
    assert len(list(tmp_path.glob("*.json"))) == initial_count
