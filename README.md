# ⚡ CareerPulse AI

> **Autonomous Investigative Career Intelligence & Evidence-Backed Due-Diligence Agent**  
> Powered by SerpApi Multi-Engine Search · Built for the **SerpApi India Hackathon 2026** (PyDelhi Community Submission)

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![SerpApi](https://img.shields.io/badge/SerpApi-5%20Engines%20Integrated-orange.svg)](https://serpapi.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 💡 The Core Problem & The "Winning Angle"

Most AI job tools fail because they are simple **search-and-summarizers**: they query job boards, pass the text to an LLM, and hallucinate company details or churn out generic, ungrounded cover letters.

**CareerPulse AI** transforms this into an **Autonomous Investigative Verification Agent**:
1. **Evidence-Grounded Intelligence**: Every corporate health signal (layoffs, funding, leadership moves, Glassdoor sentiment) is backed by an explicit **SerpApi Citation** (`[cit-01]`, `[cit-02]`, etc.) containing the verified source URL, timestamp, and snippet.
2. **Zero-Hallucination Outreach**: Generated application packs (cover letters and tailored resume bullets) are strictly constrained to only cite verified facts from the SerpApi evidence vault.
3. **Multi-Engine SerpApi Fusion**: Instead of a cosmetic single API call, CareerPulse orchestrates **5 specialized SerpApi engines**, each powering a dedicated, real-time UI widget.

---

## 🔍 SerpApi Engine Architecture

CareerPulse utilizes 5 distinct SerpApi engines to form a 360-degree employer intelligence dossier:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CAREERPULSE AI AGENT                          │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
    ┌───────────────▼──────────────┐  ┌──────────────▼──────────────┐
    │ 1. google_jobs               │  │ 2. google_news              │
    │ Real-time postings, salary   │  │ Layoff & restructuring      │
    │ bands, and direct apply links│  │ risk scanner                │
    └───────────────┬──────────────┘  └──────────────┬──────────────┘
                    │                                │
    ┌───────────────▼──────────────┐  ┌──────────────▼──────────────┐
    │ 3. google (Organic)          │  │ 4. google_trends            │
    │ Glassdoor/AmbitionBox review │  │ 12-Month skill demand       │
    │ aggregates & interview intel │  │ velocity index              │
    └───────────────┬──────────────┘  └──────────────┬──────────────┘
                    │                                │
                    │  ┌───────────────────────────┐ │
                    └──► 5. google_maps            ◄─┘
                       │ Verified office location, │
                       │ HQ campus & transit intel │
                       └─────────────┬─────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │      EVIDENCE VAULT (CACHE)     │
                    │   Typed Pydantic Citations      │
                    └────────────────┬────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│ 360° Employer Due-Diligence     │   │ Grounded Outreach Pack          │
│ Health Verdict & Red Flag Radar │   │ Cover Letter + Bullets with [1] │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

| SerpApi Engine | Role in CareerPulse AI | Visible UI Component |
| :--- | :--- | :--- |
| `google_jobs` | Fetches live postings, salary bands, and qualifications | **Opportunity Radar** with match score % |
| `google_news` | Scans for workforce reductions, leadership turnover, funding | **Health & Layoff Risk Scanner** |
| `google` | Aggregates employee review sentiment & interview patterns | **Culture & Review Intel** (ratings / pros / cons) |
| `google_trends` | Analyzes 12-month search velocity for target tech stacks | **Tech Stack Demand Velocity** |
| `google_maps` | Verifies physical corporate headquarters and office hub | **HQ & Commute Context** |

---

## 🛡️ Hackathon Safeguards & Architecture Rigor

* **Persistent Disk Caching Layer**: Every SerpApi response is hashed and saved to `backend/cache/`. This guarantees instant response times, prevents rate limits, protects API credits, and ensures 100% demo stability.
* **Offline Fallback Resilience**: The system contains deterministic fallback mock data for top tech hubs (Razorpay, Swiggy, CRED), allowing judges to run the entire application offline without an external API key.
* **Pluggable LLM Provider**: Supports Google Gemini via `GEMINI_API_KEY`, OpenAI via `OPENAI_API_KEY`, or an offline deterministic generator by default (`LLM_PROVIDER=mock`).

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.11, 3.12, or 3.14
* Git

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/PrinceBad/careerpulse-ai.git
cd careerpulse-ai

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp backend/.env.example backend/.env
```
*(Optional)* Add your `SERPAPI_API_KEY` to `.env`. If left empty, CareerPulse will automatically utilize its disk cache and offline demo scenarios!

### 3. Run Automated Tests
Verify all 9 unit and integration tests pass:
```bash
pytest tests -v
```

### 4. Start the Application
```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser and visit: **`http://127.0.0.1:8000`**

---

## 🎬 Judge Demo Walkthrough (Under 2 Minutes)

1. **Select a Scenario**: Click any of the 1-click scenario buttons (**Razorpay**, **Swiggy**, or **CRED**).
2. **Observe Opportunity Radar**: Watch `google_jobs` return real-time listings with candidate skill match scores (e.g. `94% Fit`).
3. **Inspect 360° Due Diligence**:
   * View the **Health & Layoff Risk Scanner** driven by `google_news`.
   * Check employee sentiment and interview difficulty from `google`.
   * Examine 12-month tech stack demand trends from `google_trends`.
   * Review verified corporate office address and transit notes from `google_maps`.
4. **Inspect Evidence Citations**: Click any `[cit-01]` badge to open the verified citation modal with source URLs and snippets.
5. **Review Grounded Outreach**: Read the tailored cover letter and resume bullets, noting how every factual hook references a numbered citation chip!

---

## 📄 Submission Metadata

* **Track**: AI Agents
* **Event**: SerpApi India Hackathon 2026
* **Official Partner Community**: **PyDelhi**
* **Lead Developer**: Prince Badsiwal ([GitHub: @PrinceBad](https://github.com/PrinceBad))
* **License**: MIT
