/* Bluesify front-end controller.
   - Talks to the FastAPI engine (/api/*)
   - Renders the arranged score with OpenSheetMusicDisplay
   - Plays the returned MIDI through a warm Tone.js Rhodes-ish synth */

const state = {
  file: null,        // File | "demo"
  level: 2,
  style: "jazz-ballad",
  supported: [1, 2],
  midi: null,        // decoded @tonejs/midi Midi
  playing: false,
  osmd: null,
  decisions: [],
  focusedDecision: -1,
  measureCount: 0,
  playbackDuration: 0,
  playbackStartedAt: 0,
  noteTimes: [],
  noteBars: [],
  cursorStep: 0,
  cursorFrame: null,
  lastCursorScrollAt: 0,
};

const $ = (id) => document.getElementById(id);
const els = {
  play: $("playBtn"), tempo: $("tempo"), tempoOut: $("tempoOut"),
  osmd: $("osmd"), empty: $("scoreEmpty"), loading: $("scoreLoading"),
  strip: $("analysisStrip"), aKey: $("aKey"), aTempo: $("aTempo"),
  aTime: $("aTime"), aBars: $("aBars"), aChords: $("aChords"),
  teacher: $("teacherList"), decCount: $("decCount"),
  levels: $("levels"), style: $("style"), mode: $("mode"),
  demo: $("demoBtn"), fileInput: $("fileInput"), toast: $("toast"),
  sourceName: $("sourceName"), currentFocus: $("currentFocus"),
  decisionRail: $("decisionRail"), prevNote: $("prevNote"), nextNote: $("nextNote"),
  timelineLabel: $("timelineLabel"),
};

/* ---------- audio (lazy, warm electric-piano voice) ---------- */
let synth, reverb, audioReady = false;
async function ensureAudio() {
  if (audioReady) return;
  await Tone.start();
  reverb = new Tone.Reverb({ decay: 3.2, wet: 0.28 }).toDestination();
  synth = new Tone.PolySynth(Tone.FMSynth, {
    harmonicity: 2.4, modulationIndex: 6,
    envelope: { attack: 0.006, decay: 1.1, sustain: 0.22, release: 1.4 },
    modulationEnvelope: { attack: 0.01, decay: 0.4, sustain: 0.1, release: 0.6 },
    volume: -8,
  }).connect(reverb);
  Tone.Transport.bpm.value = Number(els.tempo.value);
  audioReady = true;
}

/* ---------- bootstrap ---------- */
async function boot() {
  try {
    const opts = await fetch("/api/options").then((r) => r.json());
    state.supported = opts.supported_levels;
    renderLevels(opts.levels);
    renderStyles(opts.styles);
  } catch {
    toast("Could not reach the engine.", false);
  }
  wireEvents();
}

function renderLevels(levels) {
  els.levels.innerHTML = "";
  for (const lv of levels) {
    const supported = state.supported.includes(lv.value);
    const b = document.createElement("button");
    b.className = "level" + (lv.value === state.level ? " active" : "") + (supported ? "" : " locked");
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", lv.value === state.level);
    b.disabled = !supported;
    b.innerHTML = `
      <div class="lv-row">
        <span class="lv-no">${lv.value}</span>
        <span class="lv-name">${lv.name}</span>
        ${supported ? "" : '<span class="lv-soon">soon</span>'}
      </div>
      <div class="lv-blurb">${lv.blurb}</div>`;
    b.addEventListener("click", () => {
      if (!supported) return;
      state.level = lv.value;
      [...els.levels.children].forEach((c) => {
        c.classList.toggle("active", c === b);
        c.setAttribute("aria-selected", c === b);
      });
      if (state.file) run();
    });
    els.levels.appendChild(b);
  }
}

function renderStyles(styles) {
  els.style.innerHTML = styles
    .map((s) => `<option value="${s.value}">${s.name}</option>`)
    .join("");
  els.style.value = state.style;
}

