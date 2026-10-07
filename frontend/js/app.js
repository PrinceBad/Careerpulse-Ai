// CareerPulse AI - Frontend Application Logic

const state = {
  activeScenario: 'razorpay',
  currentJobs: [],
  selectedJob: null,
  currentReport: null,
  currentOutreach: null,
};

const SCENARIOS = {
  razorpay: {
    role: "Senior Python Backend Engineer",
    location: "Bengaluru, India",
    company: "Razorpay",
    skills: "Python 3.14, FastAPI, PostgreSQL, Redis, Distributed Systems, Microservices, REST APIs, Celery, High Throughput."
  },
  swiggy: {
    role: "Staff AI Platform Engineer",
    location: "Bengaluru, India",
    company: "Swiggy",
    skills: "Python, FastAPI, Redis, LLM Orchestration, Agentic Systems, Distributed Task Queues, Kafka, AsyncIO."
  },
  cred: {
    role: "Backend Architect - Real-Time Systems",
    location: "Bengaluru, India",
    company: "CRED",
    skills: "Python, Go, High Concurrency, Low-Latency Financial Ledgers, DB Sharding, Kafka, System Design."
  }
};

// DOM Elements
const jobSearchForm = document.getElementById('jobSearchForm');
const companyInput = document.getElementById('companyInput');
const roleInput = document.getElementById('roleInput');
const locationInput = document.getElementById('locationInput');
const resumeInput = document.getElementById('resumeInput');
const jobsList = document.getElementById('jobsList');
const jobsStats = document.getElementById('jobsStats');
const scenarioButtons = document.querySelectorAll('.btn-scenario');
const dataSourceBadge = document.getElementById('dataSourceBadge');
const dataSourceLabel = document.getElementById('dataSourceLabel');

// Due Diligence Elements
const companyHealthBadge = document.getElementById('companyHealthBadge');
const targetCompanyTitle = document.getElementById('targetCompanyTitle');
const targetRoleTitle = document.getElementById('targetRoleTitle');
const dossierProvenanceBadge = document.getElementById('dossierProvenanceBadge');
const executiveSummaryText = document.getElementById('executiveSummaryText');
const btnRefreshDiligence = document.getElementById('btnRefreshDiligence');
const cacheMissNotice = document.getElementById('cacheMissNotice');
const cacheMissNoticeText = document.getElementById('cacheMissNoticeText');
const investigationTraceTimeline = document.getElementById('investigationTraceTimeline');

// Intel Cards Elements
const riskLevelBadge = document.getElementById('riskLevelBadge');
const riskSummaryText = document.getElementById('riskSummaryText');
const riskCitations = document.getElementById('riskCitations');

const cultureScoreBadge = document.getElementById('cultureScoreBadge');
const culturePros = document.getElementById('culturePros');
const cultureCons = document.getElementById('cultureCons');
const cultureCitations = document.getElementById('cultureCitations');

const trendsVerdictBadge = document.getElementById('trendsVerdictBadge');
const trendsSummaryText = document.getElementById('trendsSummaryText');
const trendsCitations = document.getElementById('trendsCitations');

const mapsRatingBadge = document.getElementById('mapsRatingBadge');
const mapsAddressText = document.getElementById('mapsAddressText');
const mapsCitations = document.getElementById('mapsCitations');

const citationsVaultList = document.getElementById('citationsVaultList');
const citationCountBadge = document.getElementById('citationCountBadge');

// Outreach Elements
const btnGenerateOutreach = document.getElementById('btnGenerateOutreach');
const outreachSubject = document.getElementById('outreachSubject');
const outreachEmail = document.getElementById('outreachEmail');
const outreachBullets = document.getElementById('outreachBullets');

// Hallucination Guard Interception Elements (Beat 3)
const btnSimulateHallucination = document.getElementById('btnSimulateHallucination');
const hallucinationAlertBox = document.getElementById('hallucinationAlertBox');
const hallucinationViolationsList = document.getElementById('hallucinationViolationsList');
const blockedSentencesBadge = document.querySelector('.badge-blocked');

