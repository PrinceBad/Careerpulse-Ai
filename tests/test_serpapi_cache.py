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

    # Second call should load directly from cache and be recognized as available
    res = client.search_jobs("Python Engineer", "India")
    assert res.get("_from_cache") is True
    assert res.get("_unavailable") is False
    assert res["jobs_results"][0]["company_name"] == "Razorpay"

    # 2. Confirm that cache-miss queries with no key return unavailable and NEVER write to disk cache
    initial_count = len(list(tmp_path.glob("*.json")))
    miss_res = client.search_jobs("Totally Uncached Query 999", "Unknown")
    assert miss_res.get("_unavailable") is True
    assert miss_res.get("_reason") == "cache_miss"
    # Count of cached files must NOT have increased!
    assert len(list(tmp_path.glob("*.json"))) == initial_count

def test_committed_cache_metadata_and_date_range():
    """
    Validates genuine search_metadata and capture timestamps across all committed cache files.
    Ensures:
    1. Every cache file has real search_metadata from SerpApi.
    2. No cache file leaks api_key.
    3. Dates parse cleanly and reports single date or dynamic date range if files differ.
    """
    import json
    from datetime import datetime, timezone
    from backend.app.config import settings

    cache_dir = settings.CACHE_DIR
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) >= 20, f"Expected at least 20 committed cache files, found {len(cache_files)}"

    dates_found = set()
    timestamps = []

    for cfile in cache_files:
        with open(cfile, "r", encoding="utf-8") as f:
            content = f.read()
            data = json.loads(content)

        # 1. Zero secret leak check
        assert "api_key" not in data, f"Found raw api_key field in {cfile.name}"
        assert "api_key=" not in content, f"Found api_key query string in {cfile.name}"

        # 2. Genuine search_metadata check
        assert "search_metadata" in data, f"Missing search_metadata in {cfile.name}"
        meta = data["search_metadata"]
        created_at = meta.get("created_at") or meta.get("processed_at")
        assert created_at is not None, f"Missing created_at/processed_at timestamp in {cfile.name}"

        # 3. Parse timestamp
        clean_ts = created_at.replace(" UTC", "").strip()
        parsed_dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                parsed_dt = datetime.strptime(clean_ts, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue

        assert parsed_dt is not None, f"Failed to parse timestamp '{created_at}' in {cfile.name}"
        timestamps.append(parsed_dt)
        dates_found.add(parsed_dt.strftime("%Y-%m-%d"))

    min_dt = min(timestamps)
    max_dt = max(timestamps)

    if min_dt.date() == max_dt.date():
        date_display = f"{min_dt.strftime('%b')} {min_dt.day}, {min_dt.year}"
    else:
        date_display = f"{min_dt.strftime('%b')} {min_dt.day}, {min_dt.year} - {max_dt.strftime('%b')} {max_dt.day}, {max_dt.year}"

    # Confirm capture date range is valid and recorded
    assert len(dates_found) >= 1
    assert "2026" in date_display
    assert len(cache_files) >= 20
    assert len(timestamps) == len(cache_files)

def test_live_call_failure_returns_unavailable_not_mock():
    """
    When live API key is set but request fails (network error, timeout, HTTP 500),
    the client must return explicit unavailable marker and NEVER fallback to mock data.
    """
    client = SerpApiClient(api_key="test_key_non_empty", cache_enabled=False)
    res = client.query_engine("google_news", {"q": "RandomUncachedCompanyXYZ"})

    assert res.get("_unavailable") is True
    assert res.get("_reason") == "api_error"
    assert res.get("_is_mock") is not True
    assert "news_results" not in res