function wireEvents() {
  els.demo.addEventListener("click", () => {
    state.file = "demo";
    updateSourceLabel("Demo Lead Sheet");
    run();
  });
  els.fileInput.addEventListener("change", (e) => {
    if (e.target.files[0]) {
      state.file = e.target.files[0];
      updateSourceLabel(e.target.files[0].name);
      run();
    }
  });
  els.style.addEventListener("change", () => {
    state.style = els.style.value;
    if (state.file) run();
  });
  els.tempo.addEventListener("input", () => {
    els.tempoOut.textContent = els.tempo.value;
    if (audioReady) Tone.Transport.bpm.value = Number(els.tempo.value);
  });
  els.play.addEventListener("click", togglePlay);
  els.prevNote.addEventListener("click", () => focusDecision(state.focusedDecision - 1));
  els.nextNote.addEventListener("click", () => focusDecision(state.focusedDecision + 1));

  // drag & drop a lead sheet onto the stand
  ["dragenter", "dragover"].forEach((ev) =>
    document.addEventListener(ev, (e) => { e.preventDefault(); document.body.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach((ev) =>
    document.addEventListener(ev, (e) => { e.preventDefault(); if (ev === "drop" || e.target === document.documentElement) document.body.classList.remove("dragging"); }));
  document.addEventListener("drop", (e) => {
    const f = e.dataTransfer?.files?.[0];
    if (f) {
      state.file = f;
      updateSourceLabel(f.name);
      run();
    }
  });
}

/* ---------- the main flow: arrange → render → load audio ---------- */
async function run() {
  stopPlayback();
  showLoading(true);
  toast("");
  resetDecisionFocus();
  try {
    const fd = new FormData();
    if (state.file === "demo") {
      const xml = await fetch("/api/demo").then((r) => r.text());
      fd.append("file", new Blob([xml], { type: "application/xml" }), "demo.musicxml");
    } else {
      fd.append("file", state.file);
    }
    fd.append("level", String(state.level));
    fd.append("style", state.style);

    const res = await fetch("/api/arrange", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Engine error (${res.status})`);
    }
    const data = await res.json();
    await renderScore(data.musicxml);
    renderAnalysis(data.result.analysis);
    renderTeacher(data.result.decisions);
    await loadMidi(data.midi_b64);
    els.play.disabled = false;
    toast("Arranged. Press play to hear it.", true);
  } catch (e) {
    toast(e.message || "Something went wrong.", false);
    showLoading(false);
  }
}

async function renderScore(xml) {
  els.empty.hidden = true;
  if (!state.osmd) {
    state.osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay(els.osmd, {
      autoResize: true,
      backend: "svg",
      drawTitle: false,        // app chrome already frames the piece
      drawSubtitle: false,
      drawComposer: false,
      drawPartNames: false,
      drawPartAbbreviations: false,
      drawingParameters: "compact",
      followCursor: true,
      cursorsOptions: [{ color: "#147a65", alpha: 0.72 }],
    });
  }
  await state.osmd.load(xml);
  state.osmd.render();
  resetScoreCursor();
  showLoading(false);
}

function renderAnalysis(a) {
  els.strip.hidden = false;
  state.measureCount = Number(a.measure_count) || 0;
  document.body.classList.toggle("long-score", state.measureCount > 24);
  els.aKey.textContent = a.key;
  els.aTempo.textContent = a.tempo_bpm ? `${a.tempo_bpm} bpm` : "—";
  els.aTime.textContent = a.time_signature;
  els.aBars.textContent = a.measure_count;
  els.aChords.textContent = (a.chord_summary || []).join("  ·  ") || "—";
  els.currentFocus.textContent = `${a.key} · ${a.time_signature}`;
  updateSheetPosition(0, "Ready", { exactBar: false });
  if (a.tempo_bpm) {
    els.tempo.value = a.tempo_bpm;
    els.tempoOut.textContent = a.tempo_bpm;
    if (audioReady) Tone.Transport.bpm.value = a.tempo_bpm;
  }
}

function renderTeacher(decisions) {
  state.decisions = decisions || [];
  if (state.decisions.length > state.measureCount) {
    state.measureCount = state.decisions.length;
    els.aBars.textContent = state.measureCount;
    document.body.classList.toggle("long-score", state.measureCount > 24);
    updateSheetPosition(0, "Ready", { exactBar: false });
  }
  els.teacher.innerHTML = "";
  els.decCount.textContent = state.decisions.length ? `${state.decisions.length} notes` : "";
  renderDecisionRail(state.decisions);
  updateNoteButtons();
  if (!state.decisions.length) {
    els.teacher.innerHTML = '<p class="teacher-hint">No annotations for this arrangement yet.</p>';
    return;
  }
  state.decisions.forEach((d, index) => {
    const card = document.createElement("article");
    card.className = "card";
    card.dataset.index = String(index);
    card.tabIndex = 0;
    const tags = (d.theory_tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("");
    const tips = (d.practice_tips || []).map((t) => `<li>${escapeHtml(t)}</li>`).join("");
    card.innerHTML = `
      <div class="card-top">
        <span class="bar-no">Bar ${d.measure}</span>
        <span class="chord">${escapeHtml(d.chord_after)}</span>
      </div>
      <p class="rationale">${escapeHtml(d.rationale)}</p>
      ${tags ? `<div class="tags">${tags}</div>` : ""}
      ${tips ? `<ul class="tips">${tips}</ul>` : ""}`;
    card.addEventListener("click", () => focusDecision(index));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        focusDecision(index);
      }
    });
    els.teacher.appendChild(card);
  });
  focusDecision(0, { scroll: false });
}

function renderDecisionRail(decisions) {
  els.decisionRail.innerHTML = "";
  els.decisionRail.classList.toggle("dense", decisions.length > 18);
  for (const [index, d] of decisions.entries()) {
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = "rail-marker";
    marker.textContent = String(d.measure);
    marker.setAttribute("aria-label", `Practice note for bar ${d.measure}`);
    marker.dataset.index = String(index);
    marker.addEventListener("click", () => focusDecision(index));
    els.decisionRail.appendChild(marker);
  }
}

function focusDecision(index, opts = {}) {
  if (!state.decisions.length) return;
  const next = Math.max(0, Math.min(index, state.decisions.length - 1));
  state.focusedDecision = next;
  const d = state.decisions[next];
  els.currentFocus.textContent = `Bar ${d.measure} · ${d.chord_after}`;

  [...els.teacher.querySelectorAll(".card")].forEach((card) => {
    const active = Number(card.dataset.index) === next;
    card.classList.toggle("active", active);
    if (active && opts.scroll !== false) {
      card.scrollIntoView({ block: "nearest", behavior: motionBehavior() });
    }
  });

  [...els.decisionRail.querySelectorAll(".rail-marker")].forEach((marker) => {
    const active = Number(marker.dataset.index) === next;
    marker.classList.toggle("active", active);
    marker.setAttribute("aria-current", active ? "true" : "false");
  });
  updateNoteButtons();
}

function resetDecisionFocus() {
  state.decisions = [];
  state.focusedDecision = -1;
  els.decisionRail.innerHTML = "";
  els.decisionRail.classList.remove("dense");
  updateNoteButtons();
}

function updateNoteButtons() {
  const hasNotes = state.decisions.length > 0;
  els.prevNote.disabled = !hasNotes || state.focusedDecision <= 0;
  els.nextNote.disabled = !hasNotes || state.focusedDecision >= state.decisions.length - 1;
}

/* ---------- playback ---------- */
async function loadMidi(b64) {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const MidiCtor = (window.Midi && window.Midi.Midi) || window.Midi;
  state.midi = new MidiCtor(bytes.buffer);
  state.playbackDuration = midiDuration(state.midi);
  const timeline = midiTimeline(state.midi);
  state.noteTimes = timeline.times;
  state.noteBars = timeline.bars;
}

async function togglePlay() {
  if (!state.midi) return;
  await ensureAudio();
  if (state.playing) { stopPlayback(); return; }

  Tone.Transport.cancel();
  Tone.Transport.bpm.value = Number(els.tempo.value);
  let last = 0;
  for (const track of state.midi.tracks) {
    for (const n of track.notes) {
      last = Math.max(last, n.time + n.duration);
      if (n.duration <= 0) continue;
      Tone.Transport.schedule((t) => {
        synth.triggerAttackRelease(n.name, n.duration, t, n.velocity);
      }, n.time);
    }
  }
  state.playbackDuration = Math.max(last + 0.4, state.playbackDuration);
  Tone.Transport.schedule(() => stopPlayback(), state.playbackDuration);
  setPlaying(true);
  showScoreCursor();
  Tone.Transport.start();
  startScoreCursorLoop(state.playbackDuration);
}

function stopPlayback() {
  if (audioReady) { Tone.Transport.stop(); Tone.Transport.cancel(); synth?.releaseAll?.(); }
  stopScoreCursorLoop();
  resetScoreCursor();
  updateSheetPosition(0, "Ready", { exactBar: false });
  setPlaying(false);
}
function setPlaying(v) { state.playing = v; els.play.classList.toggle("playing", v); }

function midiDuration(midi) {
  let last = 0;
  for (const track of midi.tracks || []) {
    for (const n of track.notes || []) {
      last = Math.max(last, n.time + n.duration);
    }
  }
  return last ? last + 0.4 : 0;
}

function midiTimeline(midi) {
  const barsByTime = new Map();
  for (const track of midi.tracks || []) {
    for (const n of track.notes || []) {
      const time = Math.max(0, Math.round(n.time * 1000) / 1000);
      const bar = Math.max(1, Math.floor(n.bars || 0) + 1);
      barsByTime.set(time, Math.min(barsByTime.get(time) || bar, bar));
    }
  }
  const times = [...barsByTime.keys()].sort((a, b) => a - b);
  return { times, bars: times.map((time) => barsByTime.get(time) || 1) };
}

function showScoreCursor() {
  const cursor = state.osmd?.cursor;
  if (!cursor) return;
  try {
    cursor.reset();
    cursor.show();
    state.cursorStep = 0;
  } catch {
    // OSMD cursor support varies by render state; playback should continue.
  }
}

function resetScoreCursor() {
  const cursor = state.osmd?.cursor;
  state.cursorStep = 0;
  state.lastCursorScrollAt = 0;
  if (!cursor) return;
  try {
    cursor.reset();
    cursor.hide();
  } catch {
    // Ignore cursor reset failures so a render quirk never blocks arrangement.
  }
}

function startScoreCursorLoop(duration) {
  state.playbackStartedAt = performance.now();
  state.cursorStep = 0;
  updateSheetPosition(0, "Playing");

  const frame = () => {
    if (!state.playing) return;
    const elapsed = (performance.now() - state.playbackStartedAt) / 1000;
    while (
      state.cursorStep < state.noteTimes.length
      && state.noteTimes[state.cursorStep] <= elapsed
    ) {
      advanceScoreCursor(state.noteTimes[state.cursorStep], state.cursorStep);
    }
    if (elapsed < duration) {
      state.cursorFrame = requestAnimationFrame(frame);
      return;
    }
    stopPlayback();
  };

  state.cursorFrame = requestAnimationFrame(frame);
}

function stopScoreCursorLoop() {
  if (state.cursorFrame !== null) {
    cancelAnimationFrame(state.cursorFrame);
    state.cursorFrame = null;
  }
}

function advanceScoreCursor(noteTime, index) {
  if (!state.playing) return;
  const cursor = state.osmd?.cursor;
  try {
    if (cursor) {
      if (index === 0 && state.cursorStep === 0) {
        cursor.show();
      } else {
        cursor.next();
      }
      state.cursorStep += 1;
      revealScoreCursor();
    }
  } catch {
    // The position label still gives feedback if the notation cursor cannot advance.
  }
  updateSheetPosition(noteTime, "Playing", { bar: state.noteBars[index] });
}

function revealScoreCursor() {
  const cursorEl = state.osmd?.cursor?.cursorElement;
  if (!cursorEl) return;
  const now = performance.now();
  if (now - state.lastCursorScrollAt < 700) return;
  state.lastCursorScrollAt = now;
  cursorEl.scrollIntoView({ block: "center", inline: "center", behavior: motionBehavior() });
}

function updateSheetPosition(noteTime, stateLabel, opts = {}) {
  if (!state.measureCount) {
    els.timelineLabel.textContent = "No playback";
    return;
  }
  if (stateLabel === "Ready" && opts.exactBar === false) {
    els.timelineLabel.textContent = `Ready · ${state.measureCount} bars`;
    return;
  }
  const progressBar = state.playbackDuration
    ? Math.floor(Math.max(0, Math.min(noteTime / state.playbackDuration, 1)) * state.measureCount) + 1
    : 1;
  const currentBar = Math.min(state.measureCount, opts.bar || progressBar);
  els.timelineLabel.textContent = `${stateLabel} · bar ${currentBar} / ${state.measureCount}`;
  syncDecisionForBar(currentBar);
}

function syncDecisionForBar(bar) {
  if (!state.decisions.length) return;
  const index = state.decisions.findIndex((d) => Number(d.measure) >= bar);
  focusDecision(index === -1 ? state.decisions.length - 1 : index, { scroll: false });
}

/* ---------- ui helpers ---------- */
function showLoading(v) { els.loading.hidden = !v; }
function toast(msg, ok) {
  els.toast.hidden = !msg;
  els.toast.textContent = msg || "";
  els.toast.classList.toggle("ok", !!ok);
}
function updateSourceLabel(name) {
  els.sourceName.textContent = name || "No lead sheet loaded";
}
function motionBehavior() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

boot();