// Modal Elements
const citationModal = document.getElementById('citationModal');
const btnCloseModal = document.getElementById('btnCloseModal');
const modalCitTitle = document.getElementById('modalCitTitle');
const modalCitEngine = document.getElementById('modalCitEngine');
const modalCitSignal = document.getElementById('modalCitSignal');
const modalCitDate = document.getElementById('modalCitDate');
const modalCitSnippet = document.getElementById('modalCitSnippet');
const modalCitUrl = document.getElementById('modalCitUrl');
const modalCitVerified = document.getElementById('modalCitVerified');
const modalCitMethod = document.getElementById('modalCitMethod');

// Init
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  loadScenario('razorpay');
  runJobScan();
});

function setupEventListeners() {
  // Scenario button clicks
  scenarioButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const scenarioKey = btn.getAttribute('data-scenario');
      scenarioButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadScenario(scenarioKey);
      runJobScan();
    });
  });

  // Search form submit
  jobSearchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    runJobScan();
  });

  // Re-scan diligence
  btnRefreshDiligence.addEventListener('click', () => {
    const comp = state.selectedJob ? state.selectedJob.company_name : (companyInput ? companyInput.value.trim() : "Razorpay");
    const role = state.selectedJob ? state.selectedJob.title : roleInput.value.trim();
    loadDueDiligence(comp, role);
  });

  // Generate outreach
  btnGenerateOutreach.addEventListener('click', () => {
    generateOutreach();
  });

  // Simulate Hallucination Guard (Beat 3 proof)
  if (btnSimulateHallucination) {
    btnSimulateHallucination.addEventListener('click', async () => {
      if (!state.currentReport) {
        alert("Please wait for the Due Diligence scan to load first.");
        return;
      }
      btnSimulateHallucination.disabled = true;
      btnSimulateHallucination.innerHTML = '<span class="btn-icon">⏳</span> Intercepting Draft...';

      try {
        const res = await fetch('/api/guard/simulate-hallucination', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(state.currentReport)
        });

        const data = await res.json();
        
        // Show the alert box with intercepted claims
        if (hallucinationAlertBox) {
          hallucinationAlertBox.classList.remove('hidden');
        }
        if (blockedSentencesBadge) {
          blockedSentencesBadge.textContent = `${data.count_rejected || 2} Sentences Blocked & Stripped`;
        }
        if (hallucinationViolationsList) {
          hallucinationViolationsList.innerHTML = '';
          (data.violations || []).forEach(v => {
            const li = document.createElement('li');
            li.className = 'violation-item';
            li.innerHTML = `<strong>INTERCEPTED:</strong> ${escapeHtml(v)}`;
            hallucinationViolationsList.appendChild(li);
          });
        }

        // Show side-by-side comparison in outreachEmail container
        outreachEmail.innerHTML = `
          <div class="before-after-box">
            <div class="draft-comparison">
              <div class="draft-pane draft-original">
                <span class="pane-badge bad">Draft with Injected Hallucinations</span>
                <p>${escapeHtml(data.original_draft)}</p>
              </div>
              <div class="draft-pane draft-sanitized">
                <span class="pane-badge good">Sanitized by Grounding Guard (${data.count_rejected || 2} sentences removed)</span>
                <p>${escapeHtml(data.cleaned_result)}</p>
              </div>
            </div>
          </div>
        `;

        hallucinationAlertBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } catch (err) {
        console.error("Error simulating hallucination:", err);
      } finally {
        btnSimulateHallucination.disabled = false;
        btnSimulateHallucination.innerHTML = '<span class="btn-icon">🧪</span> Simulate Hallucination Guard';
      }
    });
  }

  // Modal close
  btnCloseModal.addEventListener('click', () => {
    citationModal.classList.add('hidden');
  });

  citationModal.addEventListener('click', (e) => {
    if (e.target === citationModal) {
      citationModal.classList.add('hidden');
    }
  });
}

function safeUrl(url) {
  if (!url) return '#';
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
      return url;
    }
  } catch (e) {}
  return '#';
}

