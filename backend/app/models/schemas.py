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
    verified: bool = Field(..., description="Computed verification: True if company entity and domain verified")
    verification_method: str = Field(..., description="Specific heuristic or check applied to verify citation")
    verification_confidence: float = Field(..., ge=0.0, le=1.0, description="Algorithmic confidence score")
    provenance: Literal["live", "cached", "mock", "unavailable"] = Field(default="cached")

class InvestigationStep(BaseModel):
    """A trace step taken by the autonomous agent during investigation."""
    step_number: int
    action: str
    reason: str
    engine: str
    result_summary: str

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
    provenance: Literal["live", "cached", "mock", "unavailable"] = "cached"
    snapshot_date: Optional[str] = None
    error_reason: Optional[str] = None

class CompanyRiskSignals(BaseModel):
    risk_level: Literal["Low", "Medium", "High", "Unknown"]
    layoffs_detected: bool = False
    executive_turnover: bool = False
    litigation_or_controversy: bool = False
    risk_summary: str
    corroborated: bool = False
    evidence_citation_ids: List[str] = Field(default_factory=list)

class CompanyCultureSignals(BaseModel):
    sentiment_rating: Optional[float] = Field(default=None, description="Extracted rating or None if not found in snippets")
    work_life_balance_rating: Optional[float] = None
    interview_difficulty: Optional[str] = None
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
    campus_note: Optional[str] = None
    maps_url: Optional[str] = None
    citation_id: Optional[str] = None

class DueDiligenceReport(BaseModel):
    """Comprehensive evidence dossier for a target employer."""
    company_name: str
    target_role: Optional[str] = None
    overall_health_verdict: Literal["Strong", "Caution", "High Risk", "Data Unavailable"]
    executive_summary: str
    
    # Specific signal categories
    risks: CompanyRiskSignals
    culture: CompanyCultureSignals
    tech_trends: List[SkillTrendSignal] = Field(default_factory=list)
    location_signal: Optional[OfficeLocationSignal] = None
    
    # Autonomous Investigation Trace
    investigation_trace: List[InvestigationStep] = Field(default_factory=list)
    
    # Consolidated Evidence Vault
    citations: List[Citation]
    provenance: Literal["live", "cached", "mock", "unavailable"] = "cached"
    snapshot_date: Optional[str] = None

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
    cited_evidence_ids: List[str]
    citations_used: List[Citation] = Field(default_factory=list)
    provenance: Literal["live", "cached", "mock", "unavailable"] = "cached"
    validation_status: str = "strictly_verified"
    blocked_claims: List[str] = Field(default_factory=list)

class OutreachRequest(BaseModel):
    company_name: str
    role_title: str
    job_description: Optional[str] = None
    candidate_profile_text: str
    due_diligence_report: DueDiligenceReport
