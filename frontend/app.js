
let state = { state: null, tasks: [], active_timer: null };
let checkinDone = false;
let selectedSpoons = 5;
let currentMode = 'green';
let activeTab = 'focus';
let timerTick = null;
let bodyDoubling = false;
let nextTaskIndex = 0;
let cachedNextTasks = [];

// ── Init ──
async function init() {
  // Start passive log checker + crisis monitor
  startPassiveLog();
  startCrisisMonitor();

  // Check onboarding
  const onboarded = localStorage.getItem('neur-os-onboarded');
  if (!onboarded) {
    document.getElementById('onboarding-card').style.display = '';
    document.getElementById('checkin-card').style.display = 'none';
    document.getElementById('mode-bar').style.display = 'none';
    document.querySelector('.tab-bar').style.display = 'none';
    return;
  }
  // Check if we already have a check-in today (from API or localStorage)
  try {
    const resp = await fetch(`${API}/api/state`);
    const data = await resp.json();
    if (data.state && data.state.date === today() && data.state.total_spoons > 0) {
      checkinDone = true;
    }
  } catch(e) {}
  const saved = localStorage.getItem('neur-os-checkin');
  if (!checkinDone && saved) {
    try { const p = JSON.parse(saved); if (p.date === today()) checkinDone = true; } catch(e) {}
  }
  if (checkinDone) {
    document.getElementById('checkin-card').style.display = 'none';
    await loadMode();
    await refreshTimers();
    await loadNextTask();
  } else {
    document.getElementById('checkin-card').style.display = '';
  }
  await refreshState();
}

function today() { return new Date().toISOString().slice(0,10); }
function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// ── Mode ──
async function loadMode() {
  try {
    const resp = await fetch(`${API}/api/mode`);
    const data = await resp.json();
    setMode(data.mode || 'green', true);
  } catch(e) { setMode('green', true); }
}

async function setMode(mode, silent) {
  currentMode = mode;
  document.body.className = `mode-${mode}`;
  document.querySelectorAll('.mode-dot').forEach(d => d.classList.toggle('active', d.dataset.mode === mode));
  const labels = { green: 'Ready', amber: 'Low energy', red: 'Rest' };
  document.getElementById('mode-label').textContent = labels[mode] || mode;
  if (!silent) {
    try { await fetch(`${API}/api/mode`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ mode })
    }); } catch(e) {}
    if (mode === 'red') {
      document.getElementById('focus-empty').classList.remove('hidden');
      document.getElementById('focus-task').classList.add('hidden');
      document.getElementById('focus-card').querySelector('h2').textContent = 'Today might be a rest day. That\'s okay.';
    } else {
      await loadNextTask();
    }
  }
}

// ── Check-In ──
function setSpoons(n) { selectedSpoons = n; }

async function doCheckIn() {
  const pain = parseInt(document.getElementById('pain-level').value);
  const note = document.getElementById('checkin-note').value;
  const resp = await fetch(`${API}/api/check-in`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ spoons: selectedSpoons, pain_level: pain, note })
  });
  if (!resp.ok) return;
  const data = await resp.json();
  localStorage.setItem('neur-os-checkin', JSON.stringify({date: today(), spoons: selectedSpoons}));
  checkinDone = true;
  document.getElementById('checkin-card').style.display = 'none';

  // Auto-set mode
  if (data.suggested_mode) setMode(data.suggested_mode, true);
  else await loadMode();

  await refreshTimers();
  await loadNextTask();
  await refreshState();
}

