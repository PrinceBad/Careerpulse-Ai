import sys
import os
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

# Load .env
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

from backend.app.config import settings
from backend.app.services.serpapi_client import SerpApiClient
from backend.app.services.due_diligence import DueDiligenceEngine

def warm_cache():
    print(f"Connecting to SerpApi with key: {settings.SERPAPI_API_KEY[:6]}...{settings.SERPAPI_API_KEY[-4:]}")
    client = SerpApiClient(api_key=settings.SERPAPI_API_KEY, cache_enabled=True)
    engine = DueDiligenceEngine()

    # 1. Warm Job Searches
    job_queries = [
        ("Senior Python Backend Engineer", "Bengaluru, India"),
        ("Staff AI Platform Engineer", "Bengaluru, India"),
        ("Backend Architect", "Bengaluru, India"),
    ]

    for q, loc in job_queries:
        print(f"--> Fetching live google_jobs for: '{q}' in '{loc}'...")
        res = client.search_jobs(query=q, location=loc)
        total = len(res.get("jobs_results", []))
        is_mock = res.get("_is_mock", False)
        print(f"    [google_jobs] Retrieved {total} real jobs. (is_mock={is_mock})")

    # 2. Warm Due Diligence for Demo Companies
    companies = [
        ("Razorpay", "Senior Python Backend Engineer", ["FastAPI", "PostgreSQL"]),
        ("Swiggy", "Staff AI Platform Engineer", ["FastAPI", "Python"]),
        ("CRED", "Backend Architect", ["Go", "Python"])
    ]

    for company, role, stack in companies:
        print(f"\n--> Running 5-engine live investigative scan for: {company}...")
        report = engine.generate_report(
            company_name=company,
            role_title=role,
            location="Bengaluru, India",
            tech_stack=stack
        )
        print(f"    Verdict: {report.overall_health_verdict} | Citations: {len(report.citations)} | is_mock: {report.is_mock}")
        for c in report.citations[:3]:
            print(f"    - [{c.id}] ({c.engine}) {c.source_title[:60]}... (Signal: {c.signal_type})")

    cache_count = len(list(settings.CACHE_DIR.glob("*.json")))
    print(f"\n[SUCCESS] Cache warmed! Total cached response files on disk: {cache_count}")

if __name__ == "__main__":
    warm_cache()
