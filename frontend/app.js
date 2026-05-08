/* ═══════════════════════════════════════════════════════════════════
   STATE
═══════════════════════════════════════════════════════════════════ */
const state = {
  attachedFiles: [],
  attachedUrls:  [],
  sessionId:     null,
};

/* ═══════════════════════════════════════════════════════════════════
   DOM REFS
═══════════════════════════════════════════════════════════════════ */
const screenInput  = document.getElementById('screen-input');
const screenActive = document.getElementById('screen-active');

const objectiveInput  = document.getElementById('objective-input');
const contentInput    = document.getElementById('content-input');
const fileInput       = document.getElementById('file-input');

const btnAttachFile    = document.getElementById('btn-attach-file');
const btnAttachUrl     = document.getElementById('btn-attach-url');
const btnSubmit        = document.getElementById('btn-submit');
const btnSetObjective  = document.getElementById('btn-set-objective');

const urlModal      = document.getElementById('url-modal');
const urlModalInput = document.getElementById('url-modal-input');
const btnUrlAdd     = document.getElementById('btn-url-add');
const btnUrlCancel  = document.getElementById('btn-url-cancel');
const btnUrlClose   = document.getElementById('btn-url-close');

const filesList  = document.getElementById('files-list');
const urlsList   = document.getElementById('urls-list');
const filesCount = document.getElementById('files-count');
const urlsCount  = document.getElementById('urls-count');
const filesEmpty = document.getElementById('files-empty');
const urlsEmpty  = document.getElementById('urls-empty');

const objectiveBox      = document.getElementById('objective-box');
const contentPreviewBox = document.getElementById('content-preview-box');
const previewText       = document.getElementById('preview-text');
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
const evalScoreFill     = document.getElementById('eval-score-fill');
const loadingBox        = document.getElementById('loading-box');
const loadingText       = document.getElementById('loading-text');

const strategyBadge     = document.getElementById('strategy-badge');
const btnNewSession     = document.getElementById('btn-new-session');
const attachmentChips   = document.getElementById('attachment-chips');
const hintText          = document.getElementById('hint-text');
const composerHint      = document.getElementById('composer-hint');
const toastContainer    = document.getElementById('toast-container');


/* ═══════════════════════════════════════════════════════════════════
   UTILITIES
═══════════════════════════════════════════════════════════════════ */
const show = el => el.classList.remove('hidden');
const hide = el => el.classList.add('hidden');

function revealCard(el) {
  el.classList.remove('hidden');
  // Double RAF: let browser apply display, then trigger transition
  requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('visible')));
}
function hideCard(el) {
  el.classList.add('hidden');
  el.classList.remove('visible');
}

function extractDomain(url) {
  try { return new URL(url).hostname.replace(/^www\./, ''); }
  catch { return url.slice(0, 40); }
}

function getFileIcon(name) {
  const ext = name.split('.').pop().toLowerCase();
  const map = {
    py: '🐍', js: '⚡', ts: '⚡', json: '{ }', csv: '📊',
    pdf: '📕', html: '🌐', htm: '🌐', md: '📝', txt: '📄',
  };
  return map[ext] || '📎';
}

function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.textContent = msg;
  toastContainer.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(14px)';
    setTimeout(() => el.remove(), 280);
  }, 4200);
}


/* ═══════════════════════════════════════════════════════════════════
   LOADING STEPS
═══════════════════════════════════════════════════════════════════ */
const LOADING_STEPS = [
  'Fetching content sources...',
  'Aggregating knowledge...',
  'Routing to best strategy...',
  'Crafting your challenge...',
  'Almost there...',
];
let _loadInterval = null;

function startLoading() {
  let i = 0;
  loadingText.textContent = LOADING_STEPS[0];
  show(loadingBox);
  _loadInterval = setInterval(() => {
    i = (i + 1) % LOADING_STEPS.length;
    loadingText.textContent = LOADING_STEPS[i];
  }, 2600);
}
function stopLoading() {
  if (_loadInterval) { clearInterval(_loadInterval); _loadInterval = null; }
  hide(loadingBox);
}


