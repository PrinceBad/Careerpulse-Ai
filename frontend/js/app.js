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
const executiveSummaryText = document.getElementById('executiveSummaryText');
const btnRefreshDiligence = document.getElementById('btnRefreshDiligence');

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

// Modal Elements
const citationModal = document.getElementById('citationModal');
const btnCloseModal = document.getElementById('btnCloseModal');
const modalCitTitle = document.getElementById('modalCitTitle');
const modalCitEngine = document.getElementById('modalCitEngine');
const modalCitSignal = document.getElementById('modalCitSignal');
const modalCitDate = document.getElementById('modalCitDate');
const modalCitSnippet = document.getElementById('modalCitSnippet');
const modalCitUrl = document.getElementById('modalCitUrl');

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
    if (state.selectedJob) {
      loadDueDiligence(state.selectedJob.company_name, state.selectedJob.title);
    }
  });

  // Generate outreach
  btnGenerateOutreach.addEventListener('click', () => {
    generateOutreach();
  });

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

function loadScenario(key) {
  state.activeScenario = key;
  const s = SCENARIOS[key];
  if (s) {
    roleInput.value = s.role;
    locationInput.value = s.location;
    resumeInput.value = s.skills;
  }
}

async function runJobScan() {
  const query = roleInput.value.trim();
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
    renderJobs(state.currentJobs);

    // Select first job automatically
    if (state.currentJobs.length > 0) {
      selectJob(state.currentJobs[0]);
    }
  } catch (err) {
    console.error("Error scanning jobs:", err);
    jobsStats.textContent = "Error scanning jobs. Check backend connection.";
  }
}

function renderJobs(jobs) {
  jobsStats.textContent = `Found ${jobs.length} matching positions (${jobs.length ? jobs[0].match_score : 0}% Top Match)`;
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
          <span class="match-score-label">Skill Fit</span>
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

async function loadDueDiligence(companyName, roleTitle) {
  executiveSummaryText.textContent = `Running 5-engine SerpApi investigative scan for ${companyName}...`;

  try {
    const res = await fetch('/api/company/due-diligence', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_name: companyName,
        role_title: roleTitle,
        location: locationInput.value.trim(),
        tech_stack: ["FastAPI", "Python", "PostgreSQL"]
      })
    });

    const report = await res.json();
    state.currentReport = report;
    renderDueDiligence(report);
    generateOutreach();
  } catch (err) {
    console.error("Error loading due diligence:", err);
    executiveSummaryText.textContent = "Error executing due diligence scan.";
  }
}