// ── Single Task Focus ──
async function loadNextTask() {
  const container = document.getElementById('focus-task');
  const empty = document.getElementById('focus-empty');
  const taskView = document.getElementById('focus-task-view');
  const timerView = document.getElementById('focus-timer-view');

  if (!checkinDone) return;

  if (currentMode === 'red') {
    empty.classList.remove('hidden');
    container.classList.add('hidden');
    document.getElementById('focus-card').querySelector('h2').textContent = 'Today might be a rest day. That\'s okay.';
    return;
  }

  try {
    const resp = await fetch(`${API}/api/tasks/next`);
    const data = await resp.json();

    if (!data.task) {
      empty.classList.remove('hidden');
      container.classList.add('hidden');
      document.getElementById('focus-card').querySelector('h2').textContent = data.message || 'What\'s one thing?';
      return;
    }

    empty.classList.add('hidden');
    container.classList.remove('hidden');
    timerView.classList.add('hidden');
    taskView.classList.remove('hidden');

    const t = data.task;
    document.getElementById('focus-title').innerHTML = esc(t.title);
    const recurring = t.recurring ? ` ↻${t.recurring}` : '';
    document.getElementById('focus-meta').innerHTML = `🍴 ${t.spoon_cost} spoons · ${t.energy_tag}${recurring}`;

    const chunks = JSON.parse(t.micro_chunks || '[]');
    const chunksEl = document.getElementById('focus-chunks');
    if (chunks.length > 0) {
      chunksEl.classList.remove('hidden');
      chunksEl.innerHTML = chunks.map(c => `<li>${esc(c)}</li>`).join('');
    } else {
      chunksEl.classList.add('hidden');
    }

    document.getElementById('focus-start-btn').textContent = `▶ Start (${t.spoon_cost <= 1 ? '15' : '25'} min)`;
    document.getElementById('focus-start-btn').dataset.taskId = t.id;
    document.getElementById('focus-start-btn').dataset.duration = t.spoon_cost <= 1 ? '15' : '25';

    // Cache next tasks for cycling
    cachedNextTasks = state.tasks.filter(t2 => t2.status === 'active' && t2.id !== t.id);
    nextTaskIndex = 0;

    // Wind-down suggestion
    checkWindDown();

  } catch(e) {
    empty.classList.remove('hidden');
    container.classList.add('hidden');
  }
}

function cycleTask(dir) {
  if (cachedNextTasks.length === 0) return loadNextTask();
  nextTaskIndex = (nextTaskIndex + cachedNextTasks.length + dir) % cachedNextTasks.length;
  const t = cachedNextTasks[nextTaskIndex];
  if (!t) return loadNextTask();
  document.getElementById('focus-empty').classList.add('hidden');
  document.getElementById('focus-task').classList.remove('hidden');
  document.getElementById('focus-task-view').classList.remove('hidden');
  document.getElementById('focus-timer-view').classList.add('hidden');
  document.getElementById('focus-title').innerHTML = esc(t.title);
  document.getElementById('focus-meta').innerHTML = `🍴 ${t.spoon_cost} spoons · ${t.energy_tag}`;
  const chunks = JSON.parse(t.micro_chunks || '[]');
  const chunksEl = document.getElementById('focus-chunks');
  if (chunks.length > 0) {
    chunksEl.classList.remove('hidden');
    chunksEl.innerHTML = chunks.map(c => `<li>${esc(c)}</li>`).join('');
  } else chunksEl.classList.add('hidden');
  document.getElementById('focus-start-btn').textContent = `▶ Start (${t.spoon_cost <= 1 ? '15' : '25'} min)`;
  document.getElementById('focus-start-btn').dataset.taskId = t.id;
  document.getElementById('focus-start-btn').dataset.duration = t.spoon_cost <= 1 ? '15' : '25';
}

document.addEventListener('DOMContentLoaded', () => {
  const next = document.getElementById('focus-next');
  if (next) next.onclick = () => cycleTask(1);
  const skip = document.getElementById('focus-skip');
  if (skip) skip.onclick = () => cycleTask(1);
});

// ── Quick Add ──
async function quickAdd() {
  const input = document.getElementById('quick-task');
  const title = input.value.trim();
  if (!title) return;
  input.value = '';
  const resp = await fetch(`${API}/api/tasks`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ title })
  });
  if (!resp.ok) return;
  await refreshState();
  await loadNextTask();
}

async function fullAddTask() {
  const input = document.getElementById('full-task-input');
  const title = input.value.trim();
  if (!title) return;
  input.value = '';
  const tag = currentMode === 'amber' ? 'low' : 'medium';
  await fetch(`${API}/api/tasks`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ title, energy_tag: tag })
  });
  await refreshState();
  renderTasks();
}

