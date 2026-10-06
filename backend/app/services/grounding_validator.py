import re
from typing import List, Dict, Tuple, Set
from ..models.schemas import Citation

class GroundingValidator:
    """
    Strict evidence validation guard for LLM generations.
    Ensures that every citation exists in the verified database, and every factual
    claim (numbers, layoffs, funding, reviews) is explicitly cited.
    """

    # Indicators of factual or high-impact corporate claims that require explicit citations
    FACTUAL_INDICATORS = [
        r"\b\d+%\b",                      # Percentages like 48%, 15%
        r"\b\d+\+?\s*(?:engineers|openings|roles|jobs|employees|headcount)\b", # Counts
        r"\b(?:₹|\$|rs\.?)\s*\d+",        # Monetary claims
        r"\b(?:layoff|laid off|job cuts|downsizing|workforce reduction)\b",     # Layoff claims
        r"\b(?:raised|series [a-e]|funding round|valuation)\b",                # Funding claims
        r"\b(?:rated|rating of)\s*\d+(?:\.\d+)?\b",                            # Review scores
        r"\brestructured|restructuring\b",                                     # Corporate restructuring
    ]

    CITATION_REGEX = r"\[(cit-\d+)\]"

    @classmethod
    def validate_and_clean_text(
        cls, 
        text: str, 
        valid_citations: List[Citation]
    ) -> Tuple[bool, str, List[str], List[str]]:
        """
        Validates text against a list of valid citations.
        Returns:
            (is_valid: bool, cleaned_text: str, violations: List[str], rejected_sentences: List[str])
        """
        valid_ids: Set[str] = {c.id for c in valid_citations}
        violations: List[str] = []
        rejected_sentences: List[str] = []
        clean_sentences: List[str] = []

        # Split into sentences (handling paragraphs and punctuation)
        raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        for sentence in raw_sentences:
            if not sentence.strip():
                continue

            # 1. Check for hallucinated/fake citation IDs
            found_citations = re.findall(cls.CITATION_REGEX, sentence)
            fake_citations = [cid for cid in found_citations if cid not in valid_ids]
            if fake_citations:
                violations.append(f"Rejected fake/hallucinated citation ID(s): {fake_citations} in sentence: '{sentence}'")
                rejected_sentences.append(sentence)
                continue

            # 2. Check for uncited factual claims
            has_factual_claim = any(
                re.search(pattern, sentence, re.IGNORECASE) 
                for pattern in cls.FACTUAL_INDICATORS
            )

            if has_factual_claim and not found_citations:
                violations.append(f"Rejected ungrounded factual claim lacking citation: '{sentence}'")
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

grounding_validator = GroundingValidator()
