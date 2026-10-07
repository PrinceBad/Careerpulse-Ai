import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests
from ..config import settings
from ..models.schemas import Citation, GroundedOutreachPack
from .grounding_validator import grounding_validator

from .resume_parser import resume_parser

logger = logging.getLogger(__name__)

class LLMService:
    """Pluggable LLM provider with strict citation grounding and validation."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.gemini_key = settings.GEMINI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL
        self.openai_key = settings.OPENAI_API_KEY

    def generate_grounded_outreach(
        self,
        company_name: str,
        role_title: str,
        candidate_profile: str,
        citations: List[Citation]
    ) -> GroundedOutreachPack:
        """
        Generates an outreach pack and strictly validates citations and factual claims.
        """
        # Format citations as an evidence reference catalog
        evidence_catalog = []
        for c in citations:
            evidence_catalog.append(f"[{c.id}] ({c.engine}) {c.source_title}: {c.snippet} (URL: {c.source_url})")
        evidence_text = "\n".join(evidence_catalog)

        # 1. Try Gemini if configured
        pack = None
        if self.provider == "gemini" and self.gemini_key:
            try:
                pack = self._call_gemini(company_name, role_title, candidate_profile, citations, evidence_text)
            except Exception as e:
                logger.warning(f"Gemini call failed, falling back to deterministic generator: {e}")

        # 2. Try OpenAI if configured
        if not pack and self.provider == "openai" and self.openai_key:
            try:
                pack = self._call_openai(company_name, role_title, candidate_profile, citations, evidence_text)
            except Exception as e:
                logger.warning(f"OpenAI call failed, falling back to deterministic generator: {e}")

        # 3. Deterministic Evidence-Grounded Fallback (zero-credit, reproducible, offline)
        if not pack:
            pack = self._deterministic_grounded_pack(company_name, role_title, candidate_profile, citations)

        # 4. Strict Code-Level Grounding Validation & Sanitization
        is_valid_letter, clean_letter, letter_violations, _ = grounding_validator.validate_and_clean_text(
            pack.cover_letter, citations, candidate_profile_text=candidate_profile, target_company=company_name
        )
        clean_bullets = []
        all_violations = list(letter_violations)

        for bullet in pack.tailored_resume_bullets:
            is_valid_b, clean_b, b_violations, _ = grounding_validator.validate_and_clean_text(
                bullet, citations, candidate_profile_text=candidate_profile, target_company=company_name
            )
            if clean_b:
                clean_bullets.append(clean_b)
            all_violations.extend(b_violations)

        # Extract strictly verified IDs
        verified_letter_ids = grounding_validator.extract_cited_ids(clean_letter)
        verified_bullet_ids = []
        for b in clean_bullets:
            verified_bullet_ids.extend(grounding_validator.extract_cited_ids(b))

        final_cited_ids = sorted(list(set(verified_letter_ids + verified_bullet_ids)))
        used_citations = [c for c in citations if c.id in final_cited_ids]
        
        if not citations:
            prov = "unavailable"
        elif any(c.provenance == "unavailable" for c in citations):
            prov = "unavailable"
        elif any(c.provenance == "mock" for c in citations):
            prov = "mock"
        elif any(c.provenance == "cached" for c in citations):
            prov = "cached"
        else:
            prov = "live"

        pack.cover_letter = clean_letter
        pack.tailored_resume_bullets = clean_bullets
        pack.cited_evidence_ids = final_cited_ids
        pack.citations_used = used_citations
        pack.provenance = prov
        pack.validation_status = "strictly_verified" if not all_violations else "sanitized_grounded"
        pack.blocked_claims = all_violations

        return pack

    def _call_gemini(
        self, 
        company_name: str, 
        role_title: str, 
        candidate_profile: str, 
        citations: List[Citation], 
        evidence_text: str
    ) -> GroundedOutreachPack:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        headers = {
            "x-goog-api-key": self.gemini_key,
            "Content-Type": "application/json"
        }
        prompt = f"""
You are an expert career intelligence strategist.
Write a personalized, evidence-backed outreach email and 3 tailored resume bullet points for a candidate applying to {company_name} for the position of {role_title}.

STRICT GROUNDING RULE:
You must weave in facts from the verified evidence catalog below. Every claim about the company (growth, tech stack, leadership, expansion, culture) MUST end with its bracketed citation ID like [cit-01]. Do NOT fabricate ungrounded claims.

EVIDENCE CATALOG:
{evidence_text}

CANDIDATE PROFILE:
{candidate_profile}

Return ONLY valid JSON in this exact structure:
{{
  "subject_line": "...",
  "cover_letter": "...",
  "tailored_resume_bullets": ["bullet 1 with citation", "bullet 2 with citation", "bullet 3"],
  "cited_evidence_ids": ["cit-01", "cit-02"]
}}
"""
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            data = res.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Extract JSON block
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw_text)
            
            used_citations = [c for c in citations if c.id in parsed.get("cited_evidence_ids", [])]
            return GroundedOutreachPack(
                company_name=company_name,
                role_title=role_title,
                subject_line=parsed.get("subject_line", f"Application for {role_title} - {company_name}"),
                cover_letter=parsed.get("cover_letter", ""),
                tailored_resume_bullets=parsed.get("tailored_resume_bullets", []),
                cited_evidence_ids=parsed.get("cited_evidence_ids", []),
                citations_used=used_citations
            )
        raise RuntimeError(f"Gemini API error: {res.status_code}")

    def _call_openai(
        self,
        company_name: str,
        role_title: str,
        candidate_profile: str,
        citations: List[Citation],
        evidence_text: str
    ) -> GroundedOutreachPack:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        prompt = f"""
