import re
from typing import List, Dict, Tuple, Set, Optional
from ..models.schemas import Citation

class GroundingValidator:
    """
    Evidence validation guard for AI generations.
    Ensures that:
    1. Every citation token [cit-xx] maps to a valid citation in the report.
    2. Every factual claim (percentages, numbers, layoffs, funding, ratings) carries a citation.
    3. The cited citation actually SUPPORTS the factual claims made in the sentence (content cross-check).
    
    LIMITATION NOTE (Honest disclosure):
    Factual claim extraction uses regex heuristics and token-overlap support checking.
    While not a formal mathematical theorem prover, it deterministically intercepts
    unsupported claims and fabricated citations.
    """

    FACTUAL_INDICATORS = [
        r"\b\d+%",                                                        # Percentages (e.g. 48%, 35%)
        r"\b\d+\+?\s*(?:engineers|openings|roles|jobs|employees|staff)\b",# Headcount counts
        r"(?:[\$₹]|rs\.?)\s*\d+",                                         # Monetary figures
        r"\b(?:layoff|laid off|job cuts|downsizing|headcount reduction)\b", # Layoff terms
        r"\b(?:raised|series [a-e]|funding round|valuation)\b",            # Funding terms
        r"\b(?:rated|rating of)\s*\d+(?:\.\d+)?\b",                        # Review ratings
    ]

    CITATION_REGEX = r"\[(cit-\d+)\]"

    @classmethod
    def validate_and_clean_text(
        cls, 
        text: str, 
        valid_citations: List[Citation],
        candidate_profile_text: Optional[str] = None
    ) -> Tuple[bool, str, List[str], List[str]]:
        """
        Validates text against a list of valid citations with support checks.
        Distinguishes candidate's own background metrics from employer company claims.
        Returns:
            (is_valid: bool, cleaned_text: str, violations: List[str], rejected_sentences: List[str])
        """
        citations_by_id: Dict[str, Citation] = {c.id: c for c in valid_citations}
        valid_ids: Set[str] = set(citations_by_id.keys())
        violations: List[str] = []
        rejected_sentences: List[str] = []
        clean_sentences: List[str] = []

        # Split into individual sentences
        raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        for sentence in raw_sentences:
            if not sentence.strip():
                continue

            # Check 1: Detect fake/hallucinated citation IDs
            found_citations = re.findall(cls.CITATION_REGEX, sentence)
            fake_citations = [cid for cid in found_citations if cid not in valid_ids]
            if fake_citations:
                violations.append(f"Rejected hallucinated citation ID(s): {fake_citations} in sentence: '{sentence}'")
                rejected_sentences.append(sentence)
                continue

            # Strip citation tags to evaluate factual claims purely on sentence text
            sentence_text = re.sub(cls.CITATION_REGEX, "", sentence).strip()

            # Check 2: Detect uncited factual claims about the company vs candidate experience
            has_factual_claim = any(
                re.search(pattern, sentence_text, re.IGNORECASE) 
                for pattern in cls.FACTUAL_INDICATORS
            )

            if has_factual_claim and not found_citations:
                is_candidate_fact = False
                is_company_claim = any(
                    term in sentence_text.lower() 
                    for term in ["layoff", "laid off", "job cuts", "downsizing", "raised", "funding", "revenue", "valuation", "series"]
                )
                if not is_company_claim:
                    candidate_action_verbs = any(
                        verb in sentence_text.lower() 
                        for verb in [
                            "built", "architected", "engineered", "designed", "scaled", 
                            "led", "developed", "implemented", "reduced", "increased", 
                            "improved", "serving", "handling", "optimized", "managed"
                        ]
                    )
                    if candidate_action_verbs:
                        is_candidate_fact = True
                    elif candidate_profile_text:
                        sentence_nums = re.findall(r"\b\d+k?\b|\b\d+%", sentence_text, re.IGNORECASE)
                        if any(n.lower() in candidate_profile_text.lower() for n in sentence_nums):
                            is_candidate_fact = True

                if not is_candidate_fact:
                    violations.append(f"Rejected ungrounded factual claim lacking citation: '{sentence}'")
                    rejected_sentences.append(sentence)
                    continue

            # Check 3: Support verification (Does the cited source actually support the claim?)
            if found_citations and has_factual_claim:
                is_supported = False
                unsupported_reasons = []

                # Extract numbers from sentence (excluding citation IDs)
                numbers_in_sentence = set(re.findall(r"\b\d+%", sentence_text) + re.findall(r"\b\d+\b", sentence_text))
                # Ignore common words like 'q1', 'q2' by filtering out single digits that might just be quarters
                numbers_in_sentence = {n for n in numbers_in_sentence if len(n.replace('%','')) > 1 or '%' in n}

                sensitive_terms = [
                    w for w in ["layoff", "laid off", "cuts", "downsizing", "raised", "funding", "revenue"]
                    if w in sentence_text.lower()
                ]

                for cid in found_citations:
                    cit = citations_by_id.get(cid)
                    if not cit:
                        continue
                    evidence_corpus = f"{cit.source_title} {cit.snippet}".lower()

                    numbers_matched = [n for n in numbers_in_sentence if n.lower() in evidence_corpus]
                    terms_matched = [t for t in sensitive_terms if t in evidence_corpus]

                    if numbers_matched or terms_matched or (not numbers_in_sentence and not sensitive_terms):
                        is_supported = True
                        break
                    else:
                        unsupported_reasons.append(f"Source [{cid}] does not contain sentence facts ({numbers_in_sentence or sensitive_terms})")

                if not is_supported and (numbers_in_sentence or sensitive_terms):
                    violations.append(f"Rejected unsupported claim (citation mismatch): '{sentence}' - {'; '.join(unsupported_reasons)}")
                    rejected_sentences.append(sentence)
                    continue

            clean_sentences.append(sentence)

        is_valid = len(violations) == 0
        cleaned_text = " ".join(clean_sentences)
        return is_valid, cleaned_text, violations, rejected_sentences

    @classmethod
    def extract_cited_ids(cls, text: str) -> List[str]:
        """Extracts unique citation IDs mentioned in text."""
        return sorted(list(set(re.findall(cls.CITATION_REGEX, text))))

    @classmethod
    def simulate_hallucination_test(cls, valid_citations: List[Citation]) -> Dict:
        """
        Creates a demonstration test draft with intentional hallucinations:
        1. An unsupported factual claim (claiming 35% layoff against a funding citation).
        2. A completely fabricated citation ID [cit-99].
        Runs the validator and returns before/after comparisons for demo verification.
        """
        lead_id = valid_citations[0].id if valid_citations else "cit-01"
        draft = (
            f"I was inspired by your recent technical expansion [{lead_id}]. "
            f"The company quietly instituted a 35% headcount reduction in Q2 [{lead_id}]. "
            f"Furthermore, your planned expansion to Australia [{ 'cit-99' }] represents an exciting opportunity. "
            f"I have extensive experience architecting high-throughput backend systems."
        )

        is_valid, cleaned, violations, rejected = cls.validate_and_clean_text(draft, valid_citations)
        return {
            "original_draft": draft,
            "cleaned_result": cleaned,
            "is_valid": is_valid,
            "violations": violations,
            "rejected_sentences": rejected,
            "count_rejected": len(rejected)
        }

grounding_validator = GroundingValidator()
