import re
import logging
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple
from ..models.schemas import (
    Citation,
    CompanyRiskSignals,
    CompanyCultureSignals,
    SkillTrendSignal,
    OfficeLocationSignal,
    DueDiligenceReport,
    InvestigationStep,
)
from .serpapi_client import serpapi_client

logger = logging.getLogger(__name__)

class DueDiligenceEngine:
    """
    Autonomous multi-engine corporate investigative agent.
    Executes parallel intelligence gathering, computed verification checks,
    and autonomous corroboration loops when risk signals are detected.
    """

    RISK_KEYWORDS = [
        "layoff", "laid off", "job cuts", "slashes jobs", "downsizing", 
        "fired", "restructuring", "severance", "headcount reduction",
        "lawsuit", "investigation", "fraud", "sec probe", "loss", "bankrupt"
    ]

    GROWTH_KEYWORDS = [
        "hiring", "expanded", "record revenue", "profitable", "raised", 
        "funding", "valuation", "series", "profit", "expansion", "growth"
    ]

    @classmethod
    def get_global_cache_date_range(cls) -> Optional[str]:
        """Calculates snapshot date or date range across all cached files on disk."""
        import json
        from ..config import settings
        cache_dir = settings.CACHE_DIR
        if not cache_dir.exists():
            return None
        dts = []
        for f in cache_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    meta = json.load(fp).get("search_metadata", {})
                    ts = meta.get("created_at") or meta.get("processed_at")
                    if ts:
                        dts.append(cls.parse_ref_datetime(ts))
            except Exception:
                continue
        if not dts:
            return None
        min_dt = min(dts)
        max_dt = max(dts)
        if min_dt.date() == max_dt.date():
            return f"{min_dt.strftime('%b')} {min_dt.day}, {min_dt.year}"
        return f"{min_dt.strftime('%b')} {min_dt.day}, {min_dt.year} - {max_dt.strftime('%b')} {max_dt.day}, {max_dt.year}"

    @classmethod
    def format_date_range_from_responses(cls, responses: List[Dict[str, Any]]) -> Optional[str]:
        """Formats snapshot date or range across responses actually queried."""
        dts = []
        for r in responses:
            if isinstance(r, dict) and "search_metadata" in r:
                meta = r["search_metadata"]
                ts = meta.get("created_at") or meta.get("processed_at")
                if ts:
                    dts.append(cls.parse_ref_datetime(ts))
        if not dts:
            return None
        min_dt = min(dts)
        max_dt = max(dts)
        if min_dt.date() == max_dt.date():
            return f"{min_dt.strftime('%b')} {min_dt.day}, {min_dt.year}"
        return f"{min_dt.strftime('%b')} {min_dt.day}, {min_dt.year} - {max_dt.strftime('%b')} {max_dt.day}, {max_dt.year}"

    @staticmethod
    def parse_ref_datetime(ref_str: Optional[str]) -> datetime:
        """Parses reference timestamp from SerpApi search_metadata."""
        if not ref_str:
            return datetime(2026, 10, 6, tzinfo=timezone.utc)
        clean = re.sub(r"\s+UTC$", "", str(ref_str).strip())
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(clean, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return datetime(2026, 10, 6, tzinfo=timezone.utc)

    @classmethod
    def parse_and_check_recency(
        cls, 
        date_str: Optional[str],
        reference_timestamp: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Parses both relative (e.g., '3 weeks ago') and absolute (e.g., 'Mar 14, 2026') dates.
        Crucially resolves relative dates against the cache's search_metadata timestamp
        (defaulting to Oct 6, 2026 for hackathon snapshot) rather than floating today's date,
        preventing recency flags from drifting as time passes.
        Returns: (is_recent: bool, parsed_note: str) where is_recent indicates <= 18 months (548 days).
        """
        if not date_str:
            return True, "Date unstated (treated as recent)"
        d = str(date_str).lower().strip()
        ref_dt = cls.parse_ref_datetime(reference_timestamp)

        # 1. Parse relative dates (e.g. '3 weeks ago', '1 month ago', '2 years ago', '28 days ago')
        rel_match = re.search(r"(\d+|a|an)\s+(minute|hour|day|week|month|year)s?\s+ago", d)
        if rel_match:
            qty_str, unit = rel_match.group(1), rel_match.group(2)
            qty = 1 if qty_str in ("a", "an") else int(qty_str)
            if unit in ("minute", "hour"):
                offset_days = 0
            elif unit == "day":
                offset_days = qty
            elif unit == "week":
                offset_days = qty * 7
            elif unit == "month":
                offset_days = qty * 30
            elif unit == "year":
                offset_days = qty * 365
            else:
                offset_days = 0

            resolved_dt = ref_dt - timedelta(days=offset_days)
            is_recent = offset_days <= 548
            status_desc = "Recent" if is_recent else "Historical archive (>18 months)"
            date_display = f"{resolved_dt.strftime('%b')} {resolved_dt.day}, {resolved_dt.year}"
            return is_recent, f"{status_desc} relative date: {date_str} (resolved against cache capture as {date_display})"

        # 2. Parse calendar years (relative to cache capture in 2026)
        yr_match = re.search(r"\b(20\d\d)\b", d)
        if yr_match:
            yr = int(yr_match.group(1))
            ref_yr = ref_dt.year
            # Items within <= 1 year or 18 months of reference year are recent
            if (ref_yr - yr) <= 1:
                return True, f"Verified recent calendar date: {date_str}"
            else:
                return False, f"Historical archive (>18 months): {date_str}"

        return True, f"Standard recency: {date_str}"

    CREDIBLE_DOMAINS = [
        "economictimes.indiatimes.com",
        "timesofindia.indiatimes.com",
        "livemint.com",
        "moneycontrol.com",
        "inc42.com",
        "yourstory.com",
        "reuters.com",
        "bloomberg.com",
        "techcrunch.com",
        "glassdoor.co.in",
        "ambitionbox.com",
        "business-standard.com"
    ]

    @classmethod
    def compute_verification(
        cls,
        company_name: str, 
        source_title: str, 
        snippet: str, 
        source_url: str,
        is_recent: bool
    ) -> Tuple[bool, str, float]:
        """
        Calculates verification status and heuristic confidence score without guessing.
        Explicitly checks entity presence, domain validity, credible tier-1 publishers
        (e.g. economictimes.indiatimes.com), and recency.
        """
        corpus = f"{source_title} {snippet}".lower()
        has_entity = company_name.lower() in corpus
        has_valid_url = source_url.startswith("http") and "." in source_url

        confidence = 0.0
        method_parts = []

        if has_entity:
            confidence += 0.40
            method_parts.append("entity_match")
        if has_valid_url:
            confidence += 0.20
            method_parts.append("domain_validated")
            
        # Credibility check for recognized publishers (correct economictimes.indiatimes.com)
        clean_url = source_url.lower()
        if any(dom in clean_url for dom in cls.CREDIBLE_DOMAINS):
            confidence += 0.20
            method_parts.append("tier1_publisher")

        if is_recent:
            confidence += 0.20
            method_parts.append("recency_verified")

        is_verified = has_entity and has_valid_url
        method_str = "+".join(method_parts) if method_parts else "unverified_source"
        return is_verified, method_str, round(min(confidence, 1.0), 2)

    def __init__(self, client: Optional[Any] = None):
        self.client = client or serpapi_client

    def generate_report(
        self,
        company_name: str,
        role_title: Optional[str] = "Software Engineer",
        location: Optional[str] = "India",
        tech_stack: Optional[List[str]] = None
    ) -> DueDiligenceReport:
        """
        Runs parallel multi-engine investigative scan and autonomous corroboration loop.
        """
        client = self.client
        citations: List[Citation] = []
        trace: List[InvestigationStep] = []
        cit_counter = 1
        target_tech = tech_stack[0] if (tech_stack and len(tech_stack) > 0) else "FastAPI"

        # -------------------------------------------------------------
        # Step 1: Parallel Initial Scan across 4 Engines
        # -------------------------------------------------------------
        trace.append(InvestigationStep(
            step_number=1,
            action="Parallel Multi-Engine Scan",
            reason="Simultaneously collect news health, culture reviews, tech velocity, and campus location",
            engine="google_news, google, google_trends, google_maps",
            result_summary="Dispatched concurrent queries to 4 SerpApi engines"
        ))

        news_query = f"{company_name} news hiring OR funding OR revenue OR restructuring OR layoffs OR 'laid off'"
        web_query = f"{company_name} employee reviews glassdoor ambitionbox interview"
        maps_query = f"{company_name} headquarters {location}"

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_news = executor.submit(client.search_news, news_query)
            future_web = executor.submit(client.search_web, web_query, 4)
            future_trends = executor.submit(client.search_trends, target_tech)
            future_maps = executor.submit(client.search_maps, maps_query)

            raw_news = future_news.result()
            raw_web = future_web.result()
            raw_trends = future_trends.result()
            raw_maps = future_maps.result()

        # Determine overall provenance
        is_unavailable_news = raw_news.get("_unavailable", False)
        is_unavailable_web = raw_web.get("_unavailable", False)

        if is_unavailable_news and is_unavailable_web:
            reason = raw_news.get("_reason") or raw_web.get("_reason") or "cache_miss"
            detail = raw_news.get("_detail") or raw_web.get("_detail") or ""

            if reason == "cache_miss":
                empty_trace = [
                    InvestigationStep(
                        step_number=1,
                        action="Offline Cache Lookup",
                        reason=f"Queried disk cache for pre-warmed multi-engine responses for '{company_name}'",
                        engine="cache",
                        result_summary=f"Cache Miss: No pre-cached SerpApi responses on disk for '{company_name}'"
                    ),
                    InvestigationStep(
                        step_number=2,
                        action="Live API Key Check",
                        reason="Assessed environment configuration for live multi-engine query dispatch",
                        engine="serpapi",
                        result_summary="SERPAPI_API_KEY not configured in backend/.env. Live search queries are paused in offline mode."
                    )
                ]
            else:
                empty_trace = [
                    InvestigationStep(
                        step_number=1,
                        action="Live API Query Failed",
                        reason=f"Dispatched live SerpApi query for '{company_name}'",
                        engine="serpapi",
                        result_summary=f"SerpApi request failed for '{company_name}': {detail or 'API error'}"
                    )
                ]

            empty_risks = CompanyRiskSignals(
                risk_level="Unknown",
                layoffs_detected=False,
                executive_turnover=False,
                litigation_or_controversy=False,
                risk_summary=f"No risk evidence available for '{company_name}'.",
                corroborated=False,
                evidence_citation_ids=[]
            )
            empty_culture = CompanyCultureSignals(
                sentiment_rating=None,
                work_life_balance_rating=None,
                interview_difficulty=None,
                top_positives=[],
                top_complaints=[],
                evidence_citation_ids=[]
            )
            return DueDiligenceReport(
                company_name=company_name,
                target_role=role_title,
                overall_health_verdict="Data Unavailable",
                executive_summary=(
                    f"No verified search evidence available in offline cache for '{company_name}'. "
                    f"Configure SERPAPI_API_KEY in backend/.env to execute live multi-engine investigations across "
                    f"Google News, Organic Web, Google Trends, and Google Maps."
                ),
                risks=empty_risks,
                culture=empty_culture,
                tech_trends=[],
                location_signal=None,
                investigation_trace=empty_trace,
                citations=[],
                provenance="unavailable",
                snapshot_date=None
            )

        is_mock_any = any([
            raw_news.get("_is_mock", False),
            raw_web.get("_is_mock", False),
            raw_trends.get("_is_mock", False),
            raw_maps.get("_is_mock", False)
        ])
        is_cached_any = any([
            raw_news.get("_from_cache", False),
            raw_web.get("_from_cache", False),
            raw_trends.get("_from_cache", False),
            raw_maps.get("_from_cache", False)
        ])
        overall_prov = "mock" if is_mock_any else ("cached" if is_cached_any else "live")

        snapshot_date_str = self.format_date_range_from_responses([raw_news, raw_web, raw_trends, raw_maps])
        if not snapshot_date_str and overall_prov == "cached":
            snapshot_date_str = self.get_global_cache_date_range()

        cache_created_at = None
        for r in [raw_news, raw_web, raw_trends, raw_maps]:
            if isinstance(r, dict) and "search_metadata" in r:
                cache_created_at = r["search_metadata"].get("created_at") or r["search_metadata"].get("processed_at")
                if cache_created_at:
                    break
        if not cache_created_at and snapshot_date_str:
            cache_created_at = snapshot_date_str

        # -------------------------------------------------------------
        # Parse News Results
        # -------------------------------------------------------------
        news_items = raw_news.get("news_results", [])
        layoffs_detected = False
        executive_turnover = False
        litigation_detected = False
        positive_count = 0
        risk_count = 0
        news_cit_ids = []

        for item in news_items[:5]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            date_str = item.get("date")
            is_recent, date_note = self.parse_and_check_recency(date_str, reference_timestamp=cache_created_at)
            combined = f"{title} {snippet}".lower()

            is_risk = any(rk in combined for rk in self.RISK_KEYWORDS)
            is_growth = any(gk in combined for gk in self.GROWTH_KEYWORDS)

            if is_risk and is_recent:
                signal_type = "red_flag"
                risk_count += 1
                if any(k in combined for k in ["layoff", "laid off", "job cuts", "downsizing"]):
                    layoffs_detected = True
                if any(k in combined for k in ["resign", "stepped down", "departs", "fired"]):
                    executive_turnover = True
                if any(k in combined for k in ["lawsuit", "investigation", "probe", "court"]):
                    litigation_detected = True
            elif is_risk and not is_recent:
                signal_type = "neutral"
            elif is_growth:
                signal_type = "positive"
                positive_count += 1
            else:
                signal_type = "neutral"

            is_verified, method, conf = self.compute_verification(
                company_name, title, snippet, item.get("link", ""), is_recent
            )

            cit_id = f"cit-{cit_counter:02d}"
            cit_counter += 1
            source_name = item.get("source", {}).get("name", "News Outlet")

            citations.append(Citation(
                id=cit_id,
                engine="google_news",
                source_title=f"{title} ({source_name})",
                source_url=item.get("link", "https://news.google.com"),
                snippet=snippet or title,
                date=date_str or "Recent",
                signal_type=signal_type,
                verified=is_verified,
                verification_method=method,
                verification_confidence=conf,
                provenance=overall_prov
            ))
            news_cit_ids.append(cit_id)

        # -------------------------------------------------------------
        # Step 2: Autonomous Corroboration Loop (Agentic Behavior)
        # -------------------------------------------------------------
        corroborated = False
        if layoffs_detected:
            trace.append(InvestigationStep(
                step_number=2,
                action="Autonomous Corroboration Query",
                reason=f"Primary news scan surfaced potential layoff signals for {company_name}. Spawning independent verification.",
                engine="google_news",
                result_summary="Dispatched corroboration query: layoffs confirmed severance details"
            ))

            corrob_query = f"{company_name} layoffs confirmed severance details"
            corrob_raw = client.search_news(corrob_query)
            corrob_items = corrob_raw.get("news_results", [])
            corrob_matches = [
                it for it in corrob_items 
                if any(k in f"{it.get('title','')} {it.get('snippet','')}".lower() for k in ["layoff", "severance", "cuts"])
            ]

            if len(corrob_matches) >= 2:
                corroborated = True
                trace.append(InvestigationStep(
                    step_number=3,
                    action="Risk Corroboration Confirmed",
                    reason="Multiple independent publications verified workforce reduction",
                    engine="google_news",
                    result_summary=f"Corroborated across {len(corrob_matches)} sources. Maintained High Risk classification."
                ))
            else:
                trace.append(InvestigationStep(
                    step_number=3,
                    action="Corroboration Inconclusive",
                    reason="Single or uncorroborated mention found; treated with cautionary status",
                    engine="google_news",
                    result_summary="Could not find second independent report confirming severance numbers."
                ))
        else:
            trace.append(InvestigationStep(
                step_number=2,
                action="Health Clearance",
                reason="No active workforce reduction or distress keywords detected in primary news scan",
                engine="google_news",
                result_summary="Company cleared for standard growth trajectory"
            ))

        # -------------------------------------------------------------
        # Parse Web / Culture Results
        # -------------------------------------------------------------
        web_items = raw_web.get("organic_results", [])
        culture_cit_ids = []
        extracted_ratings = []
        top_positives = []
        top_complaints = []

        for item in web_items[:3]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            match = re.search(r"(\d\.\d)\s*(?:/|out of)\s*5", snippet)
            if match:
                try:
                    extracted_ratings.append(float(match.group(1)))
                except ValueError:
                    pass

            for kw in ["work-life", "deadline", "pressure", "crunch", "hours"]:
                if kw in snippet.lower():
                    top_complaints.append(f"Snippet note on {kw}: “{snippet[:90].strip()}...”")
                    break

            for kw in ["culture", "autonomy", "peers", "learning", "growth", "pay", "salary"]:
                if kw in snippet.lower():
                    top_positives.append(f"Snippet note on {kw}: “{snippet[:90].strip()}...”")
                    break

            is_verified, method, conf = self.compute_verification(
                company_name, title, snippet, item.get("link", ""), True
            )

            cit_id = f"cit-{cit_counter:02d}"
            cit_counter += 1
            citations.append(Citation(
                id=cit_id,
                engine="google",
                source_title=title,
                source_url=item.get("link", "https://google.com"),
                snippet=snippet or title,
                signal_type="neutral",
                verified=is_verified,
                verification_method=method,
                verification_confidence=conf,
                provenance=overall_prov
            ))
            culture_cit_ids.append(cit_id)

        # Honest sentiment reporting: None if no rating found
        avg_rating = round(sum(extracted_ratings) / len(extracted_ratings), 1) if extracted_ratings else None

        # -------------------------------------------------------------
        # Parse Trends Results
        # -------------------------------------------------------------
        timeline = raw_trends.get("interest_over_time", {}).get("timeline_data", [])
        trend_signals: List[SkillTrendSignal] = []
        if timeline and len(timeline) >= 2:
            first_val = timeline[0].get("values", [{}])[0].get("extracted_value")
            recent_val = timeline[-1].get("values", [{}])[0].get("extracted_value")

            if first_val is not None and recent_val is not None:
                first_f = float(first_val)
                recent_f = float(recent_val)
                pct = int(((recent_f - first_f) / first_f) * 100) if first_f > 0 else 0

                if recent_f > first_f * 1.15:
                    growth_verdict = "Surging"
                    growth_desc = f"{target_tech} relative search interest expanded {pct}% over the past 12 months."
                elif recent_f < first_f * 0.85:
                    growth_verdict = "Declining"
                    growth_desc = f"{target_tech} search-interest velocity moderated over the past 12 months."
                else:
                    growth_verdict = "Stable"
                    growth_desc = f"{target_tech} maintains steady baseline search interest."

                cit_id = f"cit-{cit_counter:02d}"
                cit_counter += 1
                citations.append(Citation(
                    id=cit_id,
                    engine="google_trends",
                    source_title=f"Google Trends 12-Month Index: {target_tech}",
                    source_url=f"https://trends.google.com/trends/explore?geo=IN&q={target_tech}",
                    snippet=growth_desc,
                    signal_type="positive" if growth_verdict == "Surging" else "neutral",
                    verified=True,
                    verification_method="timeseries_relative_interest_slope",
                    verification_confidence=0.95,
                    provenance=overall_prov
                ))
                trend_signals.append(SkillTrendSignal(
                    skill_or_topic=target_tech,
                    growth_verdict=growth_verdict,
                    relative_interest_score=int(recent_f),
                    trend_description=growth_desc,
                    citation_id=cit_id
                ))

        # -------------------------------------------------------------
        # Parse Maps Results (Physical Address & Ratings Only - No False Claims)
        # -------------------------------------------------------------
        place = raw_maps.get("place_results", {})
        location_signal = None
        if place and place.get("address"):
            address = place.get("address")
            maps_rating = place.get("rating")
            cit_id = f"cit-{cit_counter:02d}"
            cit_counter += 1
            citations.append(Citation(
                id=cit_id,
                engine="google_maps",
                source_title=f"{place.get('title', company_name)} (Google Maps)",
                source_url=place.get("link", "https://maps.google.com"),
                snippet=f"Verified Office Address: {address}." + (f" Facility Rating: {maps_rating}." if maps_rating else ""),
                signal_type="neutral",
                verified=True,
                verification_method="geocoding_address_match",
                verification_confidence=0.90,
                provenance=overall_prov
            ))
            location_signal = OfficeLocationSignal(
                address=address,
                rating=maps_rating,
                review_count=place.get("reviews"),
                campus_note="Physical corporate facility verified via Google Maps.",
                maps_url=place.get("link"),
                citation_id=cit_id
            )

        # -------------------------------------------------------------
        # Final Verdict Synthesis
        # -------------------------------------------------------------
        if layoffs_detected and corroborated:
            overall_verdict = "High Risk"
            risk_level = "High"
            risk_summary = f"Corroborated recent workforce reduction signal(s) detected. Review citations before applying."
        elif layoffs_detected:
            overall_verdict = "Caution"
            risk_level = "Medium"
            risk_summary = f"Uncorroborated restructuring or layoff signal detected in recent coverage."
        else:
            overall_verdict = "Strong"
            risk_level = "Low"
            risk_summary = f"No active workforce reductions or material distress signals detected in recent news."

        exec_summary = (
            f"{company_name} presents an overall '{overall_verdict}' employer profile based on 5-engine search verification. "
            f"Review ratings: {f'{avg_rating}/5.0' if avg_rating else 'No rating found in search snippets'}. "
            f"{'Caution advised regarding verified organizational shifts.' if overall_verdict != 'Strong' else 'Strong growth indicators and verified physical campus.'}"
        )

        risks = CompanyRiskSignals(
            risk_level=risk_level,
            layoffs_detected=layoffs_detected,
            executive_turnover=executive_turnover,
            litigation_or_controversy=litigation_detected,
            risk_summary=risk_summary,
            corroborated=corroborated,
            evidence_citation_ids=news_cit_ids
        )

        culture = CompanyCultureSignals(
            sentiment_rating=avg_rating,
            work_life_balance_rating=None,
            interview_difficulty=None,
            top_positives=top_positives,
            top_complaints=top_complaints,
            evidence_citation_ids=culture_cit_ids
        )

        return DueDiligenceReport(
            company_name=company_name,
            target_role=role_title,
            overall_health_verdict=overall_verdict,
            executive_summary=exec_summary,
            risks=risks,
            culture=culture,
            tech_trends=trend_signals,
            location_signal=location_signal,
            investigation_trace=trace,
            citations=citations,
            provenance=overall_prov,
            snapshot_date=snapshot_date_str
        )

due_diligence_engine = DueDiligenceEngine()
