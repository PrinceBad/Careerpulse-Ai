from backend.app.services.due_diligence import due_diligence_engine
from backend.app.services.llm_service import llm_service

def test_due_diligence_report_generation():
    report = due_diligence_engine.generate_report(
        company_name="Razorpay",
        role_title="Senior Python Backend Engineer",
        location="Bengaluru, India",
        tech_stack=["FastAPI", "PostgreSQL"]
    )
    
    assert report.company_name == "Razorpay"
    assert len(report.citations) >= 4
    # Check that citation IDs are formatted as cit-XX
    for c in report.citations:
        assert c.id.startswith("cit-")
        assert c.source_url is not None
        assert len(c.snippet) > 0

    # Test grounded outreach generation from this report
    candidate_profile = "5 years building FastAPI and Python microservices with Redis and PostgreSQL."
    outreach = llm_service.generate_grounded_outreach(
        company_name=report.company_name,
        role_title=report.target_role,
        candidate_profile=candidate_profile,
        citations=report.citations
    )

    assert outreach.company_name == "Razorpay"
    assert len(outreach.cited_evidence_ids) > 0
    assert len(outreach.tailored_resume_bullets) > 0
    # Every cited evidence ID must exist in report citations
    valid_ids = {c.id for c in report.citations}
    for cid in outreach.cited_evidence_ids:
        assert cid in valid_ids

def test_recency_date_parsing():
    is_recent, note = due_diligence_engine.parse_and_check_recency("3 weeks ago")
    assert is_recent is True

    is_recent, note = due_diligence_engine.parse_and_check_recency("Mar 3, 2025")
    assert is_recent is True

    is_recent, note = due_diligence_engine.parse_and_check_recency("May 20, 2026")
    assert is_recent is True

    is_recent, note = due_diligence_engine.parse_and_check_recency("January 15, 2023")
    assert is_recent is False
    assert "historical" in note.lower()

    is_recent, note = due_diligence_engine.parse_and_check_recency("3 years ago")
    assert is_recent is False

def test_investigation_trace_present():
    report = due_diligence_engine.generate_report("Swiggy")
    assert len(report.investigation_trace) >= 2
    step1 = report.investigation_trace[0]
    assert step1.step_number == 1
    assert "Parallel" in step1.action
    assert step1.engine != ""

def test_computed_verification_integrity():
    is_v, method, conf = due_diligence_engine.compute_verification(
        company_name="Razorpay",
        source_title="Razorpay reports strong Q4 expansion",
        snippet="Razorpay hired 200 engineers across Bengaluru.",
        source_url="https://economictimes.indiatimes.com/tech",
        is_recent=True
    )
    assert is_v is True
    assert conf >= 0.90
    assert "entity_match" in method
    assert "tier1_publisher" in method
    assert "recency_verified" in method

def test_economic_times_domain_credibility_boost():
    # Real ET domain economictimes.indiatimes.com gets tier1_publisher boost
    is_v, method, conf_et = due_diligence_engine.compute_verification(
        company_name="CRED",
        source_title="CRED financial metrics update",
        snippet="CRED reports growth in member payments.",
        source_url="https://economictimes.indiatimes.com/tech/startups/cred-revenue",
        is_recent=True
    )
    assert "tier1_publisher" in method
    assert conf_et == 1.0

    # Unknown random blog does NOT get tier1_publisher boost
    is_v2, method2, conf_unknown = due_diligence_engine.compute_verification(
        company_name="CRED",
        source_title="CRED financial metrics update",
        snippet="CRED reports growth in member payments.",
        source_url="https://randomtechblog123.com/cred-revenue",
        is_recent=True
    )
    assert "tier1_publisher" not in method2
    assert conf_unknown == 0.80

def test_dynamic_investigation_trace(monkeypatch):
    # 1. Layoff fixture: primary news detects restructuring/layoffs
    def mock_layoff_news(query):
        if "layoffs confirmed" in query:
            return {
                "search_metadata": {"id": "corrob_123"},
                "news_results": [
                    {"title": "Company confirms layoff of 400 staff", "snippet": "severance packages offered to impacted employees", "date": "1 week ago", "link": "https://economictimes.indiatimes.com/tech"},
                    {"title": "Second report: Major cuts and severance across units", "snippet": "layoff confirmed by internal memo", "date": "2 weeks ago", "link": "https://moneycontrol.com/news"}
                ]
            }
        return {
            "search_metadata": {"id": "primary_123"},
            "news_results": [
                {"title": "Company initiates major layoff and restructuring", "snippet": "Over 500 job cuts announced today amid market shift.", "date": "3 days ago", "link": "https://economictimes.indiatimes.com/news"}
            ]
        }

    monkeypatch.setattr("backend.app.services.due_diligence.serpapi_client.search_news", mock_layoff_news)
    report_layoff = due_diligence_engine.generate_report("AcmeCorp")
    trace_actions_layoff = [step.action for step in report_layoff.investigation_trace]
    assert any("Autonomous Corroboration" in a for a in trace_actions_layoff)
    assert report_layoff.risks.layoffs_detected is True
    assert report_layoff.risks.corroborated is True

    # 2. Clean fixture: primary news detects only hiring/funding growth
    def mock_clean_news(query):
        return {
            "search_metadata": {"id": "clean_123"},
            "news_results": [
                {"title": "AcmeCorp raises Series D funding", "snippet": "Company hiring 100 new engineers to scale platform.", "date": "1 week ago", "link": "https://economictimes.indiatimes.com/news"}
            ]
        }

    monkeypatch.setattr("backend.app.services.due_diligence.serpapi_client.search_news", mock_clean_news)
    report_clean = due_diligence_engine.generate_report("AcmeCorp")
    trace_actions_clean = [step.action for step in report_clean.investigation_trace]
    assert any("Health Clearance" in a for a in trace_actions_clean)
    assert not any("Autonomous Corroboration" in a for a in trace_actions_clean)
    assert report_clean.risks.layoffs_detected is False
