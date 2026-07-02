/**
 * dashboard.js – Blueprint history dashboard logic
 * Handles:
 *   - View blueprint in modal
 *   - PDF download from dashboard
 *   - Clear history with confirmation
 */

'use strict';

const blueprintModal   = document.getElementById('blueprintModal');
const modalBlueprintName    = document.getElementById('modalBlueprintName');
const modalBlueprintContent = document.getElementById('modalBlueprintContent');
const modalDownloadPDF = document.getElementById('modalDownloadPDF');
const btnClearHistory  = document.getElementById('btnClearHistory');
const clearModal       = document.getElementById('clearModal');
const btnConfirmClear  = document.getElementById('btnConfirmClear');

let modalCurrentBlueprint = '';
let modalCurrentName      = '';

// ---------------------------------------------------------------------------
// "View" buttons – open modal and render blueprint
// ---------------------------------------------------------------------------
document.querySelectorAll('.btn-view-blueprint').forEach(btn => {
  btn.addEventListener('click', () => {
    modalCurrentBlueprint = btn.dataset.blueprint || '';
    modalCurrentName      = btn.dataset.name      || 'Startup Blueprint';
    modalBlueprintName.textContent    = modalCurrentName;
    modalBlueprintContent.innerHTML   = window.SBP.renderMarkdown(modalCurrentBlueprint);

    const modal = bootstrap.Modal.getOrCreate(blueprintModal);
    modal.show();
  });
});

// ---------------------------------------------------------------------------
// PDF download from "PDF" button on cards
// ---------------------------------------------------------------------------
document.querySelectorAll('.btn-dl-blueprint').forEach(btn => {
  btn.addEventListener('click', () => {
    const bp   = btn.dataset.blueprint || '';
    const name = btn.dataset.name      || 'Startup';
    if (bp) window.SBP.downloadBlueprintPDF(bp, name);
  });
});

// ---------------------------------------------------------------------------
// PDF download from modal footer
// ---------------------------------------------------------------------------
if (modalDownloadPDF) {
  modalDownloadPDF.addEventListener('click', () => {
    if (modalCurrentBlueprint)
      window.SBP.downloadBlueprintPDF(modalCurrentBlueprint, modalCurrentName);
  });
}

// ---------------------------------------------------------------------------
// Clear history
// ---------------------------------------------------------------------------
if (btnClearHistory) {
  btnClearHistory.addEventListener('click', () => {
    const modal = bootstrap.Modal.getOrCreate(clearModal);
    modal.show();
  });
}

if (btnConfirmClear) {
  btnConfirmClear.addEventListener('click', async () => {
    try {
      const res  = await fetch('/api/clear-history', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        // Reload page to reflect cleared state
        window.location.reload();
      }
    } catch (err) {
      alert('Failed to clear history: ' + err.message);
    }
  });
}
