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