// ── Start Task ──
async function startOnTask() {
  const btn = document.getElementById('focus-start-btn');
  const taskId = btn.dataset.taskId;
  const duration = parseInt(btn.dataset.duration) || 25;
  await timerStart(taskId, duration, 'focus');
}

// ── Timer ──
async function timerStart(taskId, duration, startedAs) {
  duration = duration || timerDuration || 25;
  startedAs = startedAs || 'focus';
  const resp = await fetch(`${API}/api/timer`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ action: 'start', task_id: taskId || null, duration_minutes: duration, body_doubling: bodyDoubling, started_as: startedAs })
  });
  if (!resp.ok) return;
  const data = await resp.json();
  state.active_timer = data;
  startTimerTick();
  updateTimerUI('running', duration);

  // Show timer view
  document.getElementById('focus-task-view').classList.add('hidden');
  document.getElementById('focus-timer-view').classList.remove('hidden');
}

function showJustStart() {
  const taskId = document.getElementById('focus-start-btn').dataset.taskId;
  timerStart(taskId, 2, 'just_start');
}

function toggleBodyDoubling() {
  bodyDoubling = !bodyDoubling;
  document.getElementById('bd-indicator').classList.toggle('hidden', !bodyDoubling);
}

async function timerPause() {
  const resp = await fetch(`${API}/api/timer`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ action: 'pause' })
  });
  state.active_timer.status = 'paused';
  clearInterval(timerTick);
  updateTimerUI('paused');
}

async function timerResume() {
  await fetch(`${API}/api/timer`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ action: 'resume' })
  });
  state.active_timer.status = 'running';
  startTimerTick();
  updateTimerUI('running');
}

// Pause without penalty - no elapsed calculation, user can resume anytime

async function timerStop() {
  await fetch(`${API}/api/timer`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ action: 'stop' })
  });
  state.active_timer = null;
  clearInterval(timerTick);
  document.getElementById('focus-timer-view').classList.add('hidden');
  document.getElementById('focus-task-view').classList.remove('hidden');
  await refreshState();
  await loadNextTask();
}

