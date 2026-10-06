import pytest
from backend.app.models.schemas import Citation
from backend.app.services.grounding_validator import grounding_validator

@pytest.fixture
def sample_citations():
    return [
        Citation(
            id="cit-01",
            engine="google_news",
            source_title="Razorpay raises Series F",
            source_url="https://example.com/news",
            snippet="Razorpay raised $375M at $7.5B valuation.",
            signal_type="positive",
            verified=True,
            verification_method="entity_match+domain_validated",
            verification_confidence=0.95,
            provenance="cached"
        ),
        Citation(
            id="cit-02",
            engine="google",
            source_title="Glassdoor reviews",
            source_url="https://example.com/reviews",
            snippet="Rated 4.3 out of 5 by engineers.",
            signal_type="positive",
            verified=True,
            verification_method="review_snippet_match",
            verification_confidence=0.90,
            provenance="cached"
        )
    ]

def test_grounding_accepts_valid_citations(sample_citations):
    text = "Razorpay raised $375M in their latest round [cit-01]. The engineering culture is rated 4.3 out of 5 [cit-02]."
    is_valid, cleaned, violations, rejected = grounding_validator.validate_and_clean_text(text, sample_citations)
    
    assert is_valid is True
    assert len(violations) == 0
    assert len(rejected) == 0
    assert "[cit-01]" in cleaned
    assert "[cit-02]" in cleaned

def test_grounding_rejects_hallucinated_citation_id(sample_citations):
    # cit-99 is fake and not in sample_citations
    text = "Razorpay opened an office in Singapore [cit-99]. The engineering culture is strong [cit-02]."
    is_valid, cleaned, violations, rejected = grounding_validator.validate_and_clean_text(text, sample_citations)
    
    assert is_valid is False
    assert len(violations) >= 1
    assert any("cit-99" in v for v in violations)
    # The offending sentence should be stripped
    assert "[cit-99]" not in cleaned
    assert "[cit-02]" in cleaned

def test_grounding_rejects_uncited_factual_claims(sample_citations):
    # Text with ungrounded layoff claim lacking citation
    text = "The company went through major downsizing and laid off 20% of staff. We are passionate about high scale systems [cit-01]."
    is_valid, cleaned, violations, rejected = grounding_validator.validate_and_clean_text(text, sample_citations)
    
    assert is_valid is False
    assert len(violations) >= 1
    assert any("ungrounded" in v.lower() for v in violations)
    # The uncited layoff claim must be dropped
    assert "laid off" not in cleaned
    assert "[cit-01]" in cleaned

def test_grounding_rejects_unsupported_citation(sample_citations):
    # cit-01 discusses $375M funding, NOT layoffs or 40% staff cuts
    text = "The company recently confirmed a 40% layoff across operations [cit-01]."
    is_valid, cleaned, violations, rejected = grounding_validator.validate_and_clean_text(text, sample_citations)

    assert is_valid is False
    assert len(violations) >= 1
    assert any("unsupported" in v.lower() for v in violations)
    assert "[cit-01]" not in cleaned

def test_simulated_hallucination_demonstrator(sample_citations):
    res = grounding_validator.simulate_hallucination_test(sample_citations)
    assert res["is_valid"] is False
    assert res["count_rejected"] >= 2
    assert "[cit-99]" not in res["cleaned_result"]
