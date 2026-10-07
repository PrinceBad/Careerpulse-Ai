from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "cached_queries_count" in data
    assert "cache_snapshot_date" in data

def test_job_search_endpoint():
    payload = {
        "query": "Senior Python Backend Engineer",
        "location": "Bengaluru, India",
        "candidate_profile_text": "Python 3.14, FastAPI, PostgreSQL, Redis"
    }
    res = client.post("/api/jobs/search", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_found"] > 0
    assert len(data["jobs"]) > 0
    assert "match_score" in data["jobs"][0]

def test_job_search_uncached_returns_empty_and_unavailable():
    payload = {
        "query": "NonExistentCompanyXYZ Engineer 999",
        "location": "Nowhere"
    }
    res = client.post("/api/jobs/search", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_found"] == 0
    assert len(data["jobs"]) == 0
    assert data["provenance"] == "unavailable"

def test_due_diligence_endpoint():
    payload = {
        "company_name": "Razorpay",
        "role_title": "Senior Python Backend Engineer",
        "location": "Bengaluru, India"
    }
    res = client.post("/api/company/due-diligence", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["company_name"] == "Razorpay"
    assert len(data["citations"]) > 0
    assert data["overall_health_verdict"] in ["Strong", "Caution", "High Risk"]

def test_outreach_endpoint():
    # First get due diligence
    dd_res = client.post("/api/company/due-diligence", json={"company_name": "Razorpay"})
    report = dd_res.json()
    
    payload = {
        "company_name": "Razorpay",
        "role_title": "Senior Python Backend Engineer",
        "candidate_profile_text": "Python 3.14, FastAPI, Redis, Microservices.",
        "due_diligence_report": report
    }
    res = client.post("/api/outreach/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "subject_line" in data
    assert "cover_letter" in data
    assert len(data["cited_evidence_ids"]) > 0

def test_serve_frontend_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "CareerPulse" in res.text