let timerDuration = 25;
function startTimerTick() {
  clearInterval(timerTick);
  timerTick = setInterval(() => {
    if (!state.active_timer) return;
    let elapsed = state.active_timer.elapsed_seconds || 0;
    if (state.active_timer.status === 'running') elapsed++;
    state.active_timer.elapsed_seconds = elapsed;
    // ponytail: count-up display. Stop anytime.
    const mins = Math.floor(elapsed / 60);
    const secs = elapsed % 60;
    document.getElementById('timer-display').textContent = `${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;
  }, 1000);
}

function timerComplete() {
  clearInterval(timerTick);
  sendNotification('Your focus session has ended. Well done.');
  timerStop();
}

function updateTimerUI(mode, duration) {
  const start = document.getElementById('timer-start-main');
  const pause = document.getElementById('timer-pause');
  const resume = document.getElementById('timer-resume');
  const stop = document.getElementById('timer-stop');
  start.classList.add('hidden'); pause.classList.add('hidden'); resume.classList.add('hidden'); stop.classList.add('hidden');
  if (mode === 'running') { pause.classList.remove('hidden'); stop.classList.remove('hidden'); }
  else if (mode === 'paused') { resume.classList.remove('hidden'); stop.classList.remove('hidden'); }
  else { start.classList.remove('hidden'); }
  if (duration) document.getElementById('timer-display').textContent = `${String(duration).padStart(2,'0')}:00`;
}

async function refreshTimers() {
  try {
    const resp = await fetch(`${API}/api/timer/active`);
    const data = await resp.json();
    if (data.timer) {
      state.active_timer = data.timer;
      state.active_timer.elapsed_seconds = data.timer.current_elapsed || 0;
      if (data.timer.status === 'running') startTimerTick();
      const total = data.timer.duration_minutes * 60;
      const remaining = Math.max(0, total - (data.timer.current_elapsed || 0));
      document.getElementById('timer-display').textContent = `${String(Math.floor(remaining/60)).padStart(2,'0')}:${String(remaining%60).padStart(2,'0')}`;
      updateTimerUI(data.timer.status);
      document.getElementById('focus-task-view').classList.add('hidden');
      document.getElementById('focus-timer-view').classList.remove('hidden');
      if (data.timer.body_doubling) { bodyDoubling = true; document.getElementById('bd-indicator').classList.remove('hidden'); }
    }
  } catch(e) {}
}

// ── Mode Bar ──
async function switchTab(name) {
  crisisSignals.tab_switches++;
  activeTab = name;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.toggle('hidden', t.id !== 'tab-'+name));
  if (name === 'tasks') { await refreshState(); renderTasks(); }
  if (name === 'habits') loadHabits();
  if (name === 'review') loadReview();
}

// ── State ──
async function refreshState() {
  try {
    const resp = await fetch(`${API}/api/state`);
    if (!resp.ok) return;
    state = await resp.json();
    const s = state.state;
    if (s) {
      const pct = Math.round((s.remaining_spoons / (s.total_spoons || 10)) * 100);
      document.getElementById('energy-battery').textContent = `${pct}% 🔋`;
    }
    await loadPacingDashboard();
  } catch(e) {}
}

// ── Pacing Dashboard ──

async function loadPacingDashboard() {
  const card = document.getElementById('pacing-card');
  try {
    const [envelope, boom] = await Promise.all([
      fetch('/api/pacing/envelope').then(r => r.json()),
      fetch('/api/pacing/boom-bust').then(r => r.json())
    ]);
    const envEl = document.getElementById('pacing-envelope');
    if (envelope.status === 'over') {
      envEl.innerHTML = `<span class="text-red">⚠ Over: ${envelope.current_usage}% usage / ${envelope.recommended_max}% max — taking a break might help.</span>`;
    } else if (envelope.status === 'low') {
      envEl.innerHTML = `<span class="text-amber">🔋 Low energy (${envelope.current_usage}%). Rest may help.</span>`;
    } else {
      envEl.innerHTML = `<span class="text-green">✓ Energy envelope: ${envelope.current_usage}% used of ${envelope.recommended_max}% max</span>`;
    }
    const boomEl = document.getElementById('pacing-boom');
    if (boom.confidence > 0.5) {
      boomEl.innerHTML = `<span class="text-amber">📊 ${boom.message}</span>`;
    }
    document.getElementById('pacing-suggestion').textContent = boom.pattern === 'boom-bust' ? boom.message :
      envelope.status === 'over' ? `Your energy envelope suggests stopping at ${envelope.recommended_max}% today. You're at ${envelope.current_usage}%.` : '';
    card.style.display = 'block';
  } catch(e) { card.style.display = 'none'; }
}

// ── Full Task List ──
function renderTasks() {
  const container = document.getElementById('task-list');
  const tasks = (state.tasks || []).filter(t => t.status === 'active');
  if (tasks.length === 0) { container.innerHTML = '<p class="text-dim text-sm">No tasks yet.</p>'; return; }
  const remaining = (state.state && state.state.remaining_spoons) || 0;
  let html = '';
  for (const t of tasks) {
    const cost = t.spoon_cost || 1;
    const canDo = remaining >= cost;
    const tag = t.energy_tag || 'medium';
    const rec = t.recurring ? ` <span class="text-dim">↻</span>` : '';
    html += `<div class="task ${tag}">
      <h3>${esc(t.title)}${rec}</h3>
      <div class="meta">🍴 ${cost} spoons · ${tag}</div>
      <div class="actions">
        <button class="btn btn-green btn-sm" onclick="completeTask('${t.id}')" ${canDo ? '' : 'disabled'}>
          ${canDo ? '✓ Done' : '⛔ low energy'}
        </button>
      </div></div>`;
  }
  container.innerHTML = html;
}

async function completeTask(id) {
  await fetch(`${API}/api/tasks/${id}/expend`, { method: 'POST' });
  await refreshState();
  renderTasks();
}

// ── Habits ──
async function loadHabits() {
  try {
    const resp = await fetch(`${API}/api/habits`);
    const data = await resp.json();
    const container = document.getElementById('habit-list');
    if (!data.habits || data.habits.length === 0) { container.innerHTML = '<p class="text-dim text-sm">No habits yet.</p>'; return; }
    let html = '';
    for (const h of data.habits) {
      const done = h.done_today === 1 || h.done_today === true;
      html += `<div class="habit-row"><div class="habit-check ${done ? 'done' : ''}" onclick="${done ? '' : `checkHabit('${h.id}')`}">${done ? '✓' : ''}</div>
        <div style="flex:1"><span class="text-sm">${esc(h.title)}</span></div></div>`;
    }
    container.innerHTML = html;
  } catch(e) {}
}

async function checkHabit(id) {
  const resp = await fetch(`${API}/api/habits/${id}/check`, { method: 'POST' });
  if (!resp.ok) return;
  await loadHabits();
}

async function addHabit() {
  const title = document.getElementById('new-habit-name').value.trim();
  if (!title) return;
  document.getElementById('new-habit-name').value = '';
  await fetch(`${API}/api/habits`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ title })
  });
  await loadHabits();
}