/* ═══════════════════════════════════════════════════════════════════
   STRATEGY BADGE
═══════════════════════════════════════════════════════════════════ */
const STRATEGY_META = {
  direct: { label: 'Direct LLM',  cls: 's-direct' },
  qdrant: { label: 'Vector RAG',  cls: 's-qdrant'  },
  neo4j:  { label: 'Graph RAG',   cls: 's-neo4j'   },
};

function showStrategyBadge(strategy) {
  if (!strategy) return;
  const m = STRATEGY_META[strategy] || { label: strategy, cls: '' };
  strategyBadge.textContent = m.label;
  strategyBadge.className = `strategy-badge ${m.cls}`;
  show(strategyBadge);
}


/* ═══════════════════════════════════════════════════════════════════
   ATTACHMENT CHIPS (input screen)
═══════════════════════════════════════════════════════════════════ */
function updateAttachmentChips() {
  attachmentChips.innerHTML = '';
  const hasItems = state.attachedFiles.length > 0 || state.attachedUrls.length > 0;

  if (!hasItems) {
    hide(attachmentChips);
    show(hintText);
    return;
  }
  show(attachmentChips);
  hide(hintText);

  state.attachedFiles.forEach((f, i) => {
    const chip = document.createElement('span');
    chip.className = 'a-chip';
    chip.innerHTML = `
      <span>${getFileIcon(f.name)}</span>
      ${f.name}
      <button class="a-chip-remove" data-type="file" data-idx="${i}" aria-label="Remove">×</button>
    `;
    attachmentChips.appendChild(chip);
  });

  state.attachedUrls.forEach((url, i) => {
    const chip = document.createElement('span');
    chip.className = 'a-chip';
    chip.innerHTML = `
      <span>🔗</span>
      ${extractDomain(url)}
      <button class="a-chip-remove" data-type="url" data-idx="${i}" aria-label="Remove">×</button>
    `;
    attachmentChips.appendChild(chip);
  });
}

attachmentChips.addEventListener('click', e => {
  const btn = e.target.closest('.a-chip-remove');
  if (!btn) return;
  const { type, idx } = btn.dataset;
  if (type === 'file') state.attachedFiles.splice(+idx, 1);
  else state.attachedUrls.splice(+idx, 1);
  updateAttachmentChips();
});


/* ═══════════════════════════════════════════════════════════════════
   SIDEBAR RENDERERS
═══════════════════════════════════════════════════════════════════ */
function renderFilesSidebar() {
  filesList.innerHTML = '';
  const count = state.attachedFiles.length;
  filesCount.textContent = count;

  if (count === 0) { show(filesEmpty); return; }
  hide(filesEmpty);

  state.attachedFiles.forEach((f, i) => {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.style.animationDelay = `${i * 0.05}s`;
    item.innerHTML = `
      <span class="file-icon">${getFileIcon(f.name)}</span>
      <span class="file-name" title="${f.name}">${f.name}</span>
    `;
    filesList.appendChild(item);
  });
}

function renderUrlsSidebar() {
  urlsList.innerHTML = '';
  const count = state.attachedUrls.length;
  urlsCount.textContent = count;

  if (count === 0) { show(urlsEmpty); return; }
  hide(urlsEmpty);

  state.attachedUrls.forEach((url, i) => {
    const item = document.createElement('div');
    item.className = 'url-item';
    item.style.animationDelay = `${i * 0.05}s`;
    item.innerHTML = `
      <span class="url-domain">${extractDomain(url)}</span>
      <span class="url-full" title="${url}">${url}</span>
    `;
    urlsList.appendChild(item);
  });
}


/* ═══════════════════════════════════════════════════════════════════
   FILE ATTACHMENT
═══════════════════════════════════════════════════════════════════ */
btnAttachFile.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
  const added = Array.from(fileInput.files);
  state.attachedFiles = [...state.attachedFiles, ...added];
  fileInput.value = '';
  updateAttachmentChips();
  if (added.length) toast(`${added.length} file${added.length > 1 ? 's' : ''} attached`, 'success');
});


/* ═══════════════════════════════════════════════════════════════════
   URL MODAL
═══════════════════════════════════════════════════════════════════ */
btnAttachUrl.addEventListener('click', () => {
  urlModalInput.value = '';
  show(urlModal);
  setTimeout(() => urlModalInput.focus(), 60);
});