function updateProvenanceBadge(prov, snapshotDate) {
  const p = prov || 'cached';
  if (p === 'live') {
    dataSourceBadge.className = 'data-source-badge badge-live';
    dataSourceLabel.textContent = 'Live SerpApi Verified';
    if (dossierProvenanceBadge) {
      dossierProvenanceBadge.className = 'provenance-badge badge-live';
      dossierProvenanceBadge.textContent = '🔴 Live SerpApi Verified';
    }
  } else if (p === 'cached') {
    const capturedText = snapshotDate ? ` (captured ${snapshotDate})` : '';
    const labelText = `Cached real SerpApi response${capturedText}`;
    dataSourceBadge.className = 'data-source-badge badge-cached';
    dataSourceLabel.textContent = labelText;
    if (dossierProvenanceBadge) {
      dossierProvenanceBadge.className = 'provenance-badge badge-cached';
      dossierProvenanceBadge.textContent = `🟢 ${labelText}`;
    }
  } else if (p === 'unavailable') {
    dataSourceBadge.className = 'data-source-badge badge-mock';
    dataSourceLabel.textContent = '⚪ No data: offline cache miss';
    if (dossierProvenanceBadge) {
      dossierProvenanceBadge.className = 'provenance-badge badge-mock';
      dossierProvenanceBadge.textContent = '⚪ No data: offline cache miss';
    }
  } else {
    dataSourceBadge.className = 'data-source-badge badge-mock';
    dataSourceLabel.textContent = 'Offline Mode';
    if (dossierProvenanceBadge) {
      dossierProvenanceBadge.className = 'provenance-badge badge-mock';
      dossierProvenanceBadge.textContent = 'Offline Mode';
    }
  }
}

function loadScenario(key) {
  state.activeScenario = key;
  const s = SCENARIOS[key];
  if (s) {
    if (companyInput) companyInput.value = s.company;
    roleInput.value = s.role;
    locationInput.value = s.location;
    resumeInput.value = s.skills;
  }
}

async function runJobScan() {
  const targetCompany = companyInput ? companyInput.value.trim() : "";
  const role = roleInput.value.trim();
  const query = targetCompany && !role.toLowerCase().includes(targetCompany.toLowerCase())
    ? `${targetCompany} ${role}`
    : role;
  const location = locationInput.value.trim();
  const candidate_text = resumeInput.value.trim();

  jobsStats.textContent = "Querying SerpApi google_jobs...";
  jobsList.innerHTML = `<div class="loading-state">Fetching real-time opportunities & matching skills...</div>`;

  try {
    const res = await fetch('/api/jobs/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        location: location,
        candidate_profile_text: candidate_text
      })
    });

    const data = await res.json();
    state.currentJobs = data.jobs || [];
    updateProvenanceBadge(data.provenance, data.snapshot_date);
    renderJobs(state.currentJobs, targetCompany, role);

    // Select first job automatically if found
    if (state.currentJobs.length > 0) {
      selectJob(state.currentJobs[0]);
    } else {
      // If no jobs found (cache miss without live API), load due diligence for typed company
      state.selectedJob = null;
      const comp = targetCompany || "Target Company";
      targetCompanyTitle.textContent = comp;
      targetRoleTitle.textContent = role || "Software Engineer";
      loadDueDiligence(comp, role || "Software Engineer");
    }
  } catch (err) {
    console.error("Error scanning jobs:", err);
    jobsStats.textContent = "Error scanning jobs. Check backend connection.";
  }
}