// ── Wind Down ──
async function checkWindDown() {
  try {
    const resp = await fetch(`${API}/api/wind-down/today`);
    const data = await resp.json();
    if (!data.entry) {
      document.getElementById('wind-down-card').style.display = '';
    } else {
      document.getElementById('wind-down-card').style.display = 'none';
    }
  } catch(e) {}
}

function showWindDown() {
  document.getElementById('wind-down-prompt').classList.add('hidden');
  document.getElementById('wind-down-form').classList.remove('hidden');
}

function cancelWindDown() {
  document.getElementById('wind-down-prompt').classList.remove('hidden');
  document.getElementById('wind-down-form').classList.add('hidden');
}

async function saveWindDown() {
  const wentWell = document.getElementById('ww-well').value;
  const drained = document.getElementById('ww-drained').value;
  const tomorrow = document.getElementById('ww-tomorrow').value;
  await fetch(`${API}/api/wind-down`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ went_well: wentWell, drained, tomorrow_one: tomorrow })
  });
  document.getElementById('wind-down-card').style.display = 'none';
}

// ── Review ──
async function loadReview() {
  const container = document.getElementById('review-content');
  try {
    const resp = await fetch(`${API}/api/review/week`);
    const data = await resp.json();
    const ins = data.insights;

    let html = `<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:16px">
      <div class="review-stat"><div class="num">${ins.tasks_completed}</div><div class="lbl">done</div></div>
      <div class="review-stat"><div class="num">${ins.total_focus_minutes}</div><div class="lbl">focus min</div></div>
      <div class="review-stat"><div class="num">${ins.avg_spoons}</div><div class="lbl">avg 🥄</div></div>
    </div>`;

    // Energy bar chart
    if (data.energy_states && data.energy_states.length > 0) {
      html += '<div style="display:flex;gap:4px;align-items:flex-end;height:80px;margin:12px 0">';
      const maxSpoons = Math.max(...data.energy_states.map(s => s.total_spoons), 10);
      for (const s of data.energy_states) {
        const pct = Math.max(4, (s.remaining_spoons / maxSpoons) * 80);
        const day = s.date.slice(5);
        const color = s.mode === 'red' ? 'var(--red)' : s.mode === 'amber' ? 'var(--amber)' : 'var(--green)';
        html += `<div class="bar" style="height:${pct}px;background:${color};display:flex;flex-direction:column;align-items:center;font-size:10px">
          <span class="day-label" style="margin-top:4px;color:var(--text-dim)">${day}</span></div>`;
      }
      html += '</div>';
    }

    // Insight
    try {
      const ir = await fetch(`${API}/api/review/insight`);
      const id = await ir.json();
      if (id.insight) html += `<div class="insight-box">${id.insight}</div>`;
    } catch(e) {}

    // Completed tasks
    if (data.completed_tasks && data.completed_tasks.length > 0) {
      html += '<h2 class="text-sm mt-8 mb-8">Completed</h2>';
      for (const t of data.completed_tasks.slice(0,5)) {
        html += `<div class="text-sm mb-4">✅ ${esc(t.title)} <span class="text-dim">(${(t.completed_at||'').slice(0,10)})</span></div>`;
      }
    }

    // Wind-down entries
    if (data.wind_down_entries && data.wind_down_entries.length > 0) {
      html += '<h2 class="text-sm mt-8 mb-8">This week\u2019s reflections</h2>';
      for (const w of data.wind_down_entries.slice(0,3)) {
        if (w.went_well) html += `<div class="text-sm mb-4">📝 ${w.date}: ${esc(w.went_well)}</div>`;
      }
    }

    container.innerHTML = html;
    // Add export/import links
    container.innerHTML += '<div class="mt-8 text-center text-sm text-dim">' +
      '<a onclick="fetch(\'/api/export/json\').then(r=>r.blob()).then(b=>{var a=document.createElement(\'a\');a.href=URL.createObjectURL(b);a.download=\'neur-os-export.json\';a.click()})" style="cursor:pointer;text-decoration:underline">Export</a>' +
      ' · <a onclick="importData()" style="cursor:pointer;text-decoration:underline">Import</a>' +
      ' · <a onclick="fetch(\'/api/export/backup\',{method:\'POST\'}).then(r=>r.json()).then(d=>alert(\'Backup: \'+d.path.split(\'/\').pop()))" style="cursor:pointer;text-decoration:underline">Backup</a>' +
      '</div>';
  } catch(e) {
    container.innerHTML = '<p class="text-dim text-sm">Could not load review.</p>';
  }
  // Phase 4: energy patterns
  try {
    const pr = await fetch(`${API}/api/pacing/patterns`);
    const pat = await pr.json();
    if (pat.insight) {
      document.getElementById('patterns-insight').textContent = pat.insight;
      document.getElementById('patterns-card').style.display = 'block';
    }
  } catch(e) {}
}

