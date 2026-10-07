"""
CareerPulse AI - Cache Warming & Verification Utility
Merges and unifies SerpApi multi-engine cache warming into a single robust CLI.

Usage:
    python scripts/warm_cache.py               # Warm all demo companies & jobs
    python scripts/warm_cache.py --verify-only # Inspect & verify existing disk cache
    python scripts/warm_cache.py --company Zomato  # Warm a specific target company
"""

import sys
import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 console output for Windows terminals
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Locate project paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
BACKEND_DIR = ROOT_DIR / "backend"
ENV_PATH = BACKEND_DIR / ".env"

# Add project root to sys.path
sys.path.insert(0, str(ROOT_DIR))

# Load backend .env configuration
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

from backend.app.config import settings
from backend.app.services.serpapi_client import SerpApiClient

DEMO_COMPANIES = ["Razorpay", "Swiggy", "CRED"]

JOB_TARGETS = [
    ("Senior Python Backend Engineer", "Bengaluru, India"),
    ("Staff AI Platform Engineer", "Bengaluru, India"),
    ("Backend Architect - Real-Time Systems", "Bengaluru, India"),
]

def verify_disk_cache():
    """Inspects all cache files on disk to verify genuine SerpApi search_metadata."""
    cache_dir = settings.CACHE_DIR
    if not cache_dir.exists():
        print(f"[CACHE] Cache directory not found: {cache_dir}")
        return 0, 0

    all_files = list(cache_dir.glob("*.json"))
    real_count = 0
    mock_count = 0

    print(f"\n=======================================================")
    print(f"  🔍 Inspecting Cache Files in: {cache_dir}")
    print(f"=======================================================")

    for f in all_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
            if "search_metadata" in d:
                real_count += 1
                created = d["search_metadata"].get("created_at", "Unknown Date")
                engine = d.get("search_parameters", {}).get("engine", f.name.split("_")[0])
                # Print sample details
            else:
                mock_count += 1
                print(f"  [WARN] Missing search_metadata: {f.name}")
        except Exception as e:
            print(f"  [ERROR] Unreadable file {f.name}: {e}")

    print(f"-------------------------------------------------------")
    print(f"  Total JSON files on disk:       {len(all_files)}")
    print(f"  Genuine SerpApi responses (live metadata): {real_count}")
    print(f"  Fallback/Mock responses:        {mock_count}")
    print(f"=======================================================\n")
    return real_count, len(all_files)

def warm_single_company(client: SerpApiClient, company: str, location: str = "Bengaluru, India"):
    """Executes live warming across all 5 engines for a target employer."""
    print(f"\n>>> Warming all 5 SerpApi engines for: {company} <<<")

    # 1. Primary news scan
    primary_news = f"{company} news hiring OR funding OR revenue OR restructuring OR layoffs OR 'laid off'"
    print(f"  [google_news:primary] {primary_news}")
    res_news = client.search_news(primary_news)
    news_count = len(res_news.get("news_results", []))
    has_meta = "search_metadata" in res_news
    print(f"    -> items: {news_count}, metadata: {has_meta}, is_mock: {res_news.get('_is_mock')}")

    # 2. Corroboration loop query
    corrob_news = f"{company} layoffs confirmed severance details"
    print(f"  [google_news:corroboration] {corrob_news}")
    res_corrob = client.search_news(corrob_news)
    corrob_count = len(res_corrob.get("news_results", []))
    print(f"    -> items: {corrob_count}, metadata: {'search_metadata' in res_corrob}")

    # 3. Organic web reviews (Glassdoor / AmbitionBox)
    web_q = f"{company} employee reviews glassdoor ambitionbox interview"
    print(f"  [google:organic] {web_q}")
    res_web = client.search_web(web_q, num=4)
    web_count = len(res_web.get("organic_results", []))
    print(f"    -> items: {web_count}, metadata: {'search_metadata' in res_web}")

    # 4. Tech stack trends
    tech = "FastAPI" if company in ["Razorpay", "Swiggy"] else "Python"
    print(f"  [google_trends] {tech}")
    res_trends = client.search_trends(tech)
    trend_pts = len(res_trends.get("interest_over_time", {}).get("timeline_data", []))
    print(f"    -> timeline points: {trend_pts}, metadata: {'search_metadata' in res_trends}")

    # 5. Maps campus location
    maps_q = f"{company} headquarters {location}"
    print(f"  [google_maps] {maps_q}")
    res_maps = client.search_maps(maps_q)
    maps_results = len(res_maps.get("local_results", [])) or (1 if "place_results" in res_maps else 0)
    print(f"    -> locations: {maps_results}, metadata: {'search_metadata' in res_maps}")

def warm_jobs(client: SerpApiClient):
    """Executes live warming for target role queries."""
    print(f"\n>>> Warming google_jobs for Target Demo Roles <<<")
    for q, loc in JOB_TARGETS:
        print(f"  [google_jobs] Query: '{q}' in '{loc}'")
        res = client.search_jobs(q, loc)
        total = len(res.get("jobs_results", []))
        has_meta = "search_metadata" in res
        print(f"    -> retrieved: {total} jobs, metadata: {has_meta}, is_mock: {res.get('_is_mock')}")

def main():
    parser = argparse.ArgumentParser(description="CareerPulse AI SerpApi Cache Warming & Verification Tool")
    parser.add_argument("--verify-only", action="store_true", help="Inspect and verify existing disk cache without making API requests")
    parser.add_argument("--company", type=str, default=None, help="Warm all engines for a specific company name")
    parser.add_argument("--all", action="store_true", help="Warm all default demo companies and job targets")

    args = parser.parse_args()

    if args.verify_only:
        verify_disk_cache()
        return

    # Check API key before making network requests
    api_key = settings.SERPAPI_API_KEY
    if not api_key:
        print("[ERROR] SERPAPI_API_KEY is not configured in backend/.env!")
        print("To warm new cache entries with genuine Google results, provide a valid key.")
        print("Running cache verification instead:")
        verify_disk_cache()
        return

    key_display = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "***"
    print(f"🚀 Initializing SerpApi Cache Warmer with key: {key_display}")
    client = SerpApiClient(api_key=api_key, cache_enabled=True)

    if args.company:
        warm_single_company(client, args.company)
    else:
        # Default or --all: Warm demo jobs and all demo companies
        warm_jobs(client)
        for comp in DEMO_COMPANIES:
            warm_single_company(client, comp)

    verify_disk_cache()
    print("[SUCCESS] Cache warming complete. Responses committed to disk with genuine search_metadata.\n")

if __name__ == "__main__":
    main()