function renderJobs(jobs, targetCompany = "", role = "") {
  if (!jobs || jobs.length === 0) {
    const queryLabel = targetCompany ? `${targetCompany} (${role || 'Role'})` : (role || 'Role');
    jobsStats.textContent = `0 matching positions found (Offline Mode / Cache Miss)`;
    jobsList.innerHTML = `
      <div class="empty-jobs-card">
        <div class="empty-icon">📡</div>
        <h4>No Cached Postings for "${escapeHtml(queryLabel)}"</h4>
        <p>This query has no pre-warmed disk cache. In offline mode without a <code>SERPAPI_API_KEY</code>, new live queries cannot be dispatched.</p>
        <div class="empty-hint">
          💡 <strong>Options:</strong> Set <code>SERPAPI_API_KEY</code> in <code>backend/.env</code> for live queries, or select a 1-Click Scenario above (Razorpay, Swiggy, CRED).
        </div>
      </div>
    `;
    return;
  }

  jobsStats.textContent = `Found ${jobs.length} matching positions (${jobs.length ? jobs[0].match_score : 0}% Skill Overlap)`;
  jobsList.innerHTML = '';

  jobs.forEach((job, index) => {
    const card = document.createElement('div');
    card.className = `job-card ${index === 0 ? 'selected' : ''}`;
    card.id = `job-card-${job.id}`;

    const matchingBadges = (job.matching_skills || []).slice(0, 3).map(s => 
      `<span class="skill-pill matching">✓ ${s}</span>`
    ).join('');

    card.innerHTML = `
      <div class="job-header">
        <div>
          <div class="job-company">${escapeHtml(job.company_name)} · ${escapeHtml(job.via)}</div>
          <h3 class="job-title">${escapeHtml(job.title)}</h3>
        </div>
        <div class="match-meter">
          <span class="match-score-badge">${job.match_score}%</span>
          <span class="match-score-label">Skill Overlap</span>
        </div>
      </div>
      <div class="job-meta-row">
        <span>📍 ${escapeHtml(job.location)}</span>
        ${job.salary ? `<span>💰 ${escapeHtml(job.salary)}</span>` : ''}
        ${job.posted_at ? `<span>⏱ ${escapeHtml(job.posted_at)}</span>` : ''}
      </div>
      <div class="job-skills">
        ${matchingBadges}
      </div>
    `;

    card.addEventListener('click', () => {
      document.querySelectorAll('.job-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      selectJob(job);
    });

    jobsList.appendChild(card);
  });
}

function selectJob(job) {
  state.selectedJob = job;
  targetCompanyTitle.textContent = job.company_name;
  targetRoleTitle.textContent = job.title;
  loadDueDiligence(job.company_name, job.title);
}

let currentDueDiligenceController = null;
let currentDueDiligenceReqId = 0;

async function loadDueDiligence(companyName, roleTitle) {
  if (currentDueDiligenceController) {
    currentDueDiligenceController.abort();
  }
  const controller = new AbortController();
  currentDueDiligenceController = controller;
  const reqId = ++currentDueDiligenceReqId;

  executiveSummaryText.textContent = `Running 5-engine SerpApi investigative scan for ${companyName}...`;

  try {
    const timeoutId = setTimeout(() => controller.abort(), 15000);
    const res = await fetch('/api/company/due-diligence', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        company_name: companyName,
        role_title: roleTitle,
        location: locationInput.value.trim(),
        tech_stack: ["FastAPI", "Python", "PostgreSQL"]
      })
    });
    clearTimeout(timeoutId);

    if (reqId !== currentDueDiligenceReqId) {
      return; // Ignore stale response
    }

    const report = await res.json();
    state.currentReport = report;
    renderDueDiligence(report);
    generateOutreach();
  } catch (err) {
    if (err.name === 'AbortError') return;
    if (reqId !== currentDueDiligenceReqId) return;
    console.error("Error loading due diligence:", err);
    executiveSummaryText.textContent = `Notice: Error executing due diligence scan for ${companyName}. Set SERPAPI_API_KEY in .env for live multi-engine queries.`;
  }
}