const closeModal = () => hide(urlModal);
btnUrlCancel.addEventListener('click', closeModal);
btnUrlClose.addEventListener('click', closeModal);
urlModal.addEventListener('click', e => {
  if (!e.target.closest('.modal-card')) closeModal();
});
urlModalInput.addEventListener('keydown', e => { if (e.key === 'Enter') addUrl(); });
btnUrlAdd.addEventListener('click', addUrl);

function addUrl() {
  const url = urlModalInput.value.trim();
  if (!url) return;
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    toast('Please enter a valid URL starting with https://', 'error');
    urlModalInput.focus();
    return;
  }
  if (state.attachedUrls.includes(url)) {
    toast('This URL is already added', 'error');
    closeModal();
    return;
  }
  state.attachedUrls.push(url);
  closeModal();
  updateAttachmentChips();
  toast(`${extractDomain(url)} added`, 'success');
}


/* ═══════════════════════════════════════════════════════════════════
   AUTO-RESIZE TEXTAREA
═══════════════════════════════════════════════════════════════════ */
contentInput.addEventListener('input', () => {
  contentInput.style.height = 'auto';
  contentInput.style.height = Math.min(contentInput.scrollHeight, 140) + 'px';
});


/* ═══════════════════════════════════════════════════════════════════
   SET OBJECTIVE — STEP 1
═══════════════════════════════════════════════════════════════════ */
btnSetObjective.addEventListener('click', setObjective);
objectiveInput.addEventListener('keydown', e => { if (e.key === 'Enter') setObjective(); });

function setObjective() {
  const objective = objectiveInput.value.trim();
  if (!objective) {
    objectiveInput.focus();
    const field = objectiveInput.closest('.objective-field');
    field.style.borderColor = 'rgba(244,63,94,0.6)';
    setTimeout(() => (field.style.borderColor = ''), 1600);
    return;
  }
  contentInput.disabled = false;
  btnAttachFile.disabled = false;
  btnAttachUrl.disabled = false;
  btnSubmit.disabled = false;
  hide(composerHint);
  setTimeout(() => contentInput.focus(), 60);
}


/* ═══════════════════════════════════════════════════════════════════
   MAIN SUBMIT — CURATE
═══════════════════════════════════════════════════════════════════ */
btnSubmit.addEventListener('click', submitCuration);

async function submitCuration() {
  const objective = objectiveInput.value.trim();
  if (!objective) {
    objectiveInput.focus();
    const field = objectiveInput.closest('.objective-field');
    field.style.borderColor = 'rgba(244,63,94,0.6)';
    setTimeout(() => (field.style.borderColor = ''), 1600);
    return;
  }

  btnSubmit.disabled = true;

  // Transition to active screen
  hide(screenInput);
  show(screenActive);

  // Populate sidebars
  renderFilesSidebar();
  renderUrlsSidebar();

  // Reset and show objective
  hideCard(contentPreviewBox);
  hideCard(curatedBundleBox);
  hideCard(challengeBox);
  hideCard(evalResultBox);
  hide(strategyBadge);

  objectiveBox.querySelector('.msg-objective-text').textContent = objective;
  revealCard(objectiveBox);

  // Start loading
  startLoading();

  // Build form data
  const formData = new FormData();
  formData.append('learning_objective', objective);
  const content = contentInput.value.trim();
  if (content) formData.append('content', content);
  formData.append('urls', JSON.stringify(state.attachedUrls));
  for (const f of state.attachedFiles) formData.append('files', f);

  try {
    const resp = await fetch('/api/curate', { method: 'POST', body: formData });
    const data = await resp.json();

    stopLoading();

    if (!resp.ok) {
      const msg = data.detail || 'Curation failed. Please try again.';
      toast(msg, 'error');
      btnSubmit.disabled = false;
      return;
    }

    state.sessionId = data.session_id;
    renderResults(data, content);
  } catch (err) {
    stopLoading();
    toast(`Network error: ${err.message}`, 'error');
    btnSubmit.disabled = false;
  }
}


