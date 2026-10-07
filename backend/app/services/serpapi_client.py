import json
import hashlib
import logging
from typing import Dict, Any, Optional
import requests
from ..config import settings

logger = logging.getLogger(__name__)


class SerpApiClient:
    """
    Multi-Engine SerpApi client with persistent disk caching.

    Honesty contract: this client NEVER fabricates search results. Every response is either
    a genuine SerpApi response (live or from the committed disk cache) or an explicit
    "unavailable" marker that explains why no data exists (cache miss without a key, or a
    failed live call).
    """

    BASE_URL = "https://serpapi.com/search.json"
    REQUEST_TIMEOUT_SECONDS = 15

    def __init__(self, api_key: Optional[str] = None, cache_enabled: Optional[bool] = None):
        self.api_key = api_key if api_key is not None else settings.SERPAPI_API_KEY
        self.cache_enabled = cache_enabled if cache_enabled is not None else settings.SERPAPI_CACHE_ENABLED
        self.cache_dir = settings.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, engine: str, params: Dict[str, Any]) -> str:
        # Strip api_key before computing hash so cache is invariant to keys
        sanitized = {k: v for k, v in params.items() if k != "api_key"}
        raw_key = f"{engine}:{json.dumps(sanitized, sort_keys=True)}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def _read_from_cache(self, engine: str, cache_key: str) -> Optional[Dict[str, Any]]:
        if not self.cache_enabled:
            return None
        cache_file = self.cache_dir / f"{engine}_{cache_key}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Error reading cache file {cache_file}: {e}")
            return None
        # A genuine SerpApi response always contains search_metadata; anything else is ignored.
        if "search_metadata" not in data:
            logger.warning(f"Ignoring cache file without search_metadata: {cache_file.name}")
            return None
        data["_from_cache"] = True
        data["_unavailable"] = False
        logger.info(f"Loaded {engine} response from disk cache: {cache_file.name}")
        return data

    def _sanitize_data(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items() if k != "api_key"}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        return data

    def _write_to_cache(self, engine: str, cache_key: str, data: Dict[str, Any]):
        if not self.cache_enabled:
            return
        cache_file = self.cache_dir / f"{engine}_{cache_key}.json"
        clean_data = self._sanitize_data(data)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(clean_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Cached {engine} response to disk: {cache_file.name}")
        except Exception as e:
            logger.warning(f"Error saving to cache {cache_file}: {e}")

    @staticmethod
    def _unavailable(reason: str, detail: str = "") -> Dict[str, Any]:
        """Explicit no-data marker. Contains no result arrays, so nothing can be rendered as evidence."""
        return {
            "_from_cache": False,
            "_unavailable": True,
            "_reason": reason,  # "cache_miss" | "api_error"
            "_detail": detail,
        }

    def query_engine(self, engine: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query any SerpApi engine: disk cache first, then live API if a key is configured."""
        query_params = dict(params)
        query_params["engine"] = engine
        cache_key = self._get_cache_key(engine, query_params)

        # 1. Disk cache
        cached = self._read_from_cache(engine, cache_key)
        if cached:
            return cached

        # 2. No key: honest cache miss
        if not self.api_key:
            return self._unavailable("cache_miss", f"No cached {engine} response and SERPAPI_API_KEY is not set.")

        # 3. Live call
        try:
            api_params = dict(query_params)
            api_params["api_key"] = self.api_key
            response = requests.get(self.BASE_URL, params=api_params, timeout=self.REQUEST_TIMEOUT_SECONDS)
        except Exception as e:
            logger.error(f"Network error calling SerpApi engine {engine}: {e}")
            return self._unavailable("api_error", f"Network error calling SerpApi ({engine}).")

        if response.status_code != 200:
            logger.error(f"SerpApi HTTP {response.status_code} for engine {engine}")
            return self._unavailable("api_error", f"SerpApi returned HTTP {response.status_code} ({engine}).")

        try:
            data = response.json()
        except ValueError:
            return self._unavailable("api_error", f"SerpApi returned non-JSON response ({engine}).")

        if "search_metadata" not in data:
            return self._unavailable("api_error", data.get("error", f"Unexpected SerpApi response ({engine})."))

        self._write_to_cache(engine, cache_key, data)
        data["_from_cache"] = False
        data["_unavailable"] = False
        return data

    # Specialized Engine Methods
    def search_jobs(self, query: str, location: str = "India", start: int = 0) -> Dict[str, Any]:
        return self.query_engine("google_jobs", {
            "q": query,
            "location": location,
            "start": start,
            "hl": "en",
            "gl": "in"
        })

    def search_news(self, query: str) -> Dict[str, Any]:
        return self.query_engine("google_news", {
            "q": query,
            "gl": "in",
            "hl": "en"
        })

    def search_web(self, query: str, num: int = 10) -> Dict[str, Any]:
        return self.query_engine("google", {
            "q": query,
            "num": num,
            "gl": "in",
            "hl": "en"
        })

    def search_trends(self, keywords: str, date: str = "today 12-m") -> Dict[str, Any]:
        return self.query_engine("google_trends", {
            "q": keywords,
            "date": date,
            "geo": "IN",
            "data_type": "TIMESERIES"
        })

    def search_maps(self, query: str) -> Dict[str, Any]:
        return self.query_engine("google_maps", {
            "q": query,
            "ll": "@12.9716,77.5946,14z",  # Bengaluru default coordinates
            "type": "search"
        })


serpapi_client = SerpApiClient()
