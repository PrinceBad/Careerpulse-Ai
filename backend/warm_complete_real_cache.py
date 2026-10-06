import sys
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

def run_warm():
    key = settings.SERPAPI_API_KEY
    if not key:
        print("[ERROR] No SERPAPI_API_KEY found in .env!")
        return

    print(f"Executing LIVE SerpApi warming using key: {key[:6]}...{key[-4:]}")
    client = SerpApiClient(api_key=key, cache_enabled=True)

    # 1. Job queries
    jobs = [
        ("Senior Python Backend Engineer", "Bengaluru, India"),
        ("Staff AI Platform Engineer", "Bengaluru, India"),
        ("Backend Architect - Real-Time Systems", "Bengaluru, India"),
    ]

    for q, loc in jobs:
        print(f"\n[google_jobs] Querying: '{q}' in '{loc}'...")
        res = client.search_jobs(q, loc)
        has_meta = "search_metadata" in res
        total = len(res.get("jobs_results", []))
        print(f"  -> search_metadata: {has_meta}, jobs count: {total}, is_mock: {res.get('_is_mock')}")

    # 2. Companies
    companies = ["Razorpay", "Swiggy", "CRED"]

    for comp in companies:
        print(f"\n==========================================")
        print(f"Warming all engines for company: {comp}")
        print(f"==========================================")

        # News: Primary
        primary_news = f"{comp} news hiring OR funding OR revenue OR restructuring OR layoffs OR 'laid off'"
        print(f"[google_news:primary] {primary_news}")
        res_news = client.search_news(primary_news)
        print(f"  -> search_metadata: {'search_metadata' in res_news}, items: {len(res_news.get('news_results', []))}")

        # News: Follow-up corroboration
        corrob_news = f"{comp} layoffs confirmed severance details"
        print(f"[google_news:corroboration] {corrob_news}")
        res_corrob = client.search_news(corrob_news)
        print(f"  -> search_metadata: {'search_metadata' in res_corrob}, items: {len(res_corrob.get('news_results', []))}")

        # Organic Google: Reviews
        web_q = f"{comp} employee reviews glassdoor ambitionbox interview"
        print(f"[google:web] {web_q}")
        res_web = client.search_web(web_q, num=4)
        print(f"  -> search_metadata: {'search_metadata' in res_web}, items: {len(res_web.get('organic_results', []))}")

        # Trends
        tech = "FastAPI" if comp in ["Razorpay", "Swiggy"] else "Python"
        print(f"[google_trends] {tech}")
        res_trends = client.search_trends(tech)
        print(f"  -> search_metadata: {'search_metadata' in res_trends}, timeline points: {len(res_trends.get('interest_over_time', {}).get('timeline_data', []))}")

        # Maps
        maps_q = f"{comp} headquarters Bengaluru"
        print(f"[google_maps] {maps_q}")
        res_maps = client.search_maps(maps_q)
        print(f"  -> search_metadata: {'search_metadata' in res_maps}, local results: {len(res_maps.get('local_results', []))}")

    # Summary
    all_files = list(settings.CACHE_DIR.glob("*.json"))
    real_count = 0
    import json
    for f in all_files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        if "search_metadata" in d:
            real_count += 1
        else:
            print(f"[WARNING] Non-metadata file found: {f.name}")

    print(f"\n[CACHE WARMING COMPLETE]")
    print(f"Total cache files on disk: {len(all_files)}")
    print(f"Total genuine SerpApi responses with search_metadata: {real_count}")

if __name__ == "__main__":
    run_warm()
