// ── State ─────────────────────────────────────────────────────────
const state = {
  attachedFiles: [],   // File objects
  attachedUrls: [],    // string[]
  sessionId: null,
};

// ── DOM refs ──────────────────────────────────────────────────────
const screenInput  = document.getElementById('screen-input');
const screenActive = document.getElementById('screen-active');

const objectiveInput  = document.getElementById('objective-input');
const contentInput    = document.getElementById('content-input');
const fileInput       = document.getElementById('file-input');

const btnAttachFile   = document.getElementById('btn-attach-file');
const btnAttachUrl    = document.getElementById('btn-attach-url');
const btnSubmit       = document.getElementById('btn-submit');

const urlModal        = document.getElementById('url-modal');
const urlModalInput   = document.getElementById('url-modal-input');
const btnUrlAdd       = document.getElementById('btn-url-add');
const btnUrlCancel    = document.getElementById('btn-url-cancel');

const filesList         = document.getElementById('files-list');
const urlsList          = document.getElementById('urls-list');
const objectiveBox      = document.getElementById('objective-box');
const contentPreviewBox = document.getElementById('content-preview-box');
const curatedBundleBox  = document.getElementById('curated-bundle-box');
const curatedBundleText = document.getElementById('curated-bundle-text');
const challengeBox      = document.getElementById('challenge-box');
const challengeText     = document.getElementById('challenge-text');
const rationaleText     = document.getElementById('rationale-text');
const sourceSnippetBox  = document.getElementById('source-snippet-box');
const answerInput       = document.getElementById('answer-input');
const btnSubmitAnswer   = document.getElementById('btn-submit-answer');
const evalResultBox     = document.getElementById('eval-result-box');
const evalScore         = document.getElementById('eval-score');
const evalFeedback      = document.getElementById('eval-feedback');
const evalPass          = document.getElementById('eval-pass');
const loadingBox        = document.getElementById('loading-box');

// ── Helpers ───────────────────────────────────────────────────────
function show(el)  { el.classList.remove('hidden'); }
function hide(el)  { el.classList.add('hidden'); }

function renderAttachedFiles() {
  filesList.innerHTML = '';
  state.attachedFiles.forEach(f => {
    const chip = document.createElement('div');
    chip.className = 'file-chip';
    chip.textContent = f.name;
    filesList.appendChild(chip);
  });
}

function renderAttachedUrls() {
  // Hint text visibility
  const hint = document.getElementById('hint-text');
  if (hint && (state.attachedFiles.length > 0 || state.attachedUrls.length > 0)) {
    hide(hint);
  }

  urlsList.innerHTML = '';
  state.attachedUrls.forEach((url, i) => {
    const chip = document.createElement('div');
    chip.className = 'url-chip';
    chip.textContent = url;
    chip.title = url;
    urlsList.appendChild(chip);
  });
}

// Auto-resize textarea
contentInput.addEventListener('input', () => {
  contentInput.style.height = 'auto';
  contentInput.style.height = contentInput.scrollHeight + 'px';
});

// ── File attachment ────────────────────────────────────────────────
btnAttachFile.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
  const newFiles = Array.from(fileInput.files);
  state.attachedFiles = [...state.attachedFiles, ...newFiles];
  fileInput.value = '';
  renderAttachedFiles();

  const hint = document.getElementById('hint-text');
  if (hint && state.attachedFiles.length > 0) hide(hint);
});

// ── URL modal ──────────────────────────────────────────────────────
btnAttachUrl.addEventListener('click', () => {
  urlModalInput.value = '';
  show(urlModal);
  setTimeout(() => urlModalInput.focus(), 50);
});

btnUrlCancel.addEventListener('click', () => hide(urlModal));

urlModal.addEventListener('click', (e) => {
  if (e.target === urlModal) hide(urlModal);
});

urlModalInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') addUrl();
});

btnUrlAdd.addEventListener('click', addUrl);

function addUrl() {
  const url = urlModalInput.value.trim();
  if (!url) return;
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    urlModalInput.setCustomValidity('Please enter a valid URL starting with http:// or https://');
    urlModalInput.reportValidity();
    return;
  }
  if (!state.attachedUrls.includes(url)) {
    state.attachedUrls.push(url);
  }
  hide(urlModal);
  renderAttachedUrls();
}

