import pytest
from backend.app.models.schemas import Citation
from backend.app.services.grounding_validator import grounding_validator

@pytest.fixture
def sample_citations():
    return [
        Citation(
            id="cit-01",
            engine="google_news",
            source_title="Razorpay raises Series F for scaled payment services",
            source_url="https://example.com/news",
            snippet="Razorpay raised $375M at $7.5B valuation to scale payment systems and infrastructure with Python microservices.",
            signal_type="positive",
            verified=True,
            verification_method="entity_match+domain_validated",
            verification_confidence=0.95,
            provenance="cached"
        ),
        Citation(
            id="cit-02",
            engine="google",
            source_title="Glassdoor reviews and ratings",
            source_url="https://example.com/reviews",
            snippet="The engineering culture is rated 4.3 out of 5 by software engineers.",
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

def test_grounding_preserves_candidate_own_facts(sample_citations):
    # Candidate bullet with matching metric and unit (10k requests/second) describing candidate achievements
    candidate_profile = "Engineered high throughput API services handling 10k requests/second with sub-50ms latency using FastAPI."
    text = "Built an API serving 10k requests/second with sub-50ms latency. Scaled payment services with Python [cit-01]."
    is_valid, cleaned, violations, rejected = grounding_validator.validate_and_clean_text(
        text, sample_citations, candidate_profile_text=candidate_profile
    )
    assert is_valid is True
    assert len(violations) == 0
    assert "10k requests/second" in cleaned
    assert "[cit-01]" in cleaned

def test_adversarial_first_person_company_cut_stripped(sample_citations):
    # Adversarial test: First-person email sentences about company cuts start with verbs / 'I admire'
    # Must be stripped even if candidate profile exists
    candidate_profile = "Engineered high throughput API services handling 10k requests/second using FastAPI."
    text = "I admire that Swiggy cut 35% of staff. Scaled payment services with Python [cit-01]."
    is_valid, cleaned, violations, rejected = grounding_validator.validate_and_clean_text(
        text, sample_citations, candidate_profile_text=candidate_profile, target_company="Swiggy"
    )
    assert is_valid is False
    assert len(violations) >= 1
    assert any("Swiggy cut 35% of staff" in r for r in rejected)
    assert "Swiggy cut 35% of staff" not in cleaned
    assert "[cit-01]" in cleaned

def test_adversarial_target_company_default_deny(sample_citations):
    # Default-deny rule: Any sentence naming target company without citation must be stripped,
    # unless it strictly matches an application greeting or role interest allowlist.
    candidate_profile = "Experienced Python backend engineer."

    # 1. Non-quantified company assertion: "Swiggy shut down its Bengaluru office" -> stripped
    text1 = "Swiggy shut down its Bengaluru office. Scaled payment services with Python [cit-01]."
    is_valid1, cleaned1, violations1, rejected1 = grounding_validator.validate_and_clean_text(
        text1, sample_citations, candidate_profile_text=candidate_profile, target_company="Swiggy"
    )
    assert is_valid1 is False
    assert any("Swiggy shut down its Bengaluru office" in r for r in rejected1)
    assert "Swiggy shut down its Bengaluru office" not in cleaned1
    assert "[cit-01]" in cleaned1

    # 2. Application greeting & role interest allowlist -> survives
    text2 = "I am writing to express my strong interest in the Senior Backend Engineer role at Swiggy. Scaled payment services with Python [cit-01]."
    is_valid2, cleaned2, violations2, rejected2 = grounding_validator.validate_and_clean_text(
        text2, sample_citations, candidate_profile_text=candidate_profile, target_company="Swiggy"
    )
    assert is_valid2 is True
    assert len(violations2) == 0
    assert "Senior Backend Engineer role at Swiggy" in cleaned2

    # 3. Salutation allowlist -> survives
    text3 = "Dear Swiggy Hiring Team, Scaled payment services with Python [cit-01]."
    is_valid3, cleaned3, violations3, rejected3 = grounding_validator.validate_and_clean_text(
        text3, sample_citations, candidate_profile_text=candidate_profile, target_company="Swiggy"
    )
    assert is_valid3 is True
    assert len(violations3) == 0
    assert "Dear Swiggy Hiring Team," in cleaned3

def test_adversarial_candidate_metric_grounding_resume_check(sample_citations):
    # Candidate metric unit check: 10k requests/day vs 10k requests/second
    text = "Built an API serving 10k requests/day with sub-50ms latency. Scaled payment services with Python [cit-01]."

    # Subcase A: Exact quantity AND unit match (10k requests/day in resume) -> survives
    resume_matching = "Engineered high throughput API services handling 10k requests/day with sub-50ms latency using FastAPI."
    is_valid_a, cleaned_a, violations_a, rejected_a = grounding_validator.validate_and_clean_text(
        text, sample_citations, candidate_profile_text=resume_matching
    )
    assert is_valid_a is True
    assert len(violations_a) == 0
    assert "10k requests/day" in cleaned_a

    # Subcase B: Unit mismatch: resume says 10k requests/second, claim says 10k requests/day -> stripped!
    resume_unit_mismatch = "Engineered high throughput API services handling 10k requests/second using FastAPI."
    is_valid_b, cleaned_b, violations_b, rejected_b = grounding_validator.validate_and_clean_text(
        text, sample_citations, candidate_profile_text=resume_unit_mismatch
    )
    assert is_valid_b is False
    assert len(violations_b) >= 1
    assert "10k requests/day" not in cleaned_b
    assert any("10k requests/day" in r for r in rejected_b)
    assert "[cit-01]" in cleaned_b

    # Subcase C: 10k is NOT in resume at all -> stripped
    resume_without_10k = "Experienced software engineer who built microservices using Python."
    is_valid_c, cleaned_c, violations_c, rejected_c = grounding_validator.validate_and_clean_text(
        text, sample_citations, candidate_profile_text=resume_without_10k
    )
    assert is_valid_c is False
    assert len(violations_c) >= 1
    assert "10k requests/day" not in cleaned_c
    assert any("10k requests/day" in r for r in rejected_c)
    assert "[cit-01]" in cleaned_c

    # Subcase D: No resume text provided -> stripped
    is_valid_d, cleaned_d, violations_d, rejected_d = grounding_validator.validate_and_clean_text(
        text, sample_citations, candidate_profile_text=None
    )
    assert is_valid_d is False
    assert "10k requests/day" not in cleaned_d

def test_adversarial_guard_cases_suite(sample_citations):
    """
    Evaluates grounding validator against 26 labeled adversarial test cases
    covering default-deny on companies, unit mismatches, unverified claims,
    and valid applications.
    """
    import json
    from pathlib import Path

    cases_file = Path(__file__).parent / "data" / "guard_cases.json"
    with open(cases_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) >= 20

    passed_count = 0
    stripped_count = 0

    for c in cases:
        case_id = c["id"]
        sentence = c["sentence"]
        target_company = c.get("target_company")
        resume = c.get("resume")
        expected_pass = c["expected_pass"]

        is_valid, cleaned, violations, rejected = grounding_validator.validate_and_clean_text(
            sentence,
            sample_citations,
            candidate_profile_text=resume,
            target_company=target_company
        )

        if expected_pass:
            assert is_valid is True, f"Expected {case_id} ('{sentence}') to pass, but violations: {violations}"
            assert len(rejected) == 0, f"Expected {case_id} to have no rejected sentences"
            passed_count += 1
        else:
            assert is_valid is False, f"Expected {case_id} ('{sentence}') to be rejected, but it passed: '{cleaned}'"
            assert len(rejected) >= 1, f"Expected {case_id} to have rejected sentence"
            stripped_count += 1

    assert passed_count >= 10
    assert stripped_count >= 10