// ── Crisis ──
async function activateCrisis() {
  await fetch(`${API}/api/crisis/activate`, { method: 'POST' });
  document.getElementById('crisis-overlay').classList.add('active');
}

async function resolveCrisis() {
  await fetch(`${API}/api/crisis/resolve`, { method: 'POST' });
  document.getElementById('crisis-overlay').classList.remove('active');
  setMode('green');
  await loadNextTask();
}

// ── Helpers ──
function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// ── Onboarding ──
function finishOnboarding() {
  const name = document.getElementById('onboarding-name').value.trim() || 'there';
  const spoons = parseInt(document.getElementById('onboarding-spoons').value);
  localStorage.setItem('neur-os-onboarded', 'true');
  localStorage.setItem('neur-os-name', name);
  localStorage.setItem('neur-os-default-spoons', spoons.toString());
  document.getElementById('onboarding-card').style.display = 'none';
  document.getElementById('mode-bar').style.display = '';
  document.querySelector('.tab-bar').style.display = '';
  setGreeting();
  init();
}

const _origSetup = setGreeting;
function setGreeting() {
  const name = localStorage.getItem('neur-os-name') || '';
  const h = new Date().getHours();
  const g = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  const el = document.getElementById('greeting');
  if (el) el.textContent = name ? `${g}, ${name}. This is your space.` : `${g}. This is your space.`;
}

// ── Soundscape Player ──
let audioCtx = null;
let audioSource = null;
function getAudioContext() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === 'suspended') audioCtx.resume();
  return audioCtx;
}
async function playSoundscape(type) {
  stopSoundscape();
  if (!type || type === 'none' || type === 'silence') return;
  if (type === 'white_noise') {
    const ctx = getAudioContext();
    const bufSize = ctx.sampleRate * 2;
    const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < bufSize; i++) d[i] = (Math.random() * 2 - 1) * 0.3;
    audioSource = ctx.createBufferSource();
    audioSource.buffer = buf;
    audioSource.loop = true;
    audioSource.connect(ctx.destination);
    audioSource.start();
    return;
  }
  try {
    const ctx = getAudioContext();
    const resp = await fetch(`/soundscapes/${type}`);
    if (!resp.ok) return;
    const buf = await resp.arrayBuffer();
    const decoded = await ctx.decodeAudioData(buf);
    audioSource = ctx.createBufferSource();
    audioSource.buffer = decoded;
    audioSource.loop = true;
    const gain = ctx.createGain();
    gain.gain.value = 0.3;
    audioSource.connect(gain);
    gain.connect(ctx.destination);
    audioSource.start();
  } catch(e) {}
}
function stopSoundscape() {
  if (audioSource) { try { audioSource.stop(); } catch(e) {} audioSource = null; }
}

