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
    assert "recency_verified" in method