function renderDueDiligence(report) {
  // Update Live vs Cached vs Unavailable provenance badge honestly
  const prov = report.provenance || (report.is_mock ? 'mock' : 'cached');
  updateProvenanceBadge(prov, report.snapshot_date);

  // Show clear cache-miss notice banner if in offline cache miss
  if (cacheMissNotice) {
    if (prov === 'unavailable' || prov === 'mock') {
      cacheMissNotice.classList.remove('hidden');
      if (cacheMissNoticeText) {
        cacheMissNoticeText.innerHTML = `
          <strong>Offline Mode Notice:</strong>
          No pre-warmed SerpApi cache exists for "<strong>${escapeHtml(report.company_name)}</strong>". Set <code>SERPAPI_API_KEY</code> in <code>backend/.env</code> to dispatch live multi-engine investigations.
        `;
      }
    } else {
      cacheMissNotice.classList.add('hidden');
    }
  }

  // Verdict badge
  companyHealthBadge.className = 'verdict-badge';
  if (report.overall_health_verdict === 'Strong') {
    companyHealthBadge.classList.add('verdict-strong');
    companyHealthBadge.textContent = 'Strong Profile';
  } else if (report.overall_health_verdict === 'Caution') {
    companyHealthBadge.classList.add('verdict-caution');
    companyHealthBadge.textContent = 'Caution Advised';
  } else if (report.overall_health_verdict === 'Data Unavailable') {
    companyHealthBadge.classList.add('verdict-nodata');
    companyHealthBadge.textContent = 'Data Unavailable (Offline Cache Miss)';
  } else {
    companyHealthBadge.classList.add('verdict-highrisk');
    companyHealthBadge.textContent = 'High Risk';
  }

  executiveSummaryText.textContent = report.executive_summary;

  // Render Autonomous Agent Investigation Trace
  if (investigationTraceTimeline) {
    investigationTraceTimeline.innerHTML = '';
    const trace = report.investigation_trace || [];
    trace.forEach(step => {
      const item = document.createElement('div');
      item.className = 'trace-step-item';
      item.innerHTML = `
        <div class="trace-step-num">${step.step_number}</div>
        <div class="trace-step-body">
          <div class="trace-step-header">
            <span class="trace-engine-tag engine-${escapeHtml(step.engine).replace('google_', '')}">${escapeHtml(step.engine)}</span>
            <strong class="trace-action-text">${escapeHtml(step.action)}</strong>
          </div>
          <p class="trace-reason-text"><strong>Trigger / Reason:</strong> ${escapeHtml(step.reason)}</p>
          <p class="trace-result-text"><strong>Outcome:</strong> ${escapeHtml(step.result_summary)}</p>
        </div>
      `;
      investigationTraceTimeline.appendChild(item);
    });
  }

  // 1. Risks Card
  if (report.risks.risk_level === 'Unknown') {
    riskLevelBadge.className = 'badge-risk-unknown';
    riskLevelBadge.textContent = 'DATA UNAVAILABLE';
  } else if (report.risks.risk_level === 'Low') {
    riskLevelBadge.className = 'badge-risk-low';
    riskLevelBadge.textContent = 'LOW RISK';
  } else if (report.risks.risk_level === 'Medium') {
    riskLevelBadge.className = 'badge-risk-medium';
    riskLevelBadge.textContent = 'MEDIUM RISK';
  } else {
    riskLevelBadge.className = 'badge-risk-high';
    riskLevelBadge.textContent = 'HIGH RISK';
  }
  riskSummaryText.textContent = report.risks.risk_summary;
  renderCitationChips(riskCitations, report.risks.evidence_citation_ids, report.citations);

  // 2. Culture Card (honestly handle null rating)
  if (report.culture && report.culture.sentiment_rating !== null && report.culture.sentiment_rating !== undefined) {
    cultureScoreBadge.textContent = `${report.culture.sentiment_rating} / 5.0`;
  } else {
    cultureScoreBadge.textContent = "No Rating Found";
  }
  culturePros.textContent = (report.culture.top_positives || []).length > 0 
    ? report.culture.top_positives.join(', ')
    : "No verified positive culture highlights in search snippets";
  cultureCons.textContent = (report.culture.top_complaints || []).length > 0
    ? report.culture.top_complaints.join(', ')
    : "No recurring negative complaints identified in search snippets";
  renderCitationChips(cultureCitations, report.culture.evidence_citation_ids, report.citations);

  // 3. Trends Card (Reset if missing to prevent stale company trends)
  if (report.tech_trends && report.tech_trends.length > 0) {
    const t = report.tech_trends[0];
    trendsVerdictBadge.textContent = t.growth_verdict.toUpperCase();
    trendsVerdictBadge.className = t.growth_verdict === 'Surging' ? 'badge-trend-surging' : 'badge-score';
    trendsSummaryText.textContent = t.trend_description;
    renderCitationChips(trendsCitations, [t.citation_id], report.citations);
  } else {
    trendsVerdictBadge.textContent = 'NO DATA';
    trendsVerdictBadge.className = 'badge-score';
    trendsSummaryText.textContent = `No search trend signals available for ${escapeHtml(report.company_name)}.`;
    trendsCitations.innerHTML = '';
  }

  // 4. Maps Card (Reset if missing to prevent stale office location)
  if (report.location_signal && report.location_signal.address) {
    mapsRatingBadge.textContent = report.location_signal.rating ? `${report.location_signal.rating} ★` : 'Unrated';
    mapsAddressText.textContent = report.location_signal.address;
    renderCitationChips(mapsCitations, [report.location_signal.citation_id], report.citations);
  } else {
    mapsRatingBadge.textContent = 'Not found';
    mapsAddressText.textContent = `No physical campus or address found for ${escapeHtml(report.company_name)}.`;
    mapsCitations.innerHTML = '';
  }

  // 5. Evidence Vault List
  if (!report.citations || report.citations.length === 0) {
    citationCountBadge.textContent = "0 Sources (Offline Cache Miss)";
    citationsVaultList.innerHTML = `
      <div class="empty-vault-card">
        <p>No verified search evidence found in offline disk cache for <strong>${escapeHtml(report.company_name)}</strong>. Set <code>SERPAPI_API_KEY</code> in <code>backend/.env</code> to dispatch live multi-engine investigations across Google News, Web, Trends, and Maps.</p>
      </div>
    `;
  } else {
    citationCountBadge.textContent = `${report.citations.length} Verified Sources Loaded`;
    citationsVaultList.innerHTML = '';
    report.citations.forEach(c => {
      const item = document.createElement('div');
      item.className = 'vault-item';
      const safeLink = safeUrl(c.source_url);
      const isAnchorValid = safeLink !== '#';
      item.innerHTML = `
        <div class="vault-item-left">
          <button type="button" class="citation-chip" onclick="showCitationModal('${escapeHtml(c.id)}')">[${escapeHtml(c.id)}]</button>
          <span class="engine-tag engine-${escapeHtml(c.engine).replace('google_', '')}">${escapeHtml(c.engine)}</span>
          <strong>${escapeHtml(c.source_title)}</strong>
          <span class="verified-tag ${c.verified ? 'tag-verified' : 'tag-unverified'}">${c.verified ? `✓ Verified (${Math.round((c.verification_confidence ?? 0) * 100)}%)` : '⚠ Unverified'}</span>
        </div>
        <div>
          ${isAnchorValid ? `<a href="${safeLink}" target="_blank" rel="noopener noreferrer">Inspect Source ↗</a>` : '<span class="text-muted">No external link</span>'}
        </div>
      `;
      citationsVaultList.appendChild(item);
    });
  }
}