// ── Import ──
async function importData() {
  const input = document.createElement('input');
  input.type = 'file'; input.accept = '.json';
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      const resp = await fetch(`${API}/api/import`, { method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
      const result = await resp.json();
      alert(`Imported: ${JSON.stringify(result.imported)}`);
      location.reload();
    } catch(e) { alert('Invalid export file'); }
  };
  input.click();
}

// ── Crisis Signals ──
let passiveLogTimer = null;
let crisisSuppressUntil = 0;
const crisisSignals = { tab_switches: 0, task_aborts: 0, timer_aborts: 0, help_clicks: 0 };

// Track task input opens for abort counting
['quick-task', 'full-task-input'].forEach(id => {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('focus', () => el.dataset.opened = '1');
});
setInterval(() => {
  ['quick-task', 'full-task-input'].forEach(id => {
    const el = document.getElementById(id);
    if (el && el.dataset.opened === '1') { crisisSignals.task_aborts++; el.dataset.opened = '0'; }
  });
}, 60000);

// ── Notifications ──
async function sendNotification(text) {
  if (!('Notification' in window)) return;
  if (Notification.permission === 'granted') {
    new Notification('NeurOS', { body: text, silent: true });
  } else if (Notification.permission !== 'denied') {
    await Notification.requestPermission();
  }
}

init();

// ── Passive Log ──
function startPassiveLog() {
  clearInterval(passiveLogTimer);
  passiveLogTimer = setInterval(async () => {
    const onboarded = localStorage.getItem('neur-os-onboarded');
    if (!onboarded || document.getElementById('crisis-overlay').classList.contains('active')) return;
    if (!document.getElementById('passive-overlay').classList.contains('hidden')) return;
    try {
      const resp = await fetch(`${API}/api/passive-log/check`);
      const data = await resp.json();
      if (data.should_prompt) {
        document.getElementById('passive-overlay').classList.remove('hidden');
        document.getElementById('passive-input').value = '';
        document.getElementById('passive-input').focus();
      }
    } catch(e) {}
  }, 60000);
}

async function passiveSubmit() {
  const input = document.getElementById('passive-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  const s = (state && state.state) ? state.state.remaining_spoons : null;
  await fetch(`${API}/api/passive-log/submit`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ response: text, spoons_at_time: s })
  });
  document.getElementById('passive-overlay').classList.add('hidden');
}

function passiveDismiss() {
  document.getElementById('passive-overlay').classList.add('hidden');
}

// ── Dopamine Menu ──

async function showDopamineMenu() {
  const el = document.getElementById('dopamine-overlay');
  const list = document.getElementById('dopamine-list');
  try {
    const resp = await fetch('/api/dopamine-menu');
    const menu = await resp.json();
    let html = '';
    const labels = {starters: '🌟 Quick (2 min)', sides: '🎧 With something', mains: '🌿 Restorative', desserts: '🍪 Guilty pleasure'};
    for (const [cat, items] of Object.entries(menu)) {
      if (items.length) {
        html += `<h4 class="text-sm text-dim mt-4 mb-4">${labels[cat] || cat}</h4>`;
        items.forEach(i => { html += `<div class="flex justify-between items-center mb-4"><span>${i.name}</span><span class="text-dim text-xs">${i.energy_required} energy</span></div>`; });
      }
    }
    list.innerHTML = html;
  } catch(e) { list.innerHTML = '<p class="text-dim">Could not load menu</p>'; }
  el.classList.remove('hidden');
}
function dismissDopamineMenu() {
  document.getElementById('dopamine-overlay').classList.add('hidden');
}

// ── Interoception ──

async function logInteroception(signal) {
  try {
    await fetch('/api/interoception', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({signals: [signal], mood: ''})
    });
  } catch(e) {}
  document.getElementById('interoception-overlay').classList.add('hidden');
}
function showInteroception() {
  document.getElementById('interoception-overlay').classList.remove('hidden');
}
function dismissInteroception() {
  document.getElementById('interoception-overlay').classList.add('hidden');
}

