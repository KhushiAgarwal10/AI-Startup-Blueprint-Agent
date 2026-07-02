/**
 * chat.js – Blueprint generation page logic
 * Handles:
 *   - Idea input / validation
 *   - Full blueprint generation with loading steps
 *   - Typing effect / progressive render
 *   - Sections quick-nav
 *   - Copy & PDF download
 *   - Example idea injection
 */

'use strict';

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const ideaInput         = document.getElementById('ideaInput');
const charCount         = document.getElementById('charCount');
const btnGenerate       = document.getElementById('btnGenerate');
const btnValidate       = document.getElementById('btnValidate');
const errorAlert        = document.getElementById('errorAlert');
const errorMessage      = document.getElementById('errorMessage');
const emptyState        = document.getElementById('emptyState');
const loadingState      = document.getElementById('loadingState');
const loadingTitle      = document.getElementById('loadingTitle');
const loadingSubtitle   = document.getElementById('loadingSubtitle');
const validationResult  = document.getElementById('validationResult');
const validationContent = document.getElementById('validationContent');
const blueprintResult   = document.getElementById('blueprintResult');
const blueprintContent  = document.getElementById('blueprintContent');
const blueprintTitle    = document.getElementById('blueprintTitle');
const readinessBadge    = document.getElementById('readinessBadge');
const readinessScore    = document.getElementById('readinessScore');
const sectionsNav       = document.getElementById('sectionsNav');
const btnCopy           = document.getElementById('btnCopy');
const btnDownloadPDF    = document.getElementById('btnDownloadPDF');
const btnNewBlueprint   = document.getElementById('btnNewBlueprint');
const btnDismissVal     = document.getElementById('btnDismissValidation');

// State
let currentBlueprint  = '';
let currentStartupName = 'My Startup';

// ---------------------------------------------------------------------------
// Character counter
// ---------------------------------------------------------------------------
if (ideaInput) {
  ideaInput.addEventListener('input', () => {
    charCount.textContent = `${ideaInput.value.length} / 3000`;
  });
}

// ---------------------------------------------------------------------------
// Example idea buttons
// ---------------------------------------------------------------------------
document.querySelectorAll('.example-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    ideaInput.value = btn.dataset.idea;
    charCount.textContent = `${ideaInput.value.length} / 3000`;
    ideaInput.focus();
  });
});

// ---------------------------------------------------------------------------
// Show / hide helpers
// ---------------------------------------------------------------------------
function showError(msg) {
  errorMessage.textContent = msg;
  errorAlert.classList.remove('d-none');
}
function hideError() { errorAlert.classList.add('d-none'); }

function setButtonLoading(btn, loading) {
  btn.querySelector('.btn-text').classList.toggle('d-none', loading);
  btn.querySelector('.btn-loading').classList.toggle('d-none', !loading);
  btn.disabled = loading;
}

function showEmpty() {
  emptyState.classList.remove('d-none');
  loadingState.classList.add('d-none');
  blueprintResult.classList.add('d-none');
}

function showLoading() {
  emptyState.classList.add('d-none');
  loadingState.classList.remove('d-none');
  blueprintResult.classList.add('d-none');
}

function showBlueprint() {
  emptyState.classList.add('d-none');
  loadingState.classList.add('d-none');
  blueprintResult.classList.remove('d-none');
}

// ---------------------------------------------------------------------------
// Animated loading steps
// ---------------------------------------------------------------------------
const STEPS = ['step1', 'step2', 'step3', 'step4', 'step5'];
const STEP_MESSAGES = [
  ['Validating concept…',        'Checking feasibility and market need'],
  ['Analysing market…',          'Estimating TAM/SAM/SOM and competitors'],
  ['Building business canvas…',  'Mapping revenue, channels, and partners'],
  ['Generating roadmap…',        'Planning go-to-market and growth milestones'],
  ['Finalising blueprint…',      'Assembling all 18 sections'],
];

let stepTimers = [];

function startLoadingSteps() {
  // Reset
  STEPS.forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.className = 'loading-step'; el.querySelector('i').className = 'bi bi-arrow-right-circle me-2'; }
  });
  stepTimers.forEach(clearTimeout);
  stepTimers = [];

  // Activate step 1 immediately
  activateStep(0);

  // Advance remaining steps with delays
  [2800, 6000, 9500, 13000].forEach((delay, i) => {
    stepTimers.push(setTimeout(() => activateStep(i + 1), delay));
  });
}

function activateStep(index) {
  // Mark previous as done
  if (index > 0) {
    const prev = document.getElementById(STEPS[index - 1]);
    if (prev) {
      prev.className = 'loading-step done';
      prev.querySelector('i').className = 'bi bi-check2-circle me-2';
    }
  }
  const el = document.getElementById(STEPS[index]);
  if (el) {
    el.className = 'loading-step active';
    el.querySelector('i').className = 'bi bi-check2-circle me-2';
  }
  if (STEP_MESSAGES[index]) {
    loadingTitle.textContent    = STEP_MESSAGES[index][0];
    loadingSubtitle.textContent = STEP_MESSAGES[index][1];
  }
}

function stopLoadingSteps() {
  stepTimers.forEach(clearTimeout);
  stepTimers = [];
}

// ---------------------------------------------------------------------------
// Typing effect – renders markdown progressively word-by-word
// ---------------------------------------------------------------------------
function typewriterRender(mdText, container, onDone) {
  container.innerHTML = '';
  container.classList.add('typing-cursor');

  // Split into ~120-char chunks and render progressively
  const chunkSize   = 120;
  const totalChunks = Math.ceil(mdText.length / chunkSize);
  let   current     = 0;

  function tick() {
    current++;
    const slice = mdText.slice(0, current * chunkSize);
    container.innerHTML = window.SBP.renderMarkdown(slice);
    if (current < totalChunks) {
      setTimeout(tick, 18);
    } else {
      container.classList.remove('typing-cursor');
      if (typeof onDone === 'function') onDone();
    }
  }
  tick();
}