function renderCitationChips(container, citIds, allCitations) {
  container.innerHTML = '';
  (citIds || []).forEach(cid => {
    if (!cid) return;
    const c = (allCitations || []).find(item => item.id === cid);
    if (c) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'citation-chip';
      chip.innerHTML = `<span>[${escapeHtml(c.id)}]</span> <small>${escapeHtml(c.engine).replace('google_', '')}</small>`;
      chip.onclick = () => showCitationModal(c.id);
      container.appendChild(chip);
    }
  });
}

window.showCitationModal = function(citationId) {
  if (!state.currentReport) return;
  const c = state.currentReport.citations.find(item => item.id === citationId);
  if (!c) return;

  modalCitTitle.textContent = c.source_title;
  modalCitEngine.textContent = c.engine;
  modalCitEngine.className = `engine-tag engine-${c.engine.replace('google_', '')}`;
  
  modalCitSignal.textContent = (c.signal_type || 'neutral').toUpperCase();
  modalCitSignal.className = `signal-tag signal-${c.signal_type || 'neutral'}`;
  
  modalCitDate.textContent = c.date || 'Verified Live Result';
  modalCitSnippet.textContent = c.snippet;
  
  if (modalCitVerified) {
    if (c.verified) {
      modalCitVerified.textContent = `✓ VERIFIED (${Math.round((c.verification_confidence ?? 0) * 100)}%)`;
      modalCitVerified.className = 'verified-tag tag-verified';
    } else {
      modalCitVerified.textContent = '⚠ UNVERIFIED';
      modalCitVerified.className = 'verified-tag tag-unverified';
    }
  }

  if (modalCitMethod) {
    modalCitMethod.textContent = `${c.verification_method || 'exact_entity_match'} · Provenance: ${c.provenance || 'cached'}`;
  }

  const modalCitConfidence = document.getElementById('modalCitConfidence');
  if (modalCitConfidence) {
    modalCitConfidence.textContent = `${Math.round((c.verification_confidence ?? 0) * 100)}% (Heuristic Confidence Score)`;
  }
  
  const safeLink = safeUrl(c.source_url);
  modalCitUrl.href = safeLink;
  modalCitUrl.textContent = c.source_url;

  citationModal.classList.remove('hidden');
};

