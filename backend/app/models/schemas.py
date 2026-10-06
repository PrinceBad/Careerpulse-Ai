from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class Citation(BaseModel):
    """Evidence citation linking any finding directly to a SerpApi search result."""
    id: str = Field(..., description="Unique citation handle, e.g. cit-01")
    engine: Literal["google_jobs", "google_news", "google", "google_trends", "google_maps"]
    source_title: str
    source_url: str
    snippet: str
    date: Optional[str] = None
    signal_type: Literal["positive", "neutral", "red_flag"] = "neutral"

class JobListing(BaseModel):
    """A real-time job posting retrieved from SerpApi google_jobs."""
    id: str
    title: str
    company_name: str
    location: str
    description: str
    via: str
    posted_at: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None  # Full-time, Contractor, etc.
    thumbnail: Optional[str] = None
    apply_link: Optional[str] = None
    match_score: int = Field(default=0, ge=0, le=100)
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)

class JobSearchRequest(BaseModel):
    query: str = Field(..., description="Target role or keyword, e.g. 'Senior Python Backend Engineer'")
    location: Optional[str] = Field(default="India", description="Target city or country")
    candidate_profile_text: Optional[str] = Field(
        default=None, 
        description="Raw resume text or extracted candidate skills for fit scoring"
    )
    remote: bool = False

class JobSearchResponse(BaseModel):
    query: str
    location: str
    total_found: int
    jobs: List[JobListing]
    is_cached: bool = False

class CompanyRiskSignals(BaseModel):
    risk_level: Literal["Low", "Medium", "High"]
    layoffs_detected: bool = False
    executive_turnover: bool = False
    litigation_or_controversy: bool = False
    risk_summary: str
    evidence_citation_ids: List[str] = Field(default_factory=list)

class CompanyCultureSignals(BaseModel):
    sentiment_rating: float = Field(ge=0.0, le=5.0, description="Estimated rating from aggregate review sentiment")
    work_life_balance_rating: Optional[float] = None
    interview_difficulty: Optional[str] = "Medium"
    top_positives: List[str] = Field(default_factory=list)
    top_complaints: List[str] = Field(default_factory=list)
    evidence_citation_ids: List[str] = Field(default_factory=list)

class SkillTrendSignal(BaseModel):
    skill_or_topic: str
    growth_verdict: Literal["Surging", "Stable", "Declining"]
    relative_interest_score: int = Field(ge=0, le=100)
    trend_description: str
    citation_id: Optional[str] = None

class OfficeLocationSignal(BaseModel):
    address: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    transit_access_note: Optional[str] = None
    maps_url: Optional[str] = None
    citation_id: Optional[str] = None

class DueDiligenceReport(BaseModel):
    """Comprehensive evidence dossier for a target employer."""
    company_name: str
    target_role: Optional[str] = None
    overall_health_verdict: Literal["Strong", "Caution", "High Risk"]
    executive_summary: str
    
    # Specific signal categories
    risks: CompanyRiskSignals
    culture: CompanyCultureSignals
    tech_trends: List[SkillTrendSignal] = Field(default_factory=list)
    location_signal: Optional[OfficeLocationSignal] = None
    
    # Consolidated Evidence Vault
    citations: List[Citation]
    is_cached: bool = False

class DueDiligenceRequest(BaseModel):
    company_name: str
    role_title: Optional[str] = None
    location: Optional[str] = "India"
    tech_stack: Optional[List[str]] = Field(default_factory=list)

class GroundedOutreachPack(BaseModel):
    company_name: str
    role_title: str
    subject_line: str
    cover_letter: str
    tailored_resume_bullets: List[str]
    # Proof of groundedness: only cite IDs from the verified citations
    cited_evidence_ids: List[str]
    citations_used: List[Citation] = Field(default_factory=list)

class OutreachRequest(BaseModel):
    company_name: str
    role_title: str
    job_description: Optional[str] = None
    candidate_profile_text: str
    due_diligence_report: DueDiligenceReport
