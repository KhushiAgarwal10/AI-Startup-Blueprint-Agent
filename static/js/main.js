/**
 * main.js – Global utilities shared across all pages
 * - Dark / light mode toggle with localStorage persistence
 * - Navbar scroll behaviour
 */

'use strict';

// ---------------------------------------------------------------------------
// Theme management
// ---------------------------------------------------------------------------

const THEME_KEY = 'sbp-theme';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-bs-theme', theme);
  const icon  = document.getElementById('themeIcon');
  const label = document.getElementById('themeLabel');
  if (!icon || !label) return;
  if (theme === 'dark') {
    icon.className  = 'bi bi-sun-fill';
    label.textContent = 'Light';
  } else {
    icon.className  = 'bi bi-moon-stars-fill';
    label.textContent = 'Dark';
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-bs-theme') || 'light';
  const next    = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem(THEME_KEY, next); } catch (_) {}
}

// Initialise theme on load
(function initTheme() {
  let saved;
  try { saved = localStorage.getItem(THEME_KEY); } catch (_) {}
  const preferred = saved || (
    window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  );
  applyTheme(preferred);
})();

document.addEventListener('DOMContentLoaded', function () {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.addEventListener('click', toggleTheme);
});

// ---------------------------------------------------------------------------
// Utility: convert markdown to sanitised HTML using marked.js
// ---------------------------------------------------------------------------
function renderMarkdown(mdText) {
  if (typeof marked === 'undefined') return escapeHtml(mdText);
  return marked.parse(mdText, {
    gfm: true,
    breaks: true,
    headerIds: false,
    mangle: false,
  });
}

// ---------------------------------------------------------------------------
// Utility: escape HTML for safe insertion
// ---------------------------------------------------------------------------
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Utility: copy text to clipboard with button feedback
// ---------------------------------------------------------------------------
function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Copied!';
    btn.classList.add('btn-success');
    btn.classList.remove('btn-outline-secondary');
    setTimeout(() => {
      btn.innerHTML = original;
      btn.classList.remove('btn-success');
      btn.classList.add('btn-outline-secondary');
    }, 2000);
  }).catch(() => {
    alert('Copy failed – please select and copy manually.');
  });
}

// ---------------------------------------------------------------------------
// Utility: download blueprint as PDF via API
// ---------------------------------------------------------------------------
async function downloadBlueprintPDF(blueprint, startupName) {
  try {
    const res = await fetch('/api/download-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blueprint, startup_name: startupName }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'PDF download failed.');
    }

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = (startupName || 'Blueprint').replace(/\s+/g, '_') + '_Blueprint.pdf';
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert('PDF download error: ' + err.message);
  }
}

// Expose globally
window.SBP = { renderMarkdown, escapeHtml, copyToClipboard, downloadBlueprintPDF };
