# ⚡ CareerPulse AI

> **Autonomous Investigative Career Intelligence & Evidence-Backed Due-Diligence Agent**  
> Powered by SerpApi Multi-Engine Search · Built for the **SerpApi India Hackathon 2026** (Official **PyDelhi** Community Submission)

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![SerpApi](https://img.shields.io/badge/SerpApi-5%20Engines%20Integrated-orange.svg)](https://serpapi.com/)
[![Tests](https://img.shields.io/badge/Tests-25%20Passing-brightgreen.svg)](https://github.com/PrinceBad/Careerpulse-Ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> ⚖️ **Disclaimer**: Employer health verdicts (such as "High Risk", "Caution", or "Strong") are automated heuristic signals computed from public Google search results, news articles, and review snippets. They do not constitute formal legal, credit, financial, or employment advice regarding named companies.

---

## 💡 The Problem & The "Winning Angle"

Most AI job search tools fail because they are simple **search-and-summarizers**: they query a job board, feed text to an LLM, and hallucinate company details or churn out generic, ungrounded cover letters.

**CareerPulse AI** transforms this into an **Autonomous Investigative Verification Agent**:

1. **Evidence-Grounded Due Diligence**: Every employer signal (layoffs, leadership moves, Glassdoor sentiment, facility verification) is linked to a strictly typed, computed **SerpApi Citation** (`[cit-01]`, `[cit-02]`, etc.) containing the source URL, publication timestamp, and snippet.
2. **Code-Level Grounding Guard**: Generated outreach packs (cover letters and tailored resume bullets) are intercepted and verified before display. Sentences naming the target company require a supported citation by default (except for introductory greetings or role interest). Sentences with hallucinated citation IDs (e.g. `[cit-99]`) or unsupported factual claims are rejected and stripped, while candidate metrics survive only if both numerical values and units (e.g., requests/sec) match the candidate resume. Adversarial tests confirm that ungrounded statements like *"I admire that Swiggy cut 35% of staff"* and *"Swiggy shut down its Bengaluru office"* are stripped, while candidate metrics survive only when grounded in the resume.
3. **Autonomous Corroboration Loop**: Rather than running a static sequence, CareerPulse executes an agentic loop: if the primary news scan flags a layoff signal, the agent automatically spawns a targeted follow-up query (`{company} layoffs confirmed severance details`) to corroborate the finding before assigning a "High Risk" rating. Every decision is logged in the **Investigation Trace**.
4. **Honest Multi-State Provenance & Time-Drift Guard**: The UI clearly displays three distinct data provenance states: `🔴 Live SerpApi Verified`, `🟢 Cached real SerpApi response (captured Oct 6, 2026)`, and `🟡 Demo Mock Data`. Relative dates (e.g. *"3 weeks ago"*) are anchored and resolved directly against the cache's `search_metadata` capture timestamp rather than floating current time, ensuring recency flags never drift as time passes.

---

## 🔍 SerpApi Multi-Engine Architecture

CareerPulse orchestrates **5 distinct SerpApi engines**: `google_jobs` executes first to pinpoint target roles, followed by 4 engines dispatched concurrently in parallel, plus conditional follow-up queries:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CAREERPULSE AI AGENT                            │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
    ┌───────────────▼──────────────┐  ┌──────────────▼──────────────┐
    │ 1. google_jobs               │  │ 2. google_news              │
    │ Live postings, salary bands, │  │ Layoff & restructuring      │
    │ and qualification matching   │  │ risk scanner                │
    └───────────────┬──────────────┘  └──────────────┬──────────────┘
                    │                                │ (If layoff detected)
                    │                 ┌──────────────▼──────────────┐
                    │                 │ Autonomous Corroboration:   │
                    │                 │ Follow-up google_news query │
                    │                 └──────────────┬──────────────┘
                    │                                │
    ┌───────────────▼──────────────┐  ┌──────────────▼──────────────┐
    │ 3. google (Organic)          │  │ 4. google_trends            │
    │ Glassdoor/AmbitionBox review │  │ 12-Month search-interest    │
    │ aggregates & sentiment       │  │ velocity for tech stacks    │
    └───────────────┬──────────────┘  └──────────────┬──────────────┘
                    │                                │
                    │  ┌───────────────────────────┐ │
                    └──► 5. google_maps            ◄─┘
                       │ Physical campus address,  │
                       │ rating & geocode coords   │
                       └─────────────┬─────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │      EVIDENCE VAULT (CACHE)     │
                    │   Computed Pydantic Citations   │
                    └────────────────┬────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│ 360° Employer Due-Diligence     │   │ Code-Level Grounding Guard      │
│ Investigation Trace & Red Flags │   │ Blocks [cit-99] & Fake Metrics  │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

| SerpApi Engine | Role in CareerPulse AI | UI Component & Engine Details |
| :--- | :--- | :--- |
| `google_jobs` | Fetches live postings, salary bands, and qualifications | **Opportunity Radar** with algorithmic skill match % |
| `google_news` | Scans for workforce reductions, leadership turnover, funding | **Health & Layoff Risk Scanner** + Corroboration loop |
| `google` | Aggregates employee review sentiment (Glassdoor/AmbitionBox) | **Culture & Review Intel** (ratings / pros / cons; says "no rating found" if absent) |
| `google_trends` | Analyzes 12-month search-interest velocity for tech stacks | **Tech Stack Demand Velocity** (relative search index) |
| `google_maps` | Verifies physical corporate headquarters & campus location | **HQ & Campus Verification** (address, ratings, coordinates) |

---

## 🛡️ Grounding Guard & Heuristic Limits

CareerPulse includes a rigorous code-level validator (`GroundingValidator`) that verifies outreach drafts before presenting them to the candidate:

1. **Citation Existence**: Every `[cit-xx]` reference must map to a real citation in the evidence vault. Fabricated IDs (like `[cit-99]`) trigger immediate rejection.
2. **Default-Deny for Target Employer**: Any sentence naming the target employer without a citation is rejected by default, preventing ungrounded business claims (e.g. *"Swiggy shut down its Bengaluru office"* or *"I admire that Swiggy cut staff"*). Only strictly allowlisted application greetings and role interest statements are permitted without citation.
3. **Snippet Support Check**: Any sentence making a factual claim (metrics, percentages, "layoff", "severance", "raised") must find those terms or numbers in the cited source snippet. If an AI writes *"Quietly laid off 35% of engineering"* and attaches a citation about Series C funding, the validator rejects and strips the sentence.
4. **Candidate Experience Preservation with Unit Matching**: Metrics describing candidate accomplishments (e.g. *"Built an API serving 10k requests/second"*) survive only if both numerical values and units/frequency match the candidate resume.
5. **Interception Demonstration (Simulated Draft)**: The UI includes a dedicated button (`🧪 Simulate Hallucination Guard`) that injects a test draft containing `[cit-99]` and an unsupported metric. Judges can watch the validator intercept the draft, strip the invalid sentences, and present a side-by-side comparison with an explicit count of removed sentences.

> [!NOTE]
> **Heuristic Disclosure**: CareerPulse's factual-claim detection is regex and keyword-based. Verification confidence scores (0.60 to 1.00) are rule-derived **Heuristic Confidence Scores** (entity match, URL validity, tier-1 publishers like `economictimes.indiatimes.com`, and recency) rather than statistical probabilities. As with any heuristic, it is an engineering guardrail rather than a mathematical guarantee of semantic truth. Admitting these boundaries is part of building mature AI agents.

---

## 🔐 Security & Cache Architecture

* **Key-Agnostic Cache Keys**: Cache keys are SHA-256 hashes generated from the query parameters with `api_key` explicitly excluded. A judge cloning this repository can run against the pre-warmed cache without providing an API key.
* **Committed Genuine Cache**: 38 real JSON responses with verified `search_metadata` across all 5 engines and corroboration queries are committed for **Razorpay**, **Swiggy**, and **CRED**, captured on **Oct 6, 2026**.
* **Zero Secret Leakage**: All responses saved to `backend/cache/` are scrubbed of any `api_key` values prior to writing to disk. The `.env` file is strictly ignored in `.gitignore`, and only `.env.example` is tracked.
* **Honest Cache-Miss Dossier**: For cached companies, zero API credits are consumed. If a user queries an uncached company without setting a `SERPAPI_API_KEY`, CareerPulse returns an honest "Data Unavailable" dossier with empty citations rather than fabricating simulated evidence about a real company. Setting a `SERPAPI_API_KEY` in `backend/.env` dispatches live multi-engine investigations across Google News, Organic Web, Google Trends, and Google Maps.

### 🗄️ Cache Warming & Verification Utility (`scripts/warm_cache.py`)

A single consolidated script handles offline warming, selective company queries, and disk cache validation:

```bash
# Verify existing disk cache integrity (checks search_metadata without API requests)
python scripts/warm_cache.py --verify-only

# Warm all 5 engines for a specific target employer
python scripts/warm_cache.py --company Zomato

# Warm all default demo scenarios & jobs
python scripts/warm_cache.py --all
```

### 🗄️ Cache Architecture & Evaluator Reproducibility
* **Committed Snapshot Data**: 38 genuine JSON responses captured on Oct 6, 2026 across all 5 engines and corroboration queries are committed for **Razorpay**, **Swiggy**, and **CRED**. This guarantees evaluators can run deterministic, comprehensive due diligence audits offline without needing an API key or consuming API credits.
* **API Key Scrubbing**: API keys are excluded from cache key calculation and scrubbed from all stored JSON files before writing to disk (`_sanitize_data`), preventing credential exposure.
* **Offline Verification**: All cached files contain authentic SerpApi `search_metadata` and can be validated at any time using `python scripts/warm_cache.py --verify-only` or via unit tests.

---

## 📋 Prior Work Disclosure

CareerPulse AI was designed and built from scratch for the **SerpApi India Hackathon 2026**. Earlier personal hobby prototypes for keyword-based resume scanning served as initial inspiration, but all scraping code was discarded. All FastAPI microservice endpoints, GroundingValidator guardrails, multi-engine SerpApi client, autonomous corroboration agent loop, and Vanilla CSS/JS frontend interface were developed specifically for this hackathon submission.

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.11, 3.12, or 3.14
* Git

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/PrinceBad/Careerpulse-Ai.git
cd Careerpulse-Ai

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
Copy `.env.example` to `backend/.env`:
```bash
cp backend/.env.example backend/.env
```
*(Optional)* Add your `SERPAPI_API_KEY` to `backend/.env`. If left empty, CareerPulse will automatically utilize its committed real cache for the demo scenarios (Razorpay, Swiggy, CRED)!

### 3. Run Automated Tests
Verify all **25 unit and integration tests** pass:
```bash
pytest -v
```

### 4. Start the Application
```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser and navigate to: **`http://127.0.0.1:8000`**

---

## 🎬 3-Beat Demo Walkthrough (~2:30 Target)

* **Beat 1: The Problem & Opportunity Radar (0:00 – 0:45)**  
  Click **Razorpay** in the 1-Click Demo Scenarios. Show the Real-Time Opportunity Radar fetching live positions via `google_jobs`, with real-time candidate skill overlap scoring (`94% Fit`). Point out the honest provenance indicator: `🟢 Cached Real SerpApi Response`.

* **Beat 2: 360° Due Diligence & Autonomous Investigation Trace (0:45 – 1:40)**  
  Review the 360° Employer Due Diligence dossier. Highlight the **Autonomous Agent Investigation Trace** panel, which explains the trigger and outcome for each of the 5 engines. Note the layoff scanner (`google_news`), review intel (`google`), search-interest velocity (`google_trends`), and physical office verification (`google_maps`). Click any `[cit-01]` badge to show the modal with the heuristic verification confidence and snippet.

* **Beat 3: Grounding Guard Demonstration (1:40 – 2:30)**  
  Scroll to the **Evidence-Grounded Outreach Pack**. Click `🧪 Simulate Hallucination Guard`. Watch the code-level validator intercept the simulated draft, flag `[cit-99]` and the fake 35% layoff metric, display the red interception alert box, and present the side-by-side comparison showing `2 Sentences Blocked & Stripped`. Conclude with a quick terminal cut showing `25 passed in 1.64s`.

---

## 📄 Submission Metadata

* **Track**: AI Agents
* **Event**: SerpApi India Hackathon 2026
* **Official Partner Community**: **PyDelhi** (Eligible for ₹10,000 PyDelhi community award + ₹3 Lakh+ overall prize pool)
* **Lead Developer**: Prince Badsiwal ([GitHub: @PrinceBad](https://github.com/PrinceBad))
* **License**: MIT
