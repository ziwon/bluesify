# bluesify — Development Plan

> Step-by-step jazz/blues arrangement engine for self-learning piano.
> Living document. Last updated: 2026-05-26.

---

## 1. Purpose & Scope

A tool that takes a lead sheet or score and produces **level-by-level
arrangements** teaching the user how to play it in a jazz or blues style.
Primary user: the author (a piano learner with working music theory).
Secondary user (future): general learners, with an AI "teacher" persona
guiding them.

### Two input modes

| Mode | Input | Core task | Example |
|------|-------|-----------|---------|
| **A** | Pop/song lead sheet with diatonic chords | **Reharmonization** → make it jazz/blues | "Cherry Blossom Ending" C-G-Am-Em → Cmaj7-E7-Am7-A7 |
| **B** | Jazz standard lead sheet (already jazzy chords) | **Step-by-step arrangement** | Autumn Leaves Level 1→5 |

### Two performance modes

| Mode | LH | RH | Notes |
|------|----|----|-------|
| **Solo piano** | Bass line + occasional chords | Melody + voicings + fills | Self-contained |
| **Accompaniment** | Rootless voicing (3-7 or 7-3) | Rootless voicing / line comping | For melody instruments; no bass, no melody |

These are the target product axes. In the current prototype, only Mode B,
solo piano, jazz-ballad, Levels 1-5 are implemented; other combinations
should fail clearly until their phase lands.

---

## 2. Architecture Overview

```
Input (MusicXML / chord text / future: OMR from PDF)
    ↓
Analysis  (key, form, chord function, ii-V detection)
    ↓
Arranger  (per Level, per PerformanceMode, per GenreMode/Style)
  ├─ Reharmonization rules  (Mode A)
  ├─ Voicing strategy        (Mode B-heavy, both modes)
  └─ Groove pattern          (both modes)
    ↓
ArrangementDecision log  (rationale + theory_tags + practice_tips)
    ↓
Render (MusicXML / PDF / MIDI / annotations.json)
```

The **decision log** is the bridge to the future LLM teacher: every
non-trivial choice the engine makes emits a structured rationale that
can be templated now and LLM-paraphrased later.

---

## 3. Stack & Conventions

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.12 | music21 ecosystem |
| Package mgr | uv | fast, modern, lock-aware |
| Music | music21 | de facto standard, MusicXML in/out, key/chord analysis |
| Render | Verovio (Python binding) | server-side SVG/PDF, faster than MuseScore CLI |
| MIDI | music21 → optional pretty_midi post | good enough for Phase 1 |
| CLI | click + rich | quick iteration, no UI yet |
| Validation | pydantic v2 | dataclasses with serialization for `ArrangementDecision` |
| Lint/format | ruff | one tool |
| Types | mypy strict | catch issues early |
| Tests | pytest + semantic assertions + normalized golden files | regressions on rearrangements |
| Lang for UX | English (chord symbols + rationale) | matches jazz pedagogy literature |

The current frontend is a no-build FastAPI/static UI. A larger Next.js + OSMD
experience remains a Phase 3 direction if the product needs it.

---

## 4. Repository Layout

This is the target layout. Files marked with a later phase do not exist
until that work begins.

```
bluesify/
├── pyproject.toml
├── README.md
├── LICENSE              (MIT)
├── .gitignore           (copyrighted .musicxml gitignored)
├── docs/
│   ├── PLAN.md          (this file)
│   ├── reharmonization_rules.md   (future: Mode A rules)
│   ├── voicing_library.md         (future: Mode B voicings catalogue)
│   └── teacher_metadata.md        (future: decision-log schema, LLM prompts)
├── src/bluesify/
│   ├── __init__.py
│   ├── cli.py
│   ├── core/
│   │   ├── score.py          # music21 I/O wrapper
│   │   └── types.py          # Level, Mode, Style, ArrangementDecision, ...
│   ├── analysis/
│   │   ├── key.py
│   │   ├── form.py           # AABA / 12-bar / intro-verse detection (Phase 2+)
│   │   └── chord_function.py # Roman numeral, ii-V detection (Phase 2+)
│   ├── voicings/
│   │   ├── base.py           # VoicingStrategy ABC
│   │   ├── shell.py          # RootOnly, Shell37
│   │   ├── rootless.py       # A-form, B-form (Phase 2)
│   │   ├── block.py          # locked-hands block chords (Phase 2)
│   │   └── drop2.py          # drop2 voicings (Phase 3+)
│   ├── grooves/
│   │   ├── base.py
│   │   ├── walking_bass.py   # Level 3
│   │   ├── ballad.py         # default Phase 1
│   │   ├── stride.py
│   │   ├── shuffle.py
│   │   └── swing_comping.py
│   ├── arranger/
│   │   ├── base.py
│   │   ├── solo.py           # PerformanceMode.SOLO arranger
│   │   ├── accomp.py         # PerformanceMode.ACCOMP arranger (Phase 4)
│   │   └── level.py          # Level 1→5 progression utilities
│   ├── rules/                # Mode A: reharmonization (Phase 5)
│   │   ├── diatonic_7ths.py
│   │   ├── secondary_dominants.py
│   │   ├── ii_v_insertion.py
│   │   ├── tritone_sub.py
│   │   ├── modal_interchange.py
│   │   └── blues_conversion.py
│   ├── teacher/
│   │   ├── decision.py       # ArrangementDecision dataclass (in core/types.py for now)
│   │   ├── annotator.py      # rule → rationale text (templates)
│   │   └── llm_teacher.py    # Qwen-based persona (Phase 6+)
│   └── render/
│       ├── musicxml.py
│       ├── pdf.py            # verovio
│       ├── midi.py
│       └── annotation_overlay.py
├── tests/
│   ├── fixtures/             # input scores (.gitignored if copyrighted)
│   ├── golden/               # normalized expected outputs, when needed
│   └── test_*.py
└── examples/
    └── output/               # generated sample outputs
```