// ── Submit / Curate ────────────────────────────────────────────────
btnSubmit.addEventListener('click', submitCuration);
objectiveInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') submitCuration();
});

async function submitCuration() {
  const objective = objectiveInput.value.trim();
  if (!objective) {
    objectiveInput.focus();
    objectiveInput.style.borderColor = '#ef4444';
    setTimeout(() => (objectiveInput.style.borderColor = ''), 1500);
    return;
  }

  btnSubmit.disabled = true;

  // Switch to active screen
  hide(screenInput);
  show(screenActive);

  // Populate sidebar
  renderAttachedFiles();
  renderAttachedUrls();

  // Show objective
  objectiveBox.textContent = `Objective : ${objective}`;

  // Reset chat content
  hide(contentPreviewBox);
  hide(curatedBundleBox);
  hide(challengeBox);
  hide(evalResultBox);
  show(loadingBox);

  const formData = new FormData();
  formData.append('learning_objective', objective);

  const content = contentInput.value.trim();
  if (content) formData.append('content', content);

  formData.append('urls', JSON.stringify(state.attachedUrls));

  for (const f of state.attachedFiles) {
    formData.append('files', f);
  }

  try {
    const resp = await fetch('/api/curate', { method: 'POST', body: formData });
    const data = await resp.json();

    hide(loadingBox);

    if (!resp.ok) {
      showError(data.detail || 'Curation failed. Please try again.');
      btnSubmit.disabled = false;
      return;
    }

    state.sessionId = data.session_id;
    renderResults(data);
  } catch (err) {
    hide(loadingBox);
    showError(`Network error: ${err.message}`);
    btnSubmit.disabled = false;
  }
}

function renderResults(data) {
  // Content preview
  if (data.aggregated_content_preview) {
    contentPreviewBox.textContent = `Content: ${data.aggregated_content_preview}${data.aggregated_content_preview.length >= 300 ? '...........' : ''}`;
    show(contentPreviewBox);
  }

  const bundle = data.bundle || {};

  // Curated bundle
  if (bundle.curated_bundle) {
    curatedBundleText.textContent = bundle.curated_bundle;
    show(curatedBundleBox);
  }

  // Dynamic challenge
  if (bundle.dynamic_challenge) {
    challengeText.textContent = bundle.dynamic_challenge;
    rationaleText.textContent = `Rationale : ${bundle.rationale || ''}`;
    sourceSnippetBox.textContent = bundle.required_output || '';
    answerInput.value = '';
    evalResultBox.classList.add('hidden');
    show(challengeBox);
  }
}

function showError(msg) {
  const errBox = document.createElement('div');
  errBox.className = 'chat-box';
  errBox.style.borderColor = '#ef4444';
  errBox.style.color = '#dc2626';
  errBox.textContent = msg;
  document.getElementById('panel-center') || document.querySelector('.panel-center').appendChild(errBox);
}

// ── Submit Answer ─────────────────────────────────────────────────
btnSubmitAnswer.addEventListener('click', submitAnswer);

async function submitAnswer() {
  if (!state.sessionId) return;
  const answer = answerInput.value.trim();
  if (!answer) {
    answerInput.focus();
    return;
  }

  btnSubmitAnswer.disabled = true;
  btnSubmitAnswer.textContent = 'evaluating...';

  try {
    const resp = await fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.sessionId, answer }),
    });
    const result = await resp.json();

    btnSubmitAnswer.disabled = false;
    btnSubmitAnswer.textContent = 'submit';

    if (!resp.ok) {
      alert(result.detail || 'Evaluation failed.');
      return;
    }

    renderEvaluation(result);
  } catch (err) {
    btnSubmitAnswer.disabled = false;
    btnSubmitAnswer.textContent = 'submit';
    alert(`Network error: ${err.message}`);
  }
}

function renderEvaluation(result) {
  const pct = Math.round(result.score * 100);
  evalScore.textContent = `Score: ${pct}%`;
  evalScore.style.color = result.passed ? '#16a34a' : '#dc2626';
  evalFeedback.textContent = result.feedback;
  evalPass.textContent = result.passed ? '✓ Passed' : '✗ Not yet — keep trying!';
  evalPass.style.color = result.passed ? '#16a34a' : '#dc2626';
  show(evalResultBox);
  evalResultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
