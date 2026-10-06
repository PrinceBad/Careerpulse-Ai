import os
import json
import hashlib
import logging
from typing import Dict, Any, Optional
import requests
from ..config import settings

logger = logging.getLogger(__name__)

class SerpApiClient:
    """Multi-Engine SerpApi client with persistent disk caching and offline resilience."""
    
    BASE_URL = "https://serpapi.com/search.json"

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
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["_from_cache"] = True
                    logger.info(f"Loaded {engine} response from disk cache: {cache_file.name}")
                    return data
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")
        return None

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

    def query_engine(self, engine: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query any SerpApi engine with automatic disk caching and offline fallback."""
        query_params = dict(params)
        query_params["engine"] = engine
        cache_key = self._get_cache_key(engine, query_params)

        # 1. Try disk cache first
        cached = self._read_from_cache(engine, cache_key)
        if cached:
            return cached

        # 2. Live API execution if key exists
        if self.api_key:
            try:
                api_params = dict(query_params)
                api_params["api_key"] = self.api_key
                response = requests.get(self.BASE_URL, params=api_params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    self._write_to_cache(engine, cache_key, data)
                    data["_from_cache"] = False
                    return data
                else:
                    logger.error(f"SerpApi HTTP {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"Network error calling SerpApi engine {engine}: {e}")

        # 3. Fallback to built-in offline mock data for demo robustness
        logger.info(f"Using offline fallback mock for engine {engine}")
        mock_data = self._generate_mock_response(engine, params)
        self._write_to_cache(engine, cache_key, mock_data)
        mock_data["_from_cache"] = True
        mock_data["_is_mock"] = True
        return mock_data

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
            "ll": "@12.9716,77.5946,14z", # Bengaluru default coord or query place
            "type": "search"
        })

    def _generate_mock_response(self, engine: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Provides realistic mock responses for instant offline tests and demonstrations."""
        q = str(params.get("q", ""))

        if engine == "google_jobs":
            return {
                "jobs_results": [
                    {
                        "job_id": "job_01",
                        "title": f"Senior {q.title() if q else 'Python Engineer'}",
                        "company_name": "Razorpay",
                        "location": "Bengaluru, Karnataka, India",
                        "via": "via LinkedIn",
                        "description": "We are seeking an experienced Backend Engineer to scale our core payment infrastructure. Experience with Python, FastAPI, distributed systems, PostgreSQL, and high-throughput systems required. Competitive compensation and equity.",
                        "detected_extensions": {
                            "posted_at": "2 days ago",
                            "schedule_type": "Full-time",
                            "salary": "₹28,00,000 - ₹42,00,000 a year"
                        },
                        "thumbnail": "https://img.icons8.com/color/96/razorpay.png",
                        "share_link": "https://careers.razorpay.com/jobs/01"
                    },
                    {
                        "job_id": "job_02",
                        "title": "Staff AI Platform Engineer",
                        "company_name": "Swiggy",
                        "location": "Remote / Bengaluru, India",
                        "via": "via Swiggy Careers",
                        "description": "Lead the engineering efforts behind our agentic dispatch and recommendation engine. Must have deep Python expertise, FastAPI, Redis, LLM orchestration, and async architectures.",
                        "detected_extensions": {
                            "posted_at": "1 day ago",
                            "schedule_type": "Full-time",
                            "salary": "₹35,00,000 - ₹50,00,000 a year"
                        },
                        "thumbnail": "https://img.icons8.com/color/96/swiggy.png",
                        "share_link": "https://careers.swiggy.com/jobs/02"
                    },
                    {
                        "job_id": "job_03",
                        "title": "Backend Architect - Real-Time Systems",
                        "company_name": "CRED",
                        "location": "Bengaluru, Karnataka, India",
                        "via": "via Instahyre",
                        "description": "Architect mission-critical financial ledger pipelines. Expertise in Python, Go, Event-Driven Architecture, Kafka, and ultra low-latency APIs required.",
                        "detected_extensions": {
                            "posted_at": "3 days ago",
                            "schedule_type": "Full-time",
                            "salary": "₹40,00,000 - ₹60,00,000 a year"
                        },
                        "thumbnail": "https://img.icons8.com/color/96/bank-building.png",
                        "share_link": "https://careers.cred.club/jobs/03"
                    }
                ]
            }

        elif engine == "google_news":
            company = q.split()[0] if q else "Company"
            return {
                "news_results": [
                    {
                        "position": 1,
                        "title": f"{company} reports 48% YoY revenue expansion, initiates major engineering hiring drive",
                        "source": {"name": "Economic Times"},
                        "link": f"https://economictimes.indiatimes.com/tech/news/{company.lower()}-growth",
                        "snippet": f"{company} today announced stellar quarter earnings, confirming profitability and announcing plans to hire 250+ senior technical leaders across backend, platform, and applied AI infrastructure.",
                        "date": "1 week ago"
                    },
                    {
                        "position": 2,
                        "title": f"{company} restructures customer ops division to focus on AI automation; tech headcount spared",
                        "source": {"name": "TechCrunch"},
                        "link": f"https://techcrunch.com/2026/08/{company.lower()}-restructuring",
                        "snippet": f"In a strategic realignment, {company} confirmed minor operational restructuring in support while expanding investments in core platform engineering and distributed systems.",
                        "date": "3 weeks ago"
                    },
                    {
                        "position": 3,
                        "title": f"Leadership update: {company} appoints new Chief Technology Officer from Big Tech",
                        "source": {"name": "Mint"},
                        "link": f"https://livemint.com/technology/{company.lower()}-new-cto",
                        "snippet": f"Former engineering director joins {company} to steer global technical architecture and modernize backend microservices stack.",
                        "date": "1 month ago"
                    }
                ]
            }

        elif engine == "google":
            return {
                "organic_results": [
                    {
                        "position": 1,
                        "title": f"Working at {q} - Employee Reviews & Ratings",
                        "link": "https://www.glassdoor.co.in/Reviews/company-reviews.htm",
                        "snippet": "Rating: 4.3/5 - 1,840 reviews. Employees praise strong engineering culture, smart peers, competitive pay, and high ownership. Common critique: fast-paced deadlines and occasional sprint crunch.",
                    },
                    {
                        "position": 2,
                        "title": f"{q} Engineering Interview Questions & Experience",
                        "link": "https://leetcode.com/discuss/interview-experience",
                        "snippet": "Interview Process: 4 rounds. 1 DSA round (trees, graphs), 1 High Level System Design (caching, rate limiters, DB sharding), 1 Python core deep dive, and 1 Culture/Values fit.",
                    }
                ]
            }

        elif engine == "google_trends":
            return {
                "interest_over_time": {
                    "timeline_data": [
                        {"date": "2025-10", "values": [{"extracted_value": 68}]},
                        {"date": "2026-02", "values": [{"extracted_value": 82}]},
                        {"date": "2026-06", "values": [{"extracted_value": 91}]},
                        {"date": "2026-10", "values": [{"extracted_value": 96}]}
                    ]
                },
                "search_parameters": {"q": q}
            }

        elif engine == "google_maps":
            return {
                "place_results": {
                    "title": f"{q} Corporate Headquarters",
                    "address": "Salarpuria Softzone, Outer Ring Road, Bellandur, Bengaluru, Karnataka 560103",
                    "rating": 4.6,
                    "reviews": 320,
                    "website": f"https://{q.split()[0].lower()}.com",
                    "link": "https://maps.google.com/?cid=mock123"
                }
            }

        return {}

serpapi_client = SerpApiClient()