---

## 5. Core Data Model

The `ArrangementDecision` is the engine's most important output beyond
notes themselves. Every meaningful choice produces one.

```python
class ArrangementDecision(BaseModel):
    measure: int                  # 1-indexed
    beat: float                   # 1.0-indexed within measure
    chord_before: str | None      # input chord symbol (Mode A: pre-reharm)
    chord_after: str              # output chord symbol
    voicing_midi: list[int]       # concrete MIDI pitches
    rule_applied: str             # e.g. "shell_3_7", "tritone_sub"
    rationale: str                # human-readable explanation
    theory_tags: list[str]        # e.g. ["ii-V-I", "guide-tones"]
    level: int
    practice_tips: list[str]
```

The annotator emits these as **structured data first**, then a templated
English string. When the LLM teacher comes online, it consumes the same
structured data and re-renders the explanation in a persona's voice.

---

## 6. Phase Plan

### ✅ Phase 0 — Bootstrap (DONE, Day 1)

- Repo skeleton, pyproject, MIT license, .gitignore
- Core types: `PerformanceMode`, `GenreMode`, `Style`, `Level`,
  `ArrangementDecision`, `AnalysisResult`, `ArrangementResult`
- `analysis/key.py`: key/tempo/time-sig/chord-summary extraction
- `voicings/shell.py`: `RootOnly`, `Shell37`
- `arranger/solo.py`: Level 1 + Level 2 solo arranger
- CLI: `bluesify arrange` and `bluesify analyze`
- Smoke test passes end-to-end: synthesized 8-bar ii-V-i fragment →
  Level 1 root bass → Level 2 shell voicing with correct voice leading
- Outputs: `.musicxml`, `.mid`, `.annotations.json`

**Validated behaviors:**
- Cm7b5 → MIDI [51, 58] = Eb3 + Bb3 (b3, b7) ✓
- F7 → MIDI [57, 63] = A3 + Eb4 (M3, b7) ✓
- Half-step voice leading between guide tones emerges automatically ✓

**Gotchas captured:**
- music21 flat notation is `-` not `b` (`B-maj7`, not `Bbmaj7`).
  The input normalizer accepts common jazz spellings before analysis/arranging.
- Mutating `ChordSymbol.offset` corrupts measure durations.
  Use an external `dict[id(cs), float]` for absolute-offset caching.

### ✅ Phase 1 — Solo Mode End-to-End (DONE, current sprint)

**Goal:** All 5 levels working for a copyright-safe lead sheet, solo piano,
jazz ballad. Use a synthesized/public-domain fixture for committed tests and
demos; Autumn Leaves may be used only as a private manual test file.

| Day | Task |
|-----|------|
| 2 | ✅ Create a copyright-safe canonical MusicXML fixture. Optionally test privately with an untracked Autumn Leaves file. |
| 2 | ✅ Add chord-symbol input normalizer (`Bb` → `B-`, `Δ` → `maj7`, etc.) |
| 3 | ✅ **Level 3: walking bass generator.** Quarter-note line: root → approach (chromatic or scalar) → next chord's root. Must handle ii-V and longer durations on one chord. |
| 4 | ✅ **Verovio rendering.** Two-staff score with chord symbols above. SVG output is enabled when the `render` extra is installed; PDF is attempted when supported by the installed binding. |
| 5 | ✅ **Level 4: block chords / locked hands.** RH melody doubled with chord tones below, LH walking continues. |
| 6 | ✅ **Level 5: tensions, fills, intro/outro.** Tensions added to block voicings, with simple 2-bar intro and outro frames. |
| 7 | ✅ Semantic tests for all 5 levels. README updated for the playable web/CLI flow. |

**Exit criteria:** A single `bluesify arrange tests/fixtures/canonical_leadsheet.musicxml
--level N` (N=1..5) produces a clean PDF + MIDI + annotations.json. A private
Autumn Leaves run can validate musical usefulness, but it is not required for
public CI.

### Phase 2 — Style Expansion (Solo) (~2 weeks)

- Style enum fully wired: `slow-blues`, `shuffle-blues`, `jazz-blues`,
  `jazz-swing`, `jazz-ballad`