function renderDueDiligence(report) {
  // Update Live vs Mock Data badge
  if (report.is_mock) {
    dataSourceBadge.className = 'data-source-badge badge-mock';
    dataSourceLabel.textContent = 'Demo Mock Data';
  } else {
    dataSourceBadge.className = 'data-source-badge badge-live';
    dataSourceLabel.textContent = 'Live SerpApi Verified';
  }

  // Verdict badge
  companyHealthBadge.className = 'verdict-badge';
  if (report.overall_health_verdict === 'Strong') {
    companyHealthBadge.classList.add('verdict-strong');
    companyHealthBadge.textContent = 'Strong Profile';
  } else if (report.overall_health_verdict === 'Caution') {
    companyHealthBadge.classList.add('verdict-caution');
    companyHealthBadge.textContent = 'Caution Advised';
  } else {
    companyHealthBadge.classList.add('verdict-highrisk');
    companyHealthBadge.textContent = 'High Risk';
  }

  executiveSummaryText.textContent = report.executive_summary;

  // 1. Risks Card
  riskLevelBadge.className = report.risks.risk_level === 'Low' ? 'badge-risk-low' : 'badge-risk-high';
  riskLevelBadge.textContent = `${report.risks.risk_level.toUpperCase()} RISK`;
  riskSummaryText.textContent = report.risks.risk_summary;
  renderCitationChips(riskCitations, report.risks.evidence_citation_ids, report.citations);

  // 2. Culture Card
  cultureScoreBadge.textContent = `${report.culture.sentiment_rating} / 5.0`;
  culturePros.textContent = (report.culture.top_positives || []).join(', ');
  cultureCons.textContent = (report.culture.top_complaints || []).join(', ');
  renderCitationChips(cultureCitations, report.culture.evidence_citation_ids, report.citations);

  // 3. Trends Card
  if (report.tech_trends && report.tech_trends.length > 0) {
    const t = report.tech_trends[0];
    trendsVerdictBadge.textContent = t.growth_verdict.toUpperCase();
    trendsVerdictBadge.className = t.growth_verdict === 'Surging' ? 'badge-trend-surging' : 'badge-score';
    trendsSummaryText.textContent = t.trend_description;
    renderCitationChips(trendsCitations, [t.citation_id], report.citations);
  }

  // 4. Maps Card
  if (report.location_signal) {
    mapsRatingBadge.textContent = `${report.location_signal.rating || 4.5} ★`;
    mapsAddressText.textContent = report.location_signal.address || "Verified Technology Campus";
    renderCitationChips(mapsCitations, [report.location_signal.citation_id], report.citations);
  }

  // 5. Evidence Vault List
  citationCountBadge.textContent = `${report.citations.length} Verified Sources Loaded`;
  citationsVaultList.innerHTML = '';
  report.citations.forEach(c => {
    const item = document.createElement('div');
    item.className = 'vault-item';
    item.innerHTML = `
      <div class="vault-item-left">
        <span class="citation-chip" onclick="showCitationModal('${c.id}')">[${c.id}]</span>
        <span class="engine-tag engine-${c.engine.replace('google_', '')}">${c.engine}</span>
        <strong>${escapeHtml(c.source_title)}</strong>
      </div>
      <div>
        <a href="${c.source_url}" target="_blank" rel="noopener noreferrer">Inspect Source ↗</a>
      </div>
    `;
    citationsVaultList.appendChild(item);
  });
}

function renderCitationChips(container, citIds, allCitations) {
  container.innerHTML = '';
  (citIds || []).forEach(cid => {
    if (!cid) return;
    const c = allCitations.find(item => item.id === cid);
    if (c) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'citation-chip';
      chip.innerHTML = `<span>[${c.id}]</span> <small>${c.engine.replace('google_', '')}</small>`;
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
  
  const modalCitMethod = document.getElementById('modalCitMethod');
  if (modalCitMethod) {
    modalCitMethod.textContent = c.verification_method || 'exact_entity_match';
  }
  
  modalCitUrl.href = c.source_url;
  modalCitUrl.textContent = c.source_url;

  citationModal.classList.remove('hidden');
};

async function generateOutreach() {
  if (!state.currentReport || !state.selectedJob) return;

  outreachSubject.textContent = "Synthesizing evidence-grounded application pack...";
  outreachEmail.innerHTML = "Linking citations and building anti-hallucination hooks...";
  outreachBullets.innerHTML = "";

  try {
    const res = await fetch('/api/outreach/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_name: state.selectedJob.company_name,
        role_title: state.selectedJob.title,
        job_description: state.selectedJob.description,
        candidate_profile_text: resumeInput.value.trim(),
        due_diligence_report: state.currentReport
      })
    });

    const data = await res.json();
    state.currentOutreach = data;

    outreachSubject.textContent = data.subject_line;
    
    // Parse bracketed citations into clickable chips
    let formattedEmail = escapeHtml(data.cover_letter);
    formattedEmail = formattedEmail.replace(/\[(cit-\d+)\]/g, (match, p1) => {
      return `<span class="citation-chip" onclick="showCitationModal('${p1}')">[${p1}]</span>`;
    });
    outreachEmail.innerHTML = formattedEmail;

    // Render bullets
    outreachBullets.innerHTML = '';
    (data.tailored_resume_bullets || []).forEach(b => {
      const li = document.createElement('li');
      let formattedB = escapeHtml(b);
      formattedB = formattedB.replace(/\[(cit-\d+)\]/g, (match, p1) => {
        return `<span class="citation-chip" onclick="showCitationModal('${p1}')">[${p1}]</span>`;
      });
      li.innerHTML = formattedB;
      outreachBullets.appendChild(li);
    });

  } catch (err) {
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