Write an evidence-grounded outreach pack for {company_name} for {role_title}.
Every company claim MUST cite [cit-XX] from this catalog:
{evidence_text}

CANDIDATE:
{candidate_profile}

Respond with pure JSON:
{{
  "subject_line": "...",
  "cover_letter": "...",
  "tailored_resume_bullets": ["bullet 1", "bullet 2"],
  "cited_evidence_ids": ["cit-01"]
}}
"""
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            parsed = res.json()["choices"][0]["message"]["content"]
            parsed_data = json.loads(parsed)
            used_citations = [c for c in citations if c.id in parsed_data.get("cited_evidence_ids", [])]
            return GroundedOutreachPack(
                company_name=company_name,
                role_title=role_title,
                subject_line=parsed_data.get("subject_line", f"Application for {role_title}"),
                cover_letter=parsed_data.get("cover_letter", ""),
                tailored_resume_bullets=parsed_data.get("tailored_resume_bullets", []),
                cited_evidence_ids=parsed_data.get("cited_evidence_ids", []),
                citations_used=used_citations
            )
        raise RuntimeError(f"OpenAI API error: {res.status_code}")

    def _deterministic_grounded_pack(
        self,
        company_name: str,
        role_title: str,
        candidate_profile: str,
        citations: List[Citation]
    ) -> GroundedOutreachPack:
        """
        Deterministic, offline-safe generator that builds verified outreach
        referencing exact citations and extracted candidate skills without inventing metrics.
        """
        cited_ids = []
        positive_news = [c for c in citations if c.engine == "google_news" and c.signal_type == "positive"]
        reviews = [c for c in citations if c.engine == "google"]
        trends = [c for c in citations if c.engine == "google_trends"]

        # 1. Quote actual verified citations to prevent citation laundering
        hook_quote = ""
        lead_cit = positive_news[0] if positive_news else (citations[0] if citations else None)
        if lead_cit:
            cited_ids.append(lead_cit.id)
            hook_quote = f"Recent news coverage highlights: “{lead_cit.source_title}” [{lead_cit.id}]."

        culture_hook = ""
        rev_cit = reviews[0] if reviews else None
        if rev_cit:
            cited_ids.append(rev_cit.id)
            culture_hook = f"Public employee reviews note: “{rev_cit.source_title}” [{rev_cit.id}]."

        trend_hook = ""
        trend_cit = trends[0] if trends else None
        if trend_cit:
            cited_ids.append(trend_cit.id)
            trend_hook = f"Industry search trends indicate: “{trend_cit.snippet}” [{trend_cit.id}]."

        # 2. Extract real candidate skills instead of inventing years or throughput metrics
        extracted_skills = resume_parser.extract_skills(candidate_profile)
        if extracted_skills:
            primary_skill = extracted_skills[0]
            secondary_skill = extracted_skills[1] if len(extracted_skills) > 1 else extracted_skills[0]
            skills_str = ", ".join(extracted_skills[:4])
            candidate_sentence = f"In my technical background, I have developed software systems with a focus on {skills_str}."
        else:
            primary_skill = "Python"
            secondary_skill = "software architecture"
            candidate_sentence = "In my technical background, I have developed software services and modular backend applications."

        subject_line = f"Application: {role_title} | {company_name}"

        cover_letter_parts = [
            f"Dear {company_name} Hiring Team,",
            f"I am writing to express my strong interest in the {role_title} opening.",
        ]
        if hook_quote:
            cover_letter_parts.append(hook_quote)
        
        body_parts = [candidate_sentence]
        if culture_hook:
            body_parts.append(culture_hook)
        if trend_hook:
            body_parts.append(trend_hook)
        cover_letter_parts.append(" ".join(body_parts))

        cover_letter_parts.append(
            f"I would welcome the opportunity to discuss how my engineering background aligns with {company_name}'s technical roadmap."
        )
        cover_letter_parts.append("Thank you for considering my application.")
        cover_letter_parts.append("Sincerely,\nCandidate (via CareerPulse AI)")

        cover_letter = "\n\n".join(cover_letter_parts)

        # 3. Bullets referencing actual skills and verified citations
        tailored_bullets = []
        if lead_cit:
            tailored_bullets.append(
                f"Engineered modular services utilizing {primary_skill}, aligning with technical priorities highlighted in recent coverage [{lead_cit.id}]."
            )
        else:
            tailored_bullets.append(
                f"Engineered modular backend services and APIs utilizing {primary_skill}."
            )

        if rev_cit:
            tailored_bullets.append(
                f"Implemented software workflows with {secondary_skill}, consistent with operational practices reflected in employee reviews [{rev_cit.id}]."
            )
        else:
            tailored_bullets.append(
                f"Implemented software workflows and application architecture with {secondary_skill}."
            )

        tailored_bullets.append(
            f"Applied engineering practices across {extracted_skills[2] if len(extracted_skills) > 2 else 'distributed software'} to build reliable, maintainable code."
        )

        used_citations = [c for c in citations if c.id in cited_ids]

        return GroundedOutreachPack(
            company_name=company_name,
            role_title=role_title,
            subject_line=subject_line,
            cover_letter=cover_letter.strip(),
            tailored_resume_bullets=tailored_bullets,
            cited_evidence_ids=cited_ids,
            citations_used=used_citations
        )

llm_service = LLMService()
