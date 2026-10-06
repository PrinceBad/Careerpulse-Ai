import pytest
from backend.app.models.schemas import (
    Citation,
    JobListing,
    DueDiligenceReport,
    CompanyRiskSignals,
    CompanyCultureSignals,
    GroundedOutreachPack
)

def test_citation_creation():
    cit = Citation(
        id="cit-01",
        engine="google_news",
        source_title="Company hiring 200 engineers",
        source_url="https://example.com/news",
        snippet="Company announced massive expansion.",
        signal_type="positive",
        verified=True,
        verification_method="entity_match",
        verification_confidence=0.90,
        provenance="live"
    )
    assert cit.id == "cit-01"
    assert cit.engine == "google_news"
    assert cit.signal_type == "positive"
    assert cit.verified is True

def test_due_diligence_report_validation():
    cit = Citation(
        id="cit-01",
        engine="google_news",
        source_title="Layoff announcement",
        source_url="https://example.com/news",
        snippet="5% workforce reduction announced.",
        signal_type="red_flag",
        verified=True,
        verification_method="entity_match",
        verification_confidence=0.85,
        provenance="cached"
    )
    report = DueDiligenceReport(
        company_name="TestCorp",
        overall_health_verdict="Caution",
        executive_summary="Caution advised due to restructuring.",
        risks=CompanyRiskSignals(
            risk_level="Medium",
            layoffs_detected=True,
            risk_summary="Layoffs identified",
            evidence_citation_ids=["cit-01"]
        ),
        culture=CompanyCultureSignals(
            sentiment_rating=4.0,
            evidence_citation_ids=[]
        ),
        citations=[cit]
    )
    assert report.company_name == "TestCorp"
    assert report.overall_health_verdict == "Caution"
    assert report.risks.layoffs_detected is True
    assert len(report.citations) == 1