/* ═══════════════════════════════════════════════════════════════════
   RENDER RESULTS
═══════════════════════════════════════════════════════════════════ */
function renderResults(data, userContent = '') {
  showStrategyBadge(data.strategy_used);

  const bundle = data.bundle || {};

  // Content preview — show only what the user typed in the source input
  if (userContent) {
    previewText.textContent = userContent.slice(0, 300) + (userContent.length > 300 ? ' …' : '');
    revealCard(contentPreviewBox);
  }

  // Curated bundle
  if (bundle.curated_bundle) {
    curatedBundleText.textContent = bundle.curated_bundle;
    setTimeout(() => revealCard(curatedBundleBox), 220);
  }

  // Dynamic challenge
  if (bundle.dynamic_challenge) {
    challengeText.textContent = bundle.dynamic_challenge;
    rationaleText.textContent = bundle.rationale || '';
    sourceSnippetBox.textContent = bundle.required_output || '';
    answerInput.value = '';
    setTimeout(() => revealCard(challengeBox), 440);
  }

  // Scroll chat to top
  document.querySelector('.chat-panel').scrollTop = 0;
}


/* ═══════════════════════════════════════════════════════════════════
   SUBMIT ANSWER
═══════════════════════════════════════════════════════════════════ */
btnSubmitAnswer.addEventListener('click', submitAnswer);

async function submitAnswer() {
  if (!state.sessionId) return;
  const answer = answerInput.value.trim();
  if (!answer) { answerInput.focus(); return; }

  btnSubmitAnswer.disabled = true;
  btnSubmitAnswer.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
      style="animation:spin 0.7s linear infinite">
      <path d="M21 12a9 9 0 11-6.219-8.56"/>
    </svg>
    Evaluating...`;

  try {
    const resp = await fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.sessionId, answer }),
    });
    const result = await resp.json();

    btnSubmitAnswer.disabled = false;
    btnSubmitAnswer.innerHTML = `Submit Answer
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"/>
        <polyline points="12 5 19 12 12 19"/>
      </svg>`;

    if (!resp.ok) {
      toast(result.detail || 'Evaluation failed.', 'error');
      return;
    }

    renderEvaluation(result);
  } catch (err) {
    btnSubmitAnswer.disabled = false;
    btnSubmitAnswer.innerHTML = 'Submit Answer';
    toast(`Network error: ${err.message}`, 'error');
  }
}


/* ═══════════════════════════════════════════════════════════════════
   RENDER EVALUATION
═══════════════════════════════════════════════════════════════════ */
function renderEvaluation(result) {
  const pct = Math.round(result.score * 100);
  const passed = result.passed;

  evalScore.textContent = `${pct}%`;
  evalScore.style.color = passed ? 'var(--green)' : 'var(--red)';

  evalPass.textContent = passed ? '✓ Passed' : '✗ Keep going';
  evalPass.className = `eval-verdict ${passed ? 'pass' : 'fail'}`;

  evalFeedback.textContent = result.feedback;

  if (evalScoreFill) {
    evalScoreFill.className = `eval-bar-fill ${passed ? 'pass' : 'fail'}`;
    setTimeout(() => (evalScoreFill.style.width = `${pct}%`), 80);
  }

  evalResultBox.className = `msg-card msg-card--eval ${passed ? 'eval-pass' : 'eval-fail'}`;

  revealCard(evalResultBox);
  setTimeout(() => evalResultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 420);

  toast(passed ? 'Great work — challenge passed! 🎉' : 'Not quite — review the feedback and try again.', passed ? 'success' : 'info');
}


/* ═══════════════════════════════════════════════════════════════════
   NEW SESSION
═══════════════════════════════════════════════════════════════════ */
btnNewSession.addEventListener('click', () => {
  state.attachedFiles = [];
  state.attachedUrls  = [];
  state.sessionId     = null;

  objectiveInput.value = '';
  contentInput.value   = '';
  contentInput.style.height = 'auto';

  contentInput.disabled   = true;
  btnAttachFile.disabled  = true;
  btnAttachUrl.disabled   = true;
  btnSubmit.disabled      = true;
  show(composerHint);

  updateAttachmentChips();

  hide(screenActive);
  show(screenInput);

  setTimeout(() => objectiveInput.focus(), 120);
});


/* ═══════════════════════════════════════════════════════════════════
   CSS for spinner keyframe (injected once)
═══════════════════════════════════════════════════════════════════ */
const _spinStyle = document.createElement('style');
_spinStyle.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
document.head.appendChild(_spinStyle);
