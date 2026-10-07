import os
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .models.schemas import (
    JobSearchRequest,
    JobSearchResponse,
    JobListing,
    DueDiligenceRequest,
    DueDiligenceReport,
    OutreachRequest,
    GroundedOutreachPack,
)
from .services.serpapi_client import serpapi_client
from .services.resume_parser import resume_parser
from .services.due_diligence import due_diligence_engine
from .services.llm_service import llm_service

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Evidence-backed career intelligence and employer due-diligence agent powered by SerpApi."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------

@app.get("/api/health")
def health_check():
    cache_count = len(list(settings.CACHE_DIR.glob("*.json"))) if settings.CACHE_DIR.exists() else 0
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "serpapi_key_configured": bool(settings.SERPAPI_API_KEY),
        "cache_enabled": settings.SERPAPI_CACHE_ENABLED,
        "cached_queries_count": cache_count,
        "llm_provider": settings.LLM_PROVIDER
    }

@app.post("/api/resume/parse")
async def parse_resume(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    """Extracts technical skills and competencies from resume file or pasted text."""
    content = ""
    if file and file.filename:
        file_bytes = await file.read()
        if file.filename.lower().endswith(".pdf"):
            content = resume_parser.extract_text_from_pdf(file_bytes)
        else:
            content = file_bytes.decode("utf-8", errors="ignore")
    elif raw_text:
        content = raw_text
    else:
        raise HTTPException(status_code=400, detail="Provide either a file upload or raw_text")

    skills = resume_parser.extract_skills(content)
    return {
        "extracted_skills": skills,
        "character_count": len(content),
        "preview": content[:300] + ("..." if len(content) > 300 else "")
    }

@app.post("/api/jobs/search", response_model=JobSearchResponse)
def search_jobs(request: JobSearchRequest):
    """Searches real-time jobs via SerpApi google_jobs and calculates skill match scores."""
    raw = serpapi_client.search_jobs(query=request.query, location=request.location or "India")
    job_results = raw.get("jobs_results", [])
    
    parsed_jobs: List[JobListing] = []
    for item in job_results:
        desc = item.get("description", "")
        # Compute match score based on candidate profile if provided
        score, matching, missing = resume_parser.calculate_match(
            request.candidate_profile_text or "", 
            desc
        )
        
        ext = item.get("detected_extensions", {})
        parsed_jobs.append(
            JobListing(
                id=item.get("job_id", f"job-{len(parsed_jobs)}"),
                title=item.get("title", request.query),
                company_name=item.get("company_name", "Unknown Company"),
                location=item.get("location", request.location or "India"),
                description=desc,
                via=item.get("via", "Direct"),
                posted_at=ext.get("posted_at"),
                salary=ext.get("salary"),
                job_type=ext.get("schedule_type"),
                thumbnail=item.get("thumbnail"),
                apply_link=item.get("share_link") or item.get("apply_link"),
                match_score=score,
                matching_skills=matching,
                missing_skills=missing
            )
        )

    # Sort jobs by match_score descending
    parsed_jobs.sort(key=lambda j: j.match_score, reverse=True)
    prov = "mock" if raw.get("_is_mock") else ("cached" if raw.get("_from_cache") else "live")
    snapshot_date = None
    if isinstance(raw, dict) and "search_metadata" in raw:
        meta_ts = raw["search_metadata"].get("created_at") or raw["search_metadata"].get("processed_at")
        if meta_ts:
            dt = due_diligence_engine.parse_ref_datetime(meta_ts)
            snapshot_date = f"{dt.strftime('%b')} {dt.day}, {dt.year}"
    elif prov == "cached":
        snapshot_date = "Oct 6, 2026"

    return JobSearchResponse(
        query=request.query,
        location=request.location or "India",
        total_found=len(parsed_jobs),
        jobs=parsed_jobs,
        provenance=prov,
        snapshot_date=snapshot_date
    )

@app.post("/api/company/due-diligence", response_model=DueDiligenceReport)
def company_due_diligence(request: DueDiligenceRequest):
    """Executes 5-engine SerpApi investigative scan for employer due-diligence."""
    return due_diligence_engine.generate_report(
        company_name=request.company_name,
        role_title=request.role_title,
        location=request.location or "India",
        tech_stack=request.tech_stack
    )

@app.post("/api/outreach/generate", response_model=GroundedOutreachPack)
def generate_grounded_outreach(request: OutreachRequest):
    """Generates outreach email and bullets strictly referencing verified citations."""
    return llm_service.generate_grounded_outreach(
        company_name=request.company_name,
        role_title=request.role_title,
        candidate_profile=request.candidate_profile_text,
        citations=request.due_diligence_report.citations
    )

@app.post("/api/guard/simulate-hallucination")
def simulate_hallucination_endpoint(request: DueDiligenceReport):
    """Demonstrates Beat 3: Injects an ungrounded claim and fake citation to prove guard interception."""
    from .services.grounding_validator import grounding_validator
    return grounding_validator.simulate_hallucination_test(request.citations)

# -------------------------------------------------------------
# Frontend Static Mount
# -------------------------------------------------------------
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
    if (frontend_dir / "css").exists():
        app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
    if (frontend_dir / "js").exists():
        app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")

    @app.get("/")
    def serve_frontend_root():
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "CareerPulse AI API running. Frontend index.html not yet built."}