// ---------------------------------------------------------------------------
// Build quick-nav pills from h2 headings in blueprint
// ---------------------------------------------------------------------------
function buildSectionsNav(mdText) {
  sectionsNav.innerHTML = '';
  const headings = [...mdText.matchAll(/^## (.+)$/gm)].map(m => m[1].trim());
  headings.forEach((heading, i) => {
    const pill = document.createElement('button');
    pill.className = 'nav-pill';
    pill.textContent = heading.replace(/\(.*\)/, '').trim();
    pill.addEventListener('click', () => {
      // Find the matching h2 in the rendered content and scroll to it
      const h2s = blueprintContent.querySelectorAll('h2');
      if (h2s[i]) h2s[i].scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    sectionsNav.appendChild(pill);
  });
}

// ---------------------------------------------------------------------------
// Score badge colour
// ---------------------------------------------------------------------------
function applyScoreColour(score) {
  readinessBadge.style.cssText = '';
  if (score >= 75) {
    readinessBadge.style.color       = '#16a34a';
    readinessBadge.style.borderColor = '#16a34a';
    readinessBadge.style.background  = 'rgba(22,163,74,.08)';
  } else if (score >= 50) {
    readinessBadge.style.color       = '#d97706';
    readinessBadge.style.borderColor = '#d97706';
    readinessBadge.style.background  = 'rgba(217,119,6,.08)';
  } else if (score > 0) {
    readinessBadge.style.color       = '#dc2626';
    readinessBadge.style.borderColor = '#dc2626';
    readinessBadge.style.background  = 'rgba(220,38,38,.08)';
  }
}

// ---------------------------------------------------------------------------
// Generate blueprint
// ---------------------------------------------------------------------------
async function generateBlueprint() {
  const idea = ideaInput.value.trim();
  if (!idea) { showError('Please enter your startup idea.'); return; }
  if (idea.length < 10) { showError('Your idea is too short — add more detail.'); return; }
  hideError();

  setButtonLoading(btnGenerate, true);
  setButtonLoading(btnValidate, true);
  showLoading();
  startLoadingSteps();
  validationResult.classList.add('d-none');

  try {
    const res  = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idea }),
    });
    const data = await res.json();

    stopLoadingSteps();

    if (!data.success) {
      showError(data.error || 'Generation failed. Please try again.');
      showEmpty();
      return;
    }

    currentBlueprint   = data.blueprint;
    currentStartupName = data.startup_name || 'My Startup';

    blueprintTitle.textContent = currentStartupName + ' — Blueprint';
    readinessScore.textContent = data.readiness_score || '–';
    applyScoreColour(data.readiness_score || 0);

    buildSectionsNav(currentBlueprint);
    showBlueprint();

    typewriterRender(currentBlueprint, blueprintContent, () => {
      // Scroll to top of result after rendering
      blueprintResult.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

  } catch (err) {
    stopLoadingSteps();
    showError('Network error: ' + err.message);
    showEmpty();
  } finally {
    setButtonLoading(btnGenerate, false);
    setButtonLoading(btnValidate, false);
  }
}

// ---------------------------------------------------------------------------
// Validate idea (quick 5-dimension check)
// ---------------------------------------------------------------------------
async function validateIdea() {
  const idea = ideaInput.value.trim();
  if (!idea) { showError('Please enter your startup idea to validate.'); return; }
  hideError();

  setButtonLoading(btnValidate, true);
  setButtonLoading(btnGenerate, true);

  try {
    const res  = await fetch('/api/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idea }),
    });
    const data = await res.json();

    if (!data.success) {
      showError(data.error || 'Validation failed. Please try again.');
      return;
    }

    validationContent.innerHTML = window.SBP.renderMarkdown(data.validation);
    validationResult.classList.remove('d-none');
    validationResult.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    showError('Network error: ' + err.message);
  } finally {
    setButtonLoading(btnValidate, false);
    setButtonLoading(btnGenerate, false);
  }
}

// ---------------------------------------------------------------------------
// Wire up buttons
// ---------------------------------------------------------------------------
if (btnGenerate) btnGenerate.addEventListener('click', generateBlueprint);
if (btnValidate) btnValidate.addEventListener('click', validateIdea);

if (btnDismissVal) {
  btnDismissVal.addEventListener('click', () => validationResult.classList.add('d-none'));
}

if (btnNewBlueprint) {
  btnNewBlueprint.addEventListener('click', () => {
    currentBlueprint   = '';
    currentStartupName = 'My Startup';
    ideaInput.value    = '';
    charCount.textContent = '0 / 3000';
    hideError();
    showEmpty();
    validationResult.classList.add('d-none');
    blueprintContent.innerHTML = '';
    ideaInput.focus();
  });
}

if (btnCopy) {
  btnCopy.addEventListener('click', () => {
    if (currentBlueprint) window.SBP.copyToClipboard(currentBlueprint, btnCopy);
  });
}

if (btnDownloadPDF) {
  btnDownloadPDF.addEventListener('click', () => {
    if (currentBlueprint)
      window.SBP.downloadBlueprintPDF(currentBlueprint, currentStartupName);
  });
}

// Allow Ctrl/Cmd+Enter to trigger generation
if (ideaInput) {
  ideaInput.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      generateBlueprint();
    }
  });
}