let currentOutreachController = null;
let currentOutreachReqId = 0;

async function generateOutreach() {
  if (!state.currentReport) return;
  const comp = state.selectedJob ? state.selectedJob.company_name : state.currentReport.company_name;
  const role = state.selectedJob ? state.selectedJob.title : (state.currentReport.target_role || "Software Engineer");
  const jobDesc = state.selectedJob ? state.selectedJob.description : null;

  if (state.currentReport.overall_health_verdict === 'Data Unavailable') {
    outreachSubject.textContent = `Application: ${role} | ${comp}`;
    outreachEmail.innerHTML = `
      <div class="empty-jobs-card">
        <p>No verified search evidence is available in offline mode for <strong>${escapeHtml(comp)}</strong>. Application packs require verified citations or an active <code>SERPAPI_API_KEY</code>.</p>
      </div>
    `;
    outreachBullets.innerHTML = '';
    return;
  }

  if (currentOutreachController) {
    currentOutreachController.abort();
  }
  const controller = new AbortController();
  currentOutreachController = controller;
  const reqId = ++currentOutreachReqId;

  outreachSubject.textContent = "Synthesizing evidence-grounded application pack...";
  outreachEmail.innerHTML = "Linking citations and building anti-hallucination hooks...";
  outreachBullets.innerHTML = "";

  try {
    const timeoutId = setTimeout(() => controller.abort(), 15000);
    const res = await fetch('/api/outreach/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        company_name: comp,
        role_title: role,
        job_description: jobDesc,
        candidate_profile_text: resumeInput.value.trim(),
        due_diligence_report: state.currentReport
      })
    });
    clearTimeout(timeoutId);

    if (reqId !== currentOutreachReqId) {
      return;
    }

    const data = await res.json();
    state.currentOutreach = data;

    outreachSubject.textContent = data.subject_line;
    
    // Parse bracketed citations into clickable chips
    let formattedEmail = escapeHtml(data.cover_letter);
    formattedEmail = formattedEmail.replace(/\[(cit-\d+)\]/g, (match, p1) => {
      return `<button type="button" class="citation-chip" onclick="showCitationModal('${p1}')">[${p1}]</button>`;
    });
    outreachEmail.innerHTML = formattedEmail;

    // Render bullets
    outreachBullets.innerHTML = '';
    (data.tailored_resume_bullets || []).forEach(b => {
      const li = document.createElement('li');
      let formattedB = escapeHtml(b);
      formattedB = formattedB.replace(/\[(cit-\d+)\]/g, (match, p1) => {
        return `<button type="button" class="citation-chip" onclick="showCitationModal('${p1}')">[${p1}]</button>`;
      });
      li.innerHTML = formattedB;
      outreachBullets.appendChild(li);
    });

  } catch (err) {
    if (err.name === 'AbortError') return;
    if (reqId !== currentOutreachReqId) return;
    console.error("Error generating outreach:", err);
    outreachSubject.textContent = "Error generating outreach pack.";
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}
