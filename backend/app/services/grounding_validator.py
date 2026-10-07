import re
from typing import List, Dict, Tuple, Set, Optional
from ..models.schemas import Citation

class GroundingValidator:
    """
    Evidence validation guard for AI generations.
    Ensures that:
    1. Every citation token [cit-xx] maps to a valid citation in the report.
    2. Any sentence referencing the target company, "the company", "your team", or "your organization"
       requires a valid citation, unless strictly matching allowlisted greetings or application intent.
    3. Candidate experience claims: numbers, scale, latencies, and rates survive only if
       quantity and compatible unit appear within proximity in the resume text.
    4. Support checking: The cited citation must actually support the claims with at least 2 non-stopword
       content-word overlap (excluding company name) and factual verification for any numbers or sensitive terms.
    """

    STOPWORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
        "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
        "by", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
        "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
        "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
        "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
        "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should",
        "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
        "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
        "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
        "with", "would", "you", "your", "yours", "yourself", "yourselves"
    }

    FACTUAL_INDICATORS = [
        r"\b\d+%",                                                        # Percentages (e.g. 48%, 35%)
        r"\b\d+\+?\s*(?:engineers|openings|roles|jobs|employees|staff)\b",# Headcount counts
        r"(?:[\$₹]|rs\.?)\s*\d+",                                         # Monetary figures
        r"\b(?:layoff|laid off|job cuts|downsizing|headcount reduction)\b", # Layoff terms
        r"\b(?:raised|series [a-e]|funding round|valuation)\b",            # Funding terms
        r"\b(?:rated|rating of)\s*\d+(?:\.\d+)?\b",                        # Review ratings
        r"\b\d+(?:k|m|b)?\+?\s*(?:requests|reqs|users|queries|rps|tps|events|qps|dau|mau)(?:/[a-z]+)?\b", # Throughput & scale
        r"\b\d+k\b",                                                      # Shorthand thousands (e.g. 10k)
        r"\b(?:cut|cuts)\b.*\b(?:staff|employees|jobs|workforce|roles)\b",  # Workforce cuts
        r"\bcut\s+\d+%",                                                  # e.g. cut 35%
        r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds?|s|seconds?)\b",           # Latency metrics (e.g. 50ms)
        r"\b\d+(?:\.\d+)?x\b",                                            # Performance multipliers (e.g. 2x, 10x)
        r"\b\d+\+?\s*(?:years?|yrs)\b",                                   # Experience duration (e.g. 5 years)
    ]

    # Allowlist for target company mentions that do NOT require citations:
    # Strictly limited to cover letter greetings, role interest, and application courtesy.
    ALLOWLIST_APPLICATION_PATTERNS = [
        r"^(?:dear|to the|hello|hi)\s+.*hiring\s+team",
        r"^(?:dear|hello|hi)\s+[A-Za-z0-9_.\s]+,?",
        r"\b(?:apply|applying|application|candidate for)\b.*(?:\brole\b|\bposition\b|\bopportunity\b|\bteam\b|\bopening\b)",
        r"\b(?:express\s+(?:my\s+)?(?:strong\s+)?interest in)\b.*(?:\brole\b|\bposition\b|\bopportunity\b|\bteam\b|\bopening\b)",
        r"\b(?:excited|enthusiastic|thrilled|eager|delighted)\s+to\s+(?:apply|join|contribute\s+to)\b",
        r"\b(?:aligns?\s+with|contribute\s+to)\s+.*(?:mission|vision|goals?|journey|roadmaps?)\b",
        r"\bthank\s+you\s+for\s+(?:considering|reviewing|your\s+time)\b",
        r"\blook\s+forward\s+to\s+(?:discussing|speaking|hearing)\b",
    ]

    DISALLOWED_COMPANY_FACT_TERMS = [
        "layoff", "laid off", "job cuts", "downsizing", "headcount", "staff", "employees",
        "cut", "cuts", "slashed", "severance", "shut down", "closed", "office", "offices",
        "branch", "revenue", "profit", "loss", "turnover", "valuation", "series", "raised",
        "funding", "restructuring", "fired", "stepped down", "resigned", "lawsuit", "investigation",
        "announced", "expanded", "pivot", "acquired"
    ]

    CITATION_REGEX = r"\[(cit-\d+)\]"

    @classmethod
    def _check_metric_proximity(cls, qty: str, compatible_units: List[str], text: str, max_token_distance: int = 4) -> bool:
        """Verifies that a metric quantity and its compatible unit appear within proximity in candidate text."""
        tokens = re.findall(r"[a-zA-Z0-9%/+]+", text.lower())
        qty_clean = qty.lower().strip()
        qty_indices = [i for i, t in enumerate(tokens) if t == qty_clean or t.startswith(qty_clean)]
        if not qty_indices:
            return False
        for qi in qty_indices:
            start = max(0, qi - max_token_distance)
            end = min(len(tokens), qi + max_token_distance + 1)
            window_str = " ".join(tokens[start:end])
            if any(unit in window_str for unit in compatible_units):
                return True
        return False

    @classmethod
    def validate_and_clean_text(
        cls, 
        text: str, 
        valid_citations: List[Citation],
        candidate_profile_text: Optional[str] = None,
        target_company: Optional[str] = None
    ) -> Tuple[bool, str, List[str], List[str]]:
        """
        Validates text against a list of valid citations with support checks.
        Enforces:
        1. Default-deny on target company: Any sentence naming target_company or referencing
           'the company' / 'your team' / 'your organization' requires a citation unless it strictly
           matches an application greeting or role interest pattern.
        2. Candidate metrics: Candidate achievements survive only if numbers and units match resume
           with unit tied to quantity within proximity.
        3. Support check: Cited sources must contain claimed facts and at least 2 non-stopword content words overlap.
        Returns:
            (is_valid: bool, cleaned_text: str, violations: List[str], rejected_sentences: List[str])
        """
        citations_by_id: Dict[str, Citation] = {c.id: c for c in valid_citations}
        valid_ids: Set[str] = set(citations_by_id.keys())
        violations: List[str] = []
        rejected_sentences: List[str] = []
        clean_sentences: List[str] = []

        # Split into individual sentences and paragraphs
        raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if s.strip()]

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

            # Check 2: Default-Deny on Target Company or General Company Mentions without Citation
            company_ref_pattern = rf"\b(?:{re.escape(target_company.strip())}|the company|your company|your team|your organization)\b" if target_company else None
            is_company_ref = bool(company_ref_pattern and re.search(company_ref_pattern, sentence_text, re.IGNORECASE))

            if is_company_ref:
                if not found_citations:
                    s_lower = sentence_text.lower()
                    has_disallowed_fact = any(term in s_lower for term in cls.DISALLOWED_COMPANY_FACT_TERMS)
                    has_cut_or_num = any(re.search(pat, sentence_text, re.IGNORECASE) for pat in [r"\bcut\b", r"\bshut\s+down\b", r"\d+%", r"\blaid\s+off\b", r"\blayoffs?\b"])
                    is_allowlisted = (
                        any(re.search(pat, sentence_text, re.IGNORECASE) for pat in cls.ALLOWLIST_APPLICATION_PATTERNS)
                        and not has_disallowed_fact
                        and not has_cut_or_num
                    )
                    if not is_allowlisted:
                        violations.append(
                            f"Rejected ungrounded statement referencing company '{target_company or 'company'}' without citation: '{sentence}'"
                        )
                        rejected_sentences.append(sentence)
                        continue

            # Check 3: Detect uncited factual claims about company vs candidate experience
            has_factual_claim = any(
                re.search(pattern, sentence_text, re.IGNORECASE) 
                for pattern in cls.FACTUAL_INDICATORS
            )

            if has_factual_claim and not found_citations:
                is_candidate_fact = False
                
                # Check candidate action verbs
                candidate_action_verbs = any(
                    re.search(r"\b" + verb + r"\b", sentence_text, re.IGNORECASE)
                    for verb in [
                        "built", "architected", "engineered", "designed", "scaled", 
                        "led", "developed", "implemented", "reduced", "increased", 
                        "improved", "serving", "handling", "optimized", "managed",
                        "spearheaded", "created", "maintained", "deployed", "monitored",
                        "automated", "delivered", "authored", "executed", "collaborated"
                    ]
                )

                # Compound rate metrics: number + unit/frequency (e.g. 10k requests/day, 10k/day, 50 rps)
                rate_pattern = r"\b(\d+(?:\.\d+)?[kmb%]?)\s*(?:([a-zA-Z]+)\s*(?:/|per)\s*([a-zA-Z]+)|(?:/|per)\s*([a-zA-Z]+))\b"
                rate_matches = re.findall(rate_pattern, sentence_text, re.IGNORECASE)

                # Scale metrics: numbers with k, m, b, % (e.g. 10k, 35%)
                scale_metrics = re.findall(r"\b\d+(?:\.\d+)?[kmb%]\b", sentence_text, re.IGNORECASE)

                # Latency & years metrics
                latency_metrics = re.findall(r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds?)\b", sentence_text, re.IGNORECASE)
                years_metrics = re.findall(r"\b\d+\+?\s*(?:years?|yrs)\b", sentence_text, re.IGNORECASE)

                if candidate_action_verbs and candidate_profile_text:
                    profile_lower = candidate_profile_text.lower()
                    metrics_ok = True

                    # Verify rate metrics match quantity AND denominator unit within proximity in resume
                    for qty, noun, denom1, denom2 in rate_matches:
                        denom = (denom1 or denom2).lower()
                        compatible_denoms = [denom]
                        if denom in ["s", "sec", "second", "seconds"]:
                            compatible_denoms = ["/s", "sec", "second", "rps"]
                        elif denom in ["day", "days", "daily"]:
                            compatible_denoms = ["/day", "day", "daily"]
                        elif denom in ["min", "minute", "minutes"]:
                            compatible_denoms = ["/min", "minute", "min"]
                        elif denom in ["hr", "hour", "hours"]:
                            compatible_denoms = ["/hr", "hour", "hr"]
                        elif denom in ["month", "months", "monthly"]:
                            compatible_denoms = ["/month", "month", "monthly"]

                        if not cls._check_metric_proximity(qty, compatible_denoms, candidate_profile_text):
                            metrics_ok = False
                            break

                    # Verify scale metrics exist in resume
                    if metrics_ok:
                        for sm in scale_metrics:
                            if sm.lower() not in profile_lower:
                                metrics_ok = False
                                break

                    # Verify latency metrics exist in resume
                    if metrics_ok:
                        for lm in latency_metrics:
                            if lm.lower() not in profile_lower:
                                metrics_ok = False
                                break

                    # Verify years metrics exist in resume
                    if metrics_ok:
                        for ym in years_metrics:
                            if ym.lower() not in profile_lower:
                                metrics_ok = False
                                break

                    if metrics_ok:
                        is_candidate_fact = True
                elif candidate_action_verbs and not rate_matches and not scale_metrics and not latency_metrics and not years_metrics:
                    # Action statement without numbers/metrics
                    is_candidate_fact = True

                if not is_candidate_fact:
                    violations.append(f"Rejected ungrounded factual claim lacking citation: '{sentence}'")
                    rejected_sentences.append(sentence)
                    continue

            # Check 4: Support verification (Does the cited source actually support the claim with token overlap?)
            if found_citations:
                is_supported = False
                unsupported_reasons = []

                # Extract content words from sentence (alphanumeric, min length 3, excluding stopwords, target company, citation IDs)
                sent_clean = re.sub(cls.CITATION_REGEX, "", sentence_text).lower()
                sent_words = set(re.findall(r"\b[a-z]{3,}\b", sent_clean))
                company_tokens = set(re.findall(r"\b[a-z]{3,}\b", (target_company or "").lower()))
                sent_content_words = {w for w in sent_words if w not in cls.STOPWORDS and w not in company_tokens}

                # Extract numbers from sentence (excluding citation IDs)
                numbers_in_sentence = set(re.findall(r"\b\d+%", sentence_text) + re.findall(r"\b\d+\b", sentence_text))
                numbers_in_sentence = {n for n in numbers_in_sentence if len(n.replace('%','')) > 1 or '%' in n}

                sensitive_terms = [
                    w for w in ["layoff", "laid off", "cuts", "downsizing", "raised", "funding", "revenue", "loss", "restructuring"]
                    if w in sentence_text.lower()
                ]

                for cid in found_citations:
                    cit = citations_by_id.get(cid)
                    if not cit:
                        continue
                    evidence_corpus = f"{cit.source_title} {cit.snippet}".lower()
                    ev_words = set(re.findall(r"\b[a-z]{3,}\b", evidence_corpus))
                    ev_content_words = {w for w in ev_words if w not in cls.STOPWORDS and w not in company_tokens}

                    overlap = sent_content_words & ev_content_words
                    has_overlap = len(overlap) >= 2

                    numbers_matched = [n for n in numbers_in_sentence if n.lower() in evidence_corpus]
                    terms_matched = [t for t in sensitive_terms if t in evidence_corpus]

                    if numbers_in_sentence or sensitive_terms:
                        fact_supported = (bool(numbers_matched) or not numbers_in_sentence) and (bool(terms_matched) or not sensitive_terms)
                    else:
                        fact_supported = True

                    if has_overlap and fact_supported:
                        is_supported = True
                        break
                    else:
                        reasons = []
                        if not has_overlap:
                            reasons.append(f"insufficient content overlap ({len(overlap)} matching words, minimum 2 required)")
                        if not fact_supported:
                            reasons.append(f"unsupported figures/terms ({numbers_in_sentence or sensitive_terms})")
                        unsupported_reasons.append(f"Source [{cid}] mismatch: {', '.join(reasons)}")

                if not is_supported:
                    violations.append(f"Rejected unsupported claim (citation mismatch / insufficient overlap): '{sentence}' - {'; '.join(unsupported_reasons)}")
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
        lead_cit = valid_citations[0] if valid_citations else None
        lead_id = lead_cit.id if lead_cit else "cit-01"
        headline = lead_cit.source_title if lead_cit else "Expansion and Growth Updates"
        draft = (
            f"Recent public reporting highlights: “{headline}” [{lead_id}]. "
            f"The company quietly instituted a 35% headcount reduction in Q2 [{lead_id}]. "
            f"Furthermore, your planned expansion to Australia [cit-99] represents an exciting opportunity. "
            f"I have extensive experience developing backend services and systems."
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
