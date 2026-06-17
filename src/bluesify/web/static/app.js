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
  els.demo.addEventListener("click", () => { state.file = "demo"; run(); });
  els.fileInput.addEventListener("change", (e) => {
    if (e.target.files[0]) { state.file = e.target.files[0]; run(); }
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

  // drag & drop a lead sheet onto the stand
  ["dragenter", "dragover"].forEach((ev) =>
    document.addEventListener(ev, (e) => { e.preventDefault(); document.body.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach((ev) =>
    document.addEventListener(ev, (e) => { e.preventDefault(); if (ev === "drop" || e.target === document.documentElement) document.body.classList.remove("dragging"); }));
  document.addEventListener("drop", (e) => {
    const f = e.dataTransfer?.files?.[0];
    if (f) { state.file = f; run(); }
  });
}

/* ---------- the main flow: arrange → render → load audio ---------- */
async function run() {
  stopPlayback();
  showLoading(true);
  toast("");
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
      drawingParameters: "compacttight",
    });
  }
  await state.osmd.load(xml);
  state.osmd.render();
  showLoading(false);
}

function renderAnalysis(a) {
  els.strip.hidden = false;
  els.aKey.textContent = a.key;
  els.aTempo.textContent = a.tempo_bpm ? `${a.tempo_bpm} bpm` : "—";
  els.aTime.textContent = a.time_signature;
  els.aBars.textContent = a.measure_count;
  els.aChords.textContent = (a.chord_summary || []).join("  ·  ") || "—";
  if (a.tempo_bpm) {
    els.tempo.value = a.tempo_bpm;
    els.tempoOut.textContent = a.tempo_bpm;
    if (audioReady) Tone.Transport.bpm.value = a.tempo_bpm;
  }
}

function renderTeacher(decisions) {
  els.teacher.innerHTML = "";
  els.decCount.textContent = decisions.length ? `${decisions.length} notes` : "";
  if (!decisions.length) {
    els.teacher.innerHTML = '<p class="teacher-hint">No annotations for this arrangement yet.</p>';
    return;
  }
  for (const d of decisions) {
    const card = document.createElement("article");
    card.className = "card";
    const tags = (d.theory_tags || []).map((t) => `<span class="tag">${t}</span>`).join("");
    const tips = (d.practice_tips || []).map((t) => `<li>${t}</li>`).join("");
    card.innerHTML = `
      <div class="card-top">
        <span class="bar-no">bar ${d.measure}</span>
        <span class="chord">${escapeHtml(d.chord_after)}</span>
      </div>
      <p class="rationale">${escapeHtml(d.rationale)}</p>
      ${tags ? `<div class="tags">${tags}</div>` : ""}
      ${tips ? `<ul class="tips">${tips}</ul>` : ""}`;
    els.teacher.appendChild(card);
  }
}

/* ---------- playback ---------- */
async function loadMidi(b64) {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const MidiCtor = (window.Midi && window.Midi.Midi) || window.Midi;
  state.midi = new MidiCtor(bytes.buffer);
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
      Tone.Transport.schedule((t) => {
        synth.triggerAttackRelease(n.name, n.duration, t, n.velocity);
      }, n.time);
    }
  }
  Tone.Transport.schedule(() => stopPlayback(), last + 0.4);
  Tone.Transport.start();
  setPlaying(true);
}

function stopPlayback() {
  if (audioReady) { Tone.Transport.stop(); Tone.Transport.cancel(); synth?.releaseAll?.(); }
  setPlaying(false);
}
function setPlaying(v) { state.playing = v; els.play.classList.toggle("playing", v); }

/* ---------- ui helpers ---------- */
function showLoading(v) { els.loading.hidden = !v; }
function toast(msg, ok) {
  els.toast.hidden = !msg;
  els.toast.textContent = msg || "";
  els.toast.classList.toggle("ok", !!ok);
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

boot();