// ── Brain Dump ──

async function submitBrainDump() {
  const input = document.getElementById('brain-dump-input');
  const text = input.value.trim();
  if (!text) return;
  input.disabled = true;
  try {
    const resp = await fetch('/api/brain-dump', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, source: 'textarea'})
    });
    const data = await resp.json();
    const resultEl = document.getElementById('brain-dump-result');
    let html = '<div class="brain-dump-results"><p class="text-dim text-sm mb-4">I hear:";
    if (data.structured.tasks && data.structured.tasks.length) {
      html += '<ul class="mb-8">';
      data.structured.tasks.forEach(t => { html += `<li>• ${t.title} <span class="text-dim">${t.energy_tag || 'medium'}</span></li>`; });
      html += '</ul>';
    }
    if (data.structured.notes && data.structured.notes.length) {
      html += '<div class="text-sm text-dim">Notes:';
      data.structured.notes.forEach(n => { html += `<p class="mb-4">${n.content}</p>`; });
      html += '</div>';
    }
    html += `<details class="text-dim text-xs mt-4"><summary>Show original</summary><p class="mt-4">${data.original}</p></details>`;
    html += '</div>';
    resultEl.innerHTML = html;
    resultEl.classList.remove('hidden');
    input.value = '';
  } catch(e) {}
  input.disabled = false;
  input.focus();
  await refreshState();
  await loadNextTask();
}

// ── Crisis Monitor ──
function startCrisisMonitor() {
  setInterval(async () => {
    const onboarded = localStorage.getItem('neur-os-onboarded');
    if (!onboarded || Date.now() < crisisSuppressUntil) return;
    const tabRate = crisisSignals.tab_switches / 60;
    const abortRate = crisisSignals.task_aborts / 60;
    const clickRate = crisisSignals.help_clicks / 60;
    crisisSignals.tab_switches = 0;
    crisisSignals.task_aborts = 0;
    crisisSignals.timer_aborts = 0;
    crisisSignals.help_clicks = 0;
    if (tabRate < 0.05 && abortRate < 0.03 && clickRate < 0.08) return;
    try {
      const resp = await fetch(`${API}/api/crisis/check`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          cognitive_load: Math.min(1, tabRate * 3 + abortRate * 5),
          frustration_markers: Math.min(1, clickRate * 2),
          error_rate: Math.min(1, abortRate * 4)
        })
      });
      const data = await resp.json();
      if (data.trigger) {
        document.getElementById('crisis-dismiss').classList.remove('hidden');
        activateCrisis();
      }
    } catch(e) {}
  }, 60000);
}

async function dismissAutoCrisis() {
  crisisSuppressUntil = Date.now() + 2 * 60 * 60 * 1000;
  document.getElementById('crisis-dismiss').classList.add('hidden');
  resolveCrisis();
}

// ── Onboarding Chat ──
let onboardingHistory = [];
let onboardingTurn = 0;

async function onboardingSend() {
  const input = document.getElementById('onboarding-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  onboardingHistory.push({ role: 'user', content: text });
  if (onboardingTurn >= 4) { finishOnboarding(); return; }
  try {
    const resp = await fetch(`${API}/api/onboarding/chat`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ history: onboardingHistory, turn: onboardingTurn })
    });
    const data = await resp.json();
    document.getElementById('onboarding-text').textContent = data.response;
    onboardingTurn = data.turn;
    onboardingHistory.push({ role: 'assistant', content: data.response });
    if (data.done) finishOnboarding();
  } catch(e) { finishOnboarding(); }
}

window.finishOnboarding = function() {
  localStorage.setItem('neur-os-onboarded', 'true');
  document.getElementById('onboarding-card').style.display = 'none';
  document.getElementById('mode-bar').style.display = '';
  document.querySelector('.tab-bar').style.display = '';
  const h = new Date().getHours();
  const g = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  const name = localStorage.getItem('neur-os-name') || '';
  document.getElementById('onboarding-text').textContent = name ? `${g}, ${name}.` : `${g}.`;
  init();
};