- Per-style groove modules: `shuffle`, `swing_comping`, `stride`
- Rootless voicings (A-form: 3-5-7-9, B-form: 7-9-3-13)
- Drop2 voicings for RH block work
- Test on 2-3 more copyright-safe tunes. Verify public-domain status per
  target jurisdiction before committing any source score; avoid assuming
  standards such as Summertime are public domain.

### Phase 3 — Web UI (~2-3 weeks)

- FastAPI backend wrapping the engine
- Next.js + OSMD for browser score rendering
- Upload MusicXML, pick mode/style/level, preview + download
- Tone.js for in-browser MIDI playback
- Deploy to K3s with ArgoCD (`pia-` namespace decision: separate
  personal repo, so use a different namespace, e.g. `bluesify`)

### Phase 4 — Accompaniment Mode (~2 weeks)

- `arranger/accomp.py`: LH rootless + RH comping, no bass, no melody
- Register manager: keep voicings out of melody-instrument range (C4+)
- Comping rhythm patterns: Freddie Green 4-on-floor, anticipation,
  push/pull
- Output additionally writes a "lead instrument" stave with the melody
  for reference / play-along

### Phase 5 — Mode A: Reharmonization Engine (~3-4 weeks)

The hard part. Build incrementally:

1. `analysis/chord_function.py`: Roman numeral analysis, ii-V detection
2. `rules/diatonic_7ths.py`: triad → 7th chord (trivial, Level 1 of reharm)
3. `rules/secondary_dominants.py`: V/X insertion
4. `rules/ii_v_insertion.py`: ii-7 → V7 → I insertions
5. `rules/tritone_sub.py`: V7 → bII7
6. `rules/modal_interchange.py`: borrow from parallel modes
7. `rules/blues_conversion.py`: all majors → dom7, optional 12-bar reformat

Each rule:
- Takes a `ChordProgression` and returns a new one + decisions
- Validates against the melody (avoid-note check)
- Can be stacked at increasing "reharm intensity" levels

### Phase 6 — LLM Teacher Persona (ongoing, starts Phase 4-ish)

- `teacher/llm_teacher.py`: takes a list of `ArrangementDecision` +
  a persona spec → produces conversational explanations
- Local model: Qwen2.5-7B-Instruct on RTX 5080 (vLLM or llama.cpp)
- Persona templates: "patient teacher", "jazz veteran", "blues purist"
- Optional: practice session loop — user records playing, engine
  analyzes timing/notes, teacher gives feedback (Phase 7)

### Phase 7+ (future, not committed)

- **OMR**: Audiveris Docker integration + correction UI. Lowest priority
  because lead-sheet input covers 80% of value at 20% of complexity.
- **Audio recording analysis**: aubio / madmom for pitch/timing
  detection on user's practice recordings
- **Personalized curriculum**: track user progress, recommend next tune
  based on weaknesses

---

## 7. Open Decisions

- **Repo location**: GitHub (decided). Public from day one or private
  until Phase 1 exit? → currently leaning public. Keep copyrighted MusicXML
  out of the repo and avoid using it for reproducible tests or demos.
- **Verovio Python binding vs WASM in frontend**: defer to Phase 3.
- **Storage in production deploy**: MinIO for original scores + outputs;
  PostgreSQL for user progress (Phase 4+).
- **Auth**: skip until there are real users (post-Phase 4).

---

## 8. Non-Goals (explicitly)

- Performance evaluation of user's playing (Phase 7 maybe, not before).
- Real-time MIDI input → arrangement (interesting but scope creep).
- Mobile native app.
- Multi-instrument arrangements (guitar, horn section, etc.).
- Music notation engraving quality competing with Sibelius / Dorico.
  Verovio output is "practice-grade", not "publication-grade".

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| music21 quirks (offset bookkeeping, flat notation, etc.) burn time | Capture each gotcha in `docs/music21_notes.md`; build a thin internal wrapper |
| Walking bass / block-chord generation produces musically wrong output | Semantic tests with hand-verified expected pitches/rhythms; use normalized golden outputs only where stable; keep rule complexity low until each level is auditioned |
| Verovio rendering looks ugly | Verovio supports custom CSS/SVG; fallback to MuseScore CLI if needed |
| Copyright concerns on jazz standards | Commit only synthesized or verified public-domain fixtures; keep private standards untracked and out of CI/demo paths |
| LLM teacher hallucinates wrong theory | Constrain prompts to the structured `ArrangementDecision` data; fact-check rationale against the rule that fired |
| Scope explosion (Mode A × Mode B × Solo × Accomp × 5 levels × 5 styles = 250 combos) | Phase plan locks the order; each phase adds one orthogonal axis |

---

## 10. Definition of Done (Phase 1)

- [ ] `uv run bluesify arrange tests/fixtures/canonical_leadsheet.musicxml --level 5 --out ./out/`
      produces `.musicxml`, `.pdf`, `.mid`, `.annotations.json`
- [ ] All 5 levels are musically distinct and progressively harder
- [ ] Annotations include rationale + practice tips per measure
- [ ] PDF is readable and has annotation text per system
- [ ] Semantic tests pass for all 5 levels; any golden files are normalized before comparison
- [ ] README has a quickstart that works on a clean Arch Linux box